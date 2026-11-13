"""結果側の様子（ペース・位置取り・1番人気の着順・着差）を、人気薄の勝ちと全部の勝ちで比べる表。理解のためだけに使う。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .cells import percent

#: 様子（名前 → 勝ち馬の行から真偽を作る関数）。
ASPECTS: dict[str, Callable[[pd.DataFrame], pd.Series]] = {
    "前半が速かった（ハイペース。前後半の差がいつもより 0.5秒以上前寄り）": lambda w: w["pace_gap"] < -0.5,
    "前半が遅かった（スロー。いつもより 0.5秒以上後ろ寄り）": lambda w: w["pace_gap"] > 0.5,
    "勝ち馬が4コーナー3番手以内（前残り）": lambda w: w["corner4"] <= 3,
    "勝ち馬の上がり3ハロンが3位以内": lambda w: w["last3f_rank"] <= 3,
    "勝ち馬が4コーナー7番手以下から上がり3位以内（差し切り）": lambda w: (w["corner4"] >= 7) & (w["last3f_rank"] <= 3),
    "1番人気が4着以下": lambda w: w["favorite_finish"] >= 4,
    "2着との差が 0.3秒以上（完勝）": lambda w: w["second_gap"] >= 0.3,
    "2着との差が 0.0秒（ハナ・アタマ差）": lambda w: w["second_gap"] <= 0.0,
    "馬場が稍重〜不良": lambda w: w["condition"] != "良",
}


@dataclass(frozen=True)
class OutcomeSideTable:
    """``winners`` は勝ち馬の行（全レース）。``longshot_from`` 番人気以下の勝ちと、全部の勝ちを、平地全体と WIN5 で比べる。"""

    longshot_from: int = 10

    def build(self, winners: pd.DataFrame) -> Table:
        scopes = {
            "人気薄の勝ち（平地）": winners.loc[winners["popularity"] >= self.longshot_from],
            "全部の勝ち（平地）": winners,
            "人気薄の勝ち（WIN5）": winners.loc[(winners["popularity"] >= self.longshot_from) & winners["win5_leg"].notna()],
            "全部の勝ち（WIN5）": winners.loc[winners["win5_leg"].notna()],
        }
        rows = [[name, *self._shares(rule, list(scopes.values()))] for name, rule in ASPECTS.items()]
        rows.append(["（レース数）", *[len(scope) for scope in scopes.values()]])
        return Table(["結果側の様子", *scopes], rows, title="結果側の様子（理解のため。予想には使えない）")

    @staticmethod
    def _shares(rule: Callable[[pd.DataFrame], pd.Series], scopes: list[pd.DataFrame]) -> list[str]:
        return [percent(rule(scope).fillna(False).sum(), len(scope)) for scope in scopes]
