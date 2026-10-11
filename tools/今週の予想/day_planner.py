"""1開催日の予想から、買うレース（勝負・ノルマ参加・買わない）と買い目の金額を決める（設計書「買うレースと買い目を決める」03・08 の 1）。"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any

import duckdb

from yosou.review import names
from yosou.shared.repository.place_pool_repository import PlacePoolRepository

from 今週の予想 import forecast_columns as columns
from 今週の予想.mark_rule import OUT_MARK
from 今週の予想.race_plan import NO_BET, PlacePick, RacePlan
from 今週の予想.ticket_rules import PLACE_LABEL, PLACE_VALUE_LINE
from 今週の予想.wallet import Wallet

#: 勝負レースの1日の上限（重賞は別枠。利用者の決定）。
RACES_PER_DAY = 3
#: 勝負レースから外す頭数（7頭以下は複勝が2着までになる）。
MIN_FIELD_SIZE = 8
#: 期待値がこれ以上の複勝は 2単位（ただしケリー基準の4分の1と、レースの予算を超えない）。
DOUBLE_VALUE_LINE = 1.40
#: ノルマ参加（重賞）で買う複勝の点数の上限と、ノルマ参加（日）の点数。
POLICY_STAKES_POINTS, POLICY_DAY_POINTS = 2, 1
#: 複勝1点の上限: その複勝プールの売上の見込み（100円 = 1票）の 0.5%。
POOL_SHARE_LIMIT = 0.005
#: 平地の重賞（障害の重賞は、障害を予想しないので最初から入らない）。
GRADED_CLASSES: tuple[str, ...] = ("G1", "G2", "G3")
NEWCOMER_CLASS = "新馬"


class DayPlanner:
    """1開催日の予想の結果（``RaceForecaster.forecast`` の辞書。前日か当日のもの）から、次の順で買うレースを決める。

    1. 平地の重賞は全部入れる。見込みの利益 E（複勝の期待値が線以上の買い目の Σ（期待値 − 1））が 0 より大きければ勝負、
       そうでなければノルマ参加（重賞。堅い重賞）。
    2. 重賞以外で、新馬戦・7頭以下を除いた E > 0 のレースを、E の大きい順に1日 3つまで勝負レースにする。
    3. 勝負も重賞も無い日は、最大の期待値 M がいちばん高いレースをノルマ参加（日）の予備にする。

    金額は財布（``Wallet``）の予算から。勝負は1点 = 予算 ÷ 3（期待値 1.40 以上は 2単位、ただしケリー基準の4分の1とレースの予算の中）、
    ノルマ参加（重賞）は予算を最大2点に分け、ノルマ参加（日）は1点。複勝1点はその複勝プールの売上の見込みの 0.5% まで。
    1日の勝負の合計が勝負用の残高の 20% を超えれば、E の小さい勝負レースから外す。勝負用の財布が初めの 70% を下回っていれば勝負レースは買わない。
    """

    def __init__(self, wallet: Wallet) -> None:
        self._wallet = wallet

    def plan(self, con: duckdb.DuckDBPyConnection, day: date, forecasts: list[dict[str, Any]]) -> list[RacePlan]:
        plans = [self._classify(forecast) for forecast in forecasts if forecast.get("odds_known")]
        plans = self._cap_matches(plans)
        if not any(plan.kind in (names.MATCH, names.POLICY_STAKES) for plan in plans):
            plans = self._with_reserve(plans)
        stopped = self._wallet.stopped(day)
        priced = [self._priced(con, day, plan, stopped) for plan in plans]
        return self._within_day_cap(priced, day)

    def _classify(self, forecast: dict[str, Any]) -> RacePlan:
        header = forecast.get("header", {})
        graded = str(header.get("クラス", "")) in GRADED_CLASSES
        picks = self._place_candidates(forecast)
        profit = sum(max(pick.value - 1.0, 0.0) for pick in picks if pick.value is not None and pick.value >= PLACE_VALUE_LINE)
        max_value = max((horse.get(columns.PLACE_VALUE) or 0.0 for horse in forecast["horses"]), default=None)
        base = RacePlan(forecast["rid"], forecast["title"], forecast["timing"], NO_BET, "", profit, max_value, graded, tuple(picks))
        if graded:
            if profit > 0:
                return replace(base, kind=names.MATCH, reason=f"平地の重賞で、見込みの利益 E = {profit:.2f}単位 > 0")
            return replace(base, kind=names.POLICY_STAKES, reason="平地の重賞で、期待値が線を超える複勝が無い（堅い重賞。ノルマ参加）")
        if str(header.get("クラス", "")) == NEWCOMER_CLASS:
            return replace(base, reason="新馬戦は勝負レースにしない（過去の走が無く、補正が効かない）")
        if (header.get("頭数") or 0) < MIN_FIELD_SIZE:
            return replace(base, reason="7頭以下は複勝が2着までになるので勝負レースにしない")
        if profit > 0:
            return replace(base, kind=names.MATCH, reason=f"見込みの利益 E = {profit:.2f}単位 > 0")
        return replace(base, reason="期待値が線（1.25）を超える複勝が無い")

    def _place_candidates(self, forecast: dict[str, Any]) -> list[PlacePick]:
        """複勝の候補: 消を除く全頭を複勝の期待値の高い順に（勝負レースは線以上の馬だけ、ノルマ参加は線に届かなくても上から買う）。
        オッズは、印のルールの複勝の買い目（線以上の馬）にあればその最低オッズ。"""
        odds = {int(ticket["horses"][0]): ticket.get("odds") for ticket in forecast.get("tickets", [])
                if ticket.get("rule") == PLACE_LABEL and not ticket.get("dropped")}
        dropped = {int(ticket["horses"][0]) for ticket in forecast.get("tickets", []) if ticket.get("rule") == PLACE_LABEL and ticket.get("dropped")}
        picks = []
        for horse in forecast["horses"]:
            horse_no, value = horse.get(columns.HORSE_NO), horse.get(columns.PLACE_VALUE)
            if horse_no is None or value is None or horse.get(columns.MARK) == OUT_MARK or int(horse_no) in dropped:
                continue
            picks.append(PlacePick(int(horse_no), horse.get(columns.PROBABILITY), float(value), odds.get(int(horse_no)), 0))
        return sorted(picks, key=lambda pick: -(pick.value or 0.0))

    def _cap_matches(self, plans: list[RacePlan]) -> list[RacePlan]:
        """重賞以外の勝負レースを E の大きい順に3つまで残す。"""
        others = sorted([plan for plan in plans if plan.kind == names.MATCH and not plan.graded], key=lambda plan: -plan.profit_units)
        dropped = {plan.rid for plan in others[RACES_PER_DAY:]}
        return [replace(plan, kind=NO_BET, reason=f"見込みの利益 E = {plan.profit_units:.2f}単位 だが、その日の上位{RACES_PER_DAY}つに入らない")
                if plan.rid in dropped else plan for plan in plans]

    def _with_reserve(self, plans: list[RacePlan]) -> list[RacePlan]:
        """勝負も重賞も無い日の予備（最大の期待値 M がいちばん高いレース）をノルマ参加（日）にする。"""
        eligible = [plan for plan in plans if plan.kind == NO_BET and plan.picks is not None and plan.max_value is not None
                    and "新馬" not in plan.reason and "7頭以下" not in plan.reason]
        if not eligible:
            return plans
        reserve = max(eligible, key=lambda plan: plan.max_value or 0.0)
        return [replace(plan, kind=names.POLICY_DAY, reason=f"勝負も重賞も無い日の予備（最大の期待値 M = {plan.max_value:.2f} がいちばん高い）")
                if plan.rid == reserve.rid else plan for plan in plans]

    def _priced(self, con: duckdb.DuckDBPyConnection, day: date, plan: RacePlan, stopped: bool) -> RacePlan:
        """参加の種類に合わせて、買う複勝と金額を決める。"""
        if plan.kind == NO_BET:
            return replace(plan, picks=())
        if plan.kind == names.MATCH and stopped:
            return replace(plan, kind=NO_BET, reason="勝負用の財布が初めの 70% を下回ったので、勝負レースを止めて線と買い方を見直す", picks=())
        budget = self._wallet.budget(plan.kind, day)
        pool_cap = self._pool_cap(con, plan.rid)
        if plan.kind == names.MATCH:
            picks = self._match_picks(plan, budget, self._wallet.unit(day), pool_cap, day)
        elif plan.kind == names.POLICY_STAKES:
            picks = self._policy_picks(plan, budget, POLICY_STAKES_POINTS, pool_cap)
        else:
            picks = self._policy_picks(plan, budget, POLICY_DAY_POINTS, pool_cap)
        return replace(plan, picks=tuple(picks), budget_yen=budget)

    def _match_picks(self, plan: RacePlan, budget: int, unit: int, pool_cap: int | None, day: date) -> list[PlacePick]:
        """勝負レース: 期待値が線以上の複勝を高い順に最大3点、1点 1単位（1.40 以上は 2単位。ケリー基準の4分の1とレースの予算の中）。"""
        picks, spent = [], 0
        balance = self._wallet.balance("勝負用", self._wallet.month_start(day))
        for pick in [pick for pick in plan.picks if pick.value is not None and pick.value >= PLACE_VALUE_LINE][:3]:
            yen = unit * (2 if pick.value >= DOUBLE_VALUE_LINE else 1)
            kelly = self._quarter_kelly(balance, pick)
            if kelly is not None:
                yen = min(yen, max(unit, kelly))
            yen = min(yen, budget - spent, pool_cap or yen)
            yen = int(yen // 100) * 100
            if yen < 100:
                break
            picks.append(replace(pick, yen=yen))
            spent += yen
        return picks

    def _policy_picks(self, plan: RacePlan, budget: int, points: int, pool_cap: int | None) -> list[PlacePick]:
        """ノルマ参加: 期待値の高い順に最大 ``points`` 点（線に届かなくても少なくとも1点）。予算を等分（100円未満は切り捨て）。"""
        chosen = list(plan.picks[:points])
        if not chosen:
            return []
        each = max(100, int(budget / len(chosen) // 100) * 100)
        if pool_cap is not None:
            each = max(100, min(each, pool_cap))
        return [replace(pick, yen=each) for pick in chosen]

    def _quarter_kelly(self, balance: int, pick: PlacePick) -> int | None:
        """ケリー基準の4分の1 = 残高 × （p × b − 1）÷（b − 1）÷ 4（p は3着以内の確率、b は見込みの払戻倍率）。出せなければ None。"""
        if pick.probability is None or pick.value is None or not pick.probability:
            return None
        payout = pick.value / pick.probability   # 期待値 = 確率 × 見込みの払戻倍率
        if payout <= 1.0:
            return 0
        return int(balance * (pick.probability * payout - 1.0) / (payout - 1.0) / 4)

    def _pool_cap(self, con: duckdb.DuckDBPyConnection, rid: str) -> int | None:
        votes = PlacePoolRepository(con).read(rid)
        return None if votes is None else int(votes * 100 * POOL_SHARE_LIMIT // 100) * 100

    def _within_day_cap(self, plans: list[RacePlan], day: date) -> list[RacePlan]:
        """勝負レースの合計が1日の上限を超えれば、E の小さいものから外す。"""
        cap = self._wallet.day_cap(day)
        matches = sorted([plan for plan in plans if plan.kind == names.MATCH], key=lambda plan: -plan.profit_units)
        total, kept = 0, set()
        for plan in matches:
            if total + plan.stake_yen <= cap:
                total += plan.stake_yen
                kept.add(plan.rid)
        return [replace(plan, kind=NO_BET, reason=f"{plan.reason}。ただし1日の上限（勝負用の残高の 20% = {cap:,}円）を超えるので外した", picks=())
                if plan.kind == names.MATCH and plan.rid not in kept else plan for plan in plans]
