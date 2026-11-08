"""詳しく見る日の流れ: 最後の区切りまでの全部の行で学び直し、その日の全レースを展開の型で混ぜて予想し、
荒れる前提の確率・中穴と大穴の組・人気馬の4着以下の確率・理由の文を付けた表を作る。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_data import HORSE_NO, RACE_ID, LongshotData
from 既存モデルの改善.analysis.windows.test_window import TestWindow

from ..scenario_forecast.scenario_materials import FORECAST, PACE
from ..scenario_forecast.scenario_predictor import ScenarioPredictor
from .material_groups import MaterialGroups
from .reason_writer import ReasonWriter

#: 最後に学ぶときの区切り（学習の表の最後の日 2026-10-12 までを学習と検証に使う）。
FINAL_WINDOW = TestWindow("最後", date(2026, 4, 13), date(2026, 10, 13), date(2026, 12, 31))
_REASON_COLUMNS = ("予想_スロー", "予想_平均", "予想_ハイ", "位置_前", "位置_後ろ", "ハンデ戦か", "トップとの差", "斤量の前走との差", "昇級か",
                   "先のレースの内の傾き", "馬番の位置")


@dataclass(frozen=True)
class FocusDayRunner:
    """``members`` は（目的変数 → （学んだ2つのモデル, 混ぜる重み））。3着以内の LightGBM は寄与を出せる（``ContributionLightGbm``）。
    ``table`` は1行 = 1頭の表（レースID・馬番・人気（締め切り前）・3着以内と1着の混ぜた確率・展開の型ごとの3着以内の確率・
    混ぜる重み・まとまりごとの寄与・理由の文）。"""

    members: dict[str, tuple[list, object]]

    def table(self, data: dict[str, LongshotData]) -> pd.DataFrame:
        top3, win = data["top3"], data["win"]
        frame = top3.ids.reset_index(drop=True).copy()
        frame["popularity"] = top3.popularity.to_numpy()
        for target, part in (("top3", top3), ("win", win)):
            members, weights = self.members[target]
            scenarios = [ScenarioPredictor(member, weights).by_scenario(part) for member in members]
            average = np.mean(np.stack(scenarios), axis=0)
            mixing = weights.of(part.features[list(FORECAST)])
            frame[f"p_{target}"] = (average * mixing).sum(axis=1)
            for index in range(3):
                frame[f"s_{target}_{index}"] = average[:, index]
                frame[f"w_{index}"] = mixing[:, index]
        frame["m_top3"], frame["m_win"] = top3.market.to_numpy(), win.market.to_numpy()
        groups = self._groups(top3)
        frame = pd.concat([frame, groups.reset_index(drop=True), top3.features[list(_REASON_COLUMNS)].reset_index(drop=True)], axis=1)
        frame["理由"] = frame.apply(ReasonWriter().write, axis=1)
        return frame

    def _groups(self, top3: LongshotData) -> pd.DataFrame:
        """3着以内の LightGBM の寄与を、まとまりごとに足す（展開の型は、予想のペースでいちばん確率の高い型に置いて出す）。"""
        lightgbm = self.members["top3"][0][0]
        features = top3.features.copy()
        if PACE in features:
            features[PACE] = features[list(FORECAST)].to_numpy(dtype=float).argmax(axis=1).astype(float)
        likely = LongshotData(top3.ids, features, top3.label, top3.baseline, top3.popularity, top3.market, top3.categorical)
        contributions = lightgbm.contributions(likely)
        grouping = MaterialGroups()
        return contributions.T.groupby([grouping.of(column) for column in contributions.columns]).sum().T

    @staticmethod
    def ranks(frame: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
        """レースの中の順位（混ぜた1着の確率・今のモデルの1着の確率）と、人気帯の中の荒れる前提の確率と順位を足す。"""
        merged = frame.merge(current, on=[RACE_ID, HORSE_NO], how="left")
        race = merged.groupby(RACE_ID)
        merged["順位（新しい予想の1着）"] = race["p_win"].rank(ascending=False, method="first")
        merged["順位（今のモデルの1着）"] = race["今のモデルの1着"].rank(ascending=False, method="first")
        band = np.select([merged["popularity"] <= 3, merged["popularity"] <= 9], ["人気馬", "中穴"], default="大穴")
        merged["人気帯"] = band
        keys = [merged[RACE_ID], merged["人気帯"]]
        merged["荒れる前提の確率"] = merged["p_win"] / merged["p_win"].groupby(keys).transform("sum")
        merged["人気帯の中の順位"] = merged["p_win"].groupby(keys).rank(ascending=False, method="first")
        merged["4着以下の確率"] = 1 - merged["p_top3"]
        merged["4着以下の市場との差"] = merged["4着以下の確率"] - (1 - merged["m_top3"])
        return merged

    @staticmethod
    def race_ids(materials: pd.DataFrame, race_date: str) -> Sequence[str]:
        prefix = race_date.replace("-", "")
        return sorted({race_id for race_id in materials["race_id"] if race_id.startswith(prefix)})
