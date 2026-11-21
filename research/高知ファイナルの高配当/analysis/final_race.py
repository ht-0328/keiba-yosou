"""ファイナルレースの見分け: その日の最大のレース番号で、競走名に「ファイナルレース」を含むレース。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 競走名に含まれる文字。
RACE_NAME_KEY = "ファイナルレース"
#: 出走の表に付ける列（ファイナルレースの出走なら真）。
FINAL = "final"


@dataclass(frozen=True)
class FinalRace:
    """``runs``（高知の出走の行。``race_date``・``race_no``・``race_name``）→ ファイナルレースの行が真の列。"""

    def mark(self, runs: pd.DataFrame) -> pd.Series:
        last_no = runs.groupby("race_date")["race_no"].transform("max")
        named = runs["race_name"].str.contains(RACE_NAME_KEY, na=False)
        return (named & (runs["race_no"] == last_no)).astype(bool)
