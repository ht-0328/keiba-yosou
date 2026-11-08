"""テスト用の架空の WIN5（合成DB に入れる行の束）。値はすべて乱数で作った架空のもの。"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta

from 合成DB import synth

#: 乱数の種。
SEED = 20261108
#: 1レースの頭数・競馬場・対象レースのレース番号（発売の順）。
FIELD_SIZE = 8
VENUE = "05"
RACE_NUMBERS = ("07", "08", "09", "10", "11")
#: 頭数ぶんの単勝オッズ（倍）。レースごとに馬番へくじで割り当てる。
ODDS_TABLE = (2.5, 4.0, 6.0, 9.0, 13.0, 20.0, 35.0, 60.0)
#: 過去の WIN5 の日曜（毎週）の数と、最初の日曜。4回に1回、前の日の土曜にも WIN5 がある。
SUNDAY_COUNT = 20
FIRST_SUNDAY = date(2024, 1, 7)
SATURDAY_EVERY = 4
#: 発売票数（日曜・土曜）。
SUNDAY_VOTES = 4_000_000
SATURDAY_VOTES = 1_500_000
#: 払戻の作り方（log(払戻) = 切片 + 傾き × 市場の組の確率の逆数の対数 + 外れ）。
PAYOUT_INTERCEPT = 3.5
PAYOUT_SLOPE = 1.0
PAYOUT_NOISE = 0.2
#: 的中無の日・返還（取消の馬あり）の日の、何番目の日曜か。
NO_HIT_SUNDAY = 5
REFUND_SUNDAY = 8
#: 取消になる馬（返還の日の3レース目）。
SCRATCHED_LEG, SCRATCHED_HORSE = 3, 8
#: 予想する日（過去の WIN5 の後の日曜）。キャリーオーバーあり。4レース目が障害、2レース目は馬体重がまだ（前日の確率）。
FORECAST_DAY = FIRST_SUNDAY + timedelta(weeks=SUNDAY_COUNT)
FORECAST_CARRY = 300_000_000
JUMP_LEG = 4
UNWEIGHED_LEG = 2
FORECAST_ANNOUNCED = "00000930"
#: 締め切り前のオッズの無い日（木曜しか選べないので止まる）。
NO_ODDS_DAY = FORECAST_DAY + timedelta(weeks=1)
#: 障害のトラックコード（障害・芝）。
JUMP_TRACK = "54"


class Win5Sample:
    """過去の WIN5（日曜 20回と土曜 5回。的中無の回と、取消で返還のある回を含む）と、予想する日・オッズの無い日の行を作る。

    各レースは8頭。単勝オッズは決まった8つの値を馬番にくじで割り当て、勝ち馬はオッズから見た勝率のくじで決める。
    払戻は「市場の組の確率の逆数」の1次式（対数）に外れを足して作るので、配当の見積もりの式がその傾きを当て直せる。
    ``odds[(開催日, 何レース目)]`` に馬番 → 単勝オッズ、``winners[開催日]`` に当たり組を残す（テストが答えに使う）。
    """

    def __init__(self) -> None:
        self._rng = random.Random(SEED)
        self.sample = synth.Sample()
        self.odds: dict[tuple[date, int], dict[int, float]] = {}
        self.winners: dict[date, tuple[int, ...]] = {}

    def build(self) -> synth.Sample:
        for week in range(SUNDAY_COUNT):
            sunday = FIRST_SUNDAY + timedelta(weeks=week)
            if week % SATURDAY_EVERY == 0:
                self._add_past_day(sunday - timedelta(days=1), week, saturday=True)
            self._add_past_day(sunday, week, saturday=False)
        self._add_forecast_day(FORECAST_DAY, announced=True)
        self._add_forecast_day(NO_ODDS_DAY, announced=False)
        return self.sample

    def _add_past_day(self, day: date, week: int, saturday: bool) -> None:
        text = day.strftime("%Y%m%d")
        winners = []
        for leg, race_no in enumerate(RACE_NUMBERS, start=1):
            race_row = synth.race(text, race_no, venue=VENUE, field_size=f"{FIELD_SIZE:02d}", entries=f"{FIELD_SIZE:02d}")
            self.sample.ra.append(race_row)
            self.sample.win5_races.append(synth.win5_race(text, leg, race_row))
            scratched = SCRATCHED_HORSE if (not saturday and week == REFUND_SUNDAY and leg == SCRATCHED_LEG) else None
            winners.append(self._add_finished_runners(day, leg, race_row, scratched))
        combo = tuple(winners)
        self.winners[day] = combo
        votes = SATURDAY_VOTES if saturday else SUNDAY_VOTES
        no_hit = not saturday and week == NO_HIT_SUNDAY
        refunded = not saturday and week == REFUND_SUNDAY
        self.sample.win5.append(synth.win5_day(text, votes=votes, no_hit=no_hit, refunded=refunded))
        payout = 0 if no_hit else self._payout(day, combo, votes)
        hit_votes = 0 if no_hit else max(1, int(votes * 100 * 0.7 // payout))
        self.sample.win5_payouts.append(synth.win5_payout(text, "".join(f"{n:02d}" for n in combo), payout, hit_votes))

    def _add_finished_runners(self, day: date, leg: int, race_row: dict[str, str], scratched: int | None) -> int:
        """終わったレースの8頭。勝ち馬の馬番を返す。``scratched`` の馬は出走取消（オッズ無し）。"""
        odds = self._draw_odds()
        running = {number: value for number, value in odds.items() if number != scratched}
        self.odds[(day, leg)] = running
        winner = self._draw_winner(running)
        ranks = sorted(running, key=lambda number: running[number])
        for number in range(1, FIELD_SIZE + 1):
            self.sample.se.append(self._finished_runner(race_row, number, running, ranks, winner))
        return winner

    def _finished_runner(self, race_row: dict[str, str], number: int, running: dict[int, float], ranks: list[int],
                         winner: int) -> dict[str, str]:
        if number not in running:
            return synth.runner(race_row, number, 0, 0, abnormal="1", odds="----")
        popularity = ranks.index(number) + 1
        others = [each for each in ranks if each != winner]
        finish = 1 if number == winner else others.index(number) + 2
        return synth.runner(race_row, number, popularity, finish, odds=f"{round(running[number] * 10):04d}")

    def _add_forecast_day(self, day: date, announced: bool) -> None:
        """予想する日（出馬表と締め切り前のオッズ。WIN5 は速報の詳細発表時の版）。"""
        text = day.strftime("%Y%m%d")
        for leg, race_no in enumerate(RACE_NUMBERS, start=1):
            track = JUMP_TRACK if leg == JUMP_LEG else "11"
            race_row = synth.race(text, race_no, venue=VENUE, track=track, stage="2", field_size="00", entries=f"{FIELD_SIZE:02d}")
            self.sample.ra.append(race_row)
            self.sample.win5_races.append(synth.win5_race(text, leg, race_row))
            odds = self._draw_odds()
            self.odds[(day, leg)] = odds
            weight = "" if leg == UNWEIGHED_LEG else "480"
            for number in range(1, FIELD_SIZE + 1):
                self.sample.se.append(synth.runner(race_row, number, 0, 0, odds="0000", weight=weight, change=("", "")))
            if announced:
                self._add_announced_odds(race_row, odds)
        self.sample.win5.append(synth.win5_day(text, stage="1", votes=0, carry=FORECAST_CARRY))

    def _add_announced_odds(self, race_row: dict[str, str], odds: dict[int, float]) -> None:
        """締め切り前の単勝オッズ（データ区分 3 の断面）。"""
        self.sample.odds.append(("o1", synth.odds_header(race_row, "o1", stage="3", announced=FORECAST_ANNOUNCED)))
        for number, value in odds.items():
            self.sample.odds.append(("o1__単勝オッズ", synth.odds_row(race_row, "o1__単勝オッズ", f"{number:02d}", round(value * 10),
                                                                  seq=number, announced=FORECAST_ANNOUNCED)))

    def _draw_odds(self) -> dict[int, float]:
        values = list(ODDS_TABLE)
        self._rng.shuffle(values)
        return {number: value for number, value in enumerate(values, start=1)}

    def _draw_winner(self, odds: dict[int, float]) -> int:
        numbers = list(odds)
        return self._rng.choices(numbers, weights=[1.0 / odds[number] for number in numbers])[0]

    def _payout(self, day: date, combo: tuple[int, ...], votes: int) -> int:
        """100円あたりの払戻（市場の組の確率の逆数の1次式に外れを足し、払戻に回るお金で頭打ち）。"""
        inverse = 1.0 / market_combo_probability(self.odds, day, combo)
        value = math.exp(PAYOUT_INTERCEPT + PAYOUT_SLOPE * math.log(inverse) + self._rng.gauss(0.0, PAYOUT_NOISE))
        return int(min(value, votes * 100 * 0.7))


def market_combo_probability(odds: dict[tuple[date, int], dict[int, float]], day: date, combo: tuple[int, ...]) -> float:
    """組の5頭の、オッズから見た勝率のかけ算（テストの答え）。"""
    shares = []
    for leg, number in enumerate(combo, start=1):
        leg_odds = odds[(day, leg)]
        shares.append((1.0 / leg_odds[number]) / sum(1.0 / value for value in leg_odds.values()))
    return math.prod(shares)
