"""重賞の攻略ポイント（一覧と、1つの重賞のページ）を出す。CLI（``stakes.py``）と検索画面（``検索画面/server.py``）の両方が使う。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通.render import Table

from . import loading, page
from .repository import CourseRateRepository

#: グレードコード → 呼び名（一覧の表示用）。
_GRADE_NAMES = {"A": "G1", "B": "G2", "C": "G3"}


class StakesGuide:
    """重賞の出走の行（``loading.load_runners``）とコースの基準から、一覧・1レースのページを作る。

    ``before`` を渡すと、その開催日より前の開催だけで数える（予想モデルがその日に見る値の確かめ用）。
    コースの基準は全期間のまま（CLI の ``--before`` と同じ）。
    """

    def __init__(self, runners: pd.DataFrame, course_rates: pd.DataFrame) -> None:
        self._runners = runners
        self._course_rates = course_rates

    @classmethod
    def load(cls, con: duckdb.DuckDBPyConnection, before: str | None = None) -> StakesGuide:
        """元DB から読む。``before``（YYYY-MM-DD）より前の開催が無ければ ``ValueError``。"""
        runners = loading.load_runners(con)
        course_rates = CourseRateRepository(con).read()
        if not before:
            return cls(runners, course_rates)
        limit = date.fromisoformat(before).isoformat()
        runners = runners[runners["race_date"].astype(str).str[:10] < limit]
        if runners.empty:
            raise ValueError(f"{before} より前の重賞の開催がありません")
        return cls(runners, course_rates)

    def list_table(self) -> Table:
        """重賞の一覧（特別競走番号・グレード・競走名・条件・開催数・期間）。いちばん新しい開催の条件で表示する。"""
        names = loading.latest_names(self._runners)
        rows = [[row["stakes_no"], _GRADE_NAMES.get(row["grade"], row["grade"]), row["stakes_name"],
                 row["venue"], row["course"], row["distance_m"], row["editions"],
                 f"{row['first_year']}〜{row['last_year']}"] for _, row in names.iterrows()]
        return Table(columns=["特別競走番号", "グレード", "競走名", "競馬場", "コース", "距離", "開催数", "期間"],
                     rows=rows, note=f"重賞 {len(rows)} レース（いちばん新しい開催の条件で表示）")

    def stakes_numbers(self) -> list[str]:
        """一覧の並び（G1 → G2 → G3、番号の順）の特別競走番号。"""
        return [str(no) for no in loading.latest_names(self._runners)["stakes_no"]]

    def choose(self, no: str | None, name: str | None) -> str:
        """特別競走番号か競走名（部分一致）から、対象の重賞を1つに決める。決まらなければ候補を見せて ``LookupError``。"""
        if no:
            if (self._runners["stakes_no"] == no).any():
                return no
            raise LookupError(f"特別競走番号 {no} の重賞が見つかりません（一覧で確かめてください）")
        if not name:
            raise ValueError("特別競走番号か競走名を指定してください")
        names = loading.latest_names(self._runners)
        hits = names[names["stakes_name"].str.contains(name, regex=False)]
        if len(hits) == 1:
            return str(hits["stakes_no"].iloc[0])
        if hits.empty:
            raise LookupError(f"名前に「{name}」を含む重賞が見つかりません（一覧で確かめてください）")
        candidates = "・".join(hits["stakes_name"])
        raise LookupError(f"候補が複数あります: {candidates}（特別競走番号で指定してください）")

    def page(self, stakes_no: str) -> page.StakesPage:
        """1つの重賞の攻略ポイントのページ。人気の基準は同じグレードの重賞全体、脚質・枠の基準はそのコースの全クラス。"""
        race_rows = self._runners[self._runners["stakes_no"] == stakes_no]
        grade = race_rows.loc[race_rows["race_date"].idxmax(), "grade"]
        grade_rows = self._runners[self._runners["grade"] == grade]
        return page.build_page(race_rows, grade_rows, self._rates_of(race_rows))

    def _rates_of(self, race_rows: pd.DataFrame) -> pd.Series | None:
        """そのレースのコース（いちばん多く使われた組み合わせ）の基準の率。無ければ None。"""
        key = race_rows.groupby(["venue", "course", "distance_m"]).size().idxmax()
        if key not in self._course_rates.index:
            return None
        return self._course_rates.loc[key]
