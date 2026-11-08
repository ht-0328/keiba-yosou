"""地方の全頭の予想（predict の JSON）から、票の表を組むための馬の表（モデルごとの 1着・3着以内の確率と単勝オッズ）を作る。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

#: predict の JSON の列名。モデルごとの 3着以内の確率は列名がモデルの名前（LightGBM・CatBoost）。
_HORSE_NO = "馬番"
_WIN_ODDS = "単勝オッズ"
_P1, _P1_LGB, _P1_CAT = "1着になる確率", "1着になる確率（LightGBM）", "1着になる確率（CatBoost）"
_P3, _P3_LGB, _P3_CAT = "3着以内に入る確率", "LightGBM", "CatBoost"
_SOURCES: dict[str, str] = {"p1": _P1, "p1_lgb": _P1_LGB, "p1_cat": _P1_CAT, "p3": _P3, "p3_lgb": _P3_LGB, "p3_cat": _P3_CAT, "win_odds": _WIN_ODDS}


class ForecastHorses:
    """``of(forecast, race_id, race_date)`` は ``race_id``・``race_date``・``horse_no``・``popularity``（単勝オッズの順）・``win_odds``・``finish``（無い）・
    ``p1``・``p1_lgb``・``p1_cat``・``p3``・``p3_lgb``・``p3_cat`` の表。モデルごとの 1着の確率が無い古い JSON は ``ValueError``。"""

    def of(self, forecast: dict[str, Any], race_id: int, race_date: str) -> pd.DataFrame:
        table = pd.DataFrame(forecast["rows"], columns=forecast["columns"])
        missing = [name for name in (*_SOURCES.values(), _HORSE_NO) if name not in table.columns]
        if missing:
            raise ValueError(f"予想の結果に列がありません: {'・'.join(missing)}（モデルごとの 1着の確率を出す predict で作り直してください）")
        horses = pd.DataFrame({"race_id": race_id, "race_date": race_date, "horse_no": pd.to_numeric(table[_HORSE_NO], errors="coerce").astype(int)})
        for name, source in _SOURCES.items():
            horses[name] = pd.to_numeric(table[source], errors="coerce").astype(float)
        # 単勝オッズがまだ無い馬（速報の途中など）は人気も欠損値のままにする。そのレースは票の表を組むところで外れ、理由つきで点が無くなる
        horses["popularity"] = horses["win_odds"].rank(method="min").astype("Int64")
        horses["finish"] = np.nan
        return horses.sort_values("horse_no").reset_index(drop=True)
