"""印を付けた過去のレースから、いつも同じ形の成績の表を作る。"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from 共通.perf import PERF_COLUMNS, percent
from 共通.render import Table

from 今週の予想.mark_rule import NOTE_MARK, OUT_MARK, VALUE_MARK

from 印の成績.perf_rows import perf_row_of
from 印の成績.popularity_baseline import RATE_NAMES, PopularityBaseline

#: 印ごとの表に並べる印（今週の予想の印の並び）。
MARKS: tuple[str, ...] = ("◎", "○", "▲", "△", VALUE_MARK, NOTE_MARK, OUT_MARK)
#: 上位3つの印と、比べる人気（◎○▲ ↔ 1〜3番人気）。
TOP_MARKS: tuple[str, ...] = ("◎", "○", "▲")
TOP_POPULARITIES: tuple[int, ...] = (1, 2, 3)
#: 基準の行の名前。
BASELINE_LABEL = "└ 同じ人気の馬全体"
#: 印ごとの表の見出し（印・1レースの頭数のあとに、成績7つ）。
MARK_HEADERS: tuple[str, ...] = ("印", "1レースの頭数", *PERF_COLUMNS)
#: 年ごとの表で見る印（◎ は1番人気かどうかで分ける）。
_YEARLY: tuple[tuple[str, Callable[[pd.DataFrame], pd.Series]], ...] = (
    ("◎（1番人気）", lambda m: (m["mark"] == "◎") & (m["popularity"] == 1)),
    ("◎（1番人気以外）", lambda m: (m["mark"] == "◎") & (m["popularity"] != 1)),
    *((mark, (lambda mark: lambda m: m["mark"] == mark)(mark)) for mark in MARKS[1:]),
)


class MarkReport:
    """印を付けた表（``BacktestMarker.mark`` の戻り値）から、次の5つの表を作る。

    1. 印ごとの成績（成績7つ）と、同じ人気の馬全体の成績（``PopularityBaseline``）。◎ は1番人気かどうかでも分け、消は内訳も出す。
    2. ◎○▲ の3頭のうち3着以内に来た頭数の割合と、1〜3番人気の3頭の同じ割合。
    3. ◎○▲ のうち2頭とも3着以内に来た割合（組ごと）と、1〜3番人気の同じ組。
    4. 年ごとの印の成績。
    5. 区切りごとのレース数と、危険な人気馬の線。
    ``conditions`` は表の注に書く条件（予測のファイル・期間 など）。
    """

    def tables(self, marked: pd.DataFrame, conditions: str, lines: dict[str, dict[str, float]] | None = None) -> list[Table]:
        races = marked["race_id"].nunique()
        not_favorite_top = ((marked["mark"] == "◎") & (marked["popularity"] != 1)).sum() / races
        same_three = marked[marked["mark"].isin(TOP_MARKS)].groupby("race_id")["popularity"].apply(
            lambda values: set(values) == set(TOP_POPULARITIES)).mean()
        summary = (f"{conditions} レース数 {races:,}。◎が1番人気以外だったレース {percent(not_favorite_top)}。"
                   f"◎○▲が1〜3番人気と同じ3頭だったレース {percent(same_three)}。")
        return [self._marks(marked, races, summary), self._top_counts(marked), self._top_pairs(marked),
                self._yearly(marked), self._folds(marked, lines or {})]

    def _marks(self, marked: pd.DataFrame, races: int, summary: str) -> Table:
        baseline = PopularityBaseline(marked)
        rows: list[list[str]] = []

        def add(label: str, chosen: pd.DataFrame, with_baseline: bool = True) -> None:
            if chosen.empty:
                rows.append([label, "0", "0", "0-0-0-0", *["—"] * len(RATE_NAMES)])
                return
            rows.append([label, f"{len(chosen) / races:.2f}", *perf_row_of(chosen).cells()])
            if with_baseline:
                rates = baseline.rates(chosen)
                rows.append([BASELINE_LABEL, "", "", "", *(percent(rates[name]) for name in RATE_NAMES)])

        for mark in MARKS:
            add(mark, marked[marked["mark"] == mark])
        favorite = marked["popularity"] == 1
        add("◎（1番人気）", marked[(marked["mark"] == "◎") & favorite])
        add("◎（1番人気以外）", marked[(marked["mark"] == "◎") & ~favorite])
        add("消のうち 危険な1番人気", marked[marked["is_danger"]])
        add("消のうち 印が付かなかった馬", marked[(marked["mark"] == OUT_MARK) & ~marked["is_danger"]])
        add("1番人気 全体", marked[favorite], with_baseline=False)
        add("全頭", marked, with_baseline=False)
        note = (summary + f" 「{BASELINE_LABEL}」は、印の馬と同じ人気の馬全体の成績を、印の馬の人気の内訳で重み付けして平均したもの"
                "（人気どおりに同じ頭数を買った場合）。回収率は確定オッズの払戻で数えた。競走中止など着順の付かない馬は着外に数える。")
        return Table(list(MARK_HEADERS), rows, title="1. 印ごとの成績", note=note)

    def _top_counts(self, marked: pd.DataFrame) -> Table:
        races = marked["race_id"].unique()
        headers = ["3頭", "0頭", "1頭", "2頭", "3頭すべて", "2頭以上", "1頭以上"]

        def row(label: str, chosen: pd.DataFrame) -> list[str]:
            counts = (chosen["finish"] <= 3).groupby(chosen["race_id"]).sum().reindex(races, fill_value=0)
            share = counts.value_counts(normalize=True).reindex([0, 1, 2, 3], fill_value=0.0)
            return [label, *(percent(share[n]) for n in (0, 1, 2, 3)), percent(share[2] + share[3]), percent(1 - share[0])]

        rows = [row("◎○▲", marked[marked["mark"].isin(TOP_MARKS)]),
                row("1〜3番人気", marked[marked["popularity"].isin(TOP_POPULARITIES)])]
        return Table(headers, rows, title="2. ◎○▲の3頭のうち3着以内に来た頭数（レースの割合）",
                     note="1〜3番人気の行は、同じレースの1〜3番人気の3頭で同じように数えたもの（比べる基準）。")

    def _top_pairs(self, marked: pd.DataFrame) -> Table:
        marks = self._top3_by(marked[marked["mark"].isin(TOP_MARKS)], "mark")
        popularities = self._top3_by(marked[marked["popularity"].isin(TOP_POPULARITIES)], "popularity")
        pairs = ((("◎", "○"), (1, 2)), (("◎", "▲"), (1, 3)), (("○", "▲"), (2, 3)))
        rows = [[f"{a}と{b}", percent(_both(marks, a, b)), f"{x}と{y}番人気", percent(_both(popularities, x, y))]
                for (a, b), (x, y) in pairs]
        return Table(["印の組", "2頭とも3着以内", "人気の組", "2頭とも3着以内（人気）"], rows,
                     title="3. 2頭とも3着以内に来たレースの割合")

    def _yearly(self, marked: pd.DataFrame) -> Table:
        years = marked["race_date"].astype(str).str[:4]
        rows = []
        for label, pick in _YEARLY:
            chosen = marked[pick(marked)]
            for year, group in chosen.groupby(years[chosen.index]):
                rows.append([label, year, *perf_row_of(group).cells()])
        return Table(["印", "年", *PERF_COLUMNS], rows, title="4. 年ごとの印の成績")

    def _folds(self, marked: pd.DataFrame, lines: dict[str, dict[str, float]]) -> Table:
        rows = []
        for fold, group in marked.groupby("fold", sort=True):
            line = lines.get(fold, {}).get("1番人気")
            rows.append([fold, f"{group['race_id'].nunique():,}", f"{int(group['is_danger'].sum()):,}",
                         "—" if line is None or pd.isna(line) else f"{line * 100:.0f}ポイント"])
        return Table(["区切り", "レース数", "危険な1番人気", "1番人気の危険の線"], rows, title="5. 区切りごとのレース数と危険の線",
                     note="危険の線は、区切りごとに、その区切りの検証期間で決め直した値（テスト期間の結果は使っていない）。")

    def _top3_by(self, rows: pd.DataFrame, key: str) -> pd.DataFrame:
        """レース × （印か人気）→ 3着以内に来たか。"""
        return rows.assign(top3=rows["finish"] <= 3).pivot_table(index="race_id", columns=key, values="top3", aggfunc="first")


def _both(table: pd.DataFrame, a, b) -> float:
    """2頭とも3着以内に来たレースの割合。どちらかがいないレースは来なかったとみなす。"""
    if a not in table.columns or b not in table.columns:
        return 0.0
    return float((table[a].fillna(False).astype(bool) & table[b].fillna(False).astype(bool)).mean())
