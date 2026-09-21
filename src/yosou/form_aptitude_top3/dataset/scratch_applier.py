"""速報の出走取消・競走除外を、出走の行に反映する。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


class ScratchApplier:
    """速報で出走しなくなった馬を、「出走しなかった」（``ran`` が False）にする。"""

    def apply(self, entries: pd.DataFrame, scratched_horse_numbers: Sequence[int]) -> pd.DataFrame:
        is_scratched = entries["horse_no"].isin(list(scratched_horse_numbers))
        has_run = entries["ran"].eq(True)
        return entries.assign(ran=has_run & ~is_scratched)
