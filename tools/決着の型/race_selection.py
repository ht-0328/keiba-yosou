"""レースを選ぶ条件: レース単位の絞り込み（競馬場・クラス・期間 …）と、決着の表で決まる条件（オッズの散らばり・限定戦）。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import pandas as pd

from 共通 import cli
from 共通.filters import FILTER_FIELDS, Filters, Range

#: 絞り込みのうち、レース単位の項目。出走馬の条件（人気・枠・性別・騎手 …）はレースの形を壊すので使わない。
RACE_LEVEL_FIELDS: tuple[str, ...] = ("venue", "surface", "course", "distance", "condition", "class", "field", "from", "to", "month")
_EXTRA_HELP = {
    "under10": "単勝 10倍以下の頭数の範囲（例 -3）。出走した馬の確定オッズで数える",
    "under30": "単勝 30倍以下の頭数の範囲（例 -5）",
    "age-only": "出走馬が全員その馬齢のレースだけ（例 3 = 3歳限定戦）",
}


@dataclass(frozen=True)
class RaceSelection:
    """レースを選ぶ条件。``filters`` は事実表に当て、残りは決着の表に当てる。"""

    filters: Filters = Filters()
    under10: Range | None = None
    under30: Range | None = None
    age_only: int | None = None

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        """レース単位の絞り込みのフラグと、決着の表で決まる条件のフラグを足す。"""
        group = parser.add_argument_group("レースを選ぶ条件（省略した条件は効かない。範囲は 1600 か 1400-1800、1400- や -1800 も可）")
        for field in FILTER_FIELDS:
            if field.name in RACE_LEVEL_FIELDS:
                group.add_argument(f"--{field.name}", dest=f"filter_{field.name}", metavar=field.example, help=field.help)
        group.add_argument("--under10", metavar="-3", help=_EXTRA_HELP["under10"])
        group.add_argument("--under30", metavar="-5", help=_EXTRA_HELP["under30"])
        group.add_argument("--age-only", type=int, metavar="3", help=_EXTRA_HELP["age-only"])

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "RaceSelection":
        return cls(
            filters=cli.filters_from(args),
            under10=Range.parse(args.under10) if args.under10 else None,
            under30=Range.parse(args.under30) if args.under30 else None,
            age_only=args.age_only,
        )

    def apply(self, races: pd.DataFrame) -> pd.DataFrame:
        """決着の表から、オッズの散らばりと限定戦の条件に合うレースだけを残す。"""
        keep = pd.Series(True, index=races.index)
        for column, value in (("n_under10", self.under10), ("n_under30", self.under30)):
            if value is not None:
                keep &= races[column].map(value.contains)
        if self.age_only is not None:
            keep &= races["age_min"].eq(self.age_only) & races["age_max"].eq(self.age_only)
        return races[keep]

    def describe(self) -> str:
        """人が読む形。例: ``東京 芝・左 1600m 単勝10倍以下 -3頭``。"""
        parts = [] if self.filters.is_empty() else [self.filters.describe()]
        if self.under10 is not None:
            parts.append(f"単勝10倍以下 {self.under10.text()}頭")
        if self.under30 is not None:
            parts.append(f"単勝30倍以下 {self.under30.text()}頭")
        if self.age_only is not None:
            parts.append(f"{self.age_only}歳限定戦")
        return " ".join(parts) or "全レース"
