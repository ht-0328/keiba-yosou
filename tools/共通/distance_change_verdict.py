"""距離短縮と距離延長のどちらが有利かを判定する。基礎統計のページ（コースごと）と重賞攻略（レースごと）が使う。"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from . import distance_change

from .popularity_expectation import PopularityExpectation, PopularityGap, placed, won

#: 判定に要る、短縮・延長それぞれの出走数。これより少なければ「標本が少ない」。
MIN_RUNS = 30
#: 有利と書く検定の線（両側。z の絶対値）と、その印。強い線から順に見る。
_LEVELS: tuple[tuple[float, str], ...] = ((2.576, "1%"), (1.960, "5%"))
FEW = "標本が少ない"
EVEN = "差なし"
#: 表の列に並べる距離の変更（前走なしは比べない）。
SHOWN_CHANGES: tuple[str, ...] = (distance_change.SHORTER, distance_change.SAME, distance_change.LONGER)


@dataclass(frozen=True)
class ChangeResult:
    """1つの距離の変更の、実際の率と人気から見た差。"""

    rate: float
    gap: PopularityGap

    def text(self) -> str:
        """``7.1%（+0.4pt）1,234頭`` の形。出走が無ければ ``-``。"""
        if self.gap.runs == 0:
            return "-"
        return f"{self.rate * 100:.1f}%（{self.gap.gap * 100:+.1f}pt）{self.gap.runs:,}頭"


@dataclass(frozen=True)
class Verdict:
    """勝つ・穴馬の好走 のどちらか1つの見方での判定。``results`` は距離の変更 → 結果、``winner`` は有利なほうの文。

    ``p_value`` は短縮と延長の、人気から見た差の違いの検定（両側）。標本が少なく比べないときは None。
    """

    results: dict[str, ChangeResult]
    winner: str
    p_value: float | None = None

    @property
    def favored(self) -> str | None:
        """有利なほう（短縮・延長）。差なし・標本が少ないときは None。"""
        for side in (distance_change.SHORTER, distance_change.LONGER):
            if self.winner.startswith(f"{side}が有利"):
                return side
        return None


class DistanceChangeVerdict:
    """出走の集まり（1つのコースの全馬場状態や、1つの重賞の全開催）から、短縮と延長の「勝つ」「穴馬の好走」を比べる。

    出走の表には ``label_distance_change``（短縮・同じ・延長・前走なし）・``popularity``・``first``・``second``・``third`` が要る。
    人気から見た期待は、``base``（省略すると ``runs`` そのもの）の人気ごとの率。重賞では同じグレードの重賞全体を渡す。

    - 勝つ: 全馬の勝率。人気から見た差は、同じ人気の馬の勝率との差。
    - 穴馬の好走: 穴馬（6番人気以下）の複勝率（3着以内の率）。人気から見た差は、同じ人気の馬の複勝率との差。
    - 有利なほう: 短縮と延長の、人気から見た差の違いを z 検定し、5%（1%）の線を超えたときだけ有利なほうを書く。
      人気の偏り（延長の馬は人気薄が多い など）を除いて比べるため、実際の率ではなく人気から見た差で判定する。
    """

    def win(self, runs: pd.DataFrame, base: pd.DataFrame | None = None) -> Verdict:
        expectation = PopularityExpectation(runs if base is None else base)
        return self._verdict(runs, lambda group: (won(group).mean(), expectation.win_gap(group)))

    def longshot(self, runs: pd.DataFrame, base: pd.DataFrame | None = None) -> Verdict:
        expectation = PopularityExpectation(runs if base is None else base)
        longshots = runs[runs["popularity"].ge(distance_change.LONGSHOT_MIN_POPULARITY)]
        return self._verdict(longshots, lambda group: (placed(group).mean(), expectation.top3_gap(group)))

    @staticmethod
    def _verdict(runs: pd.DataFrame, measure) -> Verdict:
        results = {}
        for change in SHOWN_CHANGES:
            group = runs[runs["label_distance_change"].eq(change)]
            rate, gap = measure(group) if len(group) else (float("nan"), PopularityGap(0, float("nan"), float("nan")))
            results[change] = ChangeResult(rate, gap)
        shorter, longer = results[distance_change.SHORTER].gap, results[distance_change.LONGER].gap
        if min(shorter.runs, longer.runs) < MIN_RUNS:
            return Verdict(results, FEW)
        spread = math.hypot(shorter.std_error, longer.std_error)
        if spread == 0:
            return Verdict(results, EVEN, 1.0)
        z = (longer.gap - shorter.gap) / spread
        return Verdict(results, _winner(z), math.erfc(abs(z) / math.sqrt(2.0)))


def _winner(z: float) -> str:
    for line, mark in _LEVELS:
        if abs(z) >= line:
            side = distance_change.LONGER if z > 0 else distance_change.SHORTER
            return f"{side}が有利（{mark}）"
    return EVEN
