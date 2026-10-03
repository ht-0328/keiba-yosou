"""印を付けた過去のレースから、いつも同じ形の成績の表を作る。"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from yosou.shared.win_value import EXPECTATION_LEVELS, HIGH, LINE

from 共通.bootstrap_interval import BootstrapInterval
from 共通.perf import PERF_COLUMNS, STAKE_YEN, percent
from 共通.render import Table

from 今週の予想.forecast_columns import EXPECTATION, MARK
from 今週の予想.mark_rule import NOTE_MARK, OUT_MARK, TOP_MARK, VALUE_MARK

from 印の成績.perf_rows import perf_row_of
from 印の成績.popularity_baseline import RATE_NAMES, PopularityBaseline

#: 印ごとの表に並べる印（今週の予想の印の並び）。
MARKS: tuple[str, ...] = (TOP_MARK, "○", "▲", "△", VALUE_MARK, NOTE_MARK, OUT_MARK)
#: 上位3つの印と、比べる人気（◎○▲ ↔ 1〜3番人気）。
TOP_MARKS: tuple[str, ...] = (TOP_MARK, "○", "▲")
TOP_POPULARITIES: tuple[int, ...] = (1, 2, 3)
#: 基準の行の名前。
BASELINE_LABEL = "└ 同じ人気の馬全体"
#: 印ごとの表の見出し（印・1レースの頭数のあとに、成績7つ）。
MARK_HEADERS: tuple[str, ...] = ("印", "1レースの頭数", *PERF_COLUMNS)
#: ◎ の期待度ごとの行の名前。
ALL_TOP_LABEL = "◎ 全体"


def _expectation_label(level: str) -> str:
    return f"◎（期待度 {level}）"


def _top_at(level: str) -> Callable[[pd.DataFrame], pd.Series]:
    return lambda m: (m[MARK] == TOP_MARK) & (m[EXPECTATION] == level)


#: 年ごとの表で見る印（◎ は1番人気かどうかと、期待度「高」でも分ける）。
_YEARLY: tuple[tuple[str, Callable[[pd.DataFrame], pd.Series]], ...] = (
    ("◎（1番人気）", lambda m: (m[MARK] == TOP_MARK) & (m["popularity"] == 1)),
    ("◎（1番人気以外）", lambda m: (m[MARK] == TOP_MARK) & (m["popularity"] != 1)),
    (_expectation_label(HIGH), _top_at(HIGH)),
    *((mark, (lambda mark: lambda m: m[MARK] == mark)(mark)) for mark in MARKS[1:]),
)


class MarkReport:
    """印を付けた表（``BacktestMarker.mark`` の戻り値）から、次の6つの表を作る。

    1. 印ごとの成績（成績7つ）と、同じ人気の馬全体の成績（``PopularityBaseline``）。◎ は1番人気かどうか・期待度でも分け、消は内訳も出す。
    2. ◎○▲ の3頭のうち3着以内に来た頭数の割合と、1〜3番人気の3頭の同じ割合。
    3. ◎○▲ のうち2頭とも3着以内に来た割合（組ごと）と、1〜3番人気の同じ組。
    4. 年ごとの印の成績。
    5. 区切りごとのレース数と、危険な人気馬の線と、期待度「高」のレース数。
    6. ◎ の期待度ごとの単勝の成績（レース数・1開催日あたり・成績・単勝回収率の 90% の幅。設計書「近走と適性から3着以内を予想」の 16 の 6 の採用の基準を見る表）。
    ``conditions`` は表の注に書く条件（予測のファイル・期間 など）。
    """

    def tables(self, marked: pd.DataFrame, conditions: str, lines: dict[str, dict[str, float]] | None = None) -> list[Table]:
        races = marked["race_id"].nunique()
        not_favorite_top = ((marked[MARK] == TOP_MARK) & (marked["popularity"] != 1)).sum() / races
        same_three = marked[marked[MARK].isin(TOP_MARKS)].groupby("race_id")["popularity"].apply(
            lambda values: set(values) == set(TOP_POPULARITIES)).mean()
        summary = (f"{conditions} レース数 {races:,}。◎が1番人気以外だったレース {percent(not_favorite_top)}。"
                   f"◎○▲が1〜3番人気と同じ3頭だったレース {percent(same_three)}。")
        return [self._marks(marked, races, summary), self._top_counts(marked), self._top_pairs(marked),
                self._yearly(marked), self._folds(marked, lines or {}), self._expectations(marked)]

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
            add(mark, marked[marked[MARK] == mark])
        favorite = marked["popularity"] == 1
        add("◎（1番人気）", marked[(marked[MARK] == TOP_MARK) & favorite])
        add("◎（1番人気以外）", marked[(marked[MARK] == TOP_MARK) & ~favorite])
        for level in EXPECTATION_LEVELS:
            add(_expectation_label(level), marked[_top_at(level)(marked)])
        add("消のうち 危険な1番人気", marked[marked["is_danger"]])
        add("消のうち 印が付かなかった馬", marked[(marked[MARK] == OUT_MARK) & ~marked["is_danger"]])
        add("1番人気 全体", marked[favorite], with_baseline=False)
        add("全頭", marked, with_baseline=False)
        note = (summary + " ◎は、1着の予想があれば単勝の期待値（1着になる確率 × 確定の単勝オッズ）が1位の馬、無ければ3着以内の確率が1位の馬。"
                f"期待度は、◎の単勝の期待値が {LINE:.2f} 以上なら高、未満なら低（表6）。"
                f" 「{BASELINE_LABEL}」は、印の馬と同じ人気の馬全体の成績を、印の馬の人気の内訳で重み付けして平均したもの"
                "（人気どおりに同じ頭数を買った場合）。回収率は確定オッズの払戻で数えた。競走中止など着順の付かない馬は着外に数える。")
        return Table(list(MARK_HEADERS), rows, title="1. 印ごとの成績", note=note)

    def _top_counts(self, marked: pd.DataFrame) -> Table:
        races = marked["race_id"].unique()
        headers = ["3頭", "0頭", "1頭", "2頭", "3頭すべて", "2頭以上", "1頭以上"]

        def row(label: str, chosen: pd.DataFrame) -> list[str]:
            counts = (chosen["finish"] <= 3).groupby(chosen["race_id"]).sum().reindex(races, fill_value=0)
            share = counts.value_counts(normalize=True).reindex([0, 1, 2, 3], fill_value=0.0)
            return [label, *(percent(share[n]) for n in (0, 1, 2, 3)), percent(share[2] + share[3]), percent(1 - share[0])]

        rows = [row("◎○▲", marked[marked[MARK].isin(TOP_MARKS)]),
                row("1〜3番人気", marked[marked["popularity"].isin(TOP_POPULARITIES)])]
        return Table(headers, rows, title="2. ◎○▲の3頭のうち3着以内に来た頭数（レースの割合）",
                     note="1〜3番人気の行は、同じレースの1〜3番人気の3頭で同じように数えたもの（比べる基準）。")

    def _top_pairs(self, marked: pd.DataFrame) -> Table:
        marks = self._top3_by(marked[marked[MARK].isin(TOP_MARKS)], MARK)
        popularities = self._top3_by(marked[marked["popularity"].isin(TOP_POPULARITIES)], "popularity")
        pairs = (((TOP_MARK, "○"), (1, 2)), ((TOP_MARK, "▲"), (1, 3)), (("○", "▲"), (2, 3)))
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
                         "—" if line is None or pd.isna(line) else f"{line * 100:.0f}ポイント",
                         f"{(group[_top_at(HIGH)(group)])['race_id'].nunique():,}"])
        return Table(["区切り", "レース数", "危険な1番人気", "1番人気の危険の線", "期待度「高」のレース"], rows,
                     title="5. 区切りごとのレース数と危険の線",
                     note="危険の線は、区切りごとに、その区切りの検証期間で決め直した値（テスト期間の結果は使っていない）。"
                          f"期待度「高」は、◎の単勝の期待値が {LINE:.2f} 以上のレース。")

    def _expectations(self, marked: pd.DataFrame) -> Table:
        days = marked["race_date"].nunique()
        baseline = PopularityBaseline(marked)
        tops = marked[marked[MARK] == TOP_MARK]
        headers = ["◎の期待度", "レース数", "1開催日あたり", "着別度数", "勝率", "単勝回収率", "単勝回収率の90%の幅", "同じ人気の馬全体の単勝回収率",
                   "複勝回収率"]
        rows = []
        for label, chosen in [(level, tops[tops[EXPECTATION] == level]) for level in EXPECTATION_LEVELS] + [(ALL_TOP_LABEL, tops)]:
            if chosen.empty:
                rows.append([label, "0", "0.00", "0-0-0-0", "—", "—", "—", "—", "—"])
                continue
            rates = perf_row_of(chosen).rates()
            low, high = BootstrapInterval().of(chosen["race_date"], pd.Series(float(STAKE_YEN), index=chosen.index),
                                               chosen["win_payout"].astype(float))
            rows.append([label, f"{len(chosen):,}", f"{len(chosen) / days:.2f}", perf_row_of(chosen).counts(), percent(rates["勝率"]),
                         percent(rates["単勝回収率"]), f"{percent(low)}〜{percent(high)}", percent(baseline.rates(chosen)["単勝回収率"]),
                         percent(rates["複勝回収率"])])
        return Table(headers, rows, title="6. ◎の期待度ごとの単勝の成績",
                     note=f"開催日 {days:,}日。期待度は、◎の単勝の期待値が {LINE:.2f} 以上なら高、未満なら低。"
                          "90% の幅は、開催日を単位にしたブートストラップ。採用の基準は、「高」の単勝回収率と幅の下の端が"
                          "どちらも 100% を超えること（設計書「近走と適性から3着以内を予想」の 16 の 6）。確定オッズでの検証なので、実際に買うときより良く出る。")

    def _top3_by(self, rows: pd.DataFrame, key: str) -> pd.DataFrame:
        """レース × （印か人気）→ 3着以内に来たか。"""
        return rows.assign(top3=rows["finish"] <= 3).pivot_table(index="race_id", columns=key, values="top3", aggfunc="first")


def _both(table: pd.DataFrame, a, b) -> float:
    """2頭とも3着以内に来たレースの割合。どちらかがいないレースは来なかったとみなす。"""
    if a not in table.columns or b not in table.columns:
        return 0.0
    return float((table[a].fillna(False).astype(bool) & table[b].fillna(False).astype(bool)).mean())
