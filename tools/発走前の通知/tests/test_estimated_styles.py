"""EstimatedStyles（直近3走の脚質の中央で推定脚質を出す）のテスト。過去の走は架空。"""

from __future__ import annotations

import pandas as pd

from 発走前の通知.estimated_styles import EstimatedStyles


def _past(rows: list[tuple[int, str, float | None, float | None]]) -> pd.DataFrame:
    """（馬番, 脚質の判定, 最初のコーナーの順位, 頭数）を新しい走から。"""
    return pd.DataFrame(rows, columns=["horse_no", "style_code", "corner", "field_size"])


def test_直近3走の中央_2走なら前寄り_1走ならその脚質_4走目からは見ない() -> None:
    past = _past([
        (1, "2", None, None), (1, "3", None, None), (1, "1", None, None), (1, "4", None, None),   # 先行・差し・逃げ → 先行
        (2, "4", None, None), (2, "3", None, None),                                             # 追込・差し → 差し
        (3, "4", None, None),                                                                   # 追込
    ])
    assert EstimatedStyles().of(past) == {1: "先行", 2: "差し", 3: "追込"}


def test_中央は判定の無い走を数えない() -> None:
    past = _past([(1, "", 1.0, 12.0), (1, "3", 5.0, 12.0)])
    assert EstimatedStyles().of(past) == {1: "差し"}


def test_地方は判定が無ければ_最初のコーナーの順位と頭数から作る() -> None:
    # 12頭立て: 1番手 逃げ、5番手まで（12 × 0.35 = 4.2 の切り上げ）先行、9番手まで（8.4 の切り上げ）差し、残り 追込
    styles = EstimatedStyles(from_corners=True)
    assert styles.of(_past([(1, "", 1.0, 12.0)])) == {1: "逃げ"}
    assert styles.of(_past([(1, "", 5.0, 12.0)])) == {1: "先行"}
    assert styles.of(_past([(1, "", 9.0, 12.0)])) == {1: "差し"}
    assert styles.of(_past([(1, "", 10.0, 12.0)])) == {1: "追込"}
    assert styles.of(_past([(1, "", 3.0, None)])) == {}   # 頭数が分からなければ数えない
