"""ForecastHorses（predict の JSON → 票の表に渡す馬の表）のテスト。予想の値は架空。"""

from __future__ import annotations

import numpy as np
import pytest

from 地方の推奨買目.forecast_horses import ForecastHorses

COLUMNS = ["順位", "馬番", "馬名", "単勝オッズ", "オッズから見た3着以内率", "複勝的中の確率", "複勝の期待値", "1着になる確率",
           "1着になる確率（LightGBM）", "1着になる確率（CatBoost）", "単勝の期待値", "3着以内に入る確率", "LightGBM", "CatBoost"]
ROWS = [
    [1, 7, "イチバン", 3.0, 0.70, 0.78, 1.10, 0.35, 0.33, 0.37, 1.05, 0.78, 0.77, 0.79],
    [2, 4, "ニバン", 2.7, 0.75, 0.71, 0.95, 0.27, 0.25, 0.29, 0.74, 0.71, 0.72, 0.70],
    [3, 8, "サンバン", 5.4, 0.55, 0.60, 1.00, 0.15, 0.16, 0.14, 0.81, 0.60, 0.61, 0.59],
]


def test_列を付け替え_人気は単勝オッズの順_着順は無し():
    horses = ForecastHorses().of({"columns": COLUMNS, "rows": ROWS}, 2026110550170505, "2026-11-05")
    assert list(horses["horse_no"]) == [4, 7, 8]
    assert list(horses["popularity"]) == [1, 2, 3]
    assert list(horses["p1_lgb"]) == [0.25, 0.33, 0.16] and list(horses["p3_cat"]) == [0.70, 0.79, 0.59]
    assert horses["finish"].isna().all() and set(horses["race_id"]) == {2026110550170505} and set(horses["race_date"]) == {"2026-11-05"}
    assert np.isclose(horses["win_odds"].iloc[0], 2.7)


def test_モデルごとの1着の確率が無い古い結果は誤り():
    columns = [name for name in COLUMNS if "（" not in name]
    rows = [[value for value, name in zip(row, COLUMNS, strict=True) if "（" not in name] for row in ROWS]
    with pytest.raises(ValueError, match="1着になる確率（LightGBM）"):
        ForecastHorses().of({"columns": columns, "rows": rows}, 2026110550170505, "2026-11-05")
