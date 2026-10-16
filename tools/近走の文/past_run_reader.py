"""馬ごとの過去走（ペース・回顧の不利つき）を読む。"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date

import duckdb
import pandas as pd

from 共通 import facts

from yosou.review import names
from yosou.review.repository.review_store import ReviewStore

from .past_run import GRADES, PastRun
from .past_run_repository import PastRunRepository
from .race_pace_repository import RacePaceRepository
from .review_note_repository import ReviewNoteRepository


class PastRunReader:
    """対象の馬の、基準日より前の中央の出走を、レースのペースと回顧の不利を付けて ``PastRun`` の並び（古い順）にする。

    事実表を作り（``facts.ensure_facts``）、過去走・ペース・回顧の3つのリポジトリを1回ずつ引く。回顧は ``store``（既定は
    ``reports/回顧/review.duckdb``）から。無ければ不利なしで作る。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, store: ReviewStore | None = None) -> None:
        self._con = con
        self._runs = PastRunRepository(con)
        self._pace = RacePaceRepository(con)
        self._notes = ReviewNoteRepository(store or ReviewStore())

    def read(self, horse_ids: Sequence[str], before: date) -> dict[str, list[PastRun]]:
        """horse_id → 過去走の並び（古い順。無ければ空のリスト）。"""
        ids = list(dict.fromkeys(str(horse_id) for horse_id in horse_ids))
        result: dict[str, list[PastRun]] = {horse_id: [] for horse_id in ids}
        facts.ensure_facts(self._con)
        runs = self._runs.read(ids, before)
        if runs.empty:
            return result
        race_ids = list(dict.fromkeys(runs["race_id"].astype(str)))
        pace = self._pace.read(race_ids)
        notes = self._notes.read(race_ids, ids)
        words = {(str(row[names.RACE_ID]), str(row[names.HORSE_ID])): self._notes.words_of(row) for _, row in notes.iterrows()}
        for row in runs.to_dict("records"):
            run = self._past_run(row, pace, words)
            result[run.horse_id].append(run)
        return result

    def _past_run(self, row: dict, pace: pd.Series, words: dict[tuple[str, str], tuple[str, ...]]) -> PastRun:
        race_id, horse_id = str(row["race_id"]), str(row["horse_id"])
        return PastRun(
            race_id=race_id, race_date=pd.Timestamp(row["race_date"]).date(), horse_id=horse_id,
            venue=_text(row["venue"]), race_name=_text(row["race_name"]), class_name=_text(row["class_name"]),
            grade=GRADES.get(_text(row["grade_code"]), ""), surface=_text(row["surface"]), distance_m=_int(row["distance_m"]) or 0,
            condition=_text(row["condition"]), field_size=_int(row["field_size"]), frame_no=_int(row["frame_no"]),
            popularity=_int(row["popularity"]), finish=_int(row["finish"]), time_diff=_float(row["time_diff"]),
            first_corner_rank=_int(row["first_corner_rank"]), corner4=_int(row["corner4"]), last3f=_float(row["last3f"]),
            last3f_rank=_int(row["last3f_rank"]), last3f_count=_int(row["last3f_count"]), jockey=_text(row["jockey"]),
            carried=_float(row["carried"]), body_weight=_int(row["body_weight"]), weight_change=_int(row["weight_change"]),
            interval_days=_int(row["interval_days"]), class_order=_int(row["class_order"]),
            pace=_float(pace.get(race_id)), handicaps=words.get((race_id, horse_id), ()),
        )


def _float(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else number


def _int(value: object) -> int | None:
    number = _float(value)
    return None if number is None else int(number)


def _text(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()
