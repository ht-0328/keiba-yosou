"""近走から付ける評価のことば。"""

from __future__ import annotations

from collections.abc import Sequence

from .past_run import PastRun

#: 「上向き」: 近この走数で着差が続けて縮んでいる。
IMPROVING_RUNS = 3
#: 「大敗続き」: 近この走数が全部、着差この秒数以上。
BIG_LOSS_GAP = 1.0
BIG_LOSS_RUNS = 2
#: ことばの名前。
IMPROVING, BIG_LOSSES = "上向き", "大敗続き"


class EvaluationWords:
    """馬の過去走（古い順。基準日より前）から、近走の評価のことばを根拠つきの文にする。

    - 上向き: 近 ``IMPROVING_RUNS`` 走で着差が続けて縮んでいる
    - 大敗続き: 近 ``BIG_LOSS_RUNS`` 走が全部、着差 ``BIG_LOSS_GAP`` 秒以上
    この2つは、研究「近走の文の評価のことば」で、ことばが付いた馬の次走の3着以内率が同じ人気の馬より良い（上向き）・悪い（大敗続き）
    と確かめたもの。「負けて強し」「人気薄で好走の実績」は次走に差が無かったので付けない（同じ研究の docs/01）。
    """

    def of(self, history: Sequence[PastRun]) -> list[str]:
        """``上向き（着差が +0.9 → +0.4 → +0.1秒と縮んでいる）`` の形の文。当てはまらなければ空。"""
        runs = list(history)
        return [text for text in (self._improving(runs), self._big_losses(runs)) if text]

    def _improving(self, runs: list[PastRun]) -> str:
        recent = runs[-IMPROVING_RUNS:]
        if len(recent) < IMPROVING_RUNS or any(run.time_diff is None for run in recent):
            return ""
        gaps = [run.time_diff for run in recent]
        if all(earlier > later for earlier, later in zip(gaps, gaps[1:])):
            return f"{IMPROVING}（着差が {' → '.join(f'{gap:+.1f}' for gap in gaps)}秒と縮んでいる）"
        return ""

    def _big_losses(self, runs: list[PastRun]) -> str:
        recent = runs[-BIG_LOSS_RUNS:]
        if len(recent) < BIG_LOSS_RUNS or any(run.time_diff is None or run.time_diff < BIG_LOSS_GAP for run in recent):
            return ""
        return f"{BIG_LOSSES}（近 {BIG_LOSS_RUNS} 走の着差 {'・'.join(f'{run.time_diff:+.1f}' for run in recent)}秒）"
