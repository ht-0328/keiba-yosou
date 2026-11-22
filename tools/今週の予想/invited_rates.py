"""中央の過去走が無い招待馬を、過去の同じ種類の招待馬の中央での初出走の成績で評価する。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import keys

from 今週の予想.invited_rate import InvitedRate

#: 東西所属コード（JV-Data のコード表 2301）→ 招待の種類。
KINDS: dict[str, str] = {"3": "地方招待", "4": "外国招待"}
#: 中央の馬（美浦・栗東）の東西所属コード。人気ごとの基準の成績を数える。
_HOME_CODES: tuple[str, ...] = ("1", "2")
#: 倍率を 1 に寄せる強さ（実際の数と期待の数の両方にこの数を足す）。過去の数が少ない種類ほど、同じ人気の馬なみの評価に近づく。
SHRINK = 10.0


class InvitedRates:
    """招待馬（地方招待・外国招待）の中央での初出走の成績を、同じ人気の中央の馬の成績と比べた倍率で、1頭の確率を出す。

    1着になる確率 = 同じ人気の中央の馬の勝率 × 1着の倍率、3着以内に入る確率 = 同じ人気の中央の馬の3着以内率 × 3着以内の倍率。
    倍率 = (過去の同じ種類の初出走の1着の数 + ``SHRINK``) ÷ (同じ人気の中央の馬の率から見た1着の数 + ``SHRINK``)（3着以内も同じ）。
    先を見ないように、倍率はそのレースの日より前の初出走だけで、人気ごとの率はそのレースの年より前の年だけで数える。
    DB は ``load`` か最初の ``rate`` のときに1回だけ読む（中央の元DB の ``se``）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con
        self._kinds: dict[str, str] | None = None
        self._first_runs = pd.DataFrame()
        self._home = pd.DataFrame()
        self._base_cache: dict[int, pd.DataFrame] = {}

    def kind_of(self, horse_id: str) -> str | None:
        """招待の種類（外国招待・地方招待）。招待馬でなければ None。"""
        self.load()
        return self._kinds.get(str(horse_id))

    def rate(self, horse_id: str, popularity: float, race_date: str) -> InvitedRate | None:
        """``race_date``（YYYY-MM-DD）のレースに ``popularity`` 番人気で出る招待馬の評価。招待馬でないか、人気か基準が無ければ None。"""
        kind = self.kind_of(horse_id)
        if kind is None or pd.isna(popularity):
            return None
        base = self._base(int(race_date[:4]))
        popularity = int(popularity)
        if popularity not in base.index:
            return None
        runs = self._first_runs
        past = runs[(runs["kind"] == kind) & (runs["race_date"] < race_date) & runs["popularity"].isin(base.index)]
        expected = base.loc[past["popularity"]]
        win_factor = (float((past["finish"] == 1).sum()) + SHRINK) / (float(expected["win_rate"].sum()) + SHRINK)
        top3_factor = (float((past["finish"] <= 3).sum()) + SHRINK) / (float(expected["top3_rate"].sum()) + SHRINK)
        return InvitedRate(
            kind=kind, win=min(1.0, float(base.at[popularity, "win_rate"]) * win_factor),
            top3=min(1.0, float(base.at[popularity, "top3_rate"]) * top3_factor), runs=len(past),
            win_factor=win_factor, top3_factor=top3_factor,
        )

    def _base(self, year: int) -> pd.DataFrame:
        """``year`` より前の年の、中央の馬の人気ごとの勝率・3着以内率（index は人気）。"""
        if year not in self._base_cache:
            home = self._home[self._home["year"] < year].groupby("popularity")[["runs", "wins", "places"]].sum()
            home = home[home["runs"] > 0]
            self._base_cache[year] = pd.DataFrame({"win_rate": home["wins"] / home["runs"], "top3_rate": home["places"] / home["runs"]})
        return self._base_cache[year]

    def load(self) -> InvitedRates:
        """DB を読む（読んであれば何もしない）。接続を閉じる前に読んでおけば、閉じたあとも評価できる。自分を返す。"""
        if self._kinds is not None:
            return self
        codes = keys.sql_list(KINDS)
        kinds = self._con.execute(f"""
            SELECT {keys.q(keys.HORSE_KEY)} AS horse_id, arg_max({keys.q('東西所属コード')}, {keys.q('開催年')} || {keys.q('開催月日')}) AS code
            FROM se WHERE {keys.jra_only()} AND {keys.q('東西所属コード')} IN {codes} GROUP BY 1
        """).df()
        self._kinds = {str(row.horse_id): KINDS[row.code] for row in kinds.itertuples()}
        runs = _runs_sql()
        self._first_runs = self._con.execute(f"""
            WITH runs AS ({runs}), ordered AS (
                SELECT *, row_number() OVER (PARTITION BY horse_id ORDER BY race_date) AS nth FROM runs
            )
            SELECT race_date, horse_id, code, popularity, finish FROM ordered WHERE nth = 1 AND code IN {codes}
        """).df().assign(kind=lambda frame: frame["code"].map(KINDS))
        self._home = self._con.execute(f"""
            WITH runs AS ({runs})
            SELECT CAST(substr(race_date, 1, 4) AS INTEGER) AS year, popularity, count(*) AS runs,
                   sum(CASE WHEN finish = 1 THEN 1 ELSE 0 END) AS wins, sum(CASE WHEN finish <= 3 THEN 1 ELSE 0 END) AS places
            FROM runs WHERE code IN {keys.sql_list(_HOME_CODES)} GROUP BY ALL
        """).df()
        return self


def _runs_sql() -> str:
    """中央の確定成績の、走った（着順と人気のある）出走の行。列は race_date・horse_id・code（東西所属コード）・popularity・finish。"""
    out_of_race = keys.sql_list(keys.OUT_OF_RACE_CODES)
    return f"""
        SELECT * FROM (
            SELECT {keys.race_date_expr()} AS race_date, {keys.q(keys.HORSE_KEY)} AS horse_id, {keys.q('東西所属コード')} AS code,
                   TRY_CAST(NULLIF({keys.q('単勝人気順')}, '00') AS INTEGER) AS popularity,
                   CASE WHEN {keys.q('異常区分コード')} IN {out_of_race} THEN NULL
                        ELSE TRY_CAST(NULLIF({keys.q('確定着順')}, '00') AS INTEGER) END AS finish
            FROM se WHERE {keys.jra_only()} AND {keys.final_only()}
            {keys.latest_qualify((*keys.RACE_KEY, keys.HORSE_KEY))}
        ) WHERE finish IS NOT NULL AND popularity IS NOT NULL
    """
