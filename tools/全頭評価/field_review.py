"""1レースの全頭評価を組み立てる。"""

from __future__ import annotations

import math
from pathlib import Path

import duckdb
import pandas as pd

from yosou.shared.dataset import HORSE_ID, HORSE_NAME, RACE_DATE, RACE_ID
from yosou.shared.repository import TargetScope
from yosou.shared.repository.speed_figure_repository import DEFAULT_FOLDER
from yosou.shared.workflow import PROBABILITY, WIN_PROBABILITY
from yosou.special_registration_top3.repository import CARRIED, EXCHANGE, TABLE, TRAINER, RegistrationEntryInfoRepository
from yosou.special_registration_top3.workflow import REGISTRATION_TIMING, registration_prediction_workflow

from .horse_facts_repository import HorseFactsRepository
from .horse_points import HorsePoints
from .previous_run_repository import PreviousRunRepository
from .registration_stakes_map import RegistrationStakesMap
from .review_document import FieldReviewDocument, HorseReview
from .stakes_edition_repository import StakesEditionRepository
from .stakes_tendency_points import StakesTendencyPoints

#: 有力馬の候補の数（1着の確率の上位）。
CANDIDATES = 3
#: グレードコード → 表示。
_GRADES: dict[str, str] = {"A": "G1", "B": "G2", "C": "G3", "L": "L", "E": "特別"}


class FieldReview:
    """特別登録の登録馬の全員について、予測（確率と寄与）・事実・重賞の傾向から全頭評価の文書を組み立てる。

    予測は予想「特別登録馬の近走と適性から3着以内を予想」の ``PredictionWorkflow.explain``（登録馬の行から。``models_root`` のモデル）。
    事実は登録馬の行の一時表（``TABLE``。予測のときに作られる）と事実表から読む。重賞（G1〜G3）なら過去の開催の出走馬から傾向の文を足す。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, models_root: Path, figure_folder: Path = DEFAULT_FOLDER) -> None:
        self._con = con
        self._workflow = registration_prediction_workflow(con, models_root, figure_folder)
        self._facts = HorseFactsRepository(con)
        self._previous = PreviousRunRepository(con)
        self._info = RegistrationEntryInfoRepository(con)
        self._stakes_map = RegistrationStakesMap(con)
        self._editions = StakesEditionRepository(con)
        self._points = HorsePoints()
        self._tendency = StakesTendencyPoints()

    def build(self, race_id: str) -> FieldReviewDocument:
        """特別登録が無ければ ``LookupError``。"""
        explained = self._workflow.explain(race_id, REGISTRATION_TIMING)
        scope = TargetScope.of_table(TABLE)
        facts = self._facts.read(scope).set_index("horse_id")
        info = self._info.read(race_id).set_index(HORSE_ID)
        race = facts.iloc[0]
        stakes_no = self._stakes_map.ensure(race_id)
        previous = self._previous.read(scope).set_index("horse_id")
        editions = self._editions.read(stakes_no, race["race_date"].date()) if stakes_no else pd.DataFrame()
        table = explained.table.assign(**{HORSE_ID: explained.table[HORSE_ID].astype(str)})
        ordered = table.sort_values(PROBABILITY, ascending=False, kind="stable")
        horses = [self._horse(rank, row, explained.features.loc[index], explained.contributions.loc[index], facts, previous, info,
                              editions, len(table))
                  for rank, (index, row) in enumerate(ordered.iterrows(), start=1)]
        win_column = WIN_PROBABILITY if WIN_PROBABILITY in table.columns else PROBABILITY
        candidates = list(table.sort_values(win_column, ascending=False, kind="stable")[HORSE_NAME].head(CANDIDATES))
        notes = [f"重賞の傾向は、同じレースの過去 {editions['race_id'].nunique()} 開催（2011年以降）の出走馬から数えた。" if not editions.empty else
                 "重賞ではないので、過去の同じレースの傾向は出していない。",
                 "強み・弱みは、事実表の数字とモデルの寄与（分類ごとのロジットの上げ下げ）から定型で作った文。"]
        return FieldReviewDocument(
            race_id=race_id, race_date=race["race_date"].date(), race_name=str(race["race_name"]), venue=str(race["venue"]),
            surface=str(race["surface"]), distance_m=_int(race["distance_m"]), grade=_GRADES.get(str(race["grade_code"]).strip(), ""),
            entries=len(table), candidates=candidates, horses=horses, notes=notes,
        )

    def _horse(self, rank: int, row: pd.Series, features: pd.Series, contributions: pd.Series, facts: pd.DataFrame,
               previous: pd.DataFrame, info: pd.DataFrame, editions: pd.DataFrame, entries: int) -> HorseReview:
        horse_id = str(row[HORSE_ID])
        fact = facts.loc[horse_id]
        prev = previous.loc[horse_id] if horse_id in previous.index else None
        extra = info.loc[horse_id] if horse_id in info.index else pd.Series(dtype=object)
        points = self._points.of(fact, features, contributions, entries, prev)
        strong, weak = list(points.strong), list(points.weak)
        prev_name = str(prev["prev_race_name"]) if prev is not None and prev.get("prev_race_name") else None
        prev_stakes = str(prev["prev_stakes_no"]) if prev is not None and isinstance(prev.get("prev_stakes_no"), str) and prev.get("prev_stakes_no") else None
        for line in self._tendency.lines_of(editions, fact, prev_name, prev_stakes):
            if line.side is True:
                strong.append(line.text)
            elif line.side is False:
                weak.append(line.text)
        carried = _float(extra.get(CARRIED)) if len(extra) else _float(fact.get("carried"))
        trainer = str(extra.get(TRAINER)) if len(extra) and extra.get(TRAINER) else str(fact.get("trainer") or "")
        exchange = str(extra.get(EXCHANGE) or "") if len(extra) else ""
        sex_age = f"{fact.get('sex')}{_int(fact.get('age'))}"
        profile = (f"{sex_age}　父: {fact.get('sire') or '不明'}　母父: {fact.get('damsire') or '不明'}　調教師: {trainer}（{fact.get('affiliation')}）"
                   f"　負担重量: {carried:.0f}kg" if carried is not None else
                   f"{sex_age}　父: {fact.get('sire') or '不明'}　母父: {fact.get('damsire') or '不明'}　調教師: {trainer}（{fact.get('affiliation')}）　負担重量: 未定")
        if exchange:
            profile += f"　{exchange}馬"
        win = _float(row.get(WIN_PROBABILITY))
        return HorseReview(
            horse_id=horse_id, name=str(row[HORSE_NAME]), profile=profile, rank=rank, top3=float(row[PROBABILITY]),
            win=win if win is not None else float("nan"), sex_age=sex_age, trainer=trainer, carried=carried, exchange=exchange,
            strong=strong, weak=weak,
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
