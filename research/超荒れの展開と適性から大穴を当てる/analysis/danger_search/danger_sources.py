"""消の元になる人気馬の「4着以下の確率」の予測（今の消・今のモデルの消）を読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.shared.feature import PredictionTiming

from 印の成績.prediction_file import PredictionFile

from ..scenario_evaluation.comparison_files import CURRENT_DANGER

#: 消の元の名前。今の消は予想「人気馬が4着以下になるかを予想」の予測、今のモデルの消は今のモデル（近走と適性から3着以内を予想）の 1 − 3着以内の確率
#: （``evaluate.py danger-current`` が同じ形に書いたもの）。
CURRENT, MODEL = "今の消", "今のモデルの消"
SOURCES: tuple[str, ...] = (CURRENT, MODEL)


class DangerSources:
    """時点ごとの、消の元の予測のファイル（``PredictionFile`` が読む形。人気馬1頭 = 1行、区切り・期間・人気帯つき）。
    ``root`` は reports/超荒れの展開と適性から大穴を当てる。今の消は時点を問わず1つ。"""

    def __init__(self, timing: PredictionTiming, root: Path) -> None:
        self._paths = {CURRENT: Path(CURRENT_DANGER), MODEL: Path(root) / "predictions" / f"danger-current-top3-{timing.value}.pkl"}

    def path(self, source: str) -> Path:
        return self._paths[source]

    def load(self, source: str) -> pd.DataFrame:
        """全部の行（列は ``PredictionFile.load`` と同じ。``segment`` が人気帯）。"""
        return PredictionFile(str(self._paths[source])).load()

    def race_ids(self) -> pd.Series:
        """どちらの元にもあるレースの和（結果を読む範囲に足す）。"""
        return pd.concat([self.load(source)["race_id"] for source in SOURCES]).drop_duplicates().reset_index(drop=True)
