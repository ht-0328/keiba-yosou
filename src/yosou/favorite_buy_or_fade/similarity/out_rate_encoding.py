"""カテゴリの列を、その値の馬券外率に直す。"""

from __future__ import annotations

import pandas as pd

#: 値ごとの馬券外率を、単位全体の馬券外率に寄せる強さ。この頭数ぶんの「全体の率」を混ぜるので、頭数の少ない値が極端な率にならない。
_SMOOTHING_ROWS = 20
#: 標準偏差がこれより小さい列（どの値も同じ率）は、距離に効かないので使わない。
_MIN_SPREAD = 1e-9
#: 直した列の名前に付ける印。
_SUFFIX = "（馬券外率）"


class OutRateEncoding:
    """カテゴリの列を、その値の学習データでの馬券外率（数の列）に直し、標準化する（設計書 12 の 1。方針の ``categorical = "馬券外率"``）。

    値ごとの率は、頭数の少ない値が極端にならないよう、単位全体の馬券外率に 20頭ぶん寄せる。
    学習データに無い値と欠損値は、単位全体の馬券外率（標準化すると 0 の近く）にする。どの値も同じ率になった列は使わない。
    率を出すのに「馬券外か」の列を使うので、学習データだけで ``fit`` する（設計書 11 の 8）。
    """

    def __init__(self) -> None:
        self._rates: dict[str, pd.Series] = {}
        self._prior = 0.0
        self._means = pd.Series(dtype=float)
        self._spreads = pd.Series(dtype=float)

    def fit(self, values: pd.DataFrame, is_out: pd.Series | None) -> OutRateEncoding:
        """``values`` はカテゴリの列だけの表、``is_out`` は行ごとに馬券外か。"""
        if is_out is None:
            raise ValueError("カテゴリを馬券外率に直すには、行ごとに馬券外かの列が要ります")
        out = is_out.astype(float)
        self._prior = float(out.mean())
        rates = {column: self._rates_of(_texts(values[column]), out) for column in values.columns}
        encoded = pd.DataFrame({column: _texts(values[column]).map(rate).fillna(self._prior).astype(float)
                                for column, rate in rates.items()}, index=values.index)
        spreads = encoded.std(ddof=0)
        kept = [column for column in encoded.columns if spreads[column] > _MIN_SPREAD]
        self._rates = {column: rates[column] for column in kept}
        self._means, self._spreads = encoded[kept].mean(), spreads[kept]
        return self

    @property
    def column_names(self) -> list[str]:
        """「馬場状態（馬券外率）」の形。"""
        return [f"{column}{_SUFFIX}" for column in self._rates]

    @property
    def sources(self) -> list[str]:
        """列ごとの、元の特徴量の名前（``column_names`` と同じ並び）。"""
        return list(self._rates)

    def transform(self, values: pd.DataFrame) -> pd.DataFrame:
        encoded = pd.DataFrame({column: _texts(values[column]).map(rate).fillna(self._prior).astype(float)
                                for column, rate in self._rates.items()}, index=values.index)
        scaled = (encoded - self._means) / self._spreads
        return scaled.add_suffix(_SUFFIX)

    def _rates_of(self, texts: pd.Series, out: pd.Series) -> pd.Series:
        """値 → 寄せた馬券外率。欠損値の行は数えない。"""
        grouped = out.groupby(texts).agg(["sum", "count"])
        return (grouped["sum"] + _SMOOTHING_ROWS * self._prior) / (grouped["count"] + _SMOOTHING_ROWS)


def _texts(values: pd.Series) -> pd.Series:
    """値を文字にする（欠損値はそのまま）。"""
    return values.astype(object).where(values.notna()).map(str, na_action="ignore")
