"""2つの条件の成績の対比。"""

from __future__ import annotations

from collections.abc import Iterable

from .past_run import PastRun
from .record import Record

#: 対比を出す線。両方の側に ``MIN_RUNS_EACH`` 走以上あり、こちらの側の3着以内率が相手より ``PLACE_RATE_GAP`` 以上低いときだけ。
MIN_RUNS_EACH = 2
PLACE_RATE_GAP = 0.5


class RecordContrast:
    """ある条件（こちらの側）の成績が、ほかの条件（相手の側）よりはっきり悪いときだけ、両方の着別度数を返す。

    走が少ないとき（どちらかの側が ``MIN_RUNS_EACH`` 未満）や差が小さいときは None（対比の文を出さない。推測を書かないため）。
    対比は負けた走の説明（その走までの成績がこうだった、という事実）に使う。次走の成績を当てる線ではない
    （研究「近走の文の評価のことば」で、この対比は次走の3着以内率と関係が無かった）。
    """

    def of(self, this_side: Iterable[PastRun], other_side: Iterable[PastRun]) -> tuple[Record, Record] | None:
        this_record, other_record = Record.of(this_side), Record.of(other_side)
        if this_record.count < MIN_RUNS_EACH or other_record.count < MIN_RUNS_EACH:
            return None
        if other_record.place_rate - this_record.place_rate < PLACE_RATE_GAP:
            return None
        return this_record, other_record
