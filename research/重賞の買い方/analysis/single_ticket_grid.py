"""3回目: 重賞の単勝・複勝（単系）の買い方の候補を並べ、選ぶ期間の回収率・下の端と、確かめる期間の回収率を数える（docs/04）。"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
import pandas as pd

#: 候補の線（docs/04 の 3）。
PLACE_LINES = (1.0, 1.05, 1.1, 1.15, 1.2)
WIN_LINES = (0.9, 1.0, 1.05, 1.1, 1.2)
PLACE_MIN_POPULARITY = (1, 2, 4, 6)
WIN_MIN_POPULARITY = (1, 2, 4)
PLACE_ODDS_CAPS = (None, 5.0, 10.0)
WIN_ODDS_CAPS = (None, 5.0, 10.0, 20.0)
MIN_FIELDS = (0, 12, 16)
#: 選ぶ候補の当たりの下限（docs/04 の 3）。
MIN_HITS = 30
BOOTSTRAP = 2000


@dataclass(frozen=True)
class SingleRule:
    """単勝か複勝を、期待値の線・人気の下限・オッズの上限・頭数の下限で選ぶ買い方。1頭 1点。"""

    ticket: str          # "単勝" か "複勝"
    line: float          # 期待値の線（単勝は win_value、複勝は place_value）
    min_popularity: int  # この番人気以下（数が大きい側）だけ
    odds_cap: float | None  # 単勝オッズ（複勝は複勝の最低オッズ）の上限
    min_field: int       # 頭数の下限

    @property
    def label(self) -> str:
        odds = "上限なし" if self.odds_cap is None else f"{self.odds_cap:g}倍以下"
        popularity = "全頭" if self.min_popularity <= 1 else f"{self.min_popularity}番人気以下"
        field = "頭数を問わない" if self.min_field == 0 else f"{self.min_field}頭以上"
        return f"{self.ticket}: 期待値 {self.line:.2f} 以上・{popularity}・オッズ {odds}・{field}"

    def chosen(self, horses: pd.DataFrame) -> pd.Series:
        value, odds = ("win_value", "win_odds") if self.ticket == "単勝" else ("place_value", "place_odds_low")
        mask = (horses[value] >= self.line) & (horses["popularity"] >= self.min_popularity) & (horses["field_size"] >= self.min_field)
        if self.odds_cap is not None:
            mask &= horses[odds] <= self.odds_cap
        return mask

    @property
    def payout(self) -> str:
        return "win_payout" if self.ticket == "単勝" else "place_payout"


class SingleTicketGrid:
    """重賞の馬の表（1行 = 1頭。列 race_id・race_date・popularity・field_size・win_value・win_odds・win_payout・
    place_value・place_odds_low・place_payout）から、候補ごとの成績を数える。払戻は 100円あたり。"""

    def __init__(self, seed: int = 0) -> None:
        self._rng = np.random.default_rng(seed)

    @staticmethod
    def rules() -> list[SingleRule]:
        place = [SingleRule("複勝", *combo) for combo in itertools.product(PLACE_LINES, PLACE_MIN_POPULARITY, PLACE_ODDS_CAPS, MIN_FIELDS)]
        win = [SingleRule("単勝", line, popularity, cap, 0) for line, popularity, cap in itertools.product(WIN_LINES, WIN_MIN_POPULARITY, WIN_ODDS_CAPS)]
        return place + win

    def score(self, horses: pd.DataFrame, rule: SingleRule) -> dict[str, float]:
        """点・レース・当たり・回収率・下の端（開催日を単位にしたブートストラップの 5% 点）・的中率（当たった点 ÷ 点）。"""
        bought = horses[rule.chosen(horses)]
        payout = bought[rule.payout].fillna(0).astype(float)
        points, hits = len(bought), int((payout > 0).sum())
        if points == 0:
            return {"点": 0, "レース": 0, "当たり": 0, "回収率": np.nan, "下の端": np.nan, "的中率": np.nan}
        return {"点": points, "レース": bought["race_id"].nunique(), "当たり": hits, "回収率": payout.sum() / points / 100,
                "下の端": self._lower(bought["race_date"], payout), "的中率": hits / points}

    def yearly(self, horses: pd.DataFrame, rule: SingleRule) -> pd.DataFrame:
        bought = horses[rule.chosen(horses)]
        payout = bought[rule.payout].fillna(0).astype(float)
        frame = pd.DataFrame({"年": pd.to_datetime(bought["race_date"]).dt.year, "払戻": payout, "当たり": payout > 0})
        return frame.groupby("年").agg(点=("払戻", "size"), 回収率=("払戻", lambda s: s.sum() / len(s) / 100), 的中率=("当たり", "mean")).reset_index()

    def _lower(self, race_dates: pd.Series, payout: pd.Series) -> float:
        days = pd.DataFrame({"day": race_dates.to_numpy(), "stake": 1.0, "payout": payout.to_numpy() / 100}).groupby("day").sum()
        stake, back = days["stake"].to_numpy(), days["payout"].to_numpy()
        index = self._rng.integers(0, len(stake), (BOOTSTRAP, len(stake)))
        return float(np.quantile(back[index].sum(axis=1) / stake[index].sum(axis=1), 0.05))
