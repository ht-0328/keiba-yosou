"""登録馬の確かめの流れを進める。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from 共通 import facts

from yosou.shared.dataset import HORSE_ID, HORSE_NAME, RACE_DATE, RACE_ID
from yosou.shared.dataset.column_names import FINISH, HORSE_NO, POPULARITY
from yosou.shared.repository import EntryRepository, TargetScope
from yosou.shared.workflow import PROBABILITY, WIN_PROBABILITY, PredictionWorkflow

from ..repository import EXCHANGE, RegistrationEntryInfoRepository, RegistrationListRepository
from .prediction_timings import REGISTRATION_TIMING

#: 登録馬の確かめの表の、この流れが足す列。
RACE_NAME = "競走名"
RAN = "出走した"
#: 書く予測の表のファイルの名前。
FILE_NAME = "registrations.pkl"
#: 確定成績の列（出走の行から読む）。
_OUTCOME_COLUMNS = ["race_id", "horse_id", "ran", "finish", "popularity", "horse_no"]


@dataclass(frozen=True)
class RegistrationCheckResult:
    """登録馬の確かめの結果。

    - ``table``: 1行 = 1頭の登録馬。レースID・開催日・競走名・馬ID・馬名・交流区分・3着以内に入る確率・1着になる確率・
      出走した・確定着順・確定の単勝人気・馬番（確定成績のもの）。予測できなかったレースは入らない。
    - ``skipped``: 予測できなかったレース（レースID, 理由）。
    - ``path``: 書いた表のファイル。
    """

    table: pd.DataFrame
    path: Path
    skipped: list[tuple[str, str]] = field(default_factory=list)


class RegistrationCheckWorkflow:
    """期間の特別登録の登録馬の全員に予測を出し、確定成績と突き合わせる（設計書 05 の図6・16 の 7）。

    レースの一覧は ``RegistrationListRepository``、予測は共通の ``PredictionWorkflow``（登録馬の行から。``registration_prediction_workflow``）、
    表に添える情報は ``RegistrationEntryInfoRepository``、確定成績は共通の ``EntryRepository``（事実表の、そのレースの出走の行）。
    出走しなかった登録馬は、出走の行が無いか取消・除外の行なので、「出走した」が偽になる。印は付けない（設計書 15 の 13）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, prediction: PredictionWorkflow, races: RegistrationListRepository,
                 info: RegistrationEntryInfoRepository, predictions_root: Path) -> None:
        self._con = con
        self._prediction = prediction
        self._races = races
        self._info = info
        self._entries = EntryRepository(con)
        self._predictions_root = Path(predictions_root)

    def run(self, begin: date, end: date | None = None) -> RegistrationCheckResult:
        races = self._races.read(begin, end)
        parts: list[pd.DataFrame] = []
        skipped: list[tuple[str, str]] = []
        for race in races.itertuples(index=False):
            try:
                predicted = self._prediction.run(race.race_id, REGISTRATION_TIMING)
            except (LookupError, ValueError, FileNotFoundError) as error:
                skipped.append((race.race_id, str(error)))
                continue
            parts.append(self._with_info(predicted, race.race_id, race.race_name))
        table = self._with_outcomes(pd.concat(parts, ignore_index=True)) if parts else self._empty()
        self._predictions_root.mkdir(parents=True, exist_ok=True)
        path = self._predictions_root / FILE_NAME
        table.to_pickle(path)
        return RegistrationCheckResult(table, path, skipped)

    def _with_info(self, predicted: pd.DataFrame, race_id: str, race_name: str) -> pd.DataFrame:
        """1レースの予測に、競走名・交流区分を足す。1着のモデルが無ければ 1着になる確率は欠損値。"""
        columns = [RACE_ID, RACE_DATE, HORSE_ID, HORSE_NAME, PROBABILITY]
        frame = predicted[columns].assign(**{WIN_PROBABILITY: predicted.get(WIN_PROBABILITY, pd.Series(float("nan"), index=predicted.index))})
        frame = frame.assign(**{RACE_NAME: race_name, HORSE_ID: frame[HORSE_ID].astype(str)})
        info = self._info.read(race_id)[[HORSE_ID, EXCHANGE]]
        return frame.merge(info, on=HORSE_ID, how="left")

    def _with_outcomes(self, table: pd.DataFrame) -> pd.DataFrame:
        """確定成績（出走したか・確定着順・確定人気・馬番）を突き合わせる。終わっていないレース・出走しなかった馬は欠損値（出走したは偽）。"""
        race_ids = ", ".join(f"'{race_id}'" for race_id in table[RACE_ID].astype(str).unique())
        scope = TargetScope(f"(SELECT * FROM {facts.FACTS_TABLE} WHERE race_id IN ({race_ids}))")
        outcomes = self._entries.read(scope)[_OUTCOME_COLUMNS]
        outcomes = outcomes.assign(race_id=outcomes["race_id"].astype(str), horse_id=outcomes["horse_id"].astype(str))
        merged = table.assign(**{RACE_ID: table[RACE_ID].astype(str)}).merge(
            outcomes.rename(columns={"race_id": RACE_ID, "horse_id": HORSE_ID}), on=[RACE_ID, HORSE_ID], how="left")
        return merged.assign(**{
            RAN: merged["ran"].eq(True).fillna(False).astype(bool), FINISH: pd.to_numeric(merged["finish"], errors="coerce"),
            POPULARITY: pd.to_numeric(merged["popularity"], errors="coerce"), HORSE_NO: pd.to_numeric(merged["horse_no"], errors="coerce"),
        }).drop(columns=_OUTCOME_COLUMNS[2:])

    def _empty(self) -> pd.DataFrame:
        columns = [RACE_ID, RACE_DATE, HORSE_ID, HORSE_NAME, PROBABILITY, WIN_PROBABILITY, RACE_NAME, EXCHANGE,
                   RAN, FINISH, POPULARITY, HORSE_NO]
        return pd.DataFrame(columns=columns)
