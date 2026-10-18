"""区切りごとの組の確率の重みのファイルを読む。"""

from __future__ import annotations

import json
from pathlib import Path

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import ComboBlendWeights


def read_fold_weights(path: Path) -> dict[str, dict[TicketType, ComboBlendWeights]]:
    """``{"2016年前半": {"ワイド": {"own": …, "trifecta": …, "harville": …, "ratio": …}, …}, …}`` の JSON を、区切り → 券種 → 重みにする。
    研究「複勝以外の回収率100超」の ``combo_value.py rolling`` が書くファイル（区切りごとに直前1年で推定した重み）。"""
    saved = json.loads(Path(path).read_text(encoding="utf-8"))
    return {fold: {TicketType.parse(label): ComboBlendWeights.from_dict(value) for label, value in by_type.items()}
            for fold, by_type in saved.items()}
