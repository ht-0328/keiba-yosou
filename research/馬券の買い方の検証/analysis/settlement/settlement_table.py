"""精算表（全買い方 × 全レース）。"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from .plan_result import PlanResult

#: 精算表の列。
RACE_ID, PLAN, POINTS, STAKE_YEN, PAYOUT_YEN, HIT_COUNT, SKIPPED = (
    "race_id", "plan", "points", "stake_yen", "payout_yen", "hit_count", "skipped",
)
COLUMNS: tuple[str, ...] = (RACE_ID, PLAN, POINTS, STAKE_YEN, PAYOUT_YEN, HIT_COUNT, SKIPPED)
_ENCODING = "utf-8-sig"


class SettlementTable:
    """レース × 買い方 の精算表。1行 = 1レース × 1買い方（点数・賭け金・払戻・的中数・見送りの理由）。

    しきい値に依存しないので1回だけ作り、戦略の探索は、この表から行を選んで足すだけにする。
    JV-Data 由来の払戻を含むので、保存先は ``reports/``。
    """

    def __init__(self, rows: pd.DataFrame) -> None:
        missing = [column for column in COLUMNS if column not in rows.columns]
        if missing:
            raise ValueError(f"精算表に列がありません: {'・'.join(missing)}")
        self._rows = rows[list(COLUMNS)].reset_index(drop=True)

    @classmethod
    def from_results(cls, results: Iterable[PlanResult]) -> SettlementTable:
        rows = pd.DataFrame([vars(result) for result in results]).rename(columns={"plan_name": PLAN})
        return cls(rows.reindex(columns=list(COLUMNS)))

    @property
    def rows(self) -> pd.DataFrame:
        return self._rows

    @property
    def plan_names(self) -> list[str]:
        return list(self._rows[PLAN].unique())

    def for_plan(self, plan_name: str) -> pd.DataFrame:
        """1つの買い方の行（レースID を index に）。"""
        return self._rows[self._rows[PLAN] == plan_name].set_index(RACE_ID)

    def write(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._rows.to_csv(path, index=False, encoding=_ENCODING)

    @classmethod
    def read(cls, path: Path) -> SettlementTable:
        if not Path(path).exists():
            raise FileNotFoundError(f"精算表がありません: {path}（先に backtest.py --settle-only を実行してください）")
        return cls(pd.read_csv(path, encoding=_ENCODING, dtype={RACE_ID: str}, keep_default_na=False, na_values=[""]))
