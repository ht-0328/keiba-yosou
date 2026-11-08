"""精算の結果を、買い方ごとの成績（数の値）にまとめる。"""

from __future__ import annotations

import pandas as pd

from 共通.bootstrap_interval import BootstrapInterval

from yosou.form_aptitude_win5_tickets.settlement import HIT, PAYOUT, RACE_DATE, STAKE, STRATEGY

#: 成績の列。
DAYS = "買った日数"
HITS = "当たった回数"
RECOVERY = "回収率"
HIT_RATE = "的中率"
LOW = "90%の幅の下"
HIGH = "90%の幅の上"
SUMMARY_COLUMNS: tuple[str, ...] = (STRATEGY, DAYS, STAKE, PAYOUT, RECOVERY, HITS, HIT_RATE, LOW, HIGH)


class Win5StrategySummary:
    """買い方ごとの、買った日数・投資・払戻・回収率・当たった回数・的中率・90% の幅（WIN5 の日を単位にしたブートストラップ。
    共通の ``BootstrapInterval``）を、比べたり選んだりできる数の値で出す（設計書「近走と適性からWIN5の買い目を決める」16 の 2.）。
    表に見せる文字の形は ``Win5BacktestTables`` と、この道具の WIN5 の表のクラスが作る。"""

    def __init__(self, interval: BootstrapInterval | None = None) -> None:
        self._interval = interval or BootstrapInterval()

    def of(self, settled: pd.DataFrame) -> pd.DataFrame:
        """``settled`` は買った日の精算の行（列は ``SETTLED_COLUMNS`` を含む）。1行 = 1つの買い方。買い方の現れた順。"""
        rows = [self._row(strategy, group) for strategy, group in settled.groupby(STRATEGY, sort=False)]
        return pd.DataFrame(rows, columns=list(SUMMARY_COLUMNS))

    def _row(self, strategy: str, group: pd.DataFrame) -> dict[str, object]:
        stake, payout, hits = int(group[STAKE].sum()), int(group[PAYOUT].sum()), int(group[HIT].sum())
        low, high = self._interval.of(group[RACE_DATE], group[STAKE], group[PAYOUT])
        return {
            STRATEGY: strategy, DAYS: len(group), STAKE: stake, PAYOUT: payout, RECOVERY: payout / stake if stake else float("nan"),
            HITS: hits, HIT_RATE: hits / len(group), LOW: low, HIGH: high,
        }
