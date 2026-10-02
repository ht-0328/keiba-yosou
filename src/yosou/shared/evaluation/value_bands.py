"""複勝の期待値と、実際の回収率を、期待値の帯ごとに並べる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 期待値の帯の区切り（帯は「左以上、右より小さい」）。買うかどうかの線になる 1 の前後を細かく切る。
BANDS: tuple[float, ...] = (0.0, 0.6, 0.8, 0.9, 1.0, 1.1, 1.2, 1.4, np.inf)
#: 表の列の名前。
BAND, COUNT, VALUE = "期待値の帯", "点数", "期待値の平均"
PREDICTED_HIT, ACTUAL_HIT, PAYBACK = "予想の的中率", "実際の的中率", "回収率"
#: 複勝の払戻は 100円あたりの円。
_STAKE = 100.0


class ValueBands:
    """複勝の期待値（1 で元返し）が、実際の回収率と合っているかを、期待値の帯ごとに測る（穴馬の設計書 16 の 5）。

    例: 期待値 1.1〜1.2 の帯の複勝を 500点買って、払戻の合計が 50,000円なら、回収率は 1.00 で、期待値の平均 1.15 より低い。
    「予想の的中率」（複勝的中の確率の平均）と「実際の的中率」を並べると、ずれが確率から来ているのか、
    見込みの倍率から来ているのかが分かる。

    ``value`` は複勝の期待値、``hit_probability`` は複勝的中の確率、``payout`` は複勝の払戻（100円あたり。外れは 0 か欠損値）。
    期待値の無い馬（複勝オッズの無い馬）は数えない。
    """

    def table(self, value: pd.Series, hit_probability: pd.Series, payout: pd.Series) -> pd.DataFrame:
        """帯ごとの行（``BAND``・``COUNT``・``VALUE``・``PREDICTED_HIT``・``ACTUAL_HIT``・``PAYBACK``）。点の無い帯は出さない。"""
        bets = self._bets(value, hit_probability, payout)
        band = pd.cut(bets[VALUE], BANDS, right=False)
        rows = [self._summary(group).assign(**{BAND: self._band_text(interval)})
                for interval, group in bets.groupby(band, observed=True)]
        columns = [BAND, COUNT, VALUE, PREDICTED_HIT, ACTUAL_HIT, PAYBACK]
        return pd.concat(rows, ignore_index=True)[columns] if rows else pd.DataFrame(columns=columns)

    def at_least(self, value: pd.Series, hit_probability: pd.Series, payout: pd.Series,
                 threshold: float) -> dict[str, float]:
        """期待値が ``threshold`` 以上の複勝を全部 100円ずつ買ったときの、点数・期待値の平均・的中率・回収率。"""
        bets = self._bets(value, hit_probability, payout)
        return self._summary(bets[bets[VALUE] >= threshold]).iloc[0].to_dict()

    def _bets(self, value: pd.Series, hit_probability: pd.Series, payout: pd.Series) -> pd.DataFrame:
        bets = pd.DataFrame({
            VALUE: value.to_numpy(dtype="float64"), PREDICTED_HIT: hit_probability.to_numpy(dtype="float64"),
            PAYBACK: pd.to_numeric(payout, errors="coerce").fillna(0.0).to_numpy(dtype="float64"),
        })
        return bets[bets[VALUE].notna()]

    def _summary(self, bets: pd.DataFrame) -> pd.DataFrame:
        """点の集まり1つの、点数・期待値の平均・予想と実際の的中率・回収率（1行の表）。点が無ければ率は NaN。"""
        count = len(bets)
        paid = bets[PAYBACK]
        return pd.DataFrame([{
            COUNT: count, VALUE: bets[VALUE].mean(), PREDICTED_HIT: bets[PREDICTED_HIT].mean(),
            ACTUAL_HIT: (paid > 0).mean() if count else np.nan,
            PAYBACK: paid.sum() / (_STAKE * count) if count else np.nan,
        }])

    def _band_text(self, interval: pd.Interval) -> str:
        if np.isinf(interval.right):
            return f"{interval.left:g}以上"
        return f"{interval.left:g}〜{interval.right:g}"
