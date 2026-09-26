"""元DB から作った学習データを、ファイルに読み書きする。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.shared.dataset import TrainingData


class DatasetRepository:
    """1頭ごと・1レースごとの学習データを ``<root>/<名前>.pkl`` に書き、読む。

    学習データを元DB から作るのは、2016年からの全部のレースで 10分ほどかかる。年ごとの確かめをやり直すたびに作り直さずに
    済むよう、作った条件（``signature``。元DB の更新日時と期間）と一緒に残す。条件が違えば「まだ無い」と答える。
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def load(self, name: str, signature: str) -> TrainingData | None:
        """``signature`` が「-」で始まる（元DB の部分が空）なら、期間の部分だけを比べる。"""
        path = self._root / f"{name}.pkl"
        if not path.exists():
            return None
        saved = pd.read_pickle(path)
        return saved["data"] if self._matches(str(saved.get("signature")), signature) else None

    def _matches(self, saved: str, wanted: str) -> bool:
        if wanted.startswith("-"):
            return saved.endswith(wanted)
        return saved == wanted

    def save(self, name: str, signature: str, data: TrainingData) -> Path:
        path = self._root / f"{name}.pkl"
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.to_pickle({"signature": signature, "data": data}, path)
        return path
