"""新しい確率を採用できるかの、結果を見る前に決めた基準。"""

from __future__ import annotations

from dataclasses import dataclass

from .source_result import SourceResult

#: 回収率がこの値（%）を超えて初めて「超えた」と言う。
BREAK_EVEN = 100.0


@dataclass(frozen=True)
class SourceVerdict:
    """1つの出どころの判定。

    - ``usable``: 線が選べ、全期間（2019〜2026年）の回収率が 100% を超え、90% の下限も 100% を上回る。
    - ``better_than_original``: ``usable`` のうえ、後半（2022〜2026年）の回収率が元より高く、後半の下限も 100% を上回る。
    """

    usable: bool
    better_than_original: bool

    @property
    def text(self) -> str:
        if self.better_than_original:
            return "採用できる（元より良い）"
        if self.usable:
            return "100% は超えるが、元より良いとは言えない"
        return "採用できない"


class SourceAdoptionRule:
    """結果を見る前に決めた採用の基準（docs/04-買い方.md の 8）で、新しい出どころを判定する。

    1. 元と同じ決まりで線が選べる（前半で 100% を超え、1年あたり 300 点以上残る線がある）。
    2. 選んだ線で、全期間の回収率が 100% を超え、開催日単位の 90% の下限も 100% を上回る（この研究の「超えた」の定義）。
    3. 選んだ線で、後半（線を選ぶのに使っていない期間）の回収率が元の方法（元の線）より高く、後半の下限も 100% を上回る。
    1〜3 を全部満たせば「採用できる（元より良い）」、1・2 だけなら「100% は超えるが、元より良いとは言えない」。
    """

    def judge(self, candidate: SourceResult, original: SourceResult) -> SourceVerdict:
        usable = self._is_usable(candidate)
        better = usable and self._beats_original(candidate, original)
        return SourceVerdict(usable, better)

    def _is_usable(self, result: SourceResult) -> bool:
        if result.line is None:
            return False
        return result.total_rate > BREAK_EVEN and result.total_low > BREAK_EVEN

    def _beats_original(self, candidate: SourceResult, original: SourceResult) -> bool:
        if candidate.late is None:
            return False
        beats_rate = original.late is None or candidate.late.rate > original.late.rate
        return beats_rate and candidate.late.low > BREAK_EVEN
