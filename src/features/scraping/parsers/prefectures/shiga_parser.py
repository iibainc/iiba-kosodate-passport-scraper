"""滋賀県の店舗情報パーサー"""

import re
from datetime import datetime
from typing import Any, Optional

from bs4 import BeautifulSoup, Tag

from .....shared.logging.config import get_logger
from .....shared.utils.text import extract_phone_number, extract_postal_code, normalize_text
from ...domain.models import Shop
from ..base import BaseParser

logger = get_logger(__name__)


class ShigaParser(BaseParser):
    """滋賀県の店舗情報パーサー"""

    GENERIC_TITLES = [
        "協賛店を探す", "淡海子育て応援団", "ハグナビTOP", "協賛店検索", 
        "詳細情報", "店舗情報", "検索結果", "トップページ", "ランキング", 
        "新着情報", "おすすめ店舗", "近隣の店舗"
    ]

    # 詳細情報テーブルに含まれているはずのキーワード（これで本物のテーブルか判定する）
    DETAIL_KEYWORDS = ["住所", "所在地", "電話番号", "TEL", "営業時間", "定休日"]

    def __init__(self, prefecture_code: str = "25", prefecture_name: str = "滋賀県") -> None:
        super().__init__()
        self.prefecture_code = prefecture_code
        self.prefecture_name = prefecture_name

    def parse(self, html: str, url: str, shop_id: str) -> Optional[Shop]:
        """HTMLをパースして店舗情報を抽出"""
        try:
            soup = self.create_soup(html)
            
            # メインコンテンツエリアを特定
            main_content = self._get_main_content(soup)
            search_area = main_content if main_content else soup

            data: dict[str, Any] = {}

            # -------------------------------------------------------
            # 【修正箇所】テーブルを厳選して読み込む
            # すべてのtableを読むのではなく、詳細情報っぽいものだけを拾う
            # -------------------------------------------------------
            table_data = self._extract_table_data_selective(search_area)
            data.update(table_data)

            # DL（定義リスト）も同様に抽出
            dl_data = self.extract_dl_data(search_area, "dl")
            data.update(dl_data)

            # 店名を決定
            shop_name = self._resolve_shop_name(search_area, data, soup)
            
            if not shop_name:
                logger.warning(f"Shop name not found: {url}")
                return None

            shop = self._build_shop(shop_id, shop_name, data, url, soup)
            logger.debug(f"Parsed shop: {shop.name} ({shop.shop_id})")
            return shop

        except Exception as e:
            logger.error(f"Failed to parse shop detail: {url} - {e}")
            return None

    def _extract_table_data_selective(self, soup: Tag) -> dict[str, str]:
        """
        ページ内の複数のテーブルの中から、店舗詳細情報が含まれるテーブルのみを抽出する。
        下部にある「一覧リスト」などのテーブルによる上書きを防ぐ。
        """
        data = {}
        tables = soup.select("table")
        
        found_detail = False

        for table in tables:
            # テーブル内のテキストを全取得して、キーワードが含まれているかチェック
            table_text = table.get_text()
            
            # 「住所」や「電話番号」などのキーワードが含まれていなければ、それは詳細テーブルではない（リストなど）とみなす
            # 滋賀県のサイトは詳細テーブルに必ず「住所」などのヘッダーがあるはず
            has_keyword = any(keyword in table_text for keyword in self.DETAIL_KEYWORDS)
            
            if not has_keyword:
                continue

            # ここでテーブルをパースする（既存のロジックを使用）
            # BaseParserのextract_table_dataはsoup全体から探すので、ここではtableタグ単体を渡して処理させる
            rows = table.select("tr")
            for row in rows:
                th = row.select_one("th")
                td = row.select_one("td")
                if th and td:
                    key = normalize_text(th.get_text())
                    value = normalize_text(td.get_text())
                    if key and value:
                        data[key] = value
            
            # キーワード入りのテーブルが見つかったら、それが「メイン情報」なのでフラグを立てる
            # もしページ内に詳細テーブルが複数に分かれている場合は continue で良いが、
            # 下部にリストがある場合はここで break したい。
            # 通常、詳細情報は上部にあるため、有効なデータが取れたらループを抜けるのが安全。
            if len(data) > 2: # 2項目以上取れたら詳細テーブルとみなす
                found_detail = True
                break 

        return data

    def _get_main_content(self, soup: BeautifulSoup) -> Optional[Tag]:
        """メインコンテンツエリアを特定"""
        candidates = ["#main", "#main_column", ".main_column", "#contents", ".contents", "article", ".detail_box"]
        for selector in candidates:
            element = soup.select_one(selector)
            if element and len(element.get_text(strip=True)) > 20:
                return element
        return None

    def _resolve_shop_name(self, container: Tag, data: dict[str, Any], soup: BeautifulSoup) -> Optional[str]:
        """店名を決定"""
        # 1. データから
        name_keys = ["店舗名", "協賛店名", "施設名", "名称", "屋号", "商号", "会社名"]
        for key in name_keys:
            if key in data and data[key]:
                candidate = normalize_text(data[key])
                if self._is_valid_name(candidate):
                    return candidate

        # 2. HTMLタグから
        for selector in [".shop_name", ".detail_title", ".shop_detail_name", "h2", "h1", "h3"]:
            elements = container.select(selector)
            for element in elements:
                if self._is_inside_sidebar(element):
                    continue
                text = normalize_text(element.get_text())
                if self._is_valid_name(text):
                    return text

        # 3. Titleタグから
        if soup.title:
            return self._extract_from_title(soup.title.get_text())
        return None

    def _is_inside_sidebar(self, element: Tag) -> bool:
        """サイドバー判定"""
        for parent in element.parents:
            if parent.name == 'body': break
            classes = parent.get('class', [])
            ids = parent.get('id', '')
            banned = ['side', 'sub', 'recommend', 'ranking', 'banner', 'nav', 'menu', 'footer', 'list'] # 'list'を追加
            
            if classes:
                for cls in classes:
                    if any(w in cls.lower() for w in banned): return True
            if isinstance(ids, str) and any(w in ids.lower() for w in banned): return True
        return False

    def _extract_from_title(self, title_text: str) -> Optional[str]:
        text = normalize_text(title_text)
        separators = ["｜", "|", " - ", "："]
        for sep in separators:
            if sep in text: text = text.split(sep)[0]; break
        return text if self._is_valid_name(text) else None

    def _is_valid_name(self, text: str) -> bool:
        if not text: return False
        for generic in self.GENERIC_TITLES:
            if generic == text: return False
            if generic in text and len(text) < len(generic) + 5: return False
        return True

    def _build_shop(self, shop_id: str, shop_name: str, data: dict[str, str], url: str, soup: BeautifulSoup) -> Shop:
        # 住所等の抽出ロジック（変更なし）
        address = self._extract_address(data, soup)
        phone = self._extract_phone(data, soup)
        postal_code = self._extract_postal_code(address)

        shop = Shop(
            shop_id=shop_id,
            prefecture_code=self.prefecture_code,
            prefecture_name=self.prefecture_name,
            name=shop_name,
            address=address,
            phone=phone,
            postal_code=postal_code,
            business_hours=self._extract_field(data, ["営業時間", "利用時間", "開館時間"]),
            closed_days=self._extract_field(data, ["定休日", "休館日", "休日"]),
            detail_url=url,
            website=self._extract_field(data, ["URL", "ホームページ", "公式サイト"]),
            benefits=self._extract_field(data, ["特典内容", "優待内容", "サービス内容", "特典"]),
            description=self._extract_field(data, ["紹介コメント", "PR", "備考"]),
            parking=self._extract_field(data, ["駐車場"]),
            category=self._extract_field(data, ["業種", "ジャンル"]),
            genre=self._extract_field(data, ["小分類"]),
            scraped_at=datetime.now(),
            updated_at=datetime.now(),
            is_active=True,
        )

        excluded_keys = {
            "店舗名", "名称", "住所", "所在地", "電話番号", "TEL", 
            "営業時間", "定休日", "URL", "特典内容", "優待内容", "駐車場", "業種"
        }
        for key, value in data.items():
            if key not in excluded_keys and value:
                shop.extra_fields[key] = value

        return shop

    def _extract_address(self, data: dict[str, str], soup: BeautifulSoup) -> Optional[str]:
        address = self._extract_field(data, ["住所", "所在地"])
        if address: return address
        text_all = normalize_text(soup.get_text(" "))
        match = re.search(r"(滋賀県[^ \n　]*)", text_all)
        return match.group(1) if match else None

    def _extract_phone(self, data: dict[str, str], soup: BeautifulSoup) -> Optional[str]:
        phone = self._extract_field(data, ["電話番号", "TEL"])
        if phone: return phone
        text_all = normalize_text(soup.get_text(" "))
        return extract_phone_number(text_all)

    def _extract_postal_code(self, address: Optional[str]) -> Optional[str]:
        return extract_postal_code(address) if address else None

    def _extract_field(self, data: dict[str, str], keys: list[str]) -> Optional[str]:
        for key in keys:
            if key in data and data[key]: return data[key]
        return None