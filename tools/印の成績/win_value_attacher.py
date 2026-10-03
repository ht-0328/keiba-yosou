"""7つの区切りの1着の予想から、テスト期間の単勝の期待値を出す。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.win_value import WinExpectedValue

from 今週の予想.forecast_columns import WIN_PROBABILITY, WIN_VALUE

from 印の成績.prediction_file import TEST

#: 結果の列（今週の予想の ``forecast_columns`` の列と同じ名前）。
COLUMNS: tuple[str, ...] = ("race_id", "horse_id", WIN_PROBABILITY, WIN_VALUE)


class WinValueAttacher:
    """1着の予想（1着になる確率）の7つの区切りの予測から、テスト期間の単勝の期待値を出す（今週の予想と同じ決め方）。

    単勝の期待値 = 1着になる確率 × 確定の単勝オッズ（設計書「近走と適性から3着以内を予想」の 16 の 6）。
    ◎（期待値がいちばん高い馬）とレースの期待度は、この値から ``MarkRule``・``ExpectationLevel`` が決める。
    """

    def attach(self, predictions: pd.DataFrame, places: pd.DataFrame) -> pd.DataFrame:
        """``predictions`` は1着の予想の全部の行（``PredictionFile.load``）、``places`` は出走の行に確定の単勝オッズ（列 race_id・horse_id・win_odds）を付けた表。

        戻り値はテスト期間の行（列は ``COLUMNS``）。
        """
        tests = predictions[predictions["period"] == TEST]
        rows = tests.merge(places[["race_id", "horse_id", "win_odds"]], on=["race_id", "horse_id"], how="inner")
        rows[WIN_VALUE] = WinExpectedValue().of(rows["probability"], rows["win_odds"]).to_numpy()
        return rows.rename(columns={"probability": WIN_PROBABILITY})[list(COLUMNS)].reset_index(drop=True)
