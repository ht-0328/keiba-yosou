"""対象の出走の材料を作るのに要る出走だけに絞る。"""

from __future__ import annotations

import pandas as pd

from .ability_columns import RECORD_GROUPS


class AbilityRunFocus:
    """全出走（``runs``。対象の出走は ``is_target`` が真）から、対象の出走の材料を作るのに要る出走だけを選ぶ。

    予測（対象が1レース）では、2011年からの全出走で数えなくても、次の出走だけで同じ値になる（学習では対象が全部なので、
    絞っても全出走のまま）。道具「能力指数」の ``--all`` を速くしたときと同じく、要る馬・要る区分の出走だけを使う考え方。

    - スピード指数: 対象の馬が走ったレース（今回を含む）に出た馬の全部の走。過去のレースの強さ（相手の強さ）に、
      そのレースの全部の出走馬の「そのときの力」が要るため。
    - 過去走: 対象の馬の走だけ。
    - 通算の成績: 区分ごと（騎手・調教師・父 など）に、対象の出走と同じ区分の値の出走だけ。区分ごとに別々に数えるため。
    - 直近の成績: 対象の騎手・前走の騎手・対象の調教師の出走と、対象の馬の走（前走の騎手を知るため）。
    """

    def __init__(self, runs: pd.DataFrame) -> None:
        self._runs = runs
        self._targets = runs[runs["is_target"]]
        self._target_horses = self._runs["horse_id"].isin(self._targets["horse_id"])

    def figure_runs(self) -> pd.DataFrame:
        """スピード指数とレースの強さを作る出走。"""
        races = self._runs.loc[self._target_horses, "race_id"].unique()
        horses = self._runs.loc[self._runs["race_id"].isin(races), "horse_id"].unique()
        return self._runs[self._runs["horse_id"].isin(horses)]

    def target_horse_runs(self) -> pd.DataFrame:
        """対象の馬の走（過去走と、前走の騎手を作る出走）。"""
        return self._runs[self._target_horses]

    def record_runs(self, name: str) -> pd.DataFrame:
        """通算の成績の区分 ``name``（``RECORD_GROUPS`` の名前）で、対象の出走と同じ区分の値の出走。"""
        keys = list(RECORD_GROUPS[name])
        wanted = self._targets[keys].dropna().drop_duplicates()
        index = pd.MultiIndex.from_frame(self._runs[keys])
        return self._runs[index.isin(pd.MultiIndex.from_frame(wanted))]

    def people_runs(self) -> pd.DataFrame:
        """直近の成績を数える出走（対象と前走の騎手・対象の調教師の出走と、対象の馬の走）。"""
        horse_runs = self.target_horse_runs()
        jockeys = pd.concat([self._targets["jockey_code"], horse_runs["jockey_code"]]).dropna().unique()
        chosen = (self._target_horses | self._runs["jockey_code"].isin(jockeys)
                  | self._runs["trainer_code"].isin(self._targets["trainer_code"].dropna().unique()))
        return self._runs[chosen]
