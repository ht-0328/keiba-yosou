"""確かめる材料1つ（名前・列・足し方・足す時点）。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from yosou.shared.feature import Feature, PredictionTiming

from .material_table_builder import MaterialTableBuilder


@dataclass(frozen=True)
class Material:
    """確かめる材料（予想のまとまり）1つ。

    - ``key``: 表と予測のファイル名の頭（例 ``ascore``）。
    - ``label``: 人が読む名前（例 能力スコア）。
    - ``group``: 設計書 09 のまとまりの文字（例 T）。
    - ``features``: 足す特徴量の一覧（予想のパッケージのもの）。
    - ``builder``: 元の表に材料を足す部品を作る関数（``MaterialTableBuilder``）。
    - ``timings``: 確かめる時点（材料がその時点で分かるものだけ。3着以内と1着の両方を回す）。
    - ``design``: 材料を決めた設計書の場所（結果の文書に書く）。
    """

    key: str
    label: str
    group: str
    features: tuple[Feature, ...]
    builder: Callable[[], MaterialTableBuilder]
    timings: tuple[PredictionTiming, ...] = tuple(PredictionTiming)
    design: str = ""

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(feature.name for feature in self.features)
