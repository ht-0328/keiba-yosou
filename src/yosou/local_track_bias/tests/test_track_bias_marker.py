"""モデルの置き場所の「U で学んだ」印（``TrackBiasMarker``）。"""

from __future__ import annotations

import json
from pathlib import Path

from yosou.local_track_bias import LOCAL_TRACK_BIAS_FEATURES, TrackBiasMarker
from yosou.local_track_bias.track_bias_marker import MARKER_FILE


def test_印が無ければ_U_なしで学んだモデルと見る(tmp_path: Path):
    assert not TrackBiasMarker(tmp_path / "models").exists()


def test_印を書くと_U_の名前が入り_読めるようになる(tmp_path: Path):
    marker = TrackBiasMarker(tmp_path / "models")
    path = marker.save()
    assert path == tmp_path / "models" / MARKER_FILE and marker.exists()
    assert json.loads(path.read_text(encoding="utf-8"))["features"] == [f.name for f in LOCAL_TRACK_BIAS_FEATURES]
