"""学習データのうち、学習に使う1番人気と、評価で判定する1番人気を選ぶ。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import HORSE_NO, RACE_ID, TrainingData
from yosou.shared.dataset.column_names import POPULARITY
from yosou.shared.feature import as_numbers

from .pre_deadline_favorites import PreDeadlineFavorites

#: 評価の結果の表の、1番人気の選び方の列。
PICK = "1番人気の選び方"
#: 確定の単勝オッズ（確定単勝人気）で選んだ1番人気。学習はいつもこれで行う。
CONFIRMED = "確定オッズ"
#: 締め切り前（発走の数分前）の単勝オッズで選んだ1番人気。本番で買うときに近い。
PRE_DEADLINE = "締め切り前のオッズ"
#: 確定単勝人気の1番人気。
_FAVORITE = 1


class FavoritePicks:
    """学習データの行のうち、学習に使う行と、評価で判定する行を、1番人気の選び方ごとに選ぶ（設計書 16 の 7）。

    - 学習に使うのは、いつも確定の1番人気の行。締め切り前の断面は過去1年ほどしか無いので、学習にはそろわない。
    - ``pre_deadline`` が無ければ、判定するのは確定の1番人気だけ（いつもの評価）。
    - ``pre_deadline`` があれば、締め切り前の1番人気と、同じレースの確定の1番人気の両方を判定する。
      比べる相手をそろえるため、どちらも、締め切り前の1番人気が学習データにいるレースだけにする。
    """

    def __init__(self, pre_deadline: PreDeadlineFavorites | None = None) -> None:
        self._pre_deadline = pre_deadline

    @property
    def main(self) -> str:
        """年ごと・判定ごと・単位ごとの表に出す選び方。締め切り前の1番人気を渡したなら、そちら。"""
        return CONFIRMED if self._pre_deadline is None else PRE_DEADLINE

    def training_rows(self, data: TrainingData) -> pd.Series:
        """学習に使う行（確定の1番人気）。"""
        return as_numbers(data.evaluation[POPULARITY]) == _FAVORITE

    def judged_rows(self, data: TrainingData) -> dict[str, pd.Series]:
        """選び方の名前 → 判定する行（行ごとの真偽）。"""
        confirmed = self.training_rows(data)
        if self._pre_deadline is None:
            return {CONFIRMED: confirmed}
        races = data.ids[RACE_ID]
        pre_deadline = self._pre_deadline.contains(races, data.ids[HORSE_NO])
        covered = races.isin(races[pre_deadline])
        return {CONFIRMED: confirmed & covered, PRE_DEADLINE: pre_deadline}
