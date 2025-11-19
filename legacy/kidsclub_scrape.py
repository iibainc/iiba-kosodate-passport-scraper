import time
import csv
import re
import random
import argparse
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE = "https://www.kids.pref.ibaraki.jp"
LIST_URL_TMPL = BASE + "/kids/search_free/{page}/xs=_xiIg.b7z_riD/dt=2337,0/"
START_PAGE = 1
END_PAGE = 247  # inclusive
DEFAULT_OUT = "ibaraki_kidsclub_all.csv"

HDRS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Accept-Language": "ja,en;q=0.9",
}
TIMEOUT = 20
RETRY = 3

# --------- 汎用ユーティリティ ----------
def get(url, session=None):
    sess = session or requests
    for i in range(RETRY):
        try:
            r = sess.get(url, headers=HDRS, timeout=TIMEOUT)
            # サイトは Shift_JIS なので明示
            r.encoding = r.encoding or 'shift_jis'
            if 'shift_jis' not in (r.encoding or '').lower():
                # 念のため強制
                r.encoding = 'shift_jis'
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(1.5 + i)
    return None

def norm_text(s):
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()

def sleep_polite():
    time.sleep(1.0 + random.random()*0.8)

# --------- 検索フォーム -> セッション/トークン取得 ----------
def init_session_and_xs(keyword: str = ""):
    """検索フォームにアクセスし、POSTして結果用のセッショントークン(xs)を取得する。"""
    sess = requests.Session()
    seed_url = BASE + "/kids/search_free/xs=_xiIg.b7z_riD/dt=2337/"
    r = get(seed_url, session=sess)
    if not r:
        return None, None
    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.find("form")
    if not form:
        return sess, None
    action = form.get("action")
    inputs = {i.get("name"): i.get("value", "") for i in form.find_all("input") if i.get("name")}
    # キーワード入力欄（存在しない場合は無視）
    if "cdb_21695" in inputs:
        inputs["cdb_21695"] = keyword or ""
    try:
        pr = sess.post(action, data=inputs, headers=HDRS, timeout=TIMEOUT)
    except requests.RequestException:
        return sess, None
    pr.encoding = 'shift_jis'
    m = re.search(r"xs=(_[A-Za-z0-9]+)", pr.url)
    xs = m.group(1) if m else None
    return sess, xs

# --------- 一覧ページ -> 詳細リンク抽出 ----------
def extract_detail_links(list_html, list_url):
    # 依存最小化のため、標準のパーサを使用
    soup = BeautifulSoup(list_html, "html.parser")

    candidates = []
    for a in soup.select("a"):
        href = a.get("href", "")
        if not href:
            continue
        full = urljoin(list_url, href)
        # 同一ドメインのみ
        if urlparse(full).netloc and urlparse(full).netloc != urlparse(BASE).netloc:
            continue
        # 検索結果の「店舗詳細」リンクは dt=2339,<ID> 形式
        if re.search(r"/kids/.*/dt=2339,\d+/", full):
            candidates.append(full)

    # 重複除去
    links = []
    seen = set()
    for u in candidates:
        if u not in seen:
            seen.add(u)
            links.append(u)
    return links

