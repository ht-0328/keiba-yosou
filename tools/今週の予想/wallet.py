"""4つの財布（勝負用・ポリシー用・単勝・馬単用・組の期待値用）の残高と、参加の種類ごとの予算（設計書「買うレースと買い目を決める」08 の 1）。"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from yosou.review import ReviewStore, names

#: 財布の名前。単勝・馬単用は、当日の期待度「高」のレースの単勝と馬単（参加の種類 ``MATCH_WIN``）だけに使う。
#: 馬単は連敗が長く、複勝の勝負用と同じ財布にすると、勝負用の止まりの線（初めの 70%）を馬単の振れで割ってしまうので分ける。
#: 組の期待値用は、当日の予想で組の期待値が線以上の馬単・ワイド・3連複・3連単（参加の種類 ``MATCH_COMBO``）だけに使う。1日に買うレースが多く、
#: 連敗も長いので、ほかの財布の止まりの線をこの振れで割らないように分ける。
MATCH_WALLET, POLICY_WALLET, WIN_WALLET, COMBO_WALLET = "勝負用", "ポリシー用", "単勝・馬単用", "組の期待値用"
#: 参加の種類 → 出す財布。
WALLET_OF: dict[str, str] = {names.MATCH: MATCH_WALLET, names.POLICY_STAKES: POLICY_WALLET, names.POLICY_DAY: POLICY_WALLET,
                             names.MATCH_WIN: WIN_WALLET, names.MATCH_COMBO: COMBO_WALLET}
#: 予算の割合（残高に対して）。勝負レース 5%・ノルマ参加（重賞）3%・ノルマ参加（日）1.5%。
BUDGET_RATE: dict[str, float] = {names.MATCH: 0.05, names.POLICY_STAKES: 0.03, names.POLICY_DAY: 0.015}
#: 勝負レースの1点 = 予算 ÷ 3。1日に使う額の上限は勝負用の残高の 20%。財布が初めの 70% を下回ったら、その財布の買い目を止める。
POINTS_PER_RACE, DAY_CAP_RATE, STOP_RATE = 3, 0.20, 0.70
#: 単勝・馬単用と組の期待値用の、券種ごとの1点の額（その財布の月初の残高に対する割合）。どちらの財布も、券種ごとの振れ（1点 100円での
#: いちばん深い落ち込み）がそろう比で配り、財布の券種をまとめて 2016〜2026年の当日の予想の買い目で数えた、いちばん深い落ち込みが
#: 財布の 15%（止まりの線までの半分）に収まる割合を、切り下げた値にした（研究「レースの種類ごとの買い方」の docs/04 の買い方。
#: 数値は Git の対象外の reports/レースの種類ごとの買い方/）。100円に届かない券種は買わない。
#: 単勝・馬単用は、単勝（期待値）と期待度「高」の ◎ の馬単。単勝は1レース1点で落ち込みが浅く、馬単は 2016〜2018年の落ち込みが深い。
#: 初めの額の既定の 100,000円では単勝 300円だけになる（馬単は約 83万円から）。
#: 組の期待値用は、枠連・馬連・馬単・ワイド・3連複・3連単。初めの額の既定の 500,000円では、馬単 600円・馬連 500円・枠連 100円・ワイド 100円に
#: なる（3連単は約 101万円から、3連複は約 139万円から）。
POINT_RATE: dict[str, dict[str, float]] = {
    WIN_WALLET: {"単勝": 0.0037, "馬単": 0.00012},
    COMBO_WALLET: {"枠連": 0.00035, "馬連": 0.0011, "馬単": 0.0012, "ワイド": 0.00023, "3連複": 0.000072, "3連単": 0.000099},
}
#: 100円未満は切り捨て、最低 100円。
YEN_UNIT, MIN_YEN = 100, 100
#: 初めに入れる額の既定（設計書 08 の 1 の例。実際に買い始めるときに利用者が財布のファイルで決める）。
DEFAULT_INITIAL: dict[str, int] = {MATCH_WALLET: 100_000, POLICY_WALLET: 30_000, WIN_WALLET: 100_000, COMBO_WALLET: 500_000}
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
        if any(wallet not in saved for wallet in DEFAULT_INITIAL):   # 財布を足す前のファイルには、足した財布を既定の額で書き足す
            saved = {**DEFAULT_INITIAL, **saved}
            self._path.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
        return {wallet: int(saved[wallet]) for wallet in DEFAULT_INITIAL}

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

    def point_yen(self, ticket_type: str, day: date, wallet: str = WIN_WALLET) -> int:
        """単勝・馬単用か組の期待値用の財布で買う券種の1点の額（その財布の月初の残高 × ``POINT_RATE``。100円未満は切り捨て、
        100円に届かなければ 0 で買わない）。"""
        yen = self.balance(wallet, self.month_start(day)) * POINT_RATE[wallet][ticket_type]
        return int(yen // YEN_UNIT) * YEN_UNIT

    def stopped(self, day: date, wallet: str = MATCH_WALLET) -> bool:
        """財布が初めの 70% を下回っているか（その財布の買い目を止めて線と買い方を見直す）。"""
        return self.balance(wallet, day) < self.initial()[wallet] * STOP_RATE

    @staticmethod
    def _floor(yen: float) -> int:
        return max(MIN_YEN, int(yen // YEN_UNIT) * YEN_UNIT)
