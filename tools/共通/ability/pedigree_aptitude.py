"""初めての条件の適性を、血統（父・母の父）の産駒の、その条件での走から補う。"""

from __future__ import annotations

import pandas as pd

from .ability_index import ABILITY, APTITUDE_COLUMNS
from .ability_settings import (
    COURSE, DISTANCE, FIRST_DISTANCE, FIRST_GOING, FIRST_SURFACE, FIRST_VENUE, GOING, AbilitySettings,
)
from .first_conditions import distance_band
from .speed_figure import FIGURE

#: 出力の列（血統で補った分の合計。能力指数に足した点数）。
PEDIGREE = "血統で補った分"
#: 初めての条件の種類ごとに、補う適性の列。芝ダと馬場の組は、どちらも馬場の適性。
_TARGET = {FIRST_DISTANCE: APTITUDE_COLUMNS[DISTANCE], FIRST_VENUE: APTITUDE_COLUMNS[COURSE],
           FIRST_SURFACE: APTITUDE_COLUMNS[GOING], FIRST_GOING: APTITUDE_COLUMNS[GOING]}
#: 良・稍重を「良」、重・不良を「道悪」とする。
_GOING = {"良": "良", "稍重": "良", "重": "道悪", "不良": "道悪"}


class PedigreeAptitude:
    """初めての条件（``FirstConditions``）で走る馬の能力指数に、血統から見込んだ、その条件での上げ下げを足す。

    産駒の「初めてのその条件の走」で、スピード指数が能力指数より何点高かったか（残り）を、親ごと・条件ごとに平均する。
    同じ条件の全部の馬の初めての走の平均を引いて、その親の産駒に特有の分だけを残し、走の数が少ない親は 0 に寄せる。

        親の値 =（産駒の残りの合計 − 産駒の走の数 × 全部の馬の残りの平均）÷（産駒の走の数 + ``pedigree_prior``）

    ``pedigree`` の親（父 ``sire``・母の父 ``damsire``）の値を足し、その条件の適性の列と能力指数に足す。
    補うのは ``pedigree_kinds`` の条件だけで、``runs`` にはその条件の列（``FirstConditions``）が要る。
    例: 父の産駒が初めてのダートで、全部の馬の初めてのダートより平均 4点高く、その走が 60回・``pedigree_prior`` 20 なら、
    父の値は 4 × 60 ÷ 80 = 3点。
    使う産駒の走は、その行の開催日より前の走だけ（あとの日の結果を混ぜない）。``fit`` に渡す表の能力指数は、補う前のもの。
    """

    def __init__(self, settings: AbilitySettings) -> None:
        self._parents = settings.pedigree
        self._kinds = settings.pedigree_kinds
        self._prior = settings.pedigree_prior
        self._overall: dict[str, pd.DataFrame] = {}
        self._by_parent: dict[tuple[str, str], pd.DataFrame] = {}

    def fit(self, runs: pd.DataFrame) -> PedigreeAptitude:
        residual = runs[FIGURE] - runs[ABILITY]
        for kind in self._kinds:
            chosen = runs[kind].astype(bool) & residual.notna()
            frame = pd.DataFrame({"key": self._key(kind, runs[chosen]), "race_date": _dates(runs.loc[chosen, "race_date"]),
                                  "residual": residual[chosen]})
            self._overall[kind] = self._cumulative(frame, ["key"])
            for parent in self._parents:
                with_parent = frame.assign(parent=runs.loc[chosen, parent]).dropna(subset=["parent"])
                self._by_parent[(kind, parent)] = self._cumulative(with_parent, ["parent", "key"])
        return self

    def fill(self, runs: pd.DataFrame) -> pd.DataFrame:
        """能力指数・適性の列に、血統で補った分を足す。初めての条件でない行は、何も足さない。"""
        added = {kind: self._value(kind, runs) for kind in self._kinds}
        columns = {name: runs[name].copy() for name in set(_TARGET.values())}
        for kind, value in added.items():
            columns[_TARGET[kind]] = columns[_TARGET[kind]] + value
        total = sum(added.values(), pd.Series(0.0, index=runs.index))
        return runs.assign(**columns, **{ABILITY: runs[ABILITY] + total, PEDIGREE: total})

    def _value(self, kind: str, runs: pd.DataFrame) -> pd.Series:
        query = pd.DataFrame({"key": self._key(kind, runs), "race_date": _dates(runs["race_date"])}, index=runs.index)
        overall = self._lookup(self._overall[kind], query, ["key"])
        mean = (overall["sum"] / overall["count"]).fillna(0.0)
        value = pd.Series(0.0, index=runs.index)
        for parent in self._parents:
            found = self._lookup(self._by_parent[(kind, parent)], query.assign(parent=runs[parent]), ["parent", "key"])
            value = value + ((found["sum"] - found["count"] * mean) / (found["count"] + self._prior)).fillna(0.0)
        return value.where(runs[kind].astype(bool), 0.0)

    def _key(self, kind: str, runs: pd.DataFrame) -> pd.Series:
        if kind == FIRST_DISTANCE:
            return pd.Series(distance_band(runs["distance_m"].to_numpy()).astype(str), index=runs.index)
        if kind == FIRST_VENUE:
            return runs["venue_code"].astype(str)
        if kind == FIRST_SURFACE:
            return runs["surface"].astype(str)
        return runs["surface"].astype(str) + "・" + runs["condition"].map(_GOING).fillna("?")

    def _cumulative(self, frame: pd.DataFrame, by: list[str]) -> pd.DataFrame:
        """``by`` ごとに、その日までの残りの合計と走の数（その日を含む）を、開催日の順に並べる。"""
        daily = frame.groupby([*by, "race_date"], sort=True)["residual"].agg(["sum", "count"]).reset_index()
        daily[["sum", "count"]] = daily.groupby(by, sort=False)[["sum", "count"]].cumsum()
        return daily.sort_values("race_date", kind="stable")

    def _lookup(self, table: pd.DataFrame, query: pd.DataFrame, by: list[str]) -> pd.DataFrame:
        """``query`` の各行の開催日より前（その日を含まない）の、いちばん新しい合計と走の数。無ければ欠損値。"""
        usable = query.dropna(subset=by)
        ordered = usable.reset_index(names="_row").sort_values("race_date", kind="stable")
        # 鍵の列の型（文字列の型が表ごとに違うことがある）を、両方とも Python の文字列にそろえる。
        ordered[by] = ordered[by].astype(object)
        merged = pd.merge_asof(ordered, table.astype({column: object for column in by}), on="race_date", by=by,
                               allow_exact_matches=False)
        return merged.set_index("_row")[["sum", "count"]].reindex(query.index)


def _dates(values: pd.Series) -> pd.Series:
    """開催日を、比べられる同じ型（ナノ秒の日時）にそろえる。"""
    return pd.to_datetime(values).astype("datetime64[ns]")
