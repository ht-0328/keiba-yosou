"""WIN5 の日の予測の結果を、表にする。"""

from __future__ import annotations

import pandas as pd

from 共通 import codes
from 共通.render import Table

from yosou.shared.dataset import HORSE_NAME, HORSE_NO
from yosou.shared.feature.group import WIN_ODDS

from ..formation import FormationChoice
from ..leg import EDGE, MARKET, SHARE
from ..payout import TICKET_YEN
from ..workflow import LegForecast, Win5Forecast

#: rid の中の競馬場コードとレース番号の位置。
_VENUE = slice(8, 10)
_RACE_NO = slice(14, 16)


class Win5ForecastTables:
    """設計書 04 の「4.」の出す表: (1) 日のまとめ、(2) 買う買い目、(3) 対象レースごとの全頭の表、(4) 予算の候補ごとのいちばん良い買い目。"""

    def __init__(self, forecast: Win5Forecast) -> None:
        self._forecast = forecast

    def tables(self) -> list[Table]:
        picks = self._forecast.choice.formation.legs
        legs = [self._leg_table(number, leg, leg_picks)
                for number, (leg, leg_picks) in enumerate(zip(self._forecast.legs, picks, strict=True), start=1)]
        return [self._summary(), self._formation(), *legs, self._budgets()]

    def _summary(self) -> Table:
        forecast, choice, judge, tiers = self._forecast, self._forecast.choice, self._forecast.judge, self._forecast.tiers
        races = " / ".join(self._race_label(leg.race_id) for leg in forecast.legs)
        rows = [
            ["開催日", forecast.day.race_date.isoformat()],
            ["対象レース", races],
            ["キャリーオーバー（円）", forecast.day.carry],
            ["発売票数の見積もり", round(forecast.pool.votes)],
            ["並べ方", forecast.ordering.label],
            [f"判断用の買い目（{tiers.judge}点）の日の期待値", round(judge.expected_value, 3)],
            ["買う日の線", forecast.line],
            ["本命の確率の積", f"{forecast.favorite_product:.4%}"],
            ["多く買う日の線", f"{tiers.favorite_line:.2%}"],
            ["判断", forecast.decision.label],
            ["段階", self._tier_text()],
            ["予算（点）", forecast.budget],
            ["点数", choice.formation.points],
            ["代金（円）", choice.stake],
            ["買い目のどれかが当たる確率", round(choice.hit_probability, 4)],
            ["日の期待値", round(choice.expected_value, 3)],
            ["配当の見積もりの式に使った当たり組の数", forecast.estimator_count],
        ]
        note = ("日の期待値 = 買い目の全部の組の（当たる確率 × 見積もりの配当）の合計 ÷ 代金。1 で元返し。"
                "買うかどうかは判断用の買い目の日の期待値で決め、多く買う日か少なく買う日かは本命の確率の積（5レースの本命のそろえた1着の確率のかけ算）で決める。"
                "見送りの日は、少なく買う日の予算の買い目を参考に出す。")
        return Table(["項目", "値"], rows, title=f"WIN5 {forecast.day.race_date.isoformat()} の日のまとめ", note=note)

    def _tier_text(self) -> str:
        """段階の説明（``多く買う日（100点・10,000円まで）`` の形）。"""
        tiers, decision = self._forecast.tiers, self._forecast.decision
        if not decision.buys:
            return f"見送り（参考の買い目は少なく買う日の予算 {tiers.small}点）"
        budget = tiers.budget_for(decision)
        return f"{decision.tier_label}買う日（予算 {budget}点・{budget * TICKET_YEN:,}円まで）"

    def _formation(self) -> Table:
        rows = [[f"{number}レース目", self._race_label(leg.race_id), leg.choice.model.label, len(picks), " ".join(str(n) for n in picks)]
                for number, (leg, picks) in enumerate(zip(self._forecast.legs, self._forecast.choice.formation.legs, strict=True), start=1)]
        title = "買う買い目（フォーメーション）" if self._forecast.decision.buys else "参考の買い目（フォーメーション。見送り）"
        return Table(["何レース目", "レース", "使った確率", "頭数", "馬番"], rows, title=title,
                     note=f"{self._forecast.choice.formation.sizes_text()} = {self._forecast.choice.formation.points}点")

    def _leg_table(self, number: int, leg: LegForecast, picks: tuple[int, ...]) -> Table:
        ranked = leg.table.sort_values(SHARE, ascending=False, kind="stable")
        rows = [self._horse_row(horse, picks) for _, horse in ranked.iterrows()]
        return Table(["馬番", "馬名", "単勝オッズ", SHARE, MARKET, EDGE, "買い目"], rows,
                     title=f"{number}レース目 {self._race_label(leg.race_id)}（{leg.choice.model.label}）",
                     note=leg.choice.reason)

    def _horse_row(self, horse: pd.Series, picks: tuple[int, ...]) -> list[object]:
        number = int(horse[HORSE_NO])
        return [number, horse[HORSE_NAME], float(horse[WIN_ODDS]), round(float(horse[SHARE]), 4), round(float(horse[MARKET]), 4),
                round(float(horse[EDGE]), 3), "○" if number in picks else ""]

    def _budgets(self) -> Table:
        rows = [self._budget_row(budget, choice) for budget, choice in sorted(self._forecast.by_budget.items())]
        tiers = self._forecast.tiers
        return Table(["予算（点）", "点数", "頭数の並び", "当たる確率", "日の期待値", "使い方"], rows, title="予算の候補ごとの、いちばん良い買い目",
                     note=f"並べ方は {self._forecast.ordering.label}。使い方: 判断用 {tiers.judge}点・少なく買う日 {tiers.small}点・多く買う日 {tiers.large}点。")

    def _budget_row(self, budget: int, choice: FormationChoice) -> list[object]:
        return [budget, choice.formation.points, choice.formation.sizes_text(), round(choice.hit_probability, 4),
                round(choice.expected_value, 3), self._usage(budget)]

    def _usage(self, budget: int) -> str:
        """その予算が段階の予算のどれか（判断用・少なく買う日・多く買う日。重なれば「・」でつなぐ）。"""
        tiers = self._forecast.tiers
        names = [name for name, each in (("判断用", tiers.judge), ("少なく買う日", tiers.small), ("多く買う日", tiers.large)) if each == budget]
        return "・".join(names)

    def _race_label(self, race_id: str) -> str:
        """``東京11R`` の形。"""
        return f"{codes.venue_name(race_id[_VENUE])}{int(race_id[_RACE_NO])}R"
