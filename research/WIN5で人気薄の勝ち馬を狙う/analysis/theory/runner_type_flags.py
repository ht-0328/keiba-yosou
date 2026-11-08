"""出走の表に、馬の側の型の真偽の列と、当てはまった型を並べた文字の列を足す。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .runner_type_catalog import NO_TYPE, RUNNER_TYPES

#: 当てはまった型を「・」でつないだ列の名前。
TYPE_LABELS = "types"


@dataclass(frozen=True)
class RunnerTypeFlags:
    """型ごとに1列（列名は型の名前）と、どれにも当てはまらない ``NO_TYPE`` の列、``TYPE_LABELS`` の列を足す。"""

    def add(self, runners: pd.DataFrame) -> pd.DataFrame:
        flags = pd.DataFrame({rule.name: rule.flags(runners) for rule in RUNNER_TYPES}, index=runners.index)
        flags[NO_TYPE] = ~flags.any(axis=1)
        labels = flags.apply(lambda row: "・".join(name.split(" ")[0] for name, hit in row.items() if hit), axis=1)
        return pd.concat([runners, flags], axis=1).assign(**{TYPE_LABELS: labels})
