"""確率のずれを確かめた結果を表にする。"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

from 共通.render import Table

from ..dataset.column_names import PLACE_PAYOUT, POPULARITY
from ..evaluation.probability_bands import ProbabilityBands
from ..evaluation.value_bands import ACTUAL_HIT, COUNT, PAYBACK, PREDICTED_HIT, ValueBands
from ..place_value import PLACE_PROBABILITY, PLACE_VALUE
from ..workflow.calibration_check import LABEL, PART, PROBABILITY, SEGMENT, TIMING
from .cell_format import rounded

#: 表を分ける単位（時点・区分・期間）。
_KEYS = [TIMING, SEGMENT, PART]
#: 期待値で買うときの線（1 で元返し）。
_VALUE_LINE = 1.0
#: 「人気上位しか選ばなくなっていないか」を見る人気の線（10番人気以下を選べているか）。
_LONGSHOT_POPULARITY = 10
#: 確率を丸めるときの端（0 と 1 ではログ損失が計算できない）。
_EDGE = 1e-6


class CalibrationReportTables:
    """``CalibrationCheck`` の材料の表を、4つの表（まとめ・確率の帯ごと・人気ごと・期待値の帯ごと）にする。

    どの表も 時点 × 区分 × 期間（検証・テスト）ごとに行を分ける。検証期間は学習のとき早期終了に使った期間なので、
    確率のずれを信じてよいのはテスト期間のほうである。
    """

    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame
        self._groups = list(frame.groupby(_KEYS, sort=False))

    def tables(self) -> list[Table]:
        return [self._summary(), self._probability_bands(), self._popularity(), self._value_bands()]

    def _summary(self) -> Table:
        rows = [[*key, *self._summary_row(group)] for key, group in self._groups]
        return Table(
            [*_KEYS, "頭数", "予想の平均", "実際の割合", "実際 ÷ 予想", "帯ごとのずれの平均", "ログ損失",
             "期待値1以上の点数", "その予想の的中率", "その実際の的中率", "その回収率", "そのうち10番人気以下の割合"],
            rows, title="確率のずれのまとめ",
            note="予想の平均と実際の割合（3着以内に入った割合）が近く、「実際 ÷ 予想」が 1 に近いほど、確率をそのまま使える。"
                 "帯ごとのずれの平均は、確率の帯ごとの |予想 − 実際| を頭数で重み付けした平均（ECE。0 に近いほど良い）。"
                 "期待値1以上は、複勝の期待値が 1 以上の馬を全部 100円ずつ買ったときの成績（前日・当日だけ）。"
                 "的中率は複勝の的中率。検証期間は早期終了に使った期間なので、テスト期間の値で判断する。",
        )

    def _summary_row(self, group: pd.DataFrame) -> list[object]:
        label, probability = group[LABEL], group[PROBABILITY]
        bought = group[group[PLACE_VALUE] >= _VALUE_LINE]
        value = ValueBands().at_least(group[PLACE_VALUE], group[PLACE_PROBABILITY], group[PLACE_PAYOUT], _VALUE_LINE)
        longshots = pd.to_numeric(bought[POPULARITY], errors="coerce") >= _LONGSHOT_POPULARITY
        return [
            len(group), rounded(probability.mean()), rounded(label.mean()), rounded(label.mean() / probability.mean()),
            rounded(ProbabilityBands().gap(label, probability)),
            rounded(log_loss(label, probability.clip(_EDGE, 1 - _EDGE), labels=[0, 1])),
            int(value[COUNT]), rounded(value[PREDICTED_HIT]), rounded(value[ACTUAL_HIT]), rounded(value[PAYBACK]),
            rounded(longshots.mean() if len(bought) else np.nan),
        ]

    def _probability_bands(self) -> Table:
        parts = [ProbabilityBands().table(group[LABEL], group[PROBABILITY]).assign(**dict(zip(_KEYS, key)))
                 for key, group in self._groups]
        return self._table(pd.concat(parts, ignore_index=True), "確率の帯ごとのずれ",
                           "「実際 ÷ 予想」が 1 より小さい帯は確率を高めに、大きい帯は低めに見積もっている。"
                           "頭数の少ない帯（数十頭）は偶然で大きく振れる。")

    def _popularity(self) -> Table:
        parts = [self._popularity_rows(group).assign(**dict(zip(_KEYS, key))) for key, group in self._groups]
        return self._table(pd.concat(parts, ignore_index=True), "確定単勝人気ごとのずれ",
                           "人気薄ほど「実際 ÷ 予想」が 1 より小さければ、人気薄の確率を高めに見積もっている。")

    def _popularity_rows(self, group: pd.DataFrame) -> pd.DataFrame:
        grouped = group.groupby(pd.to_numeric(group[POPULARITY], errors="coerce"))
        rows = pd.DataFrame({"確定単勝人気": grouped.size().index.astype(int), "頭数": grouped.size().to_numpy(),
                             "予想の平均": grouped[PROBABILITY].mean().to_numpy(),
                             "実際の割合": grouped[LABEL].mean().to_numpy()})
        return rows.assign(**{"実際 ÷ 予想": rows["実際の割合"] / rows["予想の平均"]})

    def _value_bands(self) -> Table:
        parts = [ValueBands().table(group[PLACE_VALUE], group[PLACE_PROBABILITY], group[PLACE_PAYOUT])
                 .assign(**dict(zip(_KEYS, key))) for key, group in self._groups]
        return self._table(pd.concat(parts, ignore_index=True), "複勝の期待値の帯ごとの回収率",
                           "期待値の帯ごとに、全部 100円ずつ買ったときの成績（前日・当日だけ。木曜は期待値を出さない）。"
                           "回収率が期待値の平均より低ければ、期待値を高めに見積もっている。予想の的中率と実際の的中率の差は確率から、"
                           "残りは見込みの倍率から来る。")

    def _table(self, frame: pd.DataFrame, title: str, note: str) -> Table:
        """``_KEYS`` を左に寄せ、小数を丸めた表。"""
        columns = [*_KEYS, *(column for column in frame.columns if column not in _KEYS)]
        rows = [[self._cell(value) for value in row] for row in frame[columns].itertuples(index=False)]
        return Table(columns, rows, title=title, note=note)

    def _cell(self, value: object) -> object:
        if isinstance(value, float):
            return rounded(value)
        return value
