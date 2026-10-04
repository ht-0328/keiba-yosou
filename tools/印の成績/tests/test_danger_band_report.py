"""DangerBandReport（人気帯ごとの、危険度が線以上の馬の成績の表）のテスト。値は架空。"""

from __future__ import annotations

import pandas as pd

from 印の成績.danger_band_report import DangerBandReport


def _row(fold: str, band: str | None, over: bool, finish: int, win: int, place: int) -> dict:
    return {"fold": fold, "favorite_band": band, "over_line": over, "finish": float(finish), "win_payout": win, "place_payout": place}


def test_人気帯ごとに線以上と線未満と全体を並べ回収率が全体を下回った区切りを数える() -> None:
    marked = pd.DataFrame([
        # 2〜3番人気: 区切り1 は線以上の馬が負け（全体より低い）、区切り2 は線以上の馬が勝つ（全体より高い）
        _row("区切り1", "2〜3番人気", True, 5, 0, 0), _row("区切り1", "2〜3番人気", False, 1, 400, 160),
        _row("区切り2", "2〜3番人気", True, 1, 500, 200), _row("区切り2", "2〜3番人気", False, 4, 0, 0),
        # 1番人気: 線以上の馬はいない。人気馬でない馬（favorite_band が空）は数えない
        _row("区切り1", "1番人気", False, 2, 0, 120), _row("区切り1", None, False, 1, 3000, 800),
    ])
    table = DangerBandReport().table(marked)
    rows = {(row[0], row[1]): row for row in table.rows}
    assert table.title.startswith("12.")
    assert ("4〜5番人気", "全体") not in rows  # 行の無い人気帯は出さない
    assert rows[("2〜3番人気", "線以上（危険）")][2:4] == ["2", "1-0-0-1"]
    assert rows[("2〜3番人気", "線以上（危険）")][-2:] == ["1 / 2", "1 / 2"]
    assert rows[("2〜3番人気", "全体")][2] == "4"
    assert rows[("1番人気", "線以上（危険）")][2] == "0" and rows[("1番人気", "線以上（危険）")][-2:] == ["0 / 0", "0 / 0"]
