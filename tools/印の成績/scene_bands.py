"""レースの場面を、表に出す帯に分ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 印の成績.race_scene_repository import COLUMNS as SCENE_COLUMNS
from 印の成績.scene_scheme import JRA_SCENE_SCHEME, SceneScheme
from 印の成績.win_pool_size_repository import WIN_POOL

#: 帯の軸（表に出す名前）と、帯の並び。
CLASS_AXIS, VENUE_AXIS, FIELD_AXIS, POOL_AXIS, SURFACE_AXIS = "クラス", "競馬場", "頭数", "単勝の売上", "芝ダ"
AXES: tuple[str, ...] = (CLASS_AXIS, VENUE_AXIS, FIELD_AXIS, POOL_AXIS, SURFACE_AXIS)
FIELD_BANDS: tuple[str, ...] = ("〜10頭", "11〜15頭", "16頭〜")
POOL_BANDS: tuple[str, ...] = ("下位 25%", "25〜50%", "50〜75%", "上位 25%")
SURFACE_BANDS: tuple[str, ...] = ("芝", "ダート")
UNKNOWN = "不明"
_FIELD_EDGES: tuple[int, ...] = (11, 16)


class SceneBands:
    """レースの場面（``RaceSceneRepository``）と単勝の売上（``WinPoolSizeRepository``）から、軸ごとの帯の列を作る。

    - クラス・競馬場: ``scheme``（中央か地方）の区分。中央は 新馬・未勝利 / 1勝クラス / 2勝・3勝クラス / オープン・L / 重賞 と 主場 / ローカル。
    - 頭数: 〜10頭 / 11〜15頭 / 16頭〜。
    - 単勝の売上: 渡したレースの中での四分位（下位 25% … 上位 25%）。売上が読めないレースは「不明」。
    - 芝ダ: 芝 / ダート。
    戻り値は race_id と ``AXES`` の列（1レース1行）。帯の並びは ``bands``。
    """

    def __init__(self, scheme: SceneScheme = JRA_SCENE_SCHEME) -> None:
        self._scheme = scheme

    @property
    def bands(self) -> dict[str, tuple[str, ...]]:
        """軸 → 帯の名前の並び（表の行の順）。"""
        return {
            CLASS_AXIS: self._scheme.class_bands, VENUE_AXIS: self._scheme.venue_bands, FIELD_AXIS: FIELD_BANDS,
            POOL_AXIS: POOL_BANDS, SURFACE_AXIS: SURFACE_BANDS,
        }

    def build(self, scenes: pd.DataFrame, pool_sizes: pd.DataFrame) -> pd.DataFrame:
        table = scenes[["race_id", *SCENE_COLUMNS]].astype({"race_id": str}).drop_duplicates("race_id")
        table = table.merge(pool_sizes[["race_id", WIN_POOL]].astype({"race_id": str}), on="race_id", how="left")
        class_order = pd.to_numeric(table["class_order"], errors="coerce")
        field = pd.to_numeric(table["field_size"], errors="coerce")
        main, other = self._scheme.venue_bands
        return pd.DataFrame({
            "race_id": table["race_id"].to_numpy(),
            CLASS_AXIS: _banded(class_order, self._scheme.class_edges, self._scheme.class_bands),
            VENUE_AXIS: np.where(table["venue"].isna(), UNKNOWN, np.where(table["venue"].isin(self._scheme.main_venues), main, other)),
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
