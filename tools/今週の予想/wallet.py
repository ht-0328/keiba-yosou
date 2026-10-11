"""2つの財布（勝負用・ポリシー用）の残高と、参加の種類ごとの予算（設計書「買うレースと買い目を決める」08 の 1）。"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from yosou.review import ReviewStore, names

#: 財布の名前。
MATCH_WALLET, POLICY_WALLET = "勝負用", "ポリシー用"
#: 参加の種類 → 出す財布。
WALLET_OF: dict[str, str] = {names.MATCH: MATCH_WALLET, names.POLICY_STAKES: POLICY_WALLET, names.POLICY_DAY: POLICY_WALLET}
#: 予算の割合（残高に対して）。勝負レース 5%・ノルマ参加（重賞）3%・ノルマ参加（日）1.5%。
BUDGET_RATE: dict[str, float] = {names.MATCH: 0.05, names.POLICY_STAKES: 0.03, names.POLICY_DAY: 0.015}
#: 勝負レースの1点 = 予算 ÷ 3。1日に使う額の上限は勝負用の残高の 20%。勝負用が初めの 70% を下回ったら勝負レースを止める。
POINTS_PER_RACE, DAY_CAP_RATE, STOP_RATE = 3, 0.20, 0.70
#: 100円未満は切り捨て、最低 100円。
YEN_UNIT, MIN_YEN = 100, 100
#: 初めに入れる額の既定（設計書 08 の 1 の例。実際に買い始めるときに利用者が財布のファイルで決める）。
DEFAULT_INITIAL: dict[str, int] = {MATCH_WALLET: 100_000, POLICY_WALLET: 30_000}
#: 財布のファイルの既定（Git の対象外の reports/回顧/）。
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WALLET_FILE = _PROJECT_ROOT / "reports" / "回顧" / "財布.json"


class Wallet:
    """財布の初めの額（``財布.json``。無ければ既定で作る）と、買い目の記録（表1）から、財布ごとの残高を数える。

    残高 = 初めの額 − 記録した買い目の金額（記録だけのものは除く）＋ 精算した払戻。払戻は買った財布に戻す。
    毎月の初めの残高で額を決める（``month_start``）ので、同じ月の中では予算が変わらない。
    """

    def __init__(self, store: ReviewStore, path: Path = DEFAULT_WALLET_FILE) -> None:
        self._store = store
        self._path = Path(path)

    def initial(self) -> dict[str, int]:
        if not self._path.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(DEFAULT_INITIAL, ensure_ascii=False, indent=2), encoding="utf-8")
        saved = json.loads(self._path.read_text(encoding="utf-8"))
        return {wallet: int(saved.get(wallet, DEFAULT_INITIAL[wallet])) for wallet in DEFAULT_INITIAL}

    def balance(self, wallet: str, before: date | None = None) -> int:
        """``before`` より前の開催日の買い目まで数えた残高（省略すると全部）。"""
        bets = self._store.read(names.BETS_TABLE, f"NOT {names.RECORD_ONLY}" + (f" AND {names.RACE_DATE} < ?" if before else ""),
                                [before] if before else [])
        kinds = [kind for kind, name in WALLET_OF.items() if name == wallet]
        mine = bets[bets[names.PARTICIPATION].isin(kinds)]
        staked = int(mine[names.STAKE_YEN].fillna(0).sum())
        returned = int(mine.loc[mine[names.SETTLED].fillna(False).astype(bool), names.PAYOUT_YEN].fillna(0).sum())
        return self.initial()[wallet] - staked + returned

    def month_start(self, day: date) -> date:
        return date(day.year, day.month, 1)

    def budget(self, kind: str, day: date) -> int:
        """その参加の種類の1レースの予算（円。月初の残高 × 割合。100円未満は切り捨て、最低 100円）。"""
        return self._floor(self.balance(WALLET_OF[kind], self.month_start(day)) * BUDGET_RATE[kind])

    def unit(self, day: date) -> int:
        """勝負レースの1点の額（予算 ÷ 3）。"""
        return self._floor(self.budget(names.MATCH, day) / POINTS_PER_RACE)

    def day_cap(self, day: date) -> int:
        """1日に勝負用の財布から使える額の上限。"""
        return self._floor(self.balance(MATCH_WALLET, self.month_start(day)) * DAY_CAP_RATE)

    def stopped(self, day: date) -> bool:
        """勝負用の財布が初めの 70% を下回っているか（勝負レースを止めて線と買い方を見直す）。"""
        return self.balance(MATCH_WALLET, day) < self.initial()[MATCH_WALLET] * STOP_RATE

    @staticmethod
    def _floor(yen: float) -> int:
        return max(MIN_YEN, int(yen // YEN_UNIT) * YEN_UNIT)
