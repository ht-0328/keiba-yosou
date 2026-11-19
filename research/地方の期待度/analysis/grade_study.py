"""推奨買目の見込みで付けた期待度の確かめ: レースの推奨買目の見込み（見込みの回収率・期待の儲け）の帯・等級ごとの実際の成績
（回収率・最高の1点を除いた回収率・的中率・1日の儲け）を年ごとに並べ、前の期待度（◎ の点数）で分けたときと比べる。
線は最初の年の分位で決め、残りの年で等級の順に成績が上がるかを見る。最後に本番の線（``BET_PROFIT_LINES``）でも同じ表を作る。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from yosou.shared.race_grade import BET_PROFIT_LINES, GRADES, LocalBetProfitScale, LocalTopScoreScale

from 共通.render import Table

from 地方の万馬券.analysis.case_report import CaseReport

from .grade_lines import GradeLines
from .race_scores import EXPECTED, EXPECTED_PROFIT, RaceScores
from .recommended_bets_builder import LEAVE_ONE_OUT

REPORT_NAME = "推奨買目の見込みの期待度"
#: 帯の数（全部の年をまとめた分位で切る）。
BANDS = 5
#: 等級の列。
GRADE = "grade"
_COLUMNS: tuple[str, ...] = ("区分", "年", "レース", "レースの割合", "1レースの点数", "見込みの平均", "回収率", "最高の1点を除く回収率", "的中率", "1日の儲け")
_ORDER_COLUMNS: tuple[str, ...] = ("分け方", "年", "S", "A", "B", "C", "回収率が順に上がった", "的中率が順に上がった", "1日の儲けが順に上がった")
_SCORES: dict[str, str] = {EXPECTED: "見込みの回収率（期待値の平均）", EXPECTED_PROFIT: "期待の儲け（Σ（期待値 − 1））"}
_NOW = "前の期待度（◎ の点数）"
_PRODUCTION = "本番の期待度（期待の儲けを丸めた線）"


@dataclass(frozen=True)
class GradeStudy:
    """``bets`` は推奨買目の表（``RecommendedBetsBuilder``）、``races`` は対象の全レース（買わなかったレースも入る）、
    ``tops`` は ◎ の行（``TopPicks``。``race_id``・``win_probability``・``win_value``）。"""

    bets: pd.DataFrame
    races: pd.DataFrame
    tops: pd.DataFrame
    protocol: str = LEAVE_ONE_OUT

    def scored(self, column: str = EXPECTED) -> tuple[pd.DataFrame, dict[str, float]]:
        """レースの見込みと、``column``（見込みの回収率か期待の儲け）で付けた等級の表（推奨買目のあるレースだけ）と、使った線。"""
        scores = RaceScores().of(self.bets)
        first = scores["year"] == scores["year"].min()
        lines = GradeLines().decide(scores.loc[first, column])
        return scores.assign(**{GRADE: GradeLines.grade(scores[column], lines)}), lines

    def write(self, out_dir: Path) -> Path:
        years = sorted(self.races["year"].unique())
        days = self.races.groupby("year")["race_date"].nunique()
        counts = self.races.groupby("year").size()
        base = RaceScores().of(self.bets)
        tables = [self._band_table(base, column, years, days, counts, number) for number, column in enumerate(_SCORES, start=1)]
        order_rows = []
        for column, name in _SCORES.items():
            graded, lines = self.scored(column)
            tables.append(Table.from_records(_grade_rows(graded, years, days, counts), _COLUMNS, title=f"{len(tables) + 1}. {name}で付けた等級ごとの成績",
                                             note=f"線は {GradeLines.legend(lines)}（{years[0]}年の分位。上から 2割・3割・3割・2割）。"))
            order_rows += _order_rows(name, graded, years)
        production = base.assign(**{GRADE: base[EXPECTED_PROFIT].map(LocalBetProfitScale().of)})
        tables.append(Table.from_records(_grade_rows(production, years, days, counts), _COLUMNS,
                                         title=f"{len(tables) + 1}. {_PRODUCTION}ごとの成績", note=f"線は {LocalBetProfitScale.legend()}。"))
        order_rows += _order_rows(_PRODUCTION, production, years, every_year=True)
        now = self._now_grades(graded)
        tables.append(Table.from_records(_grade_rows(now, years, days, counts), _COLUMNS,
                                         title=f"{len(tables) + 1}. {_NOW}で分けたときの同じ推奨買目の成績", note=f"線は {LocalTopScoreScale.legend()}。"))
        order_rows += _order_rows(_NOW, now, years)
        tables.append(Table.from_records(order_rows, _ORDER_COLUMNS, title=f"{len(tables) + 1}. 等級ごとの回収率と、C → B → A → S の順に上がったか",
                                         note=f"S・A・B・C の欄は回収率（括弧は的中率）。線を分位で決めた分け方は、線を決めた年を数えない。本番の線（固定）は全部の年を数える。本番の線は {BET_PROFIT_LINES['S']:g}・{BET_PROFIT_LINES['A']:g}・{BET_PROFIT_LINES['B']:g}。"))
        intro = (f"推奨買目は本番と同じ決まり（道具「地方の推奨買目」の RECOMMENDED_PLANS）で作り直した。組の確率の当てはめ方は「{self.protocol}」。"
                 "1点 100円・確定オッズ・確定払戻。見込みの回収率は、そのレースの推奨買目の期待値の平均（1点 100円で買ったときの見込み）。"
                 "レースの割合は、その年の対象のレース（5頭以上）のうちの割合。推奨買目が1点も無いレースは入らない。1日の儲けは、その年の開催日1日あたりの（払戻 − 投資）。")
        name = REPORT_NAME if self.protocol == LEAVE_ONE_OUT else f"{REPORT_NAME}-{self.protocol}"
        return CaseReport(out_dir).write(name, f"地方の期待度: {name}", intro, tables)

    def _now_grades(self, scores: pd.DataFrame) -> pd.DataFrame:
        """前の期待度（◎ の1着の確率 ＋ 3 ×（単勝の期待値 − 1））で分ける。◎ の無いレースは落とす。"""
        tops = self.tops[["race_id", "win_probability", "win_value"]].assign(race_id=self.tops["race_id"].astype("int64"))
        joined = scores.drop(columns=[GRADE]).merge(tops, on="race_id", how="inner")
        scale = LocalTopScoreScale()
        grades = [scale.grade(_number(p), _number(v)) for p, v in zip(joined["win_probability"], joined["win_value"], strict=True)]
        return joined.assign(**{GRADE: grades}).dropna(subset=[GRADE])

    @staticmethod
    def _band_table(scores: pd.DataFrame, column: str, years: list[int], days: pd.Series, counts: pd.Series, number: int) -> Table:
        edges = np.unique(np.quantile(scores[column], np.linspace(0, 1, BANDS + 1)))
        labels = [f"{low:.2f}〜{high:.2f}" for low, high in zip(edges[:-1], edges[1:])]
        banded = scores.assign(band=pd.cut(scores[column], edges, labels=labels, include_lowest=True))
        rows = []
        for label in labels:
            rows += _rows(label, banded[banded["band"] == label], years, days, counts)
        return Table.from_records(rows, _COLUMNS, title=f"{number}. {_SCORES[column]}の帯ごとの成績（全部の年をまとめた {BANDS} 分位）")


def _grade_rows(scores: pd.DataFrame, years: list[int], days: pd.Series, counts: pd.Series) -> list[dict]:
    rows = []
    for grade in GRADES:
        rows += _rows(f"期待度 {grade}", scores[scores[GRADE] == grade], years, days, counts)
    return rows + _rows("全部", scores, years, days, counts)


def _order_rows(name: str, scores: pd.DataFrame, years: list[int], every_year: bool = False) -> list[dict]:
    """年ごとに、等級の順に上がったか。線を決めた最初の年は数えない（線を固定した本番の線は ``every_year`` で全部の年を数える）。"""
    rows = []
    for year in (years if every_year else years[1:]):
        part = scores[scores["year"] == year]
        paybacks, hits, profits, cells = [], [], [], {}
        for grade in GRADES:
            g = part[part[GRADE] == grade]
            payback = float(g["returned"].sum()) / float(g["stake"].sum()) if len(g) else float("nan")
            hit = float((g["returned"] > 0).mean()) if len(g) else float("nan")
            paybacks.append(payback)
            hits.append(hit)
            profits.append(float(g["returned"].sum() - g["stake"].sum()))
            cells[grade] = f"{payback:.1%}（{hit:.0%}）"
        rows.append({"分け方": name, "年": f"{year}年", **cells, "回収率が順に上がった": _mark(_rising(paybacks)), "的中率が順に上がった": _mark(_rising(hits)),
                     "1日の儲けが順に上がった": _mark(_rising(profits))})
    return rows


def _rising(values: list[float]) -> bool:
    """S・A・B・C の順の値が、C → S に向かって真に上がるか。"""
    return all(high > low for high, low in zip(values[:-1], values[1:]))


def _mark(flag: bool) -> str:
    return "○" if flag else "×"


def _number(value: object) -> float | None:
    return None if value is None or pd.isna(value) else float(value)


def _rows(label: str, part: pd.DataFrame, years: list[int], days: pd.Series, counts: pd.Series) -> list[dict]:
    rows = []
    for year in years:
        p = part[part["year"] == year]
        if p.empty:
            rows.append({"区分": label, "年": f"{year}年", "レース": 0})
            continue
        stake, returned = float(p["stake"].sum()), float(p["returned"].sum())
        rows.append({"区分": label, "年": f"{year}年", "レース": f"{len(p):,}", "レースの割合": f"{len(p) / counts[year]:.0%}",
                     "1レースの点数": f"{p['points'].mean():.1f}", "見込みの平均": f"{p[EXPECTED].mean():.2f}",
                     "回収率": f"{returned / stake:.1%}", "最高の1点を除く回収率": f"{(returned - p['best'].max()) / stake:.1%}",
                     "的中率": f"{(p['returned'] > 0).mean():.1%}", "1日の儲け": f"{(returned - stake) / days[year]:+,.0f}円"})
    return rows
