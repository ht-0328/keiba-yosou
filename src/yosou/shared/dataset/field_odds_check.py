"""前日・当日の予測で、全頭の単勝オッズがそろっているかを確かめる。"""

from __future__ import annotations

import pandas as pd

from ..feature import PredictionTiming, as_numbers


class FieldOddsCheck:
    """前日以降の予測で、オッズの分からない馬が一部にいれば止める（荒れ具合の設計書 06 の図2・11 の 8）。

    全頭のオッズから作る特徴量（10倍未満の頭数、市場勝率の合計など）は、1頭でも欠けると学習データと違う意味になる。
    全頭に無いときは、ここでは止めず、そのあとの ``RequiredInfoCheck`` が取り込み方を案内する。
    """

    def check(self, runners: pd.DataFrame, timing: PredictionTiming) -> None:
        """木曜はオッズを使わないので何もしない。一部の馬にオッズが無ければ ``ValueError``。"""
        if not timing.is_at_or_after(PredictionTiming.DAY_BEFORE):
            return
        unknown = int(as_numbers(runners["win_odds"]).isna().sum())
        if 0 < unknown < len(runners):
            raise ValueError(
                f"単勝オッズの分からない馬が {unknown}頭います（{len(runners)}頭立て）。"
                "--odds 馬番:オッズ で全頭ぶん渡すか、jvstore realtime（開催日）で締め切り前のオッズを取り込んでください。"
            )
