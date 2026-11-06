"""券種ごとの「中荒れ以上の確率」を、地方の荒れ具合の予想（yosou.local_upset_level）から当日の時点で出す。"""

from __future__ import annotations

from collections.abc import Sequence

import duckdb

from yosou.local_upset_level.workflow import DEFAULT_CACHE_DIR, DEFAULT_MODELS_DIR, LocalUpsetForecast
from yosou.shared.feature import PredictionTiming
from yosou.upset_level.dataset import BetType

#: 推奨買目の券種 → 荒れ具合の予想の券種。荒れ具合の予想が無い券種（複勝・枠連・ワイド・馬単）には条件を付けられない。
UPSET_BETS: dict[str, BetType] = {"単勝": BetType.WIN, "馬連": BetType.QUINELLA, "3連複": BetType.TRIO, "3連単": BetType.TRIFECTA}


class UpsetProbabilities:
    """``of(con, rid, tickets)`` は、券種 → その券種の中荒れ以上の確率（当日の時点。LightGBM と CatBoost の平均の、固い以外の3つの合計）。
    ``forecast`` は荒れ具合の予想の入口（省略すると既定の置き場所のモデルと過去の傾きの表）。
    モデルが無ければ ``FileNotFoundError``、要る情報（馬場状態・全頭のオッズ・1番人気の馬体重）が無ければ ``ValueError`` が上がる。"""

    def __init__(self, forecast: LocalUpsetForecast | None = None) -> None:
        self._forecast = forecast or LocalUpsetForecast(DEFAULT_MODELS_DIR, DEFAULT_CACHE_DIR)

    def of(self, con: duckdb.DuckDBPyConnection, rid: str, tickets: Sequence[str]) -> dict[str, float]:
        bets = {ticket: UPSET_BETS[ticket] for ticket in tickets}
        by_bet = self._forecast.upset_or_more(con, rid, PredictionTiming.RACE_DAY, bets=list(bets.values()))
        return {ticket: by_bet[bet] for ticket, bet in bets.items()}
