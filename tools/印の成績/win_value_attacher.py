"""7つの区切りの1着の予想から、テスト期間の単勝の期待値を出す。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.win_value import WinExpectedValue

from 今週の予想.forecast_columns import WIN_PROBABILITY, WIN_VALUE

from 印の成績.filter_columns import MEMBERS, member_column
from 印の成績.prediction_file import TEST

#: 結果の列（今週の予想の ``forecast_columns`` の列と同じ名前）。
COLUMNS: tuple[str, ...] = ("race_id", "horse_id", WIN_PROBABILITY, WIN_VALUE)


class WinValueAttacher:
    """1着の予想（1着になる確率）の7つの区切りの予測から、テスト期間の単勝の期待値を出す（今週の予想と同じ決め方）。

    単勝の期待値 = 1着になる確率 × 確定の単勝オッズ（設計書「近走と適性から3着以内を予想」の 16 の 6）。
    ◎（期待値がいちばん高い馬）とレースの期待度は、この値から ``MarkRule``・``ExpectationLevel`` が決める。
    予測にモデルごとの確率（``probability_lightgbm``・``probability_catboost``）があれば、モデルごとの1着になる確率と単勝の期待値
    （``win_probability_lightgbm``・``win_value_lightgbm`` など）も付ける（2モデル一致の絞り込みに使う）。
    """

    def __init__(self) -> None:
        self._value = WinExpectedValue()

    def attach(self, predictions: pd.DataFrame, places: pd.DataFrame) -> pd.DataFrame:
        """``predictions`` は1着の予想の全部の行（``PredictionFile.load``）、``places`` は出走の行に確定の単勝オッズ（列 race_id・horse_id・win_odds）を付けた表。

        戻り値はテスト期間の行（列は ``COLUMNS`` と、あればモデルごとの列）。
        """
        tests = predictions[predictions["period"] == TEST]
        rows = tests.merge(places[["race_id", "horse_id", "win_odds"]], on=["race_id", "horse_id"], how="inner")
        rows[WIN_VALUE] = self._value.of(rows["probability"], rows["win_odds"]).to_numpy()
        columns = list(COLUMNS)
        for member in MEMBERS:
            source = member_column("probability", member)
            if source not in rows.columns:
                continue
            probability, value = member_column(WIN_PROBABILITY, member), member_column(WIN_VALUE, member)
            rows[probability] = rows[source]
            rows[value] = self._value.of(rows[source], rows["win_odds"]).to_numpy()
            columns += [probability, value]
        return rows.rename(columns={"probability": WIN_PROBABILITY})[columns].reset_index(drop=True)
