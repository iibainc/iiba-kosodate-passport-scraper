"""基本的なテスト（CI動作確認用）"""

import pytest


def test_example_addition() -> None:
    """基本的な加算テスト"""
    assert 1 + 1 == 2


def test_example_string() -> None:
    """文字列テスト"""
    assert "hello" + " " + "world" == "hello world"


def test_example_list() -> None:
    """リストテスト"""
    test_list = [1, 2, 3]
    assert len(test_list) == 3
    assert 2 in test_list


@pytest.mark.parametrize(
    "input_value,expected",
    [
        (1, 2),
        (2, 4),
        (3, 6),
    ],
)
def test_example_parametrize(input_value: int, expected: int) -> None:
    """パラメトライズドテスト"""
    assert input_value * 2 == expected
