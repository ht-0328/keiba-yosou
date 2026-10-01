"""W. オッズ（着順の予想の比べるためだけ。2個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset.column_names import POPULARITY
from yosou.shared.feature.odds import WIN_RATE

#: 特徴量の名前（設計書 16 の 3 の「オッズを着順の段にだけ入れたモデル」）。
ODDS_WIN_RATE = "単勝オッズから見た勝率"
ODDS_POPULARITY = "単勝人気"


class OddsComparisonFeatures:
    """W. 学習データの評価用の列（確定の単勝オッズから見た勝率と、確定の単勝人気）を、特徴量の列にする。

    この設計はオッズを特徴量に使わない（設計書 15 の 16）。年ごとの確かめで「オッズを着順の段にだけ入れたら、当たりと
    回収率がどう変わるか」を別に比べるためだけに使う（予測のコマンドでは使わない）。確定オッズなので、実際に買う時点の
    オッズより当たって見えるおそれがある（設計書 11 の決まり 13）。
    """

    def horse(self, evaluation: pd.DataFrame) -> pd.DataFrame:
        """1頭ごとの 2個。index は ``evaluation`` と同じ。"""
        return pd.DataFrame({
            ODDS_WIN_RATE: pd.to_numeric(evaluation[WIN_RATE], errors="coerce"),
            ODDS_POPULARITY: pd.to_numeric(evaluation[POPULARITY], errors="coerce"),
        }, index=evaluation.index)
