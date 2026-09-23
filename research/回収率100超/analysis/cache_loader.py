"""中間データ（parquet）を1つの表にまとめて読む。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .repository import POOL_MARGINALS, POSITION_MARGINALS, VOTE_SHARES

#: 複勝の対象着順が2着までになる頭数の上限（JRA の決まり。8頭以上は3着まで）。
_TWO_PLACES_MAX_FIELD = 7
#: 出走したことにならない異常区分（出走取消・発走除外・競走除外）。
_NOT_RAN = ("1", "2", "3")
#: 障害レースのトラックコードの範囲。
_JUMP_TRACKS = ("51", "59")


class CacheLoader:
    """``extract.py`` が作った parquet を1つの表にまとめ、結果の列を付ける。

    1行 = 1頭の出走。平地で実際に出走し、単勝オッズが付いている馬だけを残す。
    """

    def __init__(self, cache: Path) -> None:
        self._cache = cache

    def read(self) -> pd.DataFrame:
        """学習と検証に使う表。"""
        table = self._read_runners()
        for marginal in POOL_MARGINALS:
            table = self._merge(table, f"pool_{marginal.key}.parquet")
        for key in POSITION_MARGINALS:
            table = self._merge(table, f"pool_{key}.parquet")
        for _, key in VOTE_SHARES.values():
            table = self._merge(table, f"pool_{key}.parquet")
        table = self._merge(table, "mining.parquet")
        table = self._merge(table, "horse_facts.parquet",
                            drop=("race_date", "race_no", "field_size"))
        table = table.merge(pd.read_parquet(self._cache / "pool_size.parquet"), on="rid", how="left")
        return self._add_mining_columns(table)

    def _read_runners(self) -> pd.DataFrame:
        """出走の表に、結果と「単勝から見た勝率」を付ける。"""
        table = pd.read_parquet(self._cache / "runners.parquet")
        table = table[~table["track_code"].between(*_JUMP_TRACKS)]
        table = table[~table["abnormal"].isin(_NOT_RAN)]
        table = table[table["win_odds"].notna() & (table["win_odds"] > 0)]
        table["field"] = table.groupby("rid")["horse_no"].transform("size")
        table = table[table["field"] >= 5].sort_values(["rid", "horse_no"]).reset_index(drop=True)

        table["year"] = table["race_date"].dt.year
        table["day"] = table["race_date"].dt.date
        table["won"] = (table["finish"] == 1).astype(int)
        table["place_places"] = np.where(table["field"] <= _TWO_PLACES_MAX_FIELD, 2, 3)
        table["placed"] = ((table["finish"] >= 1)
                           & (table["finish"] <= table["place_places"])).astype(int)
        inverse = 1.0 / table["win_odds"]
        table["単勝から見た勝率"] = inverse / inverse.groupby(table["rid"]).transform("sum")
        return table

    def _merge(self, table: pd.DataFrame, name: str,
               drop: tuple[str, ...] = ()) -> pd.DataFrame:
        other = pd.read_parquet(self._cache / name).drop(columns=list(drop), errors="ignore")
        return table.merge(other, on=["rid", "horse_no"], how="left")

    def _add_mining_columns(self, table: pd.DataFrame) -> pd.DataFrame:
        """マイニング予想を、レース内で比べられる形にする。

        予想走破タイムは距離が違えば比べられないので、レース内の順位と偏差にする。
        """
        race = table["rid"]
        table["予想タイムの順位"] = table["predicted_time"].groupby(race).rank()
        table["予想タイムの偏差"] = self._zscore(table["predicted_time"], race)
        table["対戦スコアの順位"] = (-table["mining_score"]).groupby(race).rank()
        table["対戦スコアの偏差"] = self._zscore(table["mining_score"], race)
        table["予想の信頼度＋"] = table["error_plus"] / 100.0
        table["予想の信頼度−"] = table["error_minus"] / 100.0
        return table

    def _zscore(self, values: pd.Series, race: pd.Series) -> pd.Series:
        grouped = values.groupby(race)
        return (values - grouped.transform("mean")) / grouped.transform("std").replace(0, np.nan)
