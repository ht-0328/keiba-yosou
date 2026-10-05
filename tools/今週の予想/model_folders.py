"""今週の予想が使う学習済みモデルの置き場所（定数だけ）。

予想の名前は、それぞれの予想の ``command/yosou_name.py`` の ``YOSOU_NAME`` と同じ。そちらを import すると予想の部品
（LightGBM・CatBoost）まで読み込んで重いので、ここに名前を書き、テスト（``tests/test_model_folders.py``）で一致を確かめる。
"""

from __future__ import annotations

from pathlib import Path

#: keiba-yosou のリポジトリ直下（tools/今週の予想/ から2つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
#: 全頭の予想「近走と適性から3着以内を予想」の名前（設計書 ``docs/design/`` のフォルダ名と同じ）。
FORM_YOSOU_NAME = "近走と適性から3着以内を予想"
#: 危険な人気馬を判定する予想「人気馬が4着以下になるかを予想」の名前。
FAVORITE_YOSOU_NAME = "人気馬が4着以下になるかを予想"
#: 学習済みモデルの既定の置き場所。
DEFAULT_MODELS = _PROJECT_ROOT / "reports" / FORM_YOSOU_NAME / "models"
#: 危険な人気馬を判定する予想の学習済みモデルの既定の置き場所。
DEFAULT_FAVORITE_MODELS = _PROJECT_ROOT / "reports" / FAVORITE_YOSOU_NAME / "models"
#: 今週の予想が要る学習済みモデルの置き場所の一覧（予想の名前, 置き場所）。取得と予想の状況の道具が、あるかどうかを見る。
MODEL_ROOTS: tuple[tuple[str, Path], ...] = ((FORM_YOSOU_NAME, DEFAULT_MODELS), (FAVORITE_YOSOU_NAME, DEFAULT_FAVORITE_MODELS))
