"""追加の元データを読んで、出走の行に列を足す。"""

import duckdb
import pandas as pd

from .pool_probability_source import KEY, PoolProbabilitySource

#: 使える追加の元データ（名前 → 読むクラス）。新しい元データは、クラスを作ってここに1行足す。
SOURCES = {PoolProbabilitySource.name: PoolProbabilitySource()}


class ExtraDataLoader:
    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def attach(self, entries: pd.DataFrame, scope_relation: str, names: tuple[str, ...]) -> pd.DataFrame:
        """``names`` の元データを読み、レースID・馬番で ``entries`` に列を足す。行の並びと index は変えない。

        ``scope_relation`` は ``race_id`` の列を持つ関係（学習なら対象の期間、予想なら1レース）。
        """
        for name in names:
            if name not in SOURCES:
                raise ValueError(f"未登録の追加の元データです: {name}")
            data = SOURCES[name].read(self._con, scope_relation)
            entries = self._joined(entries, data, SOURCES[name].columns)
        return entries

    def _joined(self, entries: pd.DataFrame, data: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
        keys = pd.MultiIndex.from_arrays([
            entries["race_id"].astype(str), pd.to_numeric(entries["horse_no"], errors="coerce"),
        ])
        values = data.assign(
            race_id=data["race_id"].astype(str), horse_no=pd.to_numeric(data["horse_no"], errors="coerce"),
        ).set_index(KEY).reindex(columns=list(columns))
        aligned = values.reindex(keys)
        aligned.index = entries.index
        return entries.assign(**{column: aligned[column].astype("float64") for column in columns})


def race_relation(race_id: str) -> str:
    """予想する1レースだけの関係。"""
    if not race_id.isdigit():
        raise ValueError(f"レースIDは数字だけで指定してください: {race_id}")
    return f"(SELECT '{race_id}' AS race_id)"
