"""研究「地方の万馬券」段5 の買い目（1行 = 1点）を1レースにまとめ、期待度の等級ごと・年ごとの推奨買目の成績の表を作る。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.shared.race_grade import GRADES

from 共通.perf import percent
from 共通.render import Table

from .grade_year_table import GRADE

#: 段5 の買い目の CSV（11頭以上・各年を残りの年で当てはめた未見の評価。``positions.py`` が書く）。
DEFAULT_TICKETS = Path(__file__).resolve().parents[3] / "reports" / "地方の万馬券" / "全券種の買い方の買い目.csv"
_RACE_ID, _PAYOUT, _YEAR = "race_id", "payout", "year"
_POINTS, _HIT = "points", "hit"
_STAKE = 100.0


class RecommendedTickets:
    """``path`` の買い目（列 race_id・payout ほか）を読み、レースごとの点数・払戻・的中（1点でも当たった）にまとめる。
    ``table(graded)`` は ◎ の行（列 ``race_id``・``year``・``grade``）と突き合わせ、年ごとに等級の行（買ったレース数・1レースの点数・回収率・的中レース率）を並べる。
    買い目の CSV が無ければ ``available()`` が偽（表は作らない）。CSV は 11頭以上のレースだけなので、突き合わせでレースは減る。"""

    def __init__(self, path: Path = DEFAULT_TICKETS) -> None:
        self._path = Path(path)

    def available(self) -> bool:
        return self._path.is_file()

    def per_race(self) -> pd.DataFrame:
        tickets = pd.read_csv(self._path, dtype={_RACE_ID: str})
        grouped = tickets.groupby(_RACE_ID)[_PAYOUT]
        return pd.DataFrame({_POINTS: grouped.size(), _PAYOUT: grouped.sum(), _HIT: grouped.apply(lambda s: bool((s > 0).any()))})

    def table(self, graded: pd.DataFrame, title: str, note: str = "") -> Table:
        joined = graded[[_RACE_ID, _YEAR, GRADE]].merge(self.per_race(), left_on=_RACE_ID, right_index=True, how="inner")
        rows = []
        for year, part in joined.groupby(_YEAR, sort=True):
            for grade in GRADES:
                rows.append([str(year), grade, *self._cells(part[part[GRADE] == grade])])
            rows.append([str(year), "全体", *self._cells(part)])
        return Table(["年", "期待度", "買ったレース数", "1レースの点数", "回収率", "的中レース率"], rows, title=title, note=note)

    @staticmethod
    def _cells(part: pd.DataFrame) -> list[str]:
        if part.empty:
            return ["0", "—", "—", "—"]
        points = float(part[_POINTS].sum())
        return [f"{len(part):,}", f"{points / len(part):.1f}", percent(float(part[_PAYOUT].sum()) / (_STAKE * points)), percent(float(part[_HIT].mean()))]
