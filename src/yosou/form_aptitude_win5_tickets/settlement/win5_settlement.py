"""過去の WIN5 の1回について、買い目の当たり・返還・払戻を出す。"""

from __future__ import annotations

import math

from ..formation import Formation
from ..payout import PAYOUT_CEILING, TICKET_YEN, PayoutPool
from .win5_outcome import Win5Outcome
from .win5_settled import Win5Settled


class Win5Settlement:
    """買い目（``Formation``）を、元DB の当たり組と照らして精算する（設計書 16 の 1.・5.）。

    - 返還: 出走取消・競走除外の馬を含む組は、代金（1点 100円）が戻る。点数は「全部の点数 − 取消・除外の馬を除いた頭数のかけ算」。
    - 当たり: 当たり組（同着なら2つ以上）がフォーメーションに含まれれば、その組の 100円あたりの払戻を受け取る。
    - 的中無の回に当たり組を買っていたら: 当たり票は自分の1票だけになるので、払戻に回るお金（その回の発売票数 × 100円 × 払戻率 +
      キャリーオーバー）を1票で受け取る（払戻の上限で頭打ち）。
    組を1つずつ並べずに数えるので、数百点の買い目を数百日ぶん精算しても速い。
    """

    def settle(self, formation: Formation, outcome: Win5Outcome) -> Win5Settled:
        alive = [set(picks) - scratched for picks, scratched in zip(formation.legs, outcome.scratched, strict=True)]
        refunded_points = formation.points - math.prod(len(picks) for picks in alive)
        won = [payout for combo, payout in outcome.winners if self._bought(combo, alive)]
        winnings = [self._sole_payout(outcome) for _ in won] if outcome.no_hit else won
        payout = sum(winnings) + refunded_points * TICKET_YEN
        return Win5Settled(formation.points, formation.points * TICKET_YEN, int(payout), bool(won), refunded_points)

    def _bought(self, combo: tuple[int, ...], alive: list[set[int]]) -> bool:
        """当たり組の5頭が、どれも買い目の（取消・除外でない）馬か。"""
        return len(combo) == len(alive) and all(number in picks for number, picks in zip(combo, alive, strict=True))

    def _sole_payout(self, outcome: Win5Outcome) -> int:
        """的中無の回に、自分だけが当てたときの 100円あたりの払戻。"""
        return int(min(PayoutPool(outcome.votes, outcome.carry).money, PAYOUT_CEILING))
