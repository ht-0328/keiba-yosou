"""裏が当たったか（``reverse_hit``）と、1行 = 1レースの表（``race_rows``）を、架空の印の表で確かめる。"""

from __future__ import annotations

import pandas as pd

from 裏目を買うかの予想.fit import race_rows, reverse_hit

#: 6頭のレースの印（馬番 → 印）。相手は ○1・▲5・☆6（☆ の複勝の期待値は線以上）。
_MARKS = {3: "◎", 1: "○", 5: "▲", 2: "△", 4: "△", 6: "☆"}


def _race(race_id: str, finish: dict[int, int], star_value: float = 1.30) -> pd.DataFrame:
    order = sorted(_MARKS)
    return pd.DataFrame({
        "race_id": race_id, "race_date": pd.Timestamp("2025-01-05"), "horse_no": order, "mark": [_MARKS[no] for no in order],
        "place_value": [star_value if no == 6 else 1.0 for no in order], "finish": [finish.get(no, 6) for no in order],
        "probability": 0.5, "market_top3": 0.5, "win_probability": 1 / 6, "market_win": 1 / 6, "win_odds": 6.0, "win_value": 1.0,
        "popularity": order,
    })


def test_1着が相手で本命が2着か3着なら裏が当たり() -> None:
    assert reverse_hit(_race("R", {1: 1, 3: 2})) == 1
    assert reverse_hit(_race("R", {6: 1, 2: 2, 3: 3})) == 1


def test_本命が1着か4着以下_1着が相手でなければ外れ() -> None:
    assert reverse_hit(_race("R", {3: 1, 1: 2})) == 0
    assert reverse_hit(_race("R", {1: 1, 2: 2, 4: 3})) == 0
    assert reverse_hit(_race("R", {2: 1, 3: 2})) == 0   # △ は相手でない
    assert reverse_hit(_race("R", {6: 1, 3: 2}, star_value=1.0)) == 0   # 線に届かない ☆ は相手でない


def test_1行1レースにまとめ_結果の無いレースは除く() -> None:
    blank = _race("C", {}).assign(finish=float("nan"))
    rows = race_rows(pd.concat([_race("A", {1: 1, 3: 2}), _race("B", {3: 1}), blank]))
    assert list(rows["race_id"]) == ["A", "B"] and list(rows["y"]) == [1, 0]
    assert rows["day"].iloc[0] == "2025-01-05" and rows["features"].iloc[0]["相手の数"] == 3
