"""詳しく見る日のレースの予測用データ（3着以内と1着）を、今のモデルの予測の流れと足す材料から作る。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import duckdb
import numpy as np
import pandas as pd

from yosou.shared.dataset.column_names import WIN_ODDS
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.odds import MarketWinProbability
from yosou.shared.workflow import FormAptitudePrediction
from yosou.shared.workflow.segmented_prediction import AVERAGE

from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_data import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, LongshotData

from ..scenario_forecast.scenario_materials import FORECAST

#: 足す材料の予想のペース・位置の確率が無い日（年ごとの予測の後）に、今のモデルの予測の流れが作った展開の予想の列で埋める対応。
_FILLED_FROM: dict[str, str] = {
    "位置_先頭": "展開の予想_先頭の確率", "位置_前": "展開の予想_先団の確率", "位置_中": "展開の予想_中団の確率", "位置_後ろ": "展開の予想_後方の確率",
}
_HIGH, _SLOW = "展開の予想_ハイペースの確率", "展開の予想_スローペースの確率"
_MARKET_TOP3 = "オッズから見た3着以内率"


@dataclass(frozen=True)
class FocusDayData:
    """``prediction`` は今のモデルの予測の流れ、``materials`` は足す材料の表、``columns`` は（目的変数 → 学習の列の並び）、
    ``categorical`` は（目的変数 → カテゴリ特徴量）。``build`` は（目的変数 → 予測用データ）と、今のモデルの確率の表
    （レースID・馬番・単勝オッズ・3着以内・1着の確率）を返す。人気は、元DB にある最新の単勝オッズ（締め切り前）の順。"""

    prediction: FormAptitudePrediction
    materials: pd.DataFrame
    columns: dict[str, Sequence[str]]
    categorical: dict[str, tuple[str, ...]]

    def build(self, con: duckdb.DuckDBPyConnection, race_ids: Sequence[str], timing: PredictionTiming) -> tuple[dict[str, LongshotData], pd.DataFrame]:
        workflow = self.prediction.workflow(con, timing)
        parts = [self._race(workflow, race_id, timing) for race_id in race_ids]
        data = {target: self._concat([part[target] for part, _ in parts], target) for target in ("top3", "win")}
        return data, pd.concat([table for _, table in parts], ignore_index=True)

    def _race(self, workflow, race_id: str, timing: PredictionTiming) -> tuple[dict[str, LongshotData], pd.DataFrame]:
        prepared = workflow._prepared(race_id, timing, None)  # 今のモデルと同じ予測用データ（3着以内と1着）を一度に作る
        win = prepared.win_data
        ids = win.ids.reset_index(drop=True).astype({RACE_ID: str})
        odds = win.market[WIN_ODDS].reset_index(drop=True).astype(float)
        popularity = odds.rank(method="first")
        market_win = MarketWinProbability().of(ids[RACE_ID], odds).reset_index(drop=True)
        market_top3 = prepared.top3_data.market[_MARKET_TOP3].reset_index(drop=True).astype(float)
        result = {}
        for target, source, market in (("top3", prepared.top3_data, market_top3), ("win", win, market_win)):
            features = self._features(source.features.reset_index(drop=True), ids, target)
            result[target] = LongshotData(ids[[RACE_ID, RACE_DATE, HORSE_ID, HORSE_NO]], features, pd.Series(np.zeros(len(ids), dtype=int)),
                                          source.baseline.values.reset_index(drop=True), popularity, market, self.categorical[target])
        current = ids[[RACE_ID, HORSE_NO]].assign(
            単勝オッズ=odds, 今のモデルの3着以内=prepared.predictor.predict(prepared.top3_data)[AVERAGE].to_numpy(),
            今のモデルの1着=prepared.win_predictor.predict(win)[AVERAGE].to_numpy())
        return result, current

    def _features(self, base: pd.DataFrame, ids: pd.DataFrame, target: str) -> pd.DataFrame:
        keys = ids[[RACE_ID, HORSE_NO]].rename(columns={RACE_ID: "race_id", HORSE_NO: "horse_no"}).astype({"horse_no": float})
        added = keys.merge(self.materials, on=["race_id", "horse_no"], how="left").drop(columns=["race_id", "horse_no"])
        added = added.drop(columns=[column for column in added.columns if column in base.columns])
        features = pd.concat([base, added.reset_index(drop=True)], axis=1)
        for mine, theirs in _FILLED_FROM.items():
            if theirs in features:
                features[mine] = features[mine].fillna(features[theirs])
        if _HIGH in features and _SLOW in features:
            features[FORECAST[2]] = features[FORECAST[2]].fillna(features[_HIGH])
            features[FORECAST[0]] = features[FORECAST[0]].fillna(features[_SLOW])
            features[FORECAST[1]] = features[FORECAST[1]].fillna(1 - features[_HIGH] - features[_SLOW])
        return features.reindex(columns=list(self.columns[target]))

    def _concat(self, parts: list[LongshotData], target: str) -> LongshotData:
        return LongshotData(*(pd.concat([getattr(part, name) for part in parts], ignore_index=True)
                              for name in ("ids", "features", "label", "baseline", "popularity", "market")), self.categorical[target])
