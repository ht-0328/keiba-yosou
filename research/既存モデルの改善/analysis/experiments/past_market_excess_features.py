"""近走で、オッズから期待された3着以内率をどれだけ上回ったか。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature.history import AsOfLookup, DatedRecords
from yosou.shared.feature.odds import TOP3_RATE, MarketPlaces

#: 特徴量の名前。
LAST = "前走の市場に対する成績"
MEAN = "近5走の市場に対する成績の平均"
MEAN_RANK = "近5走の市場に対する成績の平均のレース内順位"
NAMES: tuple[str, ...] = (LAST, MEAN, MEAN_RANK)
_RECENT = 5


class PastMarketExcessFeatures:
    """相手関係を考えた近走の評価（既存モデルの修正計画の 4「対戦相手の強さを考慮した評価」）。

    過去の1走ごとに「3着以内だったか（1 か 0）− そのレースのオッズから見た3着以内率」を出す。強い相手の中で
    人気薄なのに3着に入れば大きなプラス、弱い相手の中で1番人気なのに負ければ大きなマイナスになる。
    例: オッズから見た3着以内率 0.15 の走で3着なら +0.85、0.70 の走で5着なら −0.70。
    馬ごとに、開催日の前日までの前走と近5走の平均、近5走の平均のレース内順位を特徴量にする。
    """

    def build(self, history: pd.DataFrame) -> pd.DataFrame:
        """列は race_id・horse_id と ``NAMES``。"""
        expected = MarketPlaces().of(history[["race_id", "win_odds"]])[TOP3_RATE]
        placed = pd.to_numeric(history["finish"], errors="coerce").between(1, 3).astype(float)
        runs = history[["horse_id", "race_date", "race_id"]].assign(excess=(placed - expected).to_numpy())
        summary = self._recent(runs.dropna(subset=["excess"]))
        dated = DatedRecords(summary, key_column="horse_id", date_column="race_date")
        found = AsOfLookup(history[["race_id", "horse_id", "race_date"]], "horse_id").latest(dated, days_before=1)
        features = history[["race_id", "horse_id"]].assign(**{LAST: found[LAST].to_numpy(), MEAN: found[MEAN].to_numpy()})
        rank = features[MEAN].groupby(features["race_id"]).rank(ascending=False, method="min")
        return features.assign(**{MEAN_RANK: rank})

    def _recent(self, runs: pd.DataFrame) -> pd.DataFrame:
        ordered = runs.sort_values(["horse_id", "race_date", "race_id"], kind="stable").reset_index(drop=True)
        rolling = ordered.groupby("horse_id", sort=False)["excess"].rolling(_RECENT, min_periods=1).mean()
        return pd.DataFrame({
            "horse_id": ordered["horse_id"], "race_date": ordered["race_date"],
            LAST: ordered["excess"].to_numpy(), MEAN: rolling.reset_index(level=0, drop=True).to_numpy(),
        })
