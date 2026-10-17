"""作り方ごとの予測から、決めた範囲のレースの人気馬のテスト期間の行を取り出し、答えと市場の見立てを付ける。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from yosou.favorites_out_of_top3.dataset import FAVORITE_BAND
from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData
from yosou.shared.feature.odds import TOP3_RATE

from 既存モデルの改善.analysis.walk_forward import PART, PART_TEST, PREDICTION_COLUMN, WINDOW

from .race_scope import RaceScope
from .sign_columns import SIGN_COUNT

#: 行の鍵と、付ける列の名前。
_KEY = [RACE_ID, HORSE_ID]
LOST, MARKET_OUT, POPULARITY, BAND, WIN_PAYOUT, PLACE_PAYOUT = "lost", "market_out", "popularity", "band", "win_payout", "place_payout"


class ScopeTestRows:
    """作り方の名前 → 予測の表（``walk_forward`` の出力）から、1行 = ``scope`` のレースの人気馬1頭 × 作り方 の長い表を作る。

    列は 鍵・区切り（WINDOW）・作り方（``variant``）・4着以下の確率（``probability``）・4着以下か（``LOST``）・
    市場から見た4着以下の確率（``MARKET_OUT`` = 1 − オッズから見た3着以内率）・人気・人気帯・単勝と複勝の払戻・サインの数。
    どの作り方にもある行（同じ馬の集まり）だけを残すので、作り方どうしを同じ馬で比べられる。
    """

    def __init__(self, scope: RaceScope) -> None:
        self._scope = scope

    def build(self, data: TrainingData, predictions: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
        facts = self._facts(data)
        parts = []
        for key, frame in predictions.items():
            tested = frame[frame[PART].eq(PART_TEST)][[*_KEY, WINDOW, PREDICTION_COLUMN]]
            tested = tested.astype({RACE_ID: str, HORSE_ID: str}).rename(columns={PREDICTION_COLUMN: "probability"})
            parts.append(tested.merge(facts, on=_KEY, how="inner").assign(variant=key))
        rows = pd.concat(parts, ignore_index=True)
        shared = rows.groupby(_KEY)["variant"].nunique().eq(len(predictions))
        kept = shared[shared].index
        return rows.set_index(_KEY).loc[lambda frame: frame.index.isin(kept)].reset_index()

    def _facts(self, data: TrainingData) -> pd.DataFrame:
        inside = self._scope.rows(data)
        evaluation = data.evaluation[inside]
        return pd.DataFrame({
            RACE_ID: data.ids.loc[inside, RACE_ID].astype(str), HORSE_ID: data.ids.loc[inside, HORSE_ID].astype(str),
            LOST: data.label[inside].astype(int), MARKET_OUT: 1 - evaluation[TOP3_RATE],
            POPULARITY: evaluation["確定の単勝人気"], BAND: evaluation[FAVORITE_BAND],
            WIN_PAYOUT: evaluation["単勝の払戻"], PLACE_PAYOUT: evaluation["複勝の払戻"],
            SIGN_COUNT: data.features.loc[inside, SIGN_COUNT],
        })
