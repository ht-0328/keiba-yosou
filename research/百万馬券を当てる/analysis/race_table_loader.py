"""レース単位の表（1行 = 1レース）を読み、帯・大荒れの目的変数を足す。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

from yosou.shared.dataset import TrainingData

from 既存モデルの改善.analysis.tables import TableStore, spec_named

from .obi_rules import BIG_YEN, OBI_YEN

#: 表の名前（荒れ具合の予想の学習データ。作り方は予想のパッケージ ``yosou.upset_level`` のもの）。
RACE_TABLE = "upset_level"
#: 評価用の列のうち、3連単・3連複の払戻（100円あたり）。
TRIFECTA_YEN, TRIO_YEN = "3連単の払戻", "3連複の払戻"
#: 足す目的変数の名前（1 なら当てはまる。払戻の無いレースは欠損）。
OBI_LABEL, BIG_LABEL = "帯", "大荒れ以上"


class RaceTableLoader:
    """研究の置き場（``reports/百万馬券を当てる/tables``）から、レース単位の表を読む。

    表は研究「既存モデルの改善」の ``build_tables.py --only upset_level --tables <置き場>`` で作ったもの（2012年1月から）。
    目的変数に「帯（3連単の払戻が 100万円以上）」と「大荒れ以上（10万円以上）」の2列を足して返す。
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def read(self) -> TrainingData:
        spec = spec_named(RACE_TABLE)
        data = TableStore(self._root).read(spec.name, spec.catalog)
        payout = data.evaluation[TRIFECTA_YEN]
        targets = data.targets.assign(**{OBI_LABEL: _flag(payout, OBI_YEN), BIG_LABEL: _flag(payout, BIG_YEN)})
        return replace(data, targets=targets)


def _flag(payout: pd.Series, line: int) -> pd.Series:
    """払戻が線以上なら 1、未満なら 0、払戻が無ければ欠損。"""
    return (payout >= line).astype("float").where(payout.notna())