# --------- 詳細ページ -> データ抽出 ----------
def parse_detail(html, url):
    soup = BeautifulSoup(html, "html.parser")
    data = {}

    # 店名: <h1> や見出し系から
    # 店名候補: h1/h2/h4 だが、汎用タイトルは除外
    generic_titles = ["協賛店検索", "市町村を複数選択", "いばらきKids Club", "いばらき子育て家庭優待制度"]

    # まずh4を優先的に探す（詳細ページでは通常h4に店名がある）
    for sel in ["h4", "h1", "h2", ".title", ".page-title", ".shop-name"]:
        n = soup.select_one(sel)
        if n:
            t = norm_text(n.get_text())
            if t and all(g not in t for g in generic_titles):
                data["店名"] = t
                break

    # ラベル:値 が table(th/td) で並んでいる場合
    for table in soup.select("table"):
        rows = table.select("tr")
        for tr in rows:
            th = tr.find("th")
            td = tr.find("td")
            if th and td:
                key = norm_text(th.get_text())
                val = norm_text(td.get_text())
                if key:
                    data[key] = val

    # ラベル:値 が dl(dt/dd) で並んでいる場合
    for dl in soup.select("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        if len(dts) == len(dds) and len(dts) > 0:
            for dt, dd in zip(dts, dds):
                key = norm_text(dt.get_text())
                val = norm_text(dd.get_text())
                if key:
                    data[key] = val

    # 店名の補完（テーブル/ラベル由来の代表名を正規化）
    if not data.get("店名"):
        name_keys = [
            "店舗名", "協賛店名", "施設名", "施設・店舗名", "事業者名",
            "名称", "名称（屋号）", "屋号", "商号", "会社名", "店舗・事業所名"
        ]
        for k in name_keys:
            v = data.get(k)
            if v:
                data["店名"] = v
                break
    # 最後の手段として<title>から推定（区切り記号「｜」の手前など）
    if not data.get("店名") and soup.title:
        t = norm_text(soup.title.get_text())
        guessed = t.split("｜")[0] if "｜" in t else t.split("|")[0]
        if guessed and all(x not in guessed for x in ["協賛店検索", "市町村を複数選択", "いばらきKids Club", "いばらき子育て家庭優待制度"]):
            data["店名"] = guessed

    # 住所・電話が単独で置かれている場合の補完（よくある日本語キー名も併記）
    text_all = norm_text(soup.get_text(" "))
    if "住所" not in data:
        m = re.search(r"(〒?\d{3}-\d{4}[^ \n　]*)", text_all)
        # ざっくり郵便番号+続きの塊
        if m:
            data["住所(推定)"] = m.group(1)
    if not any(k in data for k in ["電話番号", "TEL", "Tel", "電話"]):
        m = re.search(r"(?:TEL|Tel|電話)\s*[:：]?\s*(0\d{1,4}-\d{1,4}-\d{3,4})", text_all)
        if m:
            data["電話番号(推定)"] = m.group(1)

    # ページURLを付与
    data["詳細URL"] = url
    return data

def main(start=START_PAGE, end=END_PAGE, out=DEFAULT_OUT):
    all_rows = []
    seen_detail = set()

    # 検索フォームを叩いてセッショントークン(xs)を取得
    sess, xs = init_session_and_xs()
    if not sess or not xs:
        raise SystemExit("[ERROR] セッション/トークン取得に失敗しました。サイト構造が変わった可能性があります。")

    def build_list_url(page: int) -> str:
        # ページ付きの一覧は dt=2337,0 の形式で出る
        return f"{BASE}/kids/search_free/{page}/xs={xs}/dt=2337,0/"

    for page in tqdm(range(start, end + 1), desc="一覧巡回"):
        list_url = build_list_url(page)
        r = get(list_url, session=sess)
        if not r:
            print(f"[WARN] 一覧ページ取得失敗: {list_url}")
            continue
        links = extract_detail_links(r.text, list_url)
        sleep_polite()

        for detail_url in tqdm(links, leave=False, desc=f"詳細({page})"):
            if detail_url in seen_detail:
                continue
            seen_detail.add(detail_url)

            rr = get(detail_url, session=sess)
            if not rr:
                print(f"[WARN] 詳細取得失敗: {detail_url}")
                continue
            row = parse_detail(rr.text, detail_url)
            if not row.get("店名"):
                row["店名"] = ""
            all_rows.append(row)
            sleep_polite()

    # 列を安定化（よく使われそうなキーを先頭に）
    preferred = ["店名", "ジャンル", "カテゴリ", "郵便番号", "住所", "住所(推定)",
                 "電話番号", "TEL", "電話番号(推定)", "URL", "公式サイト", "営業時間",
                 "定休日", "支払方法", "子育て優待内容", "割引特典", "備考", "詳細URL"]
    keys = set()
    for r in all_rows:
        keys.update(r.keys())
    ordered = [k for k in preferred if k in keys] + sorted(k for k in keys if k not in preferred)

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=ordered, extrasaction="ignore")
        w.writeheader()
        for r in all_rows:
            w.writerow(r)

    print(f"OK: {len(all_rows)}件を書き出しました -> {out}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ibaraki Kids Club scraper")
    parser.add_argument("--start", type=int, default=START_PAGE, help="開始ページ (デフォルト: 1)")
    parser.add_argument("--end", type=int, default=END_PAGE, help="終了ページ (デフォルト: 247)")
    parser.add_argument("--out", type=str, default=DEFAULT_OUT, help=f"出力CSVファイル名 (デフォルト: {DEFAULT_OUT})")
    args = parser.parse_args()

    if args.start < 1 or args.end < args.start:
        raise SystemExit("[ERROR] ページ範囲が不正です。--start と --end を見直してください。")

    main(start=args.start, end=args.end, out=args.out)
