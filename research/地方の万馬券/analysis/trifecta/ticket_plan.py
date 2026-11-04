"""買い目を組む: 戦略と、馬ごとの帯・予想と市場の差・組の確率とオッズから、1レースの買い目（組と期待値）を決める。3連単と3連複で同じ。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations_with_replacement, product

import numpy as np
import pandas as pd

from ..popularity_band import FAVORITE, LONGSHOT, MIDDLE
from .combo_market import MARKET, ComboMarket
from .race_market import EDGE, MARKET_UPSET
from .stage_predictions import BIG_OR_MORE, DANGER_EDGE, LONGSHOT_EDGE, MID_OR_MORE, STAGE_UPSET, TRIFECTA_KEY, TRIO_KEY, upset_column
from .strategy import ANY_PATTERN, EDGE_DANGER, EDGE_LONGSHOT, TRIO, UPSET_STAGE, Strategy

#: 買い目の表の列。
TICKET_COLUMNS: tuple[str, ...] = ("race_id", "first", "second", "third", "probability", "odds", "ev", "pattern")
_ROLE_ORDER = (FAVORITE, MIDDLE, LONGSHOT)
_ALL_ORDERED: tuple[str, ...] = tuple("".join(roles) for roles in product(_ROLE_ORDER, repeat=3))
_ALL_UNORDERED: tuple[str, ...] = tuple("".join(roles) for roles in combinations_with_replacement(_ROLE_ORDER, 3))
_RANK = {role: index for index, role in enumerate(_ROLE_ORDER)}


@dataclass(frozen=True)
class TicketPlan:
    """``runners``（帯・差・荒れ具合つき）、``combos``（全部の組の確率）、``odds``（組の確定オッズ）から、戦略に合う買い目を返す。"""

    strategy: Strategy

    def build(self, runners: pd.DataFrame, combos: pd.DataFrame, odds: pd.DataFrame) -> pd.DataFrame:
        roles = self._roles(runners)
        candidates = self._with_roles(self._shrunk(combos, odds), roles)
        candidates = candidates.merge(self._allowed_patterns(runners), on=["race_id", "pattern"], how="inner")
        candidates = candidates[candidates["race_id"].isin(self._races_in_upset_range(runners))]
        candidates = candidates.merge(odds, on=["race_id", "first", "second", "third"], how="inner")
        candidates["ev"] = candidates["probability"] * candidates["odds"]
        s = self.strategy
        chosen = candidates[(candidates["ev"] >= s.ev_min) & (candidates["odds"] >= s.odds_min) & (candidates["odds"] <= s.odds_max)]
        chosen = chosen.sort_values(["race_id", "ev"], ascending=[True, False]).groupby("race_id").head(s.max_points)
        chosen = self._races_worth_buying(chosen)
        return chosen[list(TICKET_COLUMNS)].reset_index(drop=True)

    def _shrunk(self, combos: pd.DataFrame, odds: pd.DataFrame) -> pd.DataFrame:
        """組の確率を市場の組の確率（1 ÷ オッズ をレース内で合計 1 に）に寄せる: p ^ shrink × m ^ (1 − shrink) をレース内で合計 1 に。
        オッズの無い組（発売が無い）は落ちる。``shrink`` が 1 ならそのまま。"""
        alpha = self.strategy.shrink
        if alpha >= 1.0:
            return combos
        market = ComboMarket().attach(odds)
        table = combos.merge(market[["race_id", "first", "second", "third", MARKET]], on=["race_id", "first", "second", "third"], how="inner")
        blended = np.power(table["probability"], alpha) * np.power(table[MARKET], 1.0 - alpha)
        table["probability"] = blended / blended.groupby(table["race_id"]).transform("sum")
        return table[list(combos.columns)]

    def _races_worth_buying(self, chosen: pd.DataFrame) -> pd.DataFrame:
        """レース単位の線: 残した買い目の確率の合計（当たる見込み）と期待値の平均が線に届かないレースは丸ごと買わない。"""
        s = self.strategy
        if s.race_hit_min <= 0 and s.race_ev_min <= 0:
            return chosen
        by_race = chosen.groupby("race_id").agg(hit=("probability", "sum"), ev=("ev", "mean"))
        worth = by_race[(by_race["hit"] >= s.race_hit_min) & (by_race["ev"] >= s.race_ev_min)].index
        return chosen[chosen["race_id"].isin(worth)]

    def _with_roles(self, combos: pd.DataFrame, roles: pd.DataFrame) -> pd.DataFrame:
        """組の3頭に帯（役）を付け、役の無い馬を含む組を落とす。3連複は役を 人→中→大 の順に並べて型にする。"""
        table = combos
        for position, name in (("first", "r1"), ("second", "r2"), ("third", "r3")):
            table = table.merge(roles.rename(columns={"horse_no": position, "role": name}), on=["race_id", position], how="inner")
        if self.strategy.ticket == TRIO:
            table["pattern"] = [self._unordered(r1, r2, r3) for r1, r2, r3 in zip(table["r1"], table["r2"], table["r3"])]
        else:
            table["pattern"] = table["r1"] + table["r2"] + table["r3"]
        return table

    def _unordered(self, *roles: str) -> str:
        return "".join(sorted(roles, key=_RANK.get))

    def _roles(self, runners: pd.DataFrame) -> pd.DataFrame:
        """帯ごとに使う馬（``race_id``・``horse_no``・``role``）。人気馬は消す1頭（①の差がいちばん低い馬か、②の差がいちばん高い馬）を外して
        ①の差の高い順に頭数ぶん、中穴・大穴は差（①か③）の高い順に頭数ぶん。"""
        s = self.strategy
        favorites_all = runners[runners["band"] == FAVORITE]
        dropped_races: set = set()
        if s.eliminate:
            favorites_all, dropped_races = self._without_danger(favorites_all)
        ordered = favorites_all.sort_values(["race_id", EDGE], ascending=[True, False])
        rank_in_race = ordered.groupby("race_id").cumcount()
        keep = np.where(ordered["race_id"].isin(dropped_races), s.favorites - 1, s.favorites)   # 消したレースだけ1頭少なく
        favorites = ordered[rank_in_race.to_numpy() < keep]
        ranked = runners.assign(_rank=self._longshot_rank(runners)).sort_values(["race_id", "_rank"], ascending=[True, False])
        ranked = ranked[ranked["_rank"] >= s.longshot_min] if s.longshot_min > 0 else ranked
        middles = ranked[ranked["band"] == MIDDLE].groupby("race_id").head(s.middles)
        longshots = ranked[ranked["band"] == LONGSHOT].groupby("race_id").head(s.longshots)
        roles = pd.concat([favorites.assign(role=FAVORITE), middles.assign(role=MIDDLE), longshots.assign(role=LONGSHOT)])
        return roles[["race_id", "horse_no", "role"]]

    def _without_danger(self, favorites: pd.DataFrame) -> tuple[pd.DataFrame, set]:
        """レースごとに消す1頭を外した人気馬と、消したレースの集合。②の差（``DANGER_EDGE``）を使う決め方で②の値が無いレースは、
        ①の差がいちばん低い馬を消す。``danger_min`` があれば、消す馬の差が線に届かないレースでは消さない。"""
        if favorites.empty:
            return favorites, set()
        score = -favorites[EDGE]
        if self.strategy.danger == EDGE_DANGER and DANGER_EDGE in favorites.columns:
            score = favorites[DANGER_EDGE].where(favorites[DANGER_EDGE].notna(), score)
        dropped = score.groupby(favorites["race_id"]).idxmax()
        if self.strategy.danger_min > 0:
            dropped = dropped[score.loc[dropped.to_numpy()].to_numpy() >= self.strategy.danger_min]
        return favorites.drop(index=dropped.to_numpy()), set(dropped.index)

    def _longshot_rank(self, runners: pd.DataFrame) -> pd.Series:
        """中穴・大穴を並べる値。③の差を使う決め方で③の値が無い馬は①の差。"""
        if self.strategy.longshot == EDGE_LONGSHOT and LONGSHOT_EDGE in runners.columns:
            return runners[LONGSHOT_EDGE].where(runners[LONGSHOT_EDGE].notna(), runners[EDGE])
        return runners[EDGE]

    def _upset_key(self) -> str:
        return TRIO_KEY if self.strategy.ticket == TRIO else TRIFECTA_KEY

    def _races_in_upset_range(self, runners: pd.DataFrame) -> pd.Index:
        """④の大荒れ以上・中荒れ以上の確率が線以上のレース（線が 0 なら全部）。④の値が無いレースは線があれば買わない。"""
        s = self.strategy
        races = runners.groupby("race_id").first()
        keep = pd.Series(True, index=races.index)
        for line, name in ((s.big_min, BIG_OR_MORE), (s.mid_min, MID_OR_MORE)):
            if line > 0:
                values = races.get(upset_column(name, self._upset_key()), pd.Series(np.nan, index=races.index))
                keep &= pd.to_numeric(values, errors="coerce").ge(line).fillna(False)
        return keep[keep].index

    def _allowed_patterns(self, runners: pd.DataFrame) -> pd.DataFrame:
        """レースごとに、その荒れ具合（市場の割れ方か、④の予想のいちばん高いクラス）で買う型。``ANY_PATTERN`` なら全部の型。"""
        column = upset_column(STAGE_UPSET, self._upset_key()) if self.strategy.upset_source == UPSET_STAGE else MARKET_UPSET
        if column not in runners.columns:
            return pd.DataFrame(columns=["race_id", "pattern"])
        upset = runners.groupby("race_id")[column].first()
        rows = [{"race_id": race_id, "pattern": pattern}
                for race_id, level in upset.items() for pattern in self._expand(self.strategy.patterns.get(level, ()))]
        return pd.DataFrame(rows, columns=["race_id", "pattern"])

    def _expand(self, patterns: tuple[str, ...]) -> tuple[str, ...]:
        if ANY_PATTERN not in patterns:
            return patterns
        return _ALL_UNORDERED if self.strategy.ticket == TRIO else _ALL_ORDERED
