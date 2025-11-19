"""スクレイピング機能のEnum定義"""
from enum import Enum


class PrefectureCode(str, Enum):
    """都道府県コード（JIS X 0401準拠）"""

    HOKKAIDO = "01"
    AOMORI = "02"
    IWATE = "03"
    MIYAGI = "04"
    AKITA = "05"
    YAMAGATA = "06"
    FUKUSHIMA = "07"
    IBARAKI = "08"
    TOCHIGI = "09"
    GUNMA = "10"
    SAITAMA = "11"
    CHIBA = "12"
    TOKYO = "13"
    KANAGAWA = "14"
    NIIGATA = "15"
    TOYAMA = "16"
    ISHIKAWA = "17"
    FUKUI = "18"
    YAMANASHI = "19"
    NAGANO = "20"
    GIFU = "21"
    SHIZUOKA = "22"
    AICHI = "23"
    MIE = "24"
    SHIGA = "25"
    KYOTO = "26"
    OSAKA = "27"
    HYOGO = "28"
    NARA = "29"
    WAKAYAMA = "30"
    TOTTORI = "31"
    SHIMANE = "32"
    OKAYAMA = "33"
    HIROSHIMA = "34"
    YAMAGUCHI = "35"
    TOKUSHIMA = "36"
    KAGAWA = "37"
    EHIME = "38"
    KOCHI = "39"
    FUKUOKA = "40"
    SAGA = "41"
    NAGASAKI = "42"
    KUMAMOTO = "43"
    OITA = "44"
    MIYAZAKI = "45"
    KAGOSHIMA = "46"
    OKINAWA = "47"

    @property
    def name_ja(self) -> str:
        """日本語の都道府県名を取得"""
        return PREFECTURE_NAMES[self]

    @property
    def name_en(self) -> str:
        """英語の都道府県名を取得（小文字）"""
        return PREFECTURE_NAMES_EN[self]

    @classmethod
    def from_code(cls, code: str) -> "PrefectureCode":
        """都道府県コードから取得"""
        try:
            return cls(code)
        except ValueError:
            raise ValueError(f"Invalid prefecture code: {code}")


# 都道府県名マッピング（日本語）
PREFECTURE_NAMES = {
    PrefectureCode.HOKKAIDO: "北海道",
    PrefectureCode.AOMORI: "青森県",
    PrefectureCode.IWATE: "岩手県",
    PrefectureCode.MIYAGI: "宮城県",
    PrefectureCode.AKITA: "秋田県",
    PrefectureCode.YAMAGATA: "山形県",
    PrefectureCode.FUKUSHIMA: "福島県",
    PrefectureCode.IBARAKI: "茨城県",
    PrefectureCode.TOCHIGI: "栃木県",
    PrefectureCode.GUNMA: "群馬県",
    PrefectureCode.SAITAMA: "埼玉県",
    PrefectureCode.CHIBA: "千葉県",
    PrefectureCode.TOKYO: "東京都",
    PrefectureCode.KANAGAWA: "神奈川県",
    PrefectureCode.NIIGATA: "新潟県",
    PrefectureCode.TOYAMA: "富山県",
    PrefectureCode.ISHIKAWA: "石川県",
    PrefectureCode.FUKUI: "福井県",
    PrefectureCode.YAMANASHI: "山梨県",
    PrefectureCode.NAGANO: "長野県",
    PrefectureCode.GIFU: "岐阜県",
    PrefectureCode.SHIZUOKA: "静岡県",
    PrefectureCode.AICHI: "愛知県",
    PrefectureCode.MIE: "三重県",
    PrefectureCode.SHIGA: "滋賀県",
    PrefectureCode.KYOTO: "京都府",
    PrefectureCode.OSAKA: "大阪府",
    PrefectureCode.HYOGO: "兵庫県",
    PrefectureCode.NARA: "奈良県",
    PrefectureCode.WAKAYAMA: "和歌山県",
    PrefectureCode.TOTTORI: "鳥取県",
    PrefectureCode.SHIMANE: "島根県",
    PrefectureCode.OKAYAMA: "岡山県",
    PrefectureCode.HIROSHIMA: "広島県",
    PrefectureCode.YAMAGUCHI: "山口県",
    PrefectureCode.TOKUSHIMA: "徳島県",
    PrefectureCode.KAGAWA: "香川県",
    PrefectureCode.EHIME: "愛媛県",
    PrefectureCode.KOCHI: "高知県",
    PrefectureCode.FUKUOKA: "福岡県",
    PrefectureCode.SAGA: "佐賀県",
    PrefectureCode.NAGASAKI: "長崎県",
    PrefectureCode.KUMAMOTO: "熊本県",
    PrefectureCode.OITA: "大分県",
    PrefectureCode.MIYAZAKI: "宮崎県",
    PrefectureCode.KAGOSHIMA: "鹿児島県",
    PrefectureCode.OKINAWA: "沖縄県",
}

