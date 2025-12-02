"""スクレイピング機能のドメインモデル"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .enums import PrefectureCode, ScrapingStatus


@dataclass
class Shop:
    """
    店舗情報（Firestore保存用）

    ユーザー指定の必須フィールド:
    - 店名、住所、電話番号
    - 営業時間、定休日
    - 詳細URL、ウェブサイト
    - 優待内容、紹介コメント
    - 駐車場
    - 緯度、経度
    """

    # ID
    shop_id: str

    # 都道府県情報
    prefecture_code: str
    prefecture_name: str

    # 店舗基本情報（必須）
    name: str  # 店名

    # 店舗詳細情報（Optional）
    address: Optional[str] = None  # 住所
    phone: Optional[str] = None  # 電話番号
    business_hours: Optional[str] = None  # 営業時間
    closed_days: Optional[str] = None  # 定休日
    detail_url: Optional[str] = None  # 詳細URL
    website: Optional[str] = None  # ウェブサイト
    benefits: Optional[str] = None  # 優待内容
    description: Optional[str] = None  # 紹介コメント
    parking: Optional[str] = None  # 駐車場

    # 位置情報（Geocoding後に設定）
    latitude: Optional[float] = None  # 緯度
    longitude: Optional[float] = None  # 経度
    geocoded_at: Optional[datetime] = None  # ジオコーディング日時

    # その他の情報（オプション）
    postal_code: Optional[str] = None  # 郵便番号
    category: Optional[str] = None  # カテゴリ
    genre: Optional[str] = None  # ジャンル

    # メタデータ
    scraped_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

    # 検索用キーワード（Firestore複合インデックス用）
    search_terms: list[str] = field(default_factory=list)

    # 都道府県固有の追加フィールド（JSON格納）
    extra_fields: dict[str, Any] = field(default_factory=dict)

    def to_firestore_dict(self) -> dict[str, Any]:
        """Firestore保存用の辞書に変換"""
        return {
            "shop_id": self.shop_id,
            "prefecture_code": self.prefecture_code,
            "prefecture_name": self.prefecture_name,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "business_hours": self.business_hours,
            "closed_days": self.closed_days,
            "detail_url": self.detail_url,
            "website": self.website,
            "benefits": self.benefits,
            "description": self.description,
            "parking": self.parking,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "geocoded_at": self.geocoded_at,
            "postal_code": self.postal_code,
            "category": self.category,
            "genre": self.genre,
            "scraped_at": self.scraped_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
            "search_terms": self.search_terms,
            "extra_fields": self.extra_fields,
        }

    @classmethod
    def from_firestore_dict(cls, data: dict[str, Any]) -> "Shop":
        """Firestoreのデータから店舗オブジェクトを生成"""
        return cls(
            shop_id=data["shop_id"],
            prefecture_code=data["prefecture_code"],
            prefecture_name=data["prefecture_name"],
            name=data["name"],
            address=data.get("address"),
            phone=data.get("phone"),
            business_hours=data.get("business_hours"),
            closed_days=data.get("closed_days"),
            detail_url=data.get("detail_url"),
            website=data.get("website"),
            benefits=data.get("benefits"),
            description=data.get("description"),
            parking=data.get("parking"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            geocoded_at=data.get("geocoded_at"),
            postal_code=data.get("postal_code"),
            category=data.get("category"),
            genre=data.get("genre"),
            scraped_at=data.get("scraped_at", datetime.now()),
            updated_at=data.get("updated_at", datetime.now()),
            is_active=data.get("is_active", True),
            search_terms=data.get("search_terms", []),
            extra_fields=data.get("extra_fields", {}),
        )

    def generate_search_terms(self) -> None:
        """検索用キーワードを生成"""
        terms = []

        if self.name:
            terms.append(self.name)

        if self.address:
            # 住所から市区町村を抽出
            for part in ["市", "区", "町", "村"]:
                if part in self.address:
                    idx = self.address.index(part)
                    terms.append(self.address[: idx + 1])

        if self.category:
            terms.append(self.category)

        if self.genre:
            terms.append(self.genre)

        self.search_terms = list(set(terms))  # 重複除去


@dataclass
class ScrapingResult:
    """スクレイピング実行結果"""

    run_id: str  # 実行ID（ユニーク）
    prefecture_code: str
    prefecture_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: ScrapingStatus = ScrapingStatus.PENDING
    total_shops: int = 0
    new_shops: int = 0
    updated_shops: int = 0
    geocoded_shops: int = 0
    geocoding_errors: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: Optional[float] = None

    def to_firestore_dict(self) -> dict[str, Any]:
        """Firestore保存用の辞書に変換"""
        return {
            "run_id": self.run_id,
            "prefecture_code": self.prefecture_code,
            "prefecture_name": self.prefecture_name,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status.value,
            "total_shops": self.total_shops,
            "new_shops": self.new_shops,
            "updated_shops": self.updated_shops,
            "geocoded_shops": self.geocoded_shops,
            "geocoding_errors": self.geocoding_errors,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class Prefecture:
    """都道府県情報"""

    code: PrefectureCode
    name: str
    name_en: str
    total_shops: int = 0
    last_scraped_at: Optional[datetime] = None
    is_active: bool = True

    @classmethod
    def from_code(cls, code: str) -> "Prefecture":
        """都道府県コードから生成"""
        pref_code = PrefectureCode.from_code(code)
        return cls(
            code=pref_code,
            name=pref_code.name_ja,
            name_en=pref_code.name_en,
        )
