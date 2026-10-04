"""人気馬の「普段より危ない」の線を、検証期間で決める。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 線の候補（危険度 = 4着以下の確率 − オッズから見た4着以下の確率。0.01 = 1ポイント）。
CANDIDATES: tuple[float, ...] = tuple(round(value, 3) for value in np.arange(0.0, 0.205, 0.01))
#: 危険と判定する頭数の下限（これより少ない線は選ばない）。
_MIN_FLAGGED = 30
#: 線の点を偶然と区別できるとみなす大きさ（点 ÷ 物差しの値の標準偏差。片側 5% の目安）。これに届かない人気帯は線を決めない（``choose_for``）。
MIN_Z = 1.645
#: 線を「実際の4着以下率」そのもので選ぶ人気帯。ほかの人気帯は「市場の見立てよりどれだけ多く負けたか」で選ぶ（``choose_for``）。
RATE_MEASURED_BANDS: tuple[str, ...] = ("1番人気",)


class DangerThreshold:
    """人気帯ごとに、「危険度がこの値以上なら危険」の線を検証期間で決める（既存モデルの修正計画の 1「人気馬の4着以下」）。

    危険度は「予想の4着以下の確率 − オッズから見た4着以下の確率（基準）」。同じオッズの馬より、どれだけ負けやすいか。
    線は、危険とした馬の物差しの値が、同じ人気帯の全体をどれだけ上回るかを、頭数も考えて（差 × √頭数。偶然では出にくい差ほど大きい）
    いちばん大きくするものを選ぶ。危険とする馬が 30頭に満たない線は選ばない。テスト期間の結果は使わない。物差しは人気帯で違う（``choose_for``）。

    - 1番人気（``RATE_MEASURED_BANDS``）: 実際の4着以下率そのもの。人気帯の中でオッズの幅が狭いので、来ない馬をそのまま拾える。
      道具「印の成績」で、市場の見立てとの差で選ぶより全券種の回収率が良かった。
    - 2〜5番人気: 市場の見立てよりどれだけ多く負けたか（実際の4着以下 − オッズから見た4着以下の確率）。人気帯の中でオッズの幅が広く、
      危険度の高い馬ほどオッズから見た4着以下の確率が低い（人気帯の中では強いと見られている）ので、4着以下率そのものでは差が出ず、
      線が候補のいちばん下（0.00）に張り付いて、ほぼ全頭が危険になる。

    ``choose_for`` は、いちばん点の高い線でも、点が偶然と区別できる大きさ（``MIN_Z``）に届かなければ線を決めない（NaN）。
    半年の検証データで差がはっきりしない人気帯に、たまたま点の高かった低い線が選ばれて、ほぼ全頭が危険になるのを防ぐ。
    ``choose`` はこの確かめをしない（研究の結果を再現するために、前の選び方のまま残す）。
    """

    def choose_for(self, band: str, danger: pd.Series, lost: pd.Series, market: pd.Series) -> float:
        """人気帯の物差しで線を決める（1番人気は4着以下率そのもの、ほかは市場の見立てとの差）。点が偶然と区別できなければ NaN。"""
        measure = None if band in RATE_MEASURED_BANDS else market
        line = self.choose(danger, lost, measure)
        if np.isnan(line):
            return line
        surprise = self._surprise(lost, measure)
        spread = float(surprise.std())
        score = self._score(danger, surprise, line, float(surprise.mean()))
        return line if spread > 0 and score / spread >= MIN_Z else float("nan")

    def choose(self, danger: pd.Series, lost: pd.Series, market: pd.Series | None = None) -> float:
        """検証期間の危険度と実際の4着以下（1 か 0）から線を決める。``market``（オッズから見た4着以下の確率）を渡すと、
        市場の見立てとの差で比べる。省くと4着以下率そのもので比べる。どの線も条件に合わなければ NaN。
        """
        surprise = self._surprise(lost, market)
        overall = float(surprise.mean())
        scores = {threshold: self._score(danger, surprise, threshold, overall) for threshold in CANDIDATES}
        valid = {threshold: score for threshold, score in scores.items() if not np.isnan(score)}
        if not valid:
            return float("nan")
        return max(valid, key=valid.get)

    def _surprise(self, lost: pd.Series, market: pd.Series | None) -> pd.Series:
        """物差しの値（実際の4着以下。``market`` を渡すと、そこからオッズから見た4着以下の確率を引いたもの）。"""
        return lost.astype(float) - (0.0 if market is None else market.astype(float))

    def _score(self, danger: pd.Series, surprise: pd.Series, threshold: float, overall: float) -> float:
        flagged = surprise[danger >= threshold]
        if len(flagged) < _MIN_FLAGGED:
            return float("nan")
        return (float(flagged.mean()) - overall) * np.sqrt(len(flagged))
