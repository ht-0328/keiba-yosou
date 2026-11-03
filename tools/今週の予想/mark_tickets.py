"""印を付けた表から、券種ごとの買い目を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.longshots_in_top3.feature import PlaceMarketRate
from yosou.shared.betting import TicketType
from yosou.shared.combo_value import ComboExpectedValue, HorseRatio
from yosou.shared.win_value import HIGH

from 今週の予想.forecast_columns import (
    AXIS,
    HORSE_NO,
    IS_DANGER,
    MARK,
    MARKET_TOP3,
    MARKET_WIN,
    PLACE_ODDS_HIGH,
    PLACE_ODDS_LOW,
    PLACE_VALUE,
    POPULARITY,
    PROBABILITY,
    TRIO_UPSET,
    WIN_ODDS,
    WIN_PROBABILITY,
    WIN_VALUE,
    WIN_VALUE_BAND,
)
from 今週の予想.mark_rule import TOP_MARK, VALUE_MARK

from 今週の予想.axis_ticket_rule import HORSE_AXIS, TOP_AXIS, AxisTicketRule
from 今週の予想.filter_columns import AGREEMENT, MEMBERS, POOL_BACKED, member_column
from 今週の予想.horse_pool import FAVORITES, LONGSHOTS, MODEL_TOP, NOT_DANGER, STRONG_FAVORITES, UP_TO, HorsePool
from 今週の予想.ticket_rules import (
    BET_RULES,
    FAVORITE_MAX_POPULARITY,
    POOL_TRIO_RULES,
    LONGSHOT_PLACE_EDGE,
    LONGSHOT_PLACE_LABEL,
    LONGSHOT_PLACE_MIN_POPULARITY,
    PLACE_AGREE_LABEL,
    PLACE_AXIS_RULES,
    PLACE_BUY_LINE,
    PLACE_LABEL,
    PLACE_MAX_POINTS,
    PLACE_MIN_FIELD,
    PLACE_ODDS_CAP,
    PLACE_STAKE_UNITS,
    PLACE_VALUE_LINE,
    WIN_FAVORITE_MIN,
    WIN_ODDS_CAP,
    WIN_VALUE_LABEL,
    WIN_VALUE_LINE,
    TicketRule,
    combo_text,
)

#: 買い目の表の列。``rule`` は買い方の名前（表の行）、``ticket_type`` は券種の名前（払戻とオッズを読む表）、``value`` は組の期待値
#: （3連複・3連単だけ。ほかは欠損値）。``agreement``・``pool_backed`` はレースの絞り込みの旗（``RaceFilter``）。
RULE, VALUE = "rule", "value"
#: 買い目のオッズの列（複勝・ワイドは最低オッズ。今週の予想は締め切り前、印の成績は確定）。買えない組（無投票・取消）は欠損値。
ODDS = "odds"
COLUMNS: tuple[str, ...] = ("race_id", "race_date", "fold", WIN_VALUE_BAND, AGREEMENT, POOL_BACKED, RULE, "ticket_type", "combo",
                            "stake_units", VALUE)
#: レースから写す列（無ければ偽）。
_RACE_COLUMNS: tuple[str, ...] = ("race_id", "race_date", "fold", WIN_VALUE_BAND)
_RACE_FLAGS: tuple[str, ...] = (AGREEMENT, POOL_BACKED)


class MarkTickets:
    """印を付けた表（``BacktestMarker.mark`` の戻り値。1行 = 1頭）から、印のルールの買い目（1行 = 1点）を作る
    （設計書「買うレースと買い目を決める」08 の 2。ルールは ``BET_RULES``）。

    - 印の位置で組む券種（``TicketRule``）: ルールの印の組み合わせを全部作る。
    - 軸から流す券種（``AxisTicketRule``。3連複・3連単）: 軸（◎軸は ◎、軸馬は列 ``axis`` の馬。無ければ ◎）から相手に流す。
      組の期待値（``ComboExpectedValue``。市場が見た組の確率 × 3頭の「モデル ÷ 市場」の比）を付け、線のあるルールは線以上の買い目だけにする。
      2モデル一致のルールは、LightGBM と CatBoost のそれぞれの確率で出した組の期待値も線以上の買い目だけにする（モデルごとの確率が無ければ 0点）。
    - 複勝: 複勝の期待値が線（1.25）以上の馬を、高い順に最大3点。2モデル一致の行は、そのうちモデルごとの期待値も線以上の馬だけ。
    - 6番人気以下の複勝: 6番人気以下で、3着以内の確率が複勝オッズから見た3着以内率より線（0.05）以上高い馬を全部。
    - 馬の集まりから組む3連複（``POOL_TRIO_RULES``）: 1頭目・2頭目・3頭目を、人気馬（5番人気までで消でない）・強い人気馬（そのうち
      3着以内の確率 − 複勝オッズから見た3着以内率が線以上）・6番人気以下（同じ差が線以上）・消を除いた全頭・予想の上位（消でない馬の
      3着以内の確率の高い順）・N番人気まで（中穴まで。消でなく、線があれば同じ差が線以上）から選ぶ。ルールに荒れ具合があれば、
      3連複の荒れ具合（列 ``trio_upset``。``TrioUpsetJudge`` が決めたもの。無ければ買わない）がそのどれかのレースだけ。組の期待値は付けるだけで
      絞らない（オッズの下限のあるルールの安い組は ``TorigamiFilter`` が外す）。
    - 複勝の馬を軸にするワイド・馬連（``PLACE_AXIS_RULES``）: 複勝の買い目の馬を軸に、◎○▲ に流す。
    列は ``COLUMNS``。
    """

    def __init__(self) -> None:
        self._ratio = HorseRatio()
        self._value = ComboExpectedValue()
        self._place_market = PlaceMarketRate()

    def build(self, marked: pd.DataFrame) -> pd.DataFrame:
        rows: list[dict] = []
        for _, race in marked.groupby("race_id", sort=False):
            head = {column: race[column].iloc[0] for column in _RACE_COLUMNS}
            head.update({flag: bool(race[flag].iloc[0]) if flag in race.columns and pd.notna(race[flag].iloc[0]) else False
                         for flag in _RACE_FLAGS})
            by_mark = self._horses_by_mark(race)
            axes = self._axes(race, by_mark)
            ratios = self._ratios(race, None)
            member_ratios = [self._ratios(race, member) for member in MEMBERS]
            for rule in BET_RULES:
                combos = rule.combos(by_mark, axes)
                values = self._values(rule, combos, ratios)
                kept = self._kept(rule, values, [self._values(rule, combos, member) for member in member_ratios])
                rows += [{**head, RULE: rule.label, "ticket_type": rule.ticket_type.label, "combo": combo_text(combo),
                          "stake_units": rule.stake_units, VALUE: value}
                         for combo, value, keep in zip(combos, values, kept, strict=True) if keep]
            rows += [{**head, RULE: WIN_VALUE_LABEL, "ticket_type": TicketType.WIN.label, "combo": combo_text((horse,)),
                      "stake_units": 1.0, VALUE: value} for horse, value in self._win_value_horses(race)]
            for label, agreement in ((PLACE_LABEL, False), (PLACE_AGREE_LABEL, True)):
                rows += [{**head, RULE: label, "ticket_type": TicketType.PLACE.label, "combo": combo_text((horse,)),
                          "stake_units": PLACE_STAKE_UNITS, VALUE: np.nan} for horse in self._place_horses(race, agreement)]
            edge = self._place_edge(race)
            longshots = self._longshot_place_horses(race, edge)
            rows += [{**head, RULE: LONGSHOT_PLACE_LABEL, "ticket_type": TicketType.PLACE.label, "combo": combo_text((horse,)),
                      "stake_units": PLACE_STAKE_UNITS, VALUE: np.nan} for horse in longshots]
            danger = self._danger(race)
            upset = race[TRIO_UPSET].iloc[0] if TRIO_UPSET in race.columns else None
            for rule in POOL_TRIO_RULES:
                if rule.upset_levels and upset not in rule.upset_levels:
                    continue
                combos = rule.combos(*(self._pool(race, edge, danger, pool) for pool in (rule.axis, rule.second, rule.third)))
                values = self._value.of(rule.ticket_type, combos, ratios)
                rows += [{**head, RULE: rule.label, "ticket_type": rule.ticket_type.label, "combo": combo_text(combo),
                          "stake_units": rule.stake_units, VALUE: value} for combo, value in zip(combos, values, strict=True)]
            place_horses = self._place_horses(race, False)
            for rule in PLACE_AXIS_RULES:
                rows += [{**head, RULE: rule.label, "ticket_type": rule.ticket_type.label, "combo": combo_text(combo),
                          "stake_units": rule.stake_units, VALUE: np.nan} for combo in rule.combos(place_horses, by_mark)]
        return pd.DataFrame(rows, columns=list(COLUMNS))

    def _horses_by_mark(self, race: pd.DataFrame) -> dict[str, list[int]]:
        """印 → 馬番の並び（3着以内の確率の高い順）。☆ は複勝の期待値が線以上の馬だけ（線に届かない ☆ は表示だけで、買い目の相手に入れない。
        ``MarkRule`` の ☆）。"""
        shown_only = (race[MARK] == VALUE_MARK) & ~(race[PLACE_VALUE] >= PLACE_VALUE_LINE)
        return {mark: [int(no) for no in group[HORSE_NO]] for mark, group in race[~shown_only].groupby(MARK, sort=False)}

    def _axes(self, race: pd.DataFrame, by_mark: dict[str, list[int]]) -> dict[str, int]:
        """パターン → 軸の馬番。◎ がいなければどちらの軸も無い。軸の列が無い（前の形の表）なら軸馬も ◎。"""
        tops = by_mark.get(TOP_MARK, [])
        if not tops:
            return {}
        flagged = race[race[AXIS].fillna(False).astype(bool)] if AXIS in race.columns else race.iloc[0:0]
        axis = int(flagged[HORSE_NO].iloc[0]) if len(flagged) else tops[0]
        return {TOP_AXIS: tops[0], HORSE_AXIS: axis}

    def _ratios(self, race: pd.DataFrame, member: str | None) -> pd.DataFrame:
        """馬番を index にした「モデル ÷ 市場」の比。``member`` を渡すとそのモデルの確率で出す。
        市場の見立てや確率の列が無ければ（木曜・前の形の表・モデルごとの確率の無い予測）欠損値。"""
        blank = pd.Series(np.nan, index=race.index)
        top3 = PROBABILITY if member is None else member_column(PROBABILITY, member)
        win = WIN_PROBABILITY if member is None else member_column(WIN_PROBABILITY, member)
        ratios = self._ratio.of(race.get(top3, blank), race.get(MARKET_TOP3, blank), race.get(win, blank), race.get(MARKET_WIN, blank))
        return ratios.set_axis(race[HORSE_NO].astype(int))

    def _values(self, rule: TicketRule | AxisTicketRule, combos: list[tuple[int, ...]], ratios: pd.DataFrame) -> np.ndarray:
        """組の期待値（軸から流す券種だけ。ほかは欠損値）。"""
        if isinstance(rule, AxisTicketRule):
            return self._value.of(rule.ticket_type, combos, ratios)
        return np.full(len(combos), np.nan)

    def _kept(self, rule: TicketRule | AxisTicketRule, values: np.ndarray, member_values: list[np.ndarray]) -> np.ndarray:
        """残す買い目（真偽）。線のあるルールは期待値が線以上、2モデル一致のルールはモデルごとの期待値も線以上。"""
        if rule.value_line is None:
            return np.ones(len(values), dtype=bool)
        with np.errstate(invalid="ignore"):
            kept = values >= rule.value_line
            if getattr(rule, "agreement", False):
                for member in member_values:
                    kept &= member >= rule.value_line
        return kept

    def _win_value_horses(self, race: pd.DataFrame) -> list[tuple[int, float]]:
        """単勝（期待値）: 1番人気が ``WIN_FAVORITE_MIN`` 倍以上のレースで、単勝の期待値が線以上・単勝オッズが上限以下の馬を、期待値の高い順に1点。
        単勝オッズか単勝の期待値の列が無ければ（木曜・前の形の表）買わない。"""
        if WIN_ODDS not in race.columns or WIN_VALUE not in race.columns or not (race[WIN_ODDS].min() >= WIN_FAVORITE_MIN):
            return []
        priced = race[(race[WIN_VALUE] >= WIN_VALUE_LINE) & (race[WIN_ODDS] <= WIN_ODDS_CAP)].sort_values(WIN_VALUE, ascending=False).head(1)
        return [(int(no), float(value)) for no, value in zip(priced[HORSE_NO], priced[WIN_VALUE], strict=True)]

    def _place_edge(self, race: pd.DataFrame) -> pd.Series | None:
        """3着以内の確率 − 複勝オッズから見た3着以内率（``PlaceMarketRate``）。複勝オッズか人気の列が無ければ（木曜・前の形の表）無し。
        複勝オッズの無い馬は欠損値。"""
        if not {PLACE_ODDS_LOW, PLACE_ODDS_HIGH, POPULARITY} <= set(race.columns):
            return None
        return race[PROBABILITY] - self._place_market.of(race[["race_id", PLACE_ODDS_LOW, PLACE_ODDS_HIGH]])

    def _longshot_place_horses(self, race: pd.DataFrame, edge: pd.Series | None) -> list[int]:
        """6番人気以下の複勝: ``LONGSHOT_PLACE_MIN_POPULARITY`` 番人気以下で、``edge`` が ``LONGSHOT_PLACE_EDGE`` 以上の馬を、馬番の順に全部。
        ``edge`` が無ければ買わない。複勝オッズの無い馬は買わない。"""
        if edge is None:
            return []
        with np.errstate(invalid="ignore"):
            chosen = (race[POPULARITY] >= LONGSHOT_PLACE_MIN_POPULARITY) & (edge >= LONGSHOT_PLACE_EDGE)
        return sorted(int(no) for no in race.loc[chosen.fillna(False), HORSE_NO])

    @staticmethod
    def _danger(race: pd.DataFrame) -> pd.Series:
        """危険な人気馬（消）か（真偽）。危険の判定の列が無ければ（消を使わない印）どの馬も偽。"""
        if IS_DANGER not in race.columns:
            return pd.Series(False, index=race.index)
        return race[IS_DANGER].fillna(False).astype(bool)

    @staticmethod
    def _pool(race: pd.DataFrame, edge: pd.Series | None, danger: pd.Series, pool: HorsePool) -> list[int]:
        """``pool`` の馬の馬番。人気馬は ``FAVORITE_MAX_POPULARITY`` 番人気までで消でない馬、強い人気馬はそのうち ``edge`` が線以上の馬、
        6番人気以下は ``LONGSHOT_PLACE_MIN_POPULARITY`` 番人気以下の馬のうち ``edge`` が線以上の馬（線 ``LONGSHOT_PLACE_EDGE`` なら
        6番人気以下の複勝の馬と同じ）。消を除いた全頭は消でない全部の馬。予想の上位は消でない馬の3着以内の確率の高い順に ``pool.count`` 頭。
        N番人気までは ``pool.count`` 番人気までで消でない馬のうち ``edge`` が線以上の馬。
        線（``pool.edge``）が無ければ線を見ない。``edge`` が無ければ（木曜・前の形の表）いない。"""
        if edge is None:
            return []
        if pool.kind == MODEL_TOP:
            ranked = race[~danger].sort_values(PROBABILITY, ascending=False, kind="stable")
            return sorted(int(no) for no in ranked[HORSE_NO].head(pool.count))
        favorites = (race[POPULARITY] <= FAVORITE_MAX_POPULARITY) & ~danger
        within = {FAVORITES: favorites, STRONG_FAVORITES: favorites, UP_TO: (race[POPULARITY] <= (pool.count or 0)) & ~danger,
                  LONGSHOTS: race[POPULARITY] >= LONGSHOT_PLACE_MIN_POPULARITY, NOT_DANGER: ~danger}[pool.kind]
        kept = within
        if pool.edge is not None:
            with np.errstate(invalid="ignore"):
                kept = within & (edge >= pool.edge).fillna(False)
        return sorted(int(no) for no in race.loc[kept, HORSE_NO])

    def _place_horses(self, race: pd.DataFrame, agreement: bool) -> list[int]:
        """複勝: ◎の期待値 1.00 以上で ``PLACE_MIN_FIELD`` 頭以上のレースで、期待値が ``PLACE_BUY_LINE`` 以上・複勝の最低オッズが ``PLACE_ODDS_CAP`` 倍以下の馬を
        高い順に最大3点。2モデル一致なら、そのうちモデルごとの期待値も線以上の馬だけ。頭数は列 ``field_size`` があればその値、無ければ行の数。
        複勝の最低オッズの列が無ければ（前の形の表）買わない。"""
        field = race["field_size"].iloc[0] if "field_size" in race.columns else len(race)
        if race[WIN_VALUE_BAND].iloc[0] != HIGH or not (field >= PLACE_MIN_FIELD) or PLACE_ODDS_LOW not in race.columns:
            return []
        chosen = (race[PLACE_VALUE] >= PLACE_BUY_LINE) & (race[PLACE_ODDS_LOW] <= PLACE_ODDS_CAP)
        priced = race[chosen].sort_values(PLACE_VALUE, ascending=False).head(PLACE_MAX_POINTS)
        if agreement:
            for member in MEMBERS:
                column = member_column("place_value", member)
                values = priced[column] if column in priced.columns else pd.Series(np.nan, index=priced.index)
                priced = priced[values >= PLACE_BUY_LINE]
        return [int(no) for no in priced[HORSE_NO]]
