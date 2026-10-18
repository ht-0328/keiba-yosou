"""組の確率を作るのに使う、馬ごとのモデルの見立て（1着の確率と、市場との比）。"""

from __future__ import annotations

import pandas as pd

#: 出す列。``win_share`` はレースで合計 1 にそろえた1着の確率（Harville の式に使う）、``win_ratio``・``top3_ratio`` は「モデル ÷ 市場」の比。
WIN_SHARE, WIN_RATIO, TOP3_RATIO = "win_share", "win_ratio", "top3_ratio"
#: 比の上限と下限。確率の小さい馬で比が極端になり、組の確率を振り回すのを防ぐ（研究「複勝以外の回収率100超」の上げ下げと同じ）。
RATIO_BOUNDS = (0.2, 5.0)
#: 1着の確率の下限（0 の馬があっても Harville の式の割り算が壊れないように）。
MIN_WIN = 1e-6


class HorseStrength:
    """1頭1行の表（列 ``race_id``・``horse_no``・``probability``（3着以内の確率）・``win_probability``（1着の確率）・
    ``market_top3``・``market_win``（オッズから見た3着以内率・勝率））から、組の確率のもとになる馬ごとの値を出す。

    - ``win_share``: 1着の確率をレースで合計 1 にそろえた値。例: 0.3・0.2・0.1 の3頭なら 0.5・0.33・0.17。
    - ``win_ratio``: 1着の確率 ÷ オッズから見た勝率（0.2〜5 に収める）。
    - ``top3_ratio``: 3着以内の確率 ÷ オッズから見た3着以内率（0.2〜5 に収める）。
    市場の見立てが無い（0 か欠損）馬の比は欠損値。戻り値の列は ``race_id``・``horse_no`` と上の3つ。
    """

    def of(self, horses: pd.DataFrame) -> pd.DataFrame:
        win = pd.to_numeric(horses["win_probability"], errors="coerce").clip(lower=MIN_WIN)
        share = win / win.groupby(horses["race_id"]).transform("sum")
        return pd.DataFrame({
            "race_id": horses["race_id"].astype(str),
            "horse_no": pd.to_numeric(horses["horse_no"], errors="coerce").astype(int),
            WIN_SHARE: share,
            WIN_RATIO: self._ratio(horses["win_probability"], horses["market_win"]),
            TOP3_RATIO: self._ratio(horses["probability"], horses["market_top3"]),
        }, index=horses.index)

    def _ratio(self, model: pd.Series, market: pd.Series) -> pd.Series:
        model = pd.to_numeric(model, errors="coerce")
        market = pd.to_numeric(market, errors="coerce")
        return (model / market.where(market > 0)).clip(*RATIO_BOUNDS)
