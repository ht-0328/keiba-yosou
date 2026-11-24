"""道具「ばんえいの予想」が使う置き場所の定数。"""

from __future__ import annotations

from pathlib import Path

#: keiba-yosou（この道具が入っているリポジトリ）。
PROJECT = Path(__file__).resolve().parents[2]
#: 学習済みモデルと記録を置く場所（Git 対象外）。
DEFAULT_FOLDER = PROJECT / "reports" / "ばんえいの予想"
#: 学習済みモデル（勝つ確率の予想・世間の見立て・材料の名前）。
MODEL_FOLDER = DEFAULT_FOLDER / "models"
