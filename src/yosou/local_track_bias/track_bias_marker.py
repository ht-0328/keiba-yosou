"""モデルの置き場所に「当日のモデルを当日の馬場傾向（U）で学んだ」印を書く・読む。"""

from __future__ import annotations

import json
from pathlib import Path

from .features import LOCAL_TRACK_BIAS_FEATURES

#: 印のファイルの名前（モデルの置き場所 ``--models`` の直下）。
MARKER_FILE = "当日の馬場傾向.json"


class TrackBiasMarker:
    """モデルの置き場所に、当日のモデルを U で学んだことを示す印を書き、``backtest``・``predict`` がそれを読んで U を足すか決める。

    印は ``<置き場所>/当日の馬場傾向.json`` で、中身は U の特徴量の名前の並び。``train --track-bias`` だけが書く。
    印が無ければ U なしで学んだモデルで、本番のモデルはこちらである（設計書 15 の 11）。
    """

    def __init__(self, models: Path) -> None:
        self._path = Path(models) / MARKER_FILE

    def save(self) -> Path:
        """印を書く（置き場所が無ければ作る）。書いた場所を返す。"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        names = [feature.name for feature in LOCAL_TRACK_BIAS_FEATURES]
        self._path.write_text(json.dumps({"features": names}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return self._path

    def exists(self) -> bool:
        """U で学んだ印があるか。"""
        return self._path.is_file()
