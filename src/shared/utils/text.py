"""テキスト処理ユーティリティ"""

import re
from typing import Optional


def normalize_text(text: Optional[str]) -> Optional[str]:
    """
    テキストを正規化

    - 前後の空白を除去
    - 連続する空白を1つに
    - 全角スペースを半角スペースに変換
    """
    if not text:
        return None

    # 全角スペースを半角に変換
    text = text.replace("\u3000", " ")

    # 連続する空白を1つに
    text = re.sub(r"\s+", " ", text)

    # 前後の空白を除去
    text = text.strip()

    return text if text else None


def extract_phone_number(text: str) -> Optional[str]:
    """
    テキストから電話番号を抽出

    対応フォーマット:
    - 03-1234-5678
    - 0312345678
    - (03)1234-5678
    """
    if not text:
        return None

    # 電話番号パターン（ハイフンあり・なし）
    patterns = [
        r"\d{2,4}[-\(]?\d{2,4}[-\)]?\d{3,4}",  # 一般的なパターン
        r"\d{10,11}",  # ハイフンなし
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group()

    return None


def extract_postal_code(text: str) -> Optional[str]:
    """
    テキストから郵便番号を抽出

    フォーマット: 123-4567 or 1234567
    """
    if not text:
        return None

    # 郵便番号パターン
    match = re.search(r"\d{3}-?\d{4}", text)
    if match:
        postal = match.group()
        # ハイフンがない場合は追加
        if "-" not in postal:
            postal = f"{postal[:3]}-{postal[3:]}"
        return postal

    return None


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    テキストを指定長で切り詰め

    Args:
        text: 対象テキスト
        max_length: 最大文字数
        suffix: 切り詰め時の接尾辞

    Returns:
        切り詰められたテキスト
    """
    if not text or len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def remove_html_tags(text: str) -> str:
    """HTMLタグを除去"""
    if not text:
        return ""

    # HTMLタグを除去
    clean = re.sub(r"<[^>]+>", "", text)
    return normalize_text(clean) or ""
