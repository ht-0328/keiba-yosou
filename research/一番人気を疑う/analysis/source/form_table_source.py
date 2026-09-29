"""研究「既存モデルの改善」が保存した学習データの表（今の予想の材料）を読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from 既存モデルの改善.analysis.experiments import EXPERIMENT_GROUPS

from yosou.form_aptitude_top3.feature import CATALOG
from yosou.shared.feature import BASE_FEATURES, MARKET_FEATURES, PredictionTiming

from .runner_frame import RunnerFrame

#: 材料の実験の表（今の予想の75個に、実験の材料を足したもの）。
TABLE_NAME = "form_experiments"
_PARTS = ("ids", "evaluation", "targets", "features")


class FormTableSource:
    """``reports/既存モデルの改善/tables/form_experiments/`` を、1行 = 1頭の表にして読む。

    材料の組は、次の名前で引ける。
    - ``thursday``: 今の予想の木曜版の材料（オッズなし・木曜に分かるものだけ。62個）
    - ``base``: 今の予想の当日版からオッズの4個を外した材料（71個）
    - ``odds``: 単勝オッズから作る4個（単勝オッズ・人気順位・オッズから見た勝率・3着以内率）
    - ``pool``: 券種ごとのオッズから見た支持と単勝の比（6個。当日だけ）
    - ``extra``: 券種のオッズ以外の実験の材料（能力指数・市場に対する成績・当日の馬場傾向）
    """

    def __init__(self, tables: Path) -> None:
        self._folder = Path(tables) / TABLE_NAME

    def read(self) -> pd.DataFrame:
        ids, evaluation, targets, features = (pd.read_pickle(self._folder / f"{part}.pkl") for part in _PARTS)
        frame = pd.concat([ids[["レースID", "開催日"]], evaluation[["確定の単勝人気", "確定着順", "確定の単勝オッズ"]],
                           targets[["3着以内"]], features], axis=1)
        return RunnerFrame().shape(frame, list(features.columns))

    @staticmethod
    def columns(name: str) -> list[str]:
        """材料の組の列。知らない名前なら ``KeyError``。"""
        extra = [column for key, (_, names, _) in EXPERIMENT_GROUPS.items() if key != "pool" for column in names]
        sets = {
            "thursday": list(CATALOG.columns_for(PredictionTiming.THURSDAY)),
            "base": [feature.name for feature in BASE_FEATURES],
            "odds": [feature.name for feature in MARKET_FEATURES],
            "pool": list(EXPERIMENT_GROUPS["pool"][1]),
            "extra": extra,
        }
        return list(sets[name])
