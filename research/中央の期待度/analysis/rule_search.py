"""◎ の選び方を広く変えて（確率の寄せ方・選ぶときのオッズの効かせ方・オッズの上下限・1番人気を外すか）、全等級で ◎ の単勝回収率が 100% を超える組を探す。"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd

from yosou.shared.race_grade import GRADES

#: 調べる値（探す期間だけで選ぶ）。
ALPHAS: tuple[float, ...] = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6)
BETAS: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25)
MIN_ODDS: tuple[float, ...] = (1.0, 2.0, 3.0, 5.0)
MAX_ODDS: tuple[float, ...] = (10.0, 20.0, 30.0, 50.0, 100.0, 1000.0)
SKIP_FAVORITE: tuple[bool, ...] = (False, True)
WEIGHTS: tuple[float, ...] = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0)
#: 等級ごとのレースの割合（上から S・A・B。残りが C）。
SHARES: tuple[tuple[float, float, float], ...] = ((0.20, 0.30, 0.30), (0.25, 0.25, 0.25))
#: ◎ が付かないレースをこの割合より多く出す決め方は使わない（全レースに ◎ を付ける前提）。
MIN_COVERAGE = 0.99


@dataclass(frozen=True)
class Rule:
    """◎ の選び方。確率 = (1 − alpha) × モデルの1着の確率 ＋ alpha × オッズの見立て。◎ = 単勝オッズが min_odds 以上 max_odds 以下（1番人気を外すなら外して）の馬のうち、
    確率 × オッズ^beta が最大の馬（beta 0 は確率1位、1 は期待値1位）。"""

    alpha: float
    beta: float
    min_odds: float
    max_odds: float
    skip_favorite: bool

    @property
    def label(self) -> str:
        favorite = "・1番人気を外す" if self.skip_favorite else ""
        top = "なし" if self.max_odds >= 1000 else f"{self.max_odds:g}倍"
        return f"寄せ {self.alpha:g}・オッズの効き {self.beta:g}・{self.min_odds:g}倍〜{top}{favorite}"


@dataclass(frozen=True)
class Combo:
    """◎ の選び方 × 期待度の重み × 等級の割合の結果。``search``・``check`` は等級 → (勝率, 単勝回収率, 複勝回収率, レース数)。"""

    rule: Rule
    weight: float
    shares: tuple[float, float, float]
    lines: tuple[float, float, float]
    coverage: float
    search_all: float
    check_all: float
    search: dict[str, tuple[float, float, float, int]]
    check: dict[str, tuple[float, float, float, int]]

    @staticmethod
    def passes(rates: dict[str, tuple[float, float, float, int]]) -> bool:
        """どの等級でも単勝回収率が 100% を超え、C → S の順に勝率と単勝回収率が真に上がる。"""
        if any(grade not in rates for grade in GRADES):
            return False
        ordered = [rates[grade] for grade in reversed(GRADES)]
        return all(rate[1] > 1.0 for rate in ordered) and all(a[0] < b[0] and a[1] < b[1] for a, b in zip(ordered, ordered[1:], strict=False))

    @staticmethod
    def lowest(rates: dict[str, tuple[float, float, float, int]]) -> float:
        return min(rates[grade][1] for grade in GRADES) if all(grade in rates for grade in GRADES) else 0.0


class RuleSearch:
    """``rows`` は印を付けた全頭の行（列 ``year`` つき）。``search_years`` の年だけで線を決めて組を比べ、残りの年（確かめる期間）の成績も添える。"""

    def __init__(self, rows: pd.DataFrame, search_years: Sequence[int]) -> None:
        frame = rows.dropna(subset=["win_probability", "win_odds", "market_win"]).copy()
        frame = frame[frame["mark"] != "消"]
        self._races = rows["race_id"].nunique()
        self._frame = frame.reset_index(drop=True)
        self._race_code = pd.factorize(self._frame["race_id"])[0]
        self._search = self._frame["year"].isin(list(search_years)).to_numpy()
        self._odds = self._frame["win_odds"].astype(float).to_numpy()
        self._model = self._frame["win_probability"].astype(float).to_numpy()
        self._market = self._frame["market_win"].astype(float).to_numpy()
        self._popularity = self._frame["popularity"].astype(float).to_numpy()
        self._finish = self._frame["finish"].astype(float).to_numpy()
        self._win_payout = self._frame["win_payout"].astype(float).to_numpy()
        self._place_payout = self._frame["place_payout"].astype(float).to_numpy()

    @staticmethod
    def rules() -> Iterator[Rule]:
        for alpha, beta, low, high, skip in product(ALPHAS, BETAS, MIN_ODDS, MAX_ODDS, SKIP_FAVORITE):
            if low < high:
                yield Rule(alpha, beta, low, high, skip)

    def tops(self, rule: Rule) -> tuple[np.ndarray, np.ndarray]:
        """（◎ の行の番号, ◎ の寄せた確率）。"""
        probability = (1 - rule.alpha) * self._model + rule.alpha * self._market
        ok = (self._odds >= rule.min_odds) & (self._odds <= rule.max_odds)
        if rule.skip_favorite:
            ok &= self._popularity != 1
        index = np.flatnonzero(ok)
        select = np.log(np.maximum(probability[index], 1e-9)) + rule.beta * np.log(self._odds[index])
        order = np.lexsort((-select, self._race_code[index]))
        sorted_index = index[order]
        first = np.ones(len(sorted_index), bool)
        first[1:] = self._race_code[sorted_index][1:] != self._race_code[sorted_index][:-1]
        chosen = sorted_index[first]
        return chosen, probability[chosen]

    def combos(self, rule: Rule) -> list[Combo]:
        chosen, probability = self.tops(rule)
        coverage = len(chosen) / self._races
        if coverage < MIN_COVERAGE:
            return []
        value = probability * self._odds[chosen]
        search = self._search[chosen]
        all_search, all_check = self._back(chosen[search]), self._back(chosen[~search])
        out = []
        for weight, shares in product(WEIGHTS, SHARES):
            score = probability + weight * (value - 1.0)
            s, a, b = shares
            lines = tuple(float(np.quantile(score[search], q)) for q in (1 - s, 1 - s - a, 1 - s - a - b))
            grade = np.select([score >= lines[0], score >= lines[1], score >= lines[2]], ["S", "A", "B"], "C")
            out.append(Combo(rule, weight, shares, lines, coverage, all_search, all_check,
                             self._rates(chosen[search], grade[search]), self._rates(chosen[~search], grade[~search])))
        return out

    def _back(self, rows: np.ndarray) -> float:
        return float(self._win_payout[rows].sum() / (100.0 * len(rows))) if len(rows) else 0.0

    def _rates(self, rows: np.ndarray, grade: np.ndarray) -> dict[str, tuple[float, float, float, int]]:
        out = {}
        for name in GRADES:
            part = rows[grade == name]
            if len(part):
                out[name] = (float((self._finish[part] == 1).mean()), float(self._win_payout[part].sum() / (100.0 * len(part))),
                             float(self._place_payout[part].sum() / (100.0 * len(part))), int(len(part)))
        return out
