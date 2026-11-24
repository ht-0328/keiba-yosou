"""年ごとの予測（確かめ用。年ごとに学んで次の年を予測したもの）のファイルを読み書きする。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.shared.betting import TicketType

#: 書いている途中のファイルの名前に足す拡張子。
_PARTIAL_SUFFIX = ".partial"


class PredictionStore:
    """``walk`` の出力（学習に使っていない年の、対象の組の全部の予測）を ``<folder>/<券種の英名>_<年>.parquet`` に置く。

    1行 = 1つの組。列は ``race_id``・``race_date``・``ticket_type``・``combo``・``h1``…・``odds``・``payout``（100円あたり。外れは 0）・
    ``hit``・``probability``（LightGBM と CatBoost の平均）・``probability_lightgbm``・``probability_catboost``・
    ``market_probability``（その券種の市場の確率 q）。買い目の成績を数える道具は、ここから読む。
    """

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)

    def path(self, ticket_type: TicketType, year: int) -> Path:
        return self._folder / f"{ticket_type.key}_{year}.parquet"

    def years(self, ticket_type: TicketType) -> list[int]:
        """その券種の予測のある年（古い順）。"""
        return sorted(int(path.stem.rsplit("_", 1)[1]) for path in self._folder.glob(f"{ticket_type.key}_*.parquet"))

    def save(self, ticket_type: TicketType, year: int, predictions: pd.DataFrame) -> Path:
        """その券種・年の予測を書き、書いたファイルを返す。前のものがあれば置き換える。

        途中は ``<名前>.partial`` に書き、書き終えてから本来の名前にする（途中で止まったファイルを、済んだものと見分けるため）。
        """
        path = self.path(ticket_type, year)
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + _PARTIAL_SUFFIX)
        predictions.to_parquet(partial, index=False, compression="zstd")
        partial.replace(path)
        return path

    def load(self, ticket_type: TicketType) -> pd.DataFrame:
        """その券種の予測を、ある年ぶん全部つないで返す（古い順）。1つも無ければ ``FileNotFoundError``。"""
        years = self.years(ticket_type)
        if not years:
            raise FileNotFoundError(f"{ticket_type.label}の予測がありません: {self._folder}（先に walk で作ってください）")
        return pd.concat([pd.read_parquet(self.path(ticket_type, year)) for year in years], ignore_index=True)
