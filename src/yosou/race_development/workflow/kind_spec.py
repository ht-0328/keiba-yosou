"""1つの予想の決めごと（目的変数・特徴量の一覧・モデルの種類・予測の列）。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.feature import FeatureCatalog, PredictionTiming

from .model_family import ModelFamily


@dataclass(frozen=True)
class KindSpec:
    """1つの予想の決めごと。

    - ``label``: 学習データの目的変数の列（``with_label`` で持ち替える）。
    - ``per_race``: 1行 = 1レースの予想か（False なら 1行 = 1頭）。
    - ``family``: モデルの種類。
    - ``catalog``: 使う特徴量の一覧（前の組の予測 S・T を含む）。
    - ``outputs``: 予測の列の名前（後の組の特徴量と、年ごとの確かめの元）。
    - ``class_labels``: 目的変数の値の並び（回帰と分位点回帰は使わないが、二値の並びを置いておく）。
    - ``label_text``: 表に出す名前。
    - ``for_prediction``: 予測に使うか（学習（train）で保存し、予測（predict）で読むか）。偽なら、年ごとの確かめで
      比べるためだけに学習する予想。
    - ``known_from``: この時点から学習する（オッズを足した ⑦ は、確定オッズの分かる当日だけ）。
    """

    label: str
    per_race: bool
    family: ModelFamily
    catalog: FeatureCatalog
    outputs: tuple[str, ...]
    class_labels: tuple[int, ...]
    label_text: str
    for_prediction: bool = True
    known_from: PredictionTiming = PredictionTiming.THURSDAY
