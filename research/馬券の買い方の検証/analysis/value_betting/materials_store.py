"""材料表をファイルに書く・読む。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from .materials import Round3Materials

#: 材料表のフォルダに置くファイル。
_RUNNERS, _RACES, _HISTORY, _META = "runners.pkl", "races.pkl", "price_history.pkl", "materials-meta.json"


class MaterialsStore:
    """``Round3Materials`` を、フォルダ（``reports/馬券の買い方の検証/round3/materials/``）に pickle で書く・読む。
    いつ・何から作ったかの記録（``materials-meta.json``）も一緒に書く。JV-Data 由来の値を含むので置き場は ``reports/``。"""

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)

    @property
    def folder(self) -> Path:
        return self._folder

    def write(self, materials: Round3Materials, meta: dict[str, object]) -> Path:
        self._folder.mkdir(parents=True, exist_ok=True)
        materials.runners.to_pickle(self._folder / _RUNNERS)
        materials.races.to_pickle(self._folder / _RACES)
        materials.price_history.to_pickle(self._folder / _HISTORY)
        record = {"written_at": datetime.now().isoformat(timespec="seconds"), "runners": len(materials.runners),
                  "races": len(materials.races), "price_history": len(materials.price_history), **meta}
        (self._folder / _META).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return self._folder

    def read(self) -> Round3Materials:
        """無ければ ``FileNotFoundError``。"""
        if not (self._folder / _META).exists():
            raise FileNotFoundError(f"材料表がありません: {self._folder}（先に backtest_round3.py --build-materials を実行してください）")
        return Round3Materials(pd.read_pickle(self._folder / _RUNNERS), pd.read_pickle(self._folder / _RACES),
                               pd.read_pickle(self._folder / _HISTORY))

    def exists(self) -> bool:
        return (self._folder / _META).exists()
