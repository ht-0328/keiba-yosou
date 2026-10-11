"""元の学習データの表に、展開スコア（まとまり S）の 5列を足す。"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from yosou.development_score import DEVELOPMENT_SCORE_FEATURES, DEVELOPMENT_SCORE_NAMES, YearlyScorer
from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData
from yosou.shared.feature import FeatureCatalog
from yosou.shared.feature.pace_forecast import pace_forecast_columns as pace

#: 元の表の P の列 → 展開の予想の元の予測の列（展開スコアに要る6つ）。
_SOURCE_OF: dict[str, str] = {
    pace.LEADER_P: pace.LEADER, pace.FRONT_P: pace.FRONT, pace.MIDDLE_P: pace.MIDDLE, pace.BACK_P: pace.BACK,
    pace.SLOW_P: pace.SLOW, pace.HIGH_P: pace.HIGH,
}
_KEY: list[str] = ["race_id", "horse_id"]


class ScoreTableBuilder:
    """``base`` の行（目的変数・評価用の列・基準もそのまま）に、同じ出走の展開スコアの 5列を足す。

    展開スコアは、①②③ の予測（その年より前だけで学習した展開のモデルの予測）と、``prepared``（``AdvantageRuns`` の表。
    表 G の材料）から、予想のパッケージの ``YearlyScorer`` で付ける（表 G はレースの年ごとに、その年の1月1日より前のレースだけで作る）。
    予測は、元の表に P の列があればそこから取り、無ければ ``forecasts``（展開の年ごとの確かめの元の予測の表。``PaceForecastHistory``）から
    出走ごとに引く。予測の無い行（展開の予測が始まる前の年）は欠損値。特徴量の一覧も 5個広げる。元の表にもう同じ列があれば置き換える。
    """

    def build(self, base: TrainingData, prepared: pd.DataFrame, forecasts: pd.DataFrame | None = None) -> TrainingData:
        keys = pd.DataFrame({"race_id": base.ids[RACE_ID].astype(str).to_numpy(), "horse_id": base.ids[HORSE_ID].astype(str).to_numpy()},
                            index=base.features.index)
        if forecasts is None:
            source = keys.assign(**{source: base.features[column].astype("float64").to_numpy() for column, source in _SOURCE_OF.items()})
        else:
            columns = [*_KEY, *_SOURCE_OF.values()]
            table = forecasts[columns].astype({key: str for key in _KEY}).drop_duplicates(_KEY)
            source = keys.merge(table, on=_KEY, how="left").set_axis(base.features.index)
        scored = YearlyScorer().of(source, prepared)
        added = scored[list(DEVELOPMENT_SCORE_NAMES)].astype("float64")
        features = pd.concat([base.features.drop(columns=list(DEVELOPMENT_SCORE_NAMES), errors="ignore"), added], axis=1)
        kept = tuple(feature for feature in base.catalog.features if feature.name not in DEVELOPMENT_SCORE_NAMES)
        return replace(base, features=features, catalog=FeatureCatalog(kept + DEVELOPMENT_SCORE_FEATURES))
