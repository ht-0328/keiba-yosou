"""区切りごとに、そのモデルの検証期間の馬ごとの確率と市場の見立てを集める（区切りごとの重みの推定に使う）。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from yosou.shared.feature.odds import TOP3_RATE, WIN_RATE

from 印の成績.backtest_marker import BacktestMarker
from 印の成績.prediction_file import VALID, PredictionFile
from 印の成績.race_results import RaceResults

from .backtest_marking import FORM, WIN


class ValidationHorses:
    """当日の予想の予測（``predictions`` の下の3着以内と1着）の、区切りごとの検証期間の行（その区切りのモデルが、テストの直前の半年を予測したもの）から、
    1頭1行の表を区切りごとに作る。列は ``race_id``・``race_date``・``horse_no``・``probability``・``win_probability``・``market_win``・
    ``market_top3``・``fold``（と、印・期待度は使わないので空の ``mark``・``expectation``）。

    検証期間のレースは前の区切りのテスト期間と同じだが、予測したモデルが違う（この区切りのモデル）ので、区切りごとに別の表にする。
    組の確率の重みを、テストを予測するのと同じモデルの確率で推定するために使う（docs/05）。
    """

    def __init__(self, predictions: Path) -> None:
        self._predictions = Path(predictions)

    def by_fold(self, con: duckdb.DuckDBPyConnection) -> dict[str, pd.DataFrame]:
        top3 = self._valid(FORM)
        win = self._valid(WIN)[["race_id", "horse_id", "fold", "probability"]].rename(columns={"probability": "win_probability"})
        places = BacktestMarker(None).places(RaceResults().read(con, top3["race_id"]))
        market = places[["race_id", "horse_id", "horse_no", WIN_RATE, TOP3_RATE]].rename(
            columns={WIN_RATE: "market_win", TOP3_RATE: "market_top3"})
        rows = top3[["race_id", "race_date", "horse_id", "probability", "fold"]].merge(win, on=["race_id", "horse_id", "fold"], how="inner")
        rows = rows.merge(market, on=["race_id", "horse_id"], how="inner").assign(mark="－", expectation="")
        return {fold: group.reset_index(drop=True) for fold, group in rows.groupby("fold", sort=False)}

    def _valid(self, name: str) -> pd.DataFrame:
        rows = PredictionFile(str(self._predictions / name)).load()
        rows = rows[rows["period"] == VALID]
        return rows.assign(race_id=rows["race_id"].astype(str), horse_id=rows["horse_id"].astype(str))
