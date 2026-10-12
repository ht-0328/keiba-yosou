"""手順1: 帯のレースの事例と、切り口ごとの帯の集まり方を、Markdown の行にする。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_DATE

from .lift_table import LiftTable
from .obi_rules import BIG, OBI, OTHER
from .race_frame import PAYOUT_CLASS, YEAR
from .race_table_loader import TRIFECTA_YEN

#: 帯の事例として1行ずつ並べる列。
CASE_COLUMNS: tuple[str, ...] = (
    RACE_DATE, "競馬場", "芝ダ", "距離", "馬場状態", "クラス名", "出走頭数", "ハンデ戦か", "1番人気のオッズ",
    "市場勝率の上位3頭の合計", "1番人気の確定着順", "勝ち馬の人気", "1〜3着の人気の和", TRIFECTA_YEN,
)
#: 帯の集まり方を数える切り口（docs/01 の 4.1 の候補）。
LIFT_COLUMNS: dict[str, tuple[str, ...]] = {
    "頭数": ("出走頭数",),
    "レースの種類": ("クラス名", "ハンデ戦か", "牡馬と牝馬が一緒に走るか", "特別戦か", "開催月", "競馬場"),
    "力の拮抗": ("近5走の平均着差の1位と2位の差", "近5走の平均着順の標準偏差", "近5走の平均着順の中央値"),
    "読めない馬が多い": ("前走が無い馬の割合", "昇級馬の数", "乗り替わりの馬の数", "前走3着以内だった馬の割合"),
    "展開が読めない": ("逃げそうな馬の数",),
    "コース": ("芝ダ", "コース", "距離"),
    "馬場": ("馬場状態",),
    "人気の割れ方": ("1番人気のオッズ", "1番人気と2番人気のオッズの比", "市場勝率の上位3頭の合計", "市場勝率のエントロピー",
                  "単勝10倍未満の頭数", "2〜5番人気の最大オッズ", "最低人気のオッズ"),
    "1番人気の危うさ": ("1番人気の前走の着順", "1番人気の近5走で人気より悪い着順だった回数", "1番人気の乗り替わり",
                     "1番人気の距離の変更", "1番人気のクラスの変更"),
}
#: コースの単位（競馬場×コース×距離×馬場状態）の表に出す行の数と、行に要るレースの数。
COURSE_UNIT = ("競馬場", "コース", "距離", "馬場状態")
COURSE_TOP, COURSE_MIN_RACES = 25, 40
#: 帯の事例として並べる年（新しい年から。全部だと長すぎるので、理論を作る年の最後の2年）。
CASE_YEARS = 2
#: 事象の列（帯なら真）。
IS_OBI = "帯のレース"


class RaceCaseReport:
    """理論を作る年のレースから、帯のレースの事例と、切り口ごとの帯の集まり方の表を作る。"""

    def __init__(self, lift: LiftTable | None = None) -> None:
        self._lift = lift or LiftTable(IS_OBI)

    def lines(self, frame: pd.DataFrame) -> list[str]:
        frame = frame.assign(**{IS_OBI: frame[PAYOUT_CLASS].eq(OBI)})
        lines = self._summary(frame)
        lines += self._outcome_shape(frame)
        for title, columns in LIFT_COLUMNS.items():
            lines += [f"## 切り口: {title}", ""]
            lines += [part for column in columns for part in self._lift_section(frame, column)]
        lines += self._course_units(frame)
        lines += self._cases(frame)
        return lines

    def _summary(self, frame: pd.DataFrame) -> list[str]:
        table = frame.pivot_table(index=YEAR, columns=PAYOUT_CLASS, values=TRIFECTA_YEN, aggfunc="size", fill_value=0)
        table = table.reindex(columns=[OBI, BIG, OTHER], fill_value=0)
        table["レース"] = table.sum(axis=1)
        table["帯の割合"] = (table[OBI] / table["レース"]).round(4)
        table["開催日"] = frame.groupby(YEAR)[RACE_DATE].nunique()
        return ["## 年ごとのレースの数（3連単の払戻の段）", "", table.to_markdown(), ""]

    def _outcome_shape(self, frame: pd.DataFrame) -> list[str]:
        """帯のレースは、どんな決着だったか（1番人気の着順・勝ち馬の人気）。"""
        obi = frame[frame[IS_OBI]]
        favorite = obi["1番人気の確定着順"].clip(upper=4).map(lambda finish: "4着以下" if finish >= 4 else f"{finish:.0f}着")
        winner = pd.cut(obi["勝ち馬の人気"], [0, 1, 3, 5, 9, 99], labels=["1番人気", "2〜3番人気", "4〜5番人気", "6〜9番人気", "10番人気以下"])
        return ["## 帯のレースの決着の形", "",
                favorite.value_counts().rename("帯のレース").to_frame().rename_axis("1番人気の着順").to_markdown(), "",
                winner.value_counts(sort=False).rename("帯のレース").to_frame().rename_axis("勝ち馬の人気").to_markdown(), ""]

    def _lift_section(self, frame: pd.DataFrame, column: str) -> list[str]:
        table = self._lift.table(frame, column).round(4)
        return [f"### {column}", "", table.to_markdown(), ""]

    def _course_units(self, frame: pd.DataFrame) -> list[str]:
        unit = frame[list(COURSE_UNIT)].astype("string").agg("・".join, axis=1)
        table = self._lift.table(frame.assign(コースの単位=unit), "コースの単位")
        table = table[table["数"] >= COURSE_MIN_RACES].sort_values("集まり方", ascending=False).head(COURSE_TOP).round(4)
        return [f"## コースの単位（{'×'.join(COURSE_UNIT)}）で帯が集まった上位 {COURSE_TOP}（{COURSE_MIN_RACES}レース以上）", "",
                table.to_markdown(), ""]

    def _cases(self, frame: pd.DataFrame) -> list[str]:
        last = int(frame[YEAR].max())
        cases = frame[frame[IS_OBI] & frame[YEAR].gt(last - CASE_YEARS)].sort_values(RACE_DATE)
        table = cases[list(CASE_COLUMNS)].assign(**{RACE_DATE: cases[RACE_DATE].dt.strftime("%Y-%m-%d")})
        return [f"## 帯のレースの事例（{last - CASE_YEARS + 1}〜{last}年、{len(cases)}レース）", "",
                table.to_markdown(index=False), ""]
