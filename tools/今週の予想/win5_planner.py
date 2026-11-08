"""1日の WIN5 の予想の記録から、ポリシー用の財布で買うかと金額を決める（設計書「買うレースと買い目を決める」08 の 1）。"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from 今週の予想.wallet import POLICY_WALLET, Wallet
from 今週の予想.win5_plan import Win5Plan
from 今週の予想.win5_record import Win5Record


class Win5Planner:
    """WIN5 は楽しむための参加費なので、ポリシー用の財布から買う（勝負用の財布とは混ぜない）。

    - 予想の判断が「見送り」（日の期待値が線未満）なら買わない。
    - 「買う」なら、代金（点数 × 100円。予算と線は予想のパッケージの ``formation/buying_defaults.py`` で決まる）を、ポリシー用の財布から出す。
      ただし、その日より前の残高が代金に足りなければ買わない（財布を負にしない）。ポリシー用の財布は減るのが想定内なので、初めの 70% の止まりは置かない。
    """

    def __init__(self, wallet: Wallet) -> None:
        self._wallet = wallet

    def plan(self, record: Win5Record, day: date) -> Win5Plan:
        base = Win5Plan(record.race_date, record.legs[0].race_id, record.decision, False, record.points, 0, record.formation,
                        record.hit_probability, record.expected_value, record.line, "")
        if not record.buys:
            return replace(base, reason=f"{record.value_text()} なので見送り")
        balance = self._wallet.balance(POLICY_WALLET, day)
        if balance < record.stake:
            return replace(base, reason=f"{record.value_text()} だが、ポリシー用の財布の残高 {balance:,}円 が代金 {record.stake:,}円 に足りないので買わない")
        return replace(base, buys=True, stake_yen=record.stake, reason=f"{record.value_text()} なので、ポリシー用の財布から買う")
