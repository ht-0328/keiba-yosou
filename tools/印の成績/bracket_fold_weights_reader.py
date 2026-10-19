"""区切りごとの枠連の組の確率の重みのファイルを読む。"""

from __future__ import annotations

import json
from pathlib import Path

from yosou.shared.combo_value import BracketBlendWeights


def read_bracket_fold_weights(path: Path) -> dict[str, BracketBlendWeights]:
    """``{"2016年前半": {"own": …, "quinella": …, "trifecta": …, "harville": …}, …}`` の JSON を、区切り → 重みにする。
    研究「レースの種類ごとの買い方」の ``all_tickets.py bracket-weights`` が書くファイル（区切りごとに直前1年で推定した重み）。"""
    saved = json.loads(Path(path).read_text(encoding="utf-8"))
    return {fold: BracketBlendWeights.from_dict(value) for fold, value in saved.items()}
