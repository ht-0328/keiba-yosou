"""レースの場面を、表に出す帯に分ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 印の成績.race_scene_repository import COLUMNS as SCENE_COLUMNS
from 印の成績.win_pool_size_repository import WIN_POOL

#: 帯の軸（表に出す名前）と、帯の並び。
CLASS_AXIS, VENUE_AXIS, FIELD_AXIS, POOL_AXIS, SURFACE_AXIS = "クラス", "競馬場", "頭数", "単勝の売上", "芝ダ"
AXES: tuple[str, ...] = (CLASS_AXIS, VENUE_AXIS, FIELD_AXIS, POOL_AXIS, SURFACE_AXIS)
CLASS_BANDS: tuple[str, ...] = ("新馬・未勝利", "1勝クラス", "2勝・3勝クラス", "オープン・L", "重賞")
VENUE_BANDS: tuple[str, ...] = ("主場", "ローカル")
FIELD_BANDS: tuple[str, ...] = ("〜10頭", "11〜15頭", "16頭〜")
POOL_BANDS: tuple[str, ...] = ("下位 25%", "25〜50%", "50〜75%", "上位 25%")
UNKNOWN = "不明"
BANDS: dict[str, tuple[str, ...]] = {
    CLASS_AXIS: CLASS_BANDS, VENUE_AXIS: VENUE_BANDS, FIELD_AXIS: FIELD_BANDS, POOL_AXIS: POOL_BANDS, SURFACE_AXIS: ("芝", "ダート"),
}
#: 主場（東京・中山・京都・阪神）。それ以外はローカル（研究「既存モデルの改善」の条件で分ける実験と同じ）。
_MAIN_VENUES = frozenset({"東京", "中山", "京都", "阪神"})
#: クラスの並び順（事実表の ``class_order``）の境目。新馬 0・未出走 1・未勝利 2 / 1勝 3 / 2勝 4・3勝 5 / オープン 6・L 7 / 重賞 8〜。
_CLASS_EDGES: tuple[int, ...] = (3, 4, 6, 8)
_FIELD_EDGES: tuple[int, ...] = (11, 16)


class SceneBands:
    """レースの場面（``RaceSceneRepository``）と単勝の売上（``WinPoolSizeRepository``）から、軸ごとの帯の列を作る。

    - クラス: 新馬・未勝利 / 1勝クラス / 2勝・3勝クラス / オープン・L / 重賞。
    - 競馬場: 主場（東京・中山・京都・阪神）/ ローカル。
    - 頭数: 〜10頭 / 11〜15頭 / 16頭〜。
    - 単勝の売上: 渡したレースの中での四分位（下位 25% … 上位 25%）。売上が読めないレースは「不明」。
    - 芝ダ: 芝 / ダート。
    戻り値は race_id と ``AXES`` の列（1レース1行）。
    """

    def build(self, scenes: pd.DataFrame, pool_sizes: pd.DataFrame) -> pd.DataFrame:
        table = scenes[["race_id", *SCENE_COLUMNS]].astype({"race_id": str}).drop_duplicates("race_id")
        table = table.merge(pool_sizes[["race_id", WIN_POOL]].astype({"race_id": str}), on="race_id", how="left")
        class_order = pd.to_numeric(table["class_order"], errors="coerce")
        field = pd.to_numeric(table["field_size"], errors="coerce")
        return pd.DataFrame({
            "race_id": table["race_id"].to_numpy(),
            CLASS_AXIS: _banded(class_order, _CLASS_EDGES, CLASS_BANDS),
            VENUE_AXIS: np.where(table["venue"].isna(), UNKNOWN, np.where(table["venue"].isin(_MAIN_VENUES), VENUE_BANDS[0], VENUE_BANDS[1])),
            FIELD_AXIS: _banded(field, _FIELD_EDGES, FIELD_BANDS),
            POOL_AXIS: self._quartiles(pd.to_numeric(table[WIN_POOL], errors="coerce")),
            SURFACE_AXIS: table["surface"].fillna(UNKNOWN).astype(str).to_numpy(),
        })

    def _quartiles(self, values: pd.Series) -> np.ndarray:
        """売上の四分位の帯。値の無い行は「不明」。"""
        known = values.dropna()
        if known.empty:
            return np.full(len(values), UNKNOWN, dtype=object)
        edges = known.quantile([0.25, 0.5, 0.75]).to_numpy()
        return _banded(values, tuple(edges), POOL_BANDS)


def _banded(values: pd.Series, edges: tuple[float, ...], labels: tuple[str, ...]) -> np.ndarray:
    """``edges`` の各値を「その値未満」の境目にして帯の名前を付ける。欠損値は「不明」。"""
    position = np.searchsorted(np.asarray(edges, dtype=float), values.to_numpy(dtype=float), side="right")
    named = np.asarray(labels, dtype=object)[np.clip(position, 0, len(labels) - 1)]
    return np.where(values.isna().to_numpy(), UNKNOWN, named)
