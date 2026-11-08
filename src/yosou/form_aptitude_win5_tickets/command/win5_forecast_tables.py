"""WIN5 の日の予測の結果を、表にする。"""

from __future__ import annotations

import pandas as pd

from 共通 import codes
from 共通.render import Table

from yosou.shared.dataset import HORSE_NAME, HORSE_NO
from yosou.shared.feature.group import WIN_ODDS

from ..formation import FormationChoice
from ..leg import EDGE, MARKET, SHARE
from ..workflow import LegForecast, Win5Forecast

#: rid の中の競馬場コードとレース番号の位置。
_VENUE = slice(8, 10)
_RACE_NO = slice(14, 16)


class Win5ForecastTables:
    """設計書 04 の「4.」の出す表: (1) 日のまとめ、(2) 選んだ買い目、(3) 対象レースごとの全頭の表、(4) 予算の候補ごとのいちばん良い買い目。"""

    def __init__(self, forecast: Win5Forecast) -> None:
        self._forecast = forecast

    def tables(self) -> list[Table]:
        picks = self._forecast.choice.formation.legs
        legs = [self._leg_table(number, leg, leg_picks)
                for number, (leg, leg_picks) in enumerate(zip(self._forecast.legs, picks, strict=True), start=1)]
        return [self._summary(), self._formation(), *legs, self._budgets()]

    def _summary(self) -> Table:
        forecast, choice = self._forecast, self._forecast.choice
        races = " / ".join(self._race_label(leg.race_id) for leg in forecast.legs)
        rows = [
            ["開催日", forecast.day.race_date.isoformat()],
            ["対象レース", races],
            ["キャリーオーバー（円）", forecast.day.carry],
            ["発売票数の見積もり", round(forecast.pool.votes)],
            ["並べ方", forecast.ordering.label],
            ["予算（点）", forecast.budget],
            ["点数", choice.formation.points],
            ["金額（円）", choice.stake],
            ["買い目のどれかが当たる確率", round(choice.hit_probability, 4)],
            ["日の期待値", round(choice.expected_value, 3)],
            ["買う日の線", forecast.line],
            ["判断", forecast.decision.label],
            ["配当の見積もりの式に使った当たり組の数", forecast.estimator_count],
        ]
        return Table(["項目", "値"], rows, title=f"WIN5 {forecast.day.race_date.isoformat()} の日のまとめ",
                     note="日の期待値 = 買い目の全部の組の（当たる確率 × 見積もりの配当）の合計 ÷ 金額。1 で元返し。")

    def _formation(self) -> Table:
        rows = [[f"{number}レース目", self._race_label(leg.race_id), leg.choice.model.label, len(picks), " ".join(str(n) for n in picks)]
                for number, (leg, picks) in enumerate(zip(self._forecast.legs, self._forecast.choice.formation.legs, strict=True), start=1)]
        return Table(["何レース目", "レース", "使った確率", "頭数", "馬番"], rows, title="選んだ買い目（フォーメーション）",
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
        return Table(["予算（点）", "点数", "頭数の並び", "当たる確率", "日の期待値"], rows, title="予算の候補ごとの、いちばん良い買い目",
                     note=f"並べ方は {self._forecast.ordering.label}。")

    def _budget_row(self, budget: int, choice: FormationChoice) -> list[object]:
        return [budget, choice.formation.points, choice.formation.sizes_text(), round(choice.hit_probability, 4),
                round(choice.expected_value, 3)]

    def _race_label(self, race_id: str) -> str:
        """``東京11R`` の形。"""
        return f"{codes.venue_name(race_id[_VENUE])}{int(race_id[_RACE_NO])}R"
