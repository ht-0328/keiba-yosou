"""この予想の名前と、リポジトリ直下の場所。"""

from __future__ import annotations

from pathlib import Path

#: この予想のパッケージ名。学習したモデルと途中の結果の置き場所（``reports/<名前>/``）に使う。
YOSOU_NAME = "race_development"
#: keiba-yosou のリポジトリ直下（src/yosou/race_development/command/ から4つ上）。
PROJECT_ROOT = Path(__file__).resolve().parents[4]
