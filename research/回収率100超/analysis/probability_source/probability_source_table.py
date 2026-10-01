"""元の確率と新しい確率を、同じ馬で突き合わせた表。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..ticket import RacePlaceProbability
from .race_day_model_predictions import MODEL_PROBABILITY

#: 出どころの列の名前。
ORIGINAL = "元の確率（全券種のオッズから）"
MODEL = "新しい確率（当日のモデル）"
AVERAGE = "2つの平均"
SOURCES: tuple[str, ...] = (ORIGINAL, MODEL, AVERAGE)
#: 元の予測から引き継ぐ列（``backtest.py`` の ``PREDICTION_COLUMNS`` のうち、確率と期待値以外）。
_ORIGINAL_COLUMNS = ("rid", "horse_no", "year", "day", "win_odds", "placed", "place_payout", "想定払戻倍率")
_ORIGINAL_PROBABILITY = "3着以内の確率"
#: 複勝の対象着順が2着までになる頭数の上限（``CacheLoader`` と同じ）。
_TWO_PLACES_MAX_FIELD = 7


class ProbabilitySourceTable:
    """元の予測（``backtest.py`` が残した ``place_predictions.parquet``）と新しい確率を、レースと馬番で突き合わせる。

    新しい確率は、元と同じ手順（docs/04-買い方.md の 1 の E）で、レース内で合計が複勝の対象着順の数（5〜7頭立ては 2、
    8頭以上は 3）になるようそろえ直してから使う。頭数は新しい確率の行（出走した馬）で数える。そろえ直しは元の予測の
    行に絞る前に行う（元の手順と同じ順）。2つの平均は、そろえ直した2つの確率の算術平均（合計はそのまま対象着順の数）。

    想定払戻倍率は元の予測のものをそのまま使う（評価する年より前の払戻から見積もった値で、確率の出どころによらない）。
    両方にある行だけを残すので、元の成績もこの表で出し直す（`検証の結果.md` とはわずかに違いうる）。
    """

    def __init__(self, normalizer: RacePlaceProbability | None = None) -> None:
        self._normalizer = normalizer or RacePlaceProbability()

    def build(self, original: pd.DataFrame, model: pd.DataFrame) -> pd.DataFrame:
        base = original[list(_ORIGINAL_COLUMNS) + [_ORIGINAL_PROBABILITY]].rename(columns={_ORIGINAL_PROBABILITY: ORIGINAL})
        base = base.assign(rid=base["rid"].astype(str), horse_no=base["horse_no"].astype(int))
        scaled = self._scaled_model(model)
        table = base.merge(scaled, on=["rid", "horse_no"], how="inner")
        table[AVERAGE] = (table[ORIGINAL] + table[MODEL]) / 2
        return table.sort_values(["rid", "horse_no"]).reset_index(drop=True)

    def _scaled_model(self, model: pd.DataFrame) -> pd.DataFrame:
        frame = model.assign(rid=model["rid"].astype(str), horse_no=model["horse_no"].astype(int))
        frame = frame.drop_duplicates(["rid", "horse_no"])
        field = frame.groupby("rid")["horse_no"].transform("size")
        places = pd.Series(np.where(field <= _TWO_PLACES_MAX_FIELD, 2, 3), index=frame.index)
        scaled = self._normalizer.normalize(frame[MODEL_PROBABILITY].astype(float), frame["rid"], places)
        return pd.DataFrame({"rid": frame["rid"], "horse_no": frame["horse_no"], MODEL: scaled})
