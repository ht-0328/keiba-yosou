"""決まりの候補ごとに、種類 × 開催日ごとの点数・払戻・買ったレース・当たったレースを数える。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType

from .buy_rule import BuyRule
from .race_kinds import KIND_GROUP, KIND_GROUPS

#: 数える4つの値の並び（最後の軸）。
POINTS, PAYOUT, RACES, HIT_RACES = range(4)


class RuleDayTable:
    """期待値を付けた組（``FoldValuer`` の表。1券種・1案）から、決まりの候補ごとに、
    配列 [決まり, 種類（芝ダ × クラス）, 開催日, 4] を作る。4 は点数・払戻（100円あたりの合計）・買ったレース・当たったレース。

    数え方は道具「印の成績」と同じ: 1レースで決まりに合う組を期待値の高い順に点数の上限まで選び、そのうえでトリガミ
    （どれが当たっても、そのレースのその買い方の投資より少なく戻る組）を外す（``TorigamiFilter`` と同じ決まり。ワイドは最低オッズ）。
    年ごとに決まりを選び直すときは、この配列の開催日の範囲を足し合わせるだけで済む。
    """

    def __init__(self, ticket_type: TicketType, days: Sequence[pd.Timestamp], groups: Sequence[str] = KIND_GROUPS) -> None:
        self._ticket_type = ticket_type
        self._days = pd.DatetimeIndex(days)
        self._groups = list(groups)

    def build(self, valued: pd.DataFrame, rules: Sequence[BuyRule]) -> np.ndarray:
        frame = valued.sort_values(["race_id", "value"], ascending=[True, False], kind="stable").reset_index(drop=True)
        arrays = self._arrays(frame)
        out = np.zeros((len(rules), len(self._groups), len(self._days), 4), dtype=np.float64)
        for (scope, cap), members in self._by_scope_cap(rules).items():
            index = np.flatnonzero(self._scope_mask(frame, scope) & (arrays["odds"] <= cap))
            rank = self._rank_in_race(arrays["race"][index])
            for at, rule in members:
                chosen = index[(arrays["value"][index] >= rule.line) & ((rule.points == 0) | (rank < rule.points))]
                self._add(out[at], self._without_torigami(chosen, arrays), arrays)
        return out

    def _arrays(self, frame: pd.DataFrame) -> dict[str, np.ndarray]:
        day = self._days.get_indexer(pd.to_datetime(frame["race_date"]))
        group = pd.Index(self._groups).get_indexer(frame[KIND_GROUP])
        if (day < 0).any() or (group < 0).any():
            raise ValueError("開催日か種類が、数える範囲に無い組があります")
        return {"race": pd.factorize(frame["race_id"], sort=True)[0], "value": frame["value"].to_numpy(dtype=float),
                "odds": frame["odds"].to_numpy(dtype=float), "payout": frame["payout"].to_numpy(dtype=float),
                "hit": frame["hit"].to_numpy(dtype=bool), "day": day, "group": group}

    def _by_scope_cap(self, rules: Sequence[BuyRule]) -> dict[tuple[str, float], list[tuple[int, BuyRule]]]:
        grouped: dict[tuple[str, float], list[tuple[int, BuyRule]]] = {}
        for at, rule in enumerate(rules):
            grouped.setdefault((rule.scope, rule.cap), []).append((at, rule))
        return grouped

    def _scope_mask(self, frame: pd.DataFrame, scope: str) -> np.ndarray:
        mask = np.ones(len(frame), dtype=bool)
        if "高" in scope:
            mask &= (frame["expectation"] == "高").to_numpy()
        if "◎" in scope:
            mask &= self._has_top(frame)
        return mask

    def _has_top(self, frame: pd.DataFrame) -> np.ndarray:
        """◎ を含む組か（着順を区別する券種は ◎ が1着の組）。"""
        if self._ticket_type.spec.is_ordered:
            return (frame["h1"] == frame["top"]).to_numpy()
        names = [f"h{at}" for at in range(1, self._ticket_type.spec.horse_count + 1)]
        return np.column_stack([(frame[name] == frame["top"]).to_numpy() for name in names]).any(axis=1)

    @staticmethod
    def _rank_in_race(race: np.ndarray) -> np.ndarray:
        """レースごとにまとまった並びで、レースの中の順位（0 から）。"""
        position = np.arange(len(race))
        first = np.r_[True, race[1:] != race[:-1]] if len(race) else np.zeros(0, dtype=bool)
        return position - np.maximum.accumulate(np.where(first, position, 0))

    @staticmethod
    def _without_torigami(chosen: np.ndarray, arrays: dict[str, np.ndarray]) -> np.ndarray:
        """レースごとに、オッズの低い組から「オッズ ≦ 残りの点数」のあいだ外す（``TorigamiFilter`` と同じ）。
        オッズの昇順で j 番目（0 から）の組は、オッズ > 点数 − j なら残る（オッズは増え、点数 − j は減るので、外すのは先頭から続く組だけ）。"""
        if not len(chosen):
            return chosen
        race = arrays["race"][chosen]
        _, inverse, counts = np.unique(race, return_inverse=True, return_counts=True)
        size = counts[inverse]
        odds = arrays["odds"][chosen]
        if not (odds <= size).any():
            return chosen
        order = np.lexsort((odds, race))
        rank = RuleDayTable._rank_in_race(race[order])
        keep = np.empty(len(chosen), dtype=bool)
        keep[order] = odds[order] > size[order] - rank
        return np.sort(chosen[keep])

    def _add(self, target: np.ndarray, kept: np.ndarray, arrays: dict[str, np.ndarray]) -> None:
        if not len(kept):
            return
        race = arrays["race"][kept]
        starts = np.flatnonzero(np.r_[True, race[1:] != race[:-1]])
        points = np.diff(np.r_[starts, len(kept)]).astype(float)
        payout = np.add.reduceat(arrays["payout"][kept], starts)
        hit = np.maximum.reduceat(arrays["hit"][kept].astype(float), starts)
        cell = arrays["group"][kept][starts] * len(self._days) + arrays["day"][kept][starts]
        size = len(self._groups) * len(self._days)
        for slot, values in ((POINTS, points), (PAYOUT, payout), (RACES, np.ones(len(starts))), (HIT_RACES, hit)):
            target[:, :, slot] += np.bincount(cell, weights=values, minlength=size).reshape(len(self._groups), len(self._days))
