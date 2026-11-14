"""等級の表を重賞だけに絞り、セルを ◎ランクだけにする。"""

from __future__ import annotations

import pandas as pd

#: セル（◎ランク）の並び。
RANKS: tuple[str, ...] = ("S", "A", "B", "C")


class GradedCells:
    """研究「全レース全券種の買い方」の等級の表（1行 = 1レース。列 race_id・race_date・rank・cell …）を、重賞の一覧（列 race_id）にあるレースだけに絞り、
    セル（``cell``）を ◎ランク（S・A・B・C）に置き換える（docs/01 の 3）。◎ランクの無いレース（◎ の期待値が無い）は落とす。
    ``full`` が真なら（2回目。docs/03 の 2）、セルは等級の表のまま（◎ランク × 配当率の等級、◎ が 2倍以下なら 2倍以下）にする。"""

    def build(self, grades: pd.DataFrame, graded: pd.DataFrame, full: bool = False) -> pd.DataFrame:
        rids = set(graded["race_id"].astype(str))
        table = grades.assign(race_id=lambda frame: frame["race_id"].astype(str))
        table = table[table["race_id"].isin(rids) & table["rank"].isin(RANKS)].copy()
        if not full:
            table["cell"] = table["rank"]
        return table.reset_index(drop=True)
