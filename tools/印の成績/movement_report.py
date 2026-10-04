"""前日夜 → 当日朝の単勝オッズの動きごとの、◎ の単勝の成績の表を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.win_value import HIGH

from 共通.bootstrap_interval import BootstrapInterval
from 共通.perf import STAKE_YEN, percent
from 共通.render import Table

from 今週の予想.forecast_columns import EXPECTATION, MARK
from 今週の予想.mark_rule import TOP_MARK

from 印の成績.filter_columns import ODDS_MOVE
from 印の成績.odds_snapshot_repository import MORNING_CUTOFF
from 印の成績.perf_rows import perf_row_of

#: 動き（log(当日朝 ÷ 前日夜)）の帯。境目は「その値未満」。負なら売れた（人気が上がった）。
_EDGES: tuple[float, ...] = (-0.3, -0.1, 0.1, 0.3)
BAND_LABELS: tuple[str, ...] = ("大きく売れた（−30%超）", "売れた（−30〜−10%）", "ほぼ変わらず（±10%）", "売れず（+10〜30%）", "大きく売れず（+30%超）")
ALL_LABEL = "動きの分かるレース全部"


class MovementReport:
    """印を付けた表（``BacktestMarker.mark``。前日夜と当日朝の単勝オッズの動き ``odds_move`` 付き）から、◎ の動きの帯ごとの単勝の成績の表（表11）を作る
    （研究「回収率100超の施策」の施策5）。

    対象は、前日夜と当日朝の両方の断面がある（時系列オッズのある）レースだけ。JV-Data の時系列オッズは提供が1年ぶんなので、
    テスト期間の終わりの約1年のレースに限られる。注に、対象のレース数と割合、期間を書く。
    """

    def table(self, marked: pd.DataFrame) -> Table:
        tops = marked[marked[MARK] == TOP_MARK]
        covered = tops[tops[ODDS_MOVE].notna()] if ODDS_MOVE in tops.columns else tops.iloc[0:0]
        headers = ["◎のオッズの動き", "レース数", "着別度数", "勝率", "単勝回収率", "90%の幅", "期待度 高のレース", "高の単勝回収率", "90%の幅"]
        rows = []
        if not covered.empty:
            band = np.asarray(BAND_LABELS, dtype=object)[np.searchsorted(np.asarray(_EDGES), covered[ODDS_MOVE].to_numpy(dtype=float), side="right")]
            for label in BAND_LABELS:
                rows.append(self._row(label, covered[band == label]))
            rows.append(self._row(ALL_LABEL, covered))
        total = tops["race_id"].nunique()
        share = covered["race_id"].nunique() / total if total else 0.0
        period = (f"{covered['race_date'].min():%Y-%m-%d} 〜 {covered['race_date'].max():%Y-%m-%d}" if not covered.empty else "—")
        note = (f"◎ のいるレース {total:,} のうち、前日夜と当日朝の単勝オッズの断面がそろうレース {covered['race_id'].nunique():,}（{percent(share)}。期間 {period}）だけが対象。"
                f"動きは log(当日 {MORNING_CUTOFF[:2]}時{MORNING_CUTOFF[2:]}分までの最後の断面のオッズ ÷ 前日の最後の断面のオッズ)。負なら前日夜より売れて人気が上がった。"
                "◎ と期待度は確定オッズで決めたもの（表6 と同じ）。1点 100円、90% の幅は開催日を単位にしたブートストラップ。"
                "時系列オッズは JV-Data の提供が1年ぶんなので対象が少なく、採用の基準を満たしても「届いたが数が少ない」と扱う（研究「回収率100超の施策」の施策5）。")
        return Table(headers, rows, title="11. 前日夜 → 当日朝のオッズの動きごとの ◎ の単勝の成績（参考）", note=note)

    def _row(self, label: str, chosen: pd.DataFrame) -> list[str]:
        if chosen.empty:
            return [label, "0", "0-0-0-0", "—", "—", "—", "0", "—", "—"]
        rates = perf_row_of(chosen).rates()
        high = chosen[chosen[EXPECTATION] == HIGH]
        return [label, f"{len(chosen):,}", perf_row_of(chosen).counts(), percent(rates["勝率"]), percent(rates["単勝回収率"]),
                self._interval(chosen), f"{len(high):,}", *self._win_cells(high)]

    def _win_cells(self, chosen: pd.DataFrame) -> list[str]:
        if chosen.empty:
            return ["—", "—"]
        return [percent(perf_row_of(chosen).rates()["単勝回収率"]), self._interval(chosen)]

    def _interval(self, chosen: pd.DataFrame) -> str:
        low, high = BootstrapInterval().of(chosen["race_date"], pd.Series(float(STAKE_YEN), index=chosen.index), chosen["win_payout"].astype(float))
        return f"{percent(low)}〜{percent(high)}"
