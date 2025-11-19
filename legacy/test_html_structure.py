import requests
from bs4 import BeautifulSoup
import time

# kidsclub_scrape.pyから関数をインポート
from kidsclub_scrape import init_session_and_xs, get, BASE

# セッションを初期化
sess, xs = init_session_and_xs()
if not sess or not xs:
    print("セッション取得に失敗しました")
    exit(1)

# 最初のページを取得
list_url = f"{BASE}/kids/search_free/1/xs={xs}/dt=2337,0/"
r = get(list_url, session=sess)
if not r:
    print("一覧ページの取得に失敗しました")
    exit(1)

# 詳細リンクを抽出
soup = BeautifulSoup(r.text, "html.parser")
links = []
for a in soup.select("a"):
    href = a.get("href", "")
    if "/kids/" in href and "dt=2339," in href:
        from urllib.parse import urljoin
        full_url = urljoin(list_url, href)
        links.append(full_url)
        break  # 最初の1つだけ

if not links:
    print("詳細リンクが見つかりませんでした")
    exit(1)

# 最初の詳細ページを取得
detail_url = links[0]
print(f"詳細URL: {detail_url}")
time.sleep(1)
rr = get(detail_url, session=sess)
if not rr:
    print("詳細ページの取得に失敗しました")
    exit(1)

# HTMLの構造を確認
detail_soup = BeautifulSoup(rr.text, "html.parser")

# ユーザーが指定したセレクタを試す
print("\n===== セレクタ #contents > div:nth-child(4) > h4 =====")
target = detail_soup.select("#contents > div:nth-child(4) > h4")
if target:
    for elem in target:
        print(f"見つかりました: {elem.get_text().strip()}")
else:
    print("このセレクタでは見つかりませんでした")

# 代替として、すべてのh4を探す
print("\n===== すべてのh4タグ =====")
all_h4 = detail_soup.select("h4")
for i, h4 in enumerate(all_h4):
    print(f"h4[{i}]: {h4.get_text().strip()}")

# 現在のロジック(h1)を試す
print("\n===== 現在のロジック(h1) =====")
h1 = detail_soup.select_one("h1")
if h1:
    print(f"h1: {h1.get_text().strip()}")
else:
    print("h1が見つかりませんでした")

# #contentsの中身を確認
print("\n===== #contents内の構造 =====")
contents = detail_soup.select_one("#contents")
if contents:
    divs = contents.find_all("div", recursive=False)
    print(f"#contents直下のdiv数: {len(divs)}")
    for i, div in enumerate(divs):
        h4s = div.find_all("h4", recursive=False)
        if h4s:
            print(f"  div[{i}]にh4が{len(h4s)}個あります:")
            for h4 in h4s:
                print(f"    -> {h4.get_text().strip()}")