# 都道府県名マッピング（英語・小文字）
PREFECTURE_NAMES_EN = {
    PrefectureCode.HOKKAIDO: "hokkaido",
    PrefectureCode.AOMORI: "aomori",
    PrefectureCode.IWATE: "iwate",
    PrefectureCode.MIYAGI: "miyagi",
    PrefectureCode.AKITA: "akita",
    PrefectureCode.YAMAGATA: "yamagata",
    PrefectureCode.FUKUSHIMA: "fukushima",
    PrefectureCode.IBARAKI: "ibaraki",
    PrefectureCode.TOCHIGI: "tochigi",
    PrefectureCode.GUNMA: "gunma",
    PrefectureCode.SAITAMA: "saitama",
    PrefectureCode.CHIBA: "chiba",
    PrefectureCode.TOKYO: "tokyo",
    PrefectureCode.KANAGAWA: "kanagawa",
    PrefectureCode.NIIGATA: "niigata",
    PrefectureCode.TOYAMA: "toyama",
    PrefectureCode.ISHIKAWA: "ishikawa",
    PrefectureCode.FUKUI: "fukui",
    PrefectureCode.YAMANASHI: "yamanashi",
    PrefectureCode.NAGANO: "nagano",
    PrefectureCode.GIFU: "gifu",
    PrefectureCode.SHIZUOKA: "shizuoka",
    PrefectureCode.AICHI: "aichi",
    PrefectureCode.MIE: "mie",
    PrefectureCode.SHIGA: "shiga",
    PrefectureCode.KYOTO: "kyoto",
    PrefectureCode.OSAKA: "osaka",
    PrefectureCode.HYOGO: "hyogo",
    PrefectureCode.NARA: "nara",
    PrefectureCode.WAKAYAMA: "wakayama",
    PrefectureCode.TOTTORI: "tottori",
    PrefectureCode.SHIMANE: "shimane",
    PrefectureCode.OKAYAMA: "okayama",
    PrefectureCode.HIROSHIMA: "hiroshima",
    PrefectureCode.YAMAGUCHI: "yamaguchi",
    PrefectureCode.TOKUSHIMA: "tokushima",
    PrefectureCode.KAGAWA: "kagawa",
    PrefectureCode.EHIME: "ehime",
    PrefectureCode.KOCHI: "kochi",
    PrefectureCode.FUKUOKA: "fukuoka",
    PrefectureCode.SAGA: "saga",
    PrefectureCode.NAGASAKI: "nagasaki",
    PrefectureCode.KUMAMOTO: "kumamoto",
    PrefectureCode.OITA: "oita",
    PrefectureCode.MIYAZAKI: "miyazaki",
    PrefectureCode.KAGOSHIMA: "kagoshima",
    PrefectureCode.OKINAWA: "okinawa",
}


class ScrapingStatus(str, Enum):
    """スクレイピングのステータス"""

    PENDING = "pending"  # 実行待ち
    RUNNING = "running"  # 実行中
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失敗
    PARTIAL = "partial"  # 部分的成功（一部エラーあり）
