"""1頭ごとの表と荒れ具合の予測とレースの属性から、1行 = 1レース × 区切り × 期間 の表にする。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_ID
from yosou.upset_level.dataset import BetType, UpsetLevel

from 既存モデルの改善.analysis.walk_forward import BET, PART as PART_JA, WINDOW as WINDOW_JA

from ..race_material import GRADED_CODES
from . import columns as c

#: レースの属性の表（``RaceFactRepository.read``）の列。
_FACT_RACE_ID, _FACT_GRADE = "race_id", "grade_code"
_KEY = [c.WINDOW, c.PART, c.RACE_ID]


class RaceTableBuilder:
    """1頭ごとの表（``RunnerTableBuilder`` の表）のレースごとに、重賞か（レースの属性のグレードコード A〜D）と、
    荒れ具合の予測（券種ごとの「中荒れ以上の確率」= 1 − 固いの確率、と いちばん確率の高い荒れ具合）を付ける。

    荒れ具合の予測は研究「既存モデルの改善」の ``UpsetWindowTrainer`` の形（1行 = 1レース × 区切り × 期間 × 券種、固い〜超荒れの4つの確率）。
    荒れ具合の無いレースは欠損、レースの属性の無いレースは重賞でないとする。
    """

    def build(self, runners: pd.DataFrame, upset: pd.DataFrame, race_facts: pd.DataFrame) -> pd.DataFrame:
        races = runners[_KEY + [c.RACE_DATE]].drop_duplicates(_KEY)
        graded = race_facts.loc[race_facts[_FACT_GRADE].fillna("").str.strip().isin(GRADED_CODES), _FACT_RACE_ID].astype(str)
        races = races.assign(**{c.IS_GRADED: races[c.RACE_ID].isin(set(graded))})
        merged = races.merge(self._upset_wide(upset), on=_KEY, how="left")
        return merged.sort_values([c.WINDOW, c.PART, c.RACE_DATE, c.RACE_ID]).reset_index(drop=True)

    def _upset_wide(self, upset: pd.DataFrame) -> pd.DataFrame:
        """券種ごとの「中荒れ以上の確率」と「いちばん確率の高い荒れ具合」を横に並べる。"""
        labels = list(UpsetLevel.labels())
        solid = UpsetLevel.SOLID.label
        frame = upset.rename(columns={WINDOW_JA: c.WINDOW, PART_JA: c.PART, RACE_ID: c.RACE_ID})
        frame = frame.assign(**{c.RACE_ID: frame[c.RACE_ID].astype(str)})
        parts = []
        for bet in BetType:
            rows = frame[frame[BET] == bet.label]
            parts.append(pd.DataFrame({
                c.WINDOW: rows[c.WINDOW].to_numpy(), c.PART: rows[c.PART].to_numpy(), c.RACE_ID: rows[c.RACE_ID].to_numpy(),
                c.upset_column(bet): (1.0 - rows[solid]).to_numpy(),
                c.upset_level_column(bet): rows[labels].idxmax(axis=1).to_numpy(),
            }).drop_duplicates(_KEY))
        wide = parts[0]
        for part in parts[1:]:
            wide = wide.merge(part, on=_KEY, how="outer")
        return wide
