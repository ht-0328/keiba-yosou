"""レースごとの傾きと過去の傾きの表をとっておく場所。"""

from __future__ import annotations

from pathlib import Path

#: keiba-yosou のリポジトリ直下（src/yosou/local_track_bias/ から3つ上）と、とっておく場所の既定。
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOCAL_BIAS_CACHE_FOLDER = _PROJECT_ROOT / "reports" / "地方の当日の馬場傾向" / "cache"


def local_bias_cache_folder_beside(models: Path) -> Path:
    """全頭の予想のモデルの置き場所（``reports/地方競馬の近走と適性から3着以内を予想/models``）の2つ上の ``地方の当日の馬場傾向/cache/``
    （既定の置き場所と同じ決め方。テストでは一時フォルダの下になり、本物の reports/ を書き換えない）。"""
    return Path(models).resolve().parent.parent / "地方の当日の馬場傾向" / "cache"
