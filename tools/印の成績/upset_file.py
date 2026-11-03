"""区切りごとの荒れ具合の予測（研究「既存モデルの改善」の walk_forward.py --model upset_level が書くもの）から、3連複の荒れ具合を読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 今週の予想.forecast_columns import TRIO_UPSET
from 今週の予想.trio_upset_judge import TrioUpsetJudge

from 印の成績.prediction_file import PREDICTIONS_FOLDER, TEST

#: 既定の予測（今の本番の作り方を7つの区切りで学んだもの）。
DEFAULT_UPSET = PREDICTIONS_FOLDER / "upset_level" / "current.pkl"
#: 読む券種。
_TRIO = "3連複"


class UpsetFile:
    """荒れ具合の予測のファイル1つ（1行 = 1レース × 1券種。列はレースID・券種・期間と、固い〜超荒れの4つの確率）。

    3連複のテスト期間の行だけを、レースごとの荒れ具合（今週の予想と同じ ``TrioUpsetJudge`` の決め方）にして返す。
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> pd.DataFrame:
        """列は race_id（文字列）と ``TRIO_UPSET``（固い・中荒れ・大荒れ・超荒れ）。1行 = 1レース。"""
        if not self.path.is_file():
            raise FileNotFoundError(f"荒れ具合の予測がありません: {self.path}（研究「既存モデルの改善」の walk_forward.py --model upset_level で作る）")
        table = pd.read_pickle(self.path)
        trio = table[(table["券種"] == _TRIO) & (table["期間"] == TEST)]
        return (pd.DataFrame({"race_id": trio["レースID"].astype(str), TRIO_UPSET: TrioUpsetJudge().of(trio)})
                .drop_duplicates("race_id").reset_index(drop=True))
