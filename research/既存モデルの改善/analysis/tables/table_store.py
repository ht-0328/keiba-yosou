"""学習データを pickle に書く・読む。"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from yosou.shared.dataset import BaselineLogit, TrainingData
from yosou.shared.feature import FeatureCatalog, PredictionTiming

#: 学習データの表ごとのファイル名と、基準・目的変数の名前を書くファイル名。
_PARTS: tuple[str, ...] = ("ids", "features", "targets", "evaluation")
_BASELINE_FILE = "baseline.pkl"
_META_FILE = "meta.json"
#: 基準の値を入れる列の名前。
_BASELINE_COLUMN = "baseline"


class TableStore:
    """学習データ（``TrainingData``）を、予想ごとのフォルダ ``<root>/<予想の名前>/`` に pickle で書く・読む。

    pickle は pandas の表をそのまま書く形で、依存を足さずに速く読み書きできる（Git 対象外の reports/ に置く作業用の保存）。

    特徴量の一覧（``FeatureCatalog``）はコードにあるので書かず、読むときに渡してもらう。
    目的変数の名前・クラスの並び・基準が分かる時点は ``meta.json`` に書く。
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def write(self, name: str, data: TrainingData) -> Path:
        """書いたフォルダを返す。前のものがあれば置き換える。"""
        folder = self._root / name
        folder.mkdir(parents=True, exist_ok=True)
        for part in _PARTS:
            getattr(data, part).reset_index(drop=True).to_pickle(folder / f"{part}.pkl")
        self._write_baseline(folder, data.baseline)
        meta = {
            "label_name": data.label_name, "class_labels": list(data.class_labels),
            "baseline_known_from": data.baseline.known_from.value if data.baseline is not None else None,
        }
        (folder / _META_FILE).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return folder

    def read(self, name: str, catalog: FeatureCatalog) -> TrainingData:
        """``write`` で書いた学習データ。無ければ ``FileNotFoundError``。"""
        folder = self._root / name
        meta = json.loads((folder / _META_FILE).read_text(encoding="utf-8"))
        parts = {part: pd.read_pickle(folder / f"{part}.pkl") for part in _PARTS}
        return TrainingData(
            parts["ids"], parts["features"], parts["targets"], parts["evaluation"], catalog,
            meta["label_name"], tuple(meta["class_labels"]), self._read_baseline(folder, meta),
        )

    def exists(self, name: str) -> bool:
        return (self._root / name / _META_FILE).exists()

    def _write_baseline(self, folder: Path, baseline: BaselineLogit | None) -> None:
        path = folder / _BASELINE_FILE
        if baseline is None:
            path.unlink(missing_ok=True)
            return
        pd.DataFrame({_BASELINE_COLUMN: baseline.values.to_numpy()}).to_pickle(path)

    def _read_baseline(self, folder: Path, meta: dict) -> BaselineLogit | None:
        known_from = meta.get("baseline_known_from")
        if known_from is None:
            return None
        values = pd.read_pickle(folder / _BASELINE_FILE)[_BASELINE_COLUMN]
        return BaselineLogit(values, PredictionTiming(known_from))
