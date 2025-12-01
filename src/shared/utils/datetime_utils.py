"""日時関連ユーティリティ"""

from datetime import datetime, timezone

import pytz

# 日本時間のタイムゾーン
JST = pytz.timezone("Asia/Tokyo")


def now_jst() -> datetime:
    """現在の日本時間を取得"""
    return datetime.now(JST)


def now_utc() -> datetime:
    """現在のUTC時間を取得"""
    return datetime.now(timezone.utc)


def to_jst(dt: datetime) -> datetime:
    """
    datetimeを日本時間に変換

    Args:
        dt: 変換対象のdatetime

    Returns:
        日本時間のdatetime
    """
    if dt.tzinfo is None:
        # タイムゾーン情報がない場合はUTCとして扱う
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(JST)


def to_utc(dt: datetime) -> datetime:
    """
    datetimeをUTCに変換

    Args:
        dt: 変換対象のdatetime

    Returns:
        UTCのdatetime
    """
    if dt.tzinfo is None:
        # タイムゾーン情報がない場合はJSTとして扱う
        dt = JST.localize(dt)

    return dt.astimezone(timezone.utc)


def format_duration(seconds: float) -> str:
    """
    秒数を読みやすい形式に変換

    Args:
        seconds: 秒数

    Returns:
        "1時間23分45秒" のような文字列
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}時間")
    if minutes > 0:
        parts.append(f"{minutes}分")
    if secs > 0 or not parts:
        parts.append(f"{secs}秒")

    return "".join(parts)
