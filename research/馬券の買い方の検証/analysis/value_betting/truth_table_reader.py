"""学習データの表から、答えと評価用の列を読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.shared.dataset import FIELD_SIZE, HORSE_ID, RACE_DATE, RACE_ID, TOP3
from yosou.shared.dataset.column_names import FINISH, PLACE_ODDS_HIGH, PLACE_ODDS_LOW, PLACE_PAYOUT, POPULARITY, WIN_ODDS
from yosou.shared.feature.odds import TOP2_RATE, TOP3_RATE

#: 表のフォルダから読む部分と、そこから取る列（学習データの表の列名のまま）。
_PARTS: dict[str, tuple[str, ...]] = {
    "ids": (RACE_ID, RACE_DATE, HORSE_ID),
    "evaluation": (FINISH, WIN_ODDS, POPULARITY, PLACE_PAYOUT, PLACE_ODDS_LOW, PLACE_ODDS_HIGH, FIELD_SIZE, TOP2_RATE, TOP3_RATE),
    "targets": (TOP3,),
}
_KEY = [RACE_ID, HORSE_ID]


class TruthTableReader:
    """学習データの表のフォルダ（``ids.pkl``・``evaluation.pkl``・``targets.pkl``。研究「既存モデルの改善」の ``TableStore`` の形）から、
    1行 = 1出走の答え（3着以内）・確定着順・人気・単勝オッズ・複勝オッズ（最低・最高）・複勝の払戻・頭数・オッズから見た2着以内率と3着以内率を読む。

    列の名前は学習データの表のまま（日本語）。同じ出走が2行あれば最初の1行にする。特徴量の表は読まない（大きいので）。
    """

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)

    def read(self) -> pd.DataFrame:
        parts = [pd.read_pickle(self._folder / f"{part}.pkl")[list(columns)].reset_index(drop=True)
                 for part, columns in _PARTS.items()]
        truth = pd.concat(parts, axis=1).drop_duplicates(_KEY)
        return truth.assign(**{RACE_ID: truth[RACE_ID].astype(str), HORSE_ID: truth[HORSE_ID].astype(str)})
