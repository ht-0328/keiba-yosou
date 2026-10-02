"""3つの1頭ごとの予測（7つの区切り）と答えを、1行 = 1頭 × 区切り × 期間 の表にする。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import FIELD_SIZE, HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, TOP3
from yosou.shared.dataset.column_names import FINISH, PLACE_ODDS_HIGH, PLACE_ODDS_LOW, PLACE_PAYOUT, POPULARITY, WIN_ODDS
from yosou.shared.feature.odds import TOP2_RATE, TOP3_RATE

from 既存モデルの改善.analysis.walk_forward import PART as PART_JA
from 既存モデルの改善.analysis.walk_forward import PREDICTION_COLUMN, SEGMENT, WINDOW as WINDOW_JA

from . import columns as c

#: 予測の表の鍵（区切り・期間・レースID・馬ID）。同じレースが隣り合う区切りの検証とテストの両方に出る。
_PREDICTION_KEY = [WINDOW_JA, PART_JA, RACE_ID, HORSE_ID]
#: 予測の表の列 → 材料表の列。
_ID_RENAME = {WINDOW_JA: c.WINDOW, PART_JA: c.PART, RACE_ID: c.RACE_ID, RACE_DATE: c.RACE_DATE, HORSE_ID: c.HORSE_ID,
              HORSE_NO: c.HORSE_NO}
_TRUTH_RENAME = {
    FINISH: c.FINISH, WIN_ODDS: c.WIN_ODDS, POPULARITY: c.POPULARITY, PLACE_PAYOUT: c.PLACE_PAYOUT,
    PLACE_ODDS_LOW: c.PLACE_ODDS, PLACE_ODDS_HIGH: c.PLACE_ODDS_HIGH, FIELD_SIZE: c.FIELD_SIZE,
    TOP2_RATE: c.MARKET_TOP2, TOP3_RATE: c.MARKET_TOP3, TOP3: c.TOP3,
}
#: 材料表の列の並び。
COLUMNS: tuple[str, ...] = (
    c.WINDOW, c.PART, c.RACE_ID, c.RACE_DATE, c.HORSE_ID, c.HORSE_NO, c.FINISH, c.TOP3, c.WIN_ODDS, c.POPULARITY,
    c.PLACE_PAYOUT, c.PLACE_ODDS, c.PLACE_ODDS_HIGH, c.FIELD_SIZE, c.MARKET_TOP2, c.MARKET_TOP3,
    c.FORM_PROB, c.DANGER_PROB, c.LONGSHOT_PROB, c.LONGSHOT_ZONE,
)


class RunnerTableBuilder:
    """近走と適性（全頭）の予測を土台に、答え（``TruthTableReader`` の表）、穴馬の予測（穴馬だけ）、人気馬の予測（人気馬だけ）を結合し、
    英語の列名の 1頭ごとの表（``COLUMNS``）にする。

    どの予測も研究「既存モデルの改善」の ``PredictionStore`` の形（区切り・期間・レースID・馬ID・確率・区分）。穴馬でない馬の
    ``longshot_prob``・``longshot_zone`` と、人気馬でない馬の ``danger_prob`` は欠損になる。答えの無い出走（表に無い）は落とす。
    """

    def build(self, form: pd.DataFrame, truth: pd.DataFrame, longshots: pd.DataFrame, favorites: pd.DataFrame) -> pd.DataFrame:
        base = form[_PREDICTION_KEY + [RACE_DATE, HORSE_NO, PREDICTION_COLUMN]].rename(columns={PREDICTION_COLUMN: c.FORM_PROB})
        base = base.assign(**{RACE_ID: base[RACE_ID].astype(str), HORSE_ID: base[HORSE_ID].astype(str)})
        merged = base.merge(truth.drop(columns=[RACE_DATE], errors="ignore"), on=[RACE_ID, HORSE_ID], how="inner")
        merged = merged.merge(self._longshots(longshots), on=_PREDICTION_KEY, how="left")
        merged = merged.merge(self._favorites(favorites), on=_PREDICTION_KEY, how="left")
        renamed = merged.rename(columns={**_ID_RENAME, **_TRUTH_RENAME})
        renamed[c.RACE_DATE] = pd.to_datetime(renamed[c.RACE_DATE])
        return renamed[list(COLUMNS)].sort_values([c.WINDOW, c.PART, c.RACE_ID, c.HORSE_NO]).reset_index(drop=True)

    def _longshots(self, longshots: pd.DataFrame) -> pd.DataFrame:
        frame = longshots[_PREDICTION_KEY + [PREDICTION_COLUMN, SEGMENT]].rename(
            columns={PREDICTION_COLUMN: c.LONGSHOT_PROB, SEGMENT: c.LONGSHOT_ZONE})
        return self._keyed(frame)

    def _favorites(self, favorites: pd.DataFrame) -> pd.DataFrame:
        frame = favorites[_PREDICTION_KEY + [PREDICTION_COLUMN]].rename(columns={PREDICTION_COLUMN: c.DANGER_PROB})
        return self._keyed(frame)

    def _keyed(self, frame: pd.DataFrame) -> pd.DataFrame:
        """鍵を文字列にそろえ、重なりを落とす。"""
        return frame.assign(**{RACE_ID: frame[RACE_ID].astype(str), HORSE_ID: frame[HORSE_ID].astype(str)}) \
            .drop_duplicates(_PREDICTION_KEY)
