"""公開ルール（全レースと勝負の2段）の成績の表（期間ごと・年ごと・勝負の線を動かしたとき）を作る。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from 共通.render import Table

#: 選ぶのに使った期間の最後の年（これより後が確かめる期間）。
CHOSEN_LAST_YEAR = 2023
#: 勝負の線を動かす表の線。
LINES = (1.15, 1.2, 1.225, 1.25, 1.275, 1.3, 1.35)
#: 開催日を引き直す回数と、「運が悪いほう」の端（下から 5%）。
_DRAWS, _LOW = 3000, 5.0


@dataclass(frozen=True)
class TierReport:
    """``final`` は確定オッズで決めたレースごとの表、``snapshot`` は締め切り前の断面で決めた表（どちらも ``PublicBets.races``）。
    全レースの段は ◎ の単勝 100円、勝負の段は直した ◎ の期待値が ``line`` 以上のレースの単勝と馬単 ◎→相手（各 100円）。払戻は確定の払戻。"""

    final: pd.DataFrame
    snapshot: pd.DataFrame
    line: float
    snapshot_label: str = "10分前のオッズ"

    def tables(self) -> list[Table]:
        return [self.periods(), self.years(), self.lines()]

    def periods(self) -> Table:
        chosen, checked = self.final[self.final["year"] <= CHOSEN_LAST_YEAR], self.final[self.final["year"] > CHOSEN_LAST_YEAR]
        parts = [(f"確定・{chosen['year'].min()}〜{CHOSEN_LAST_YEAR}年", chosen), (f"確定・{CHOSEN_LAST_YEAR + 1}年〜", checked),
                 ("確定・全部", self.final), (self.snapshot_label, self.snapshot)]
        rows = [[name, step, *_summary(part, step, self.line)] for name, part in parts for step in ("全レース", "勝負")]
        columns = ["期間", "段", "開催日", "買ったレース", "1開催日の平均", "当たったレース", "的中率", "回収率", "運が悪いと（下から 5%）"]
        return Table(columns, rows, title=f"期間ごと（勝負 = 直した ◎ の期待値 {self.line:.2f} 以上で、単勝 ◎ と馬単 ◎→相手3頭）",
                     note="払戻はどれも確定の払戻。運が悪いと = 開催日を引き直したときの回収率の下の端")

    def years(self) -> Table:
        rows = []
        for year, part in self.final.groupby("year"):
            every, shobu = _summary(part, "全レース", self.line), _summary(part, "勝負", self.line)
            rows.append([year, every[1], every[5], *shobu[1:6]])
        return Table(["年", "全レース・買ったレース", "全レース・回収率", "勝負・買ったレース", "勝負・1開催日の平均", "勝負・当たったレース", "勝負・的中率",
                      "勝負・回収率"], rows, title="年ごと（確定オッズ）")

    def lines(self) -> Table:
        chosen, checked = self.final[self.final["year"] <= CHOSEN_LAST_YEAR], self.final[self.final["year"] > CHOSEN_LAST_YEAR]
        rows = [[f"{line:.3f}", *(_rate(part, line) for part in (chosen, checked, self.snapshot))] for line in LINES]
        return Table(["勝負の線", "選ぶのに使った期間", "確かめる期間", self.snapshot_label], rows, title="勝負の線を動かしたとき（回収率・1開催日のレース数）",
                     note="公開ルールの線だけが良く、周りが崩れていないかを見る")


def _bets(races: pd.DataFrame, step: str, line: float) -> pd.DataFrame:
    """段ごとの、1行 = 1レースの投資と払戻（列 ``stake``・``back``・``race_date``）。"""
    if step == "全レース":
        return pd.DataFrame({"race_date": races["race_date"], "stake": 100.0, "back": races["win_back"].astype(float)})
    picked = races[races["value"] >= line]
    return pd.DataFrame({"race_date": picked["race_date"], "stake": 100.0 * (1 + picked["exacta_points"]),
                         "back": (picked["win_back"] + picked["exacta_back"]).astype(float)})


def _summary(races: pd.DataFrame, step: str, line: float) -> list:
    """開催日・買ったレース・1開催日の平均・当たったレース・的中率・回収率・運が悪いと。"""
    bets = _bets(races, step, line)
    days = races["race_date"].nunique()
    if bets.empty:
        return [days, 0, "0.0", 0, "-", "-", "-"]
    hits = int((bets["back"] > 0).sum())
    return [days, len(bets), f"{len(bets) / max(days, 1):.1f}", hits, f"{hits / len(bets):.1%}", f"{bets['back'].sum() / bets['stake'].sum():.1%}",
            f"{_low(bets):.1%}"]


def _rate(races: pd.DataFrame, line: float) -> str:
    bets = _bets(races, "勝負", line)
    if bets.empty:
        return "-"
    return f"{bets['back'].sum() / bets['stake'].sum():.1%}（{len(bets) / max(races['race_date'].nunique(), 1):.1f}）"


def _low(bets: pd.DataFrame) -> float:
    """開催日を引き直したときの回収率の、下から ``_LOW`` % の値。"""
    days = bets.groupby("race_date")[["stake", "back"]].sum()
    draws = np.random.default_rng(1).integers(0, len(days), (_DRAWS, len(days)))
    returns = days["back"].to_numpy()[draws].sum(axis=1) / days["stake"].to_numpy()[draws].sum(axis=1)
    return float(np.percentile(returns, _LOW))
