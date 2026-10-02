"""7つの区切りの予測（研究「既存モデルの改善」の入口② walk_forward.py が書くもの）を読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

#: keiba-yosou のリポジトリ直下（tools/印の成績/ から2つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
#: 予測の置き場所。``<予想>/<作り方>.pkl`` の形で置かれている。
PREDICTIONS_FOLDER = _PROJECT_ROOT / "reports" / "既存モデルの改善" / "predictions"
#: 予測のファイルの列 → この道具の列。
_RENAMES: dict[str, str] = {
    "レースID": "race_id", "開催日": "race_date", "馬ID": "horse_id", "馬番": "horse_no", "確率": "probability",
    "区切り": "fold", "期間": "period", "区分": "segment",
}
#: 評価に使う期間（学習にも、線を決めるのにも使っていない期間）と、線を決める期間。
TEST = "テスト"
VALID = "検証"


class PredictionFile:
    """7つの区切りの予測のファイル1つ。``name`` は ``<予想>/<作り方>``（例: ``h2h_ability/h2h-day_before``）か、pkl のパス。

    ファイルの1行は1頭の予測で、区切りごとに検証とテストの期間の行がある（``walk_forward.py`` の出力）。
    """

    def __init__(self, name: str, folder: Path = PREDICTIONS_FOLDER) -> None:
        self.name = name
        self.path = self._resolve(name, Path(folder))

    def load(self) -> pd.DataFrame:
        """全部の行。列は race_id・race_date・horse_id・horse_no・probability・fold・period・segment（鍵は文字列）。"""
        if not self.path.is_file():
            raise FileNotFoundError(f"予測のファイルがありません: {self.path}（研究「既存モデルの改善」の walk_forward.py で作る）")
        table = pd.read_pickle(self.path).rename(columns=_RENAMES)
        missing = [column for column in _RENAMES.values() if column not in table.columns]
        if missing:
            raise ValueError(f"予測のファイルの形が違います（無い列: {', '.join(missing)}）: {self.path}")
        return table[list(_RENAMES.values())].astype({"race_id": str, "horse_id": str})

    def label(self) -> str:
        """結果のファイル名などに使う短い名前（``h2h_ability/h2h-day_before`` → ``h2h_ability_h2h-day_before``）。"""
        return self.path.relative_to(self.path.parents[1]).with_suffix("").as_posix().replace("/", "_")

    def _resolve(self, name: str, folder: Path) -> Path:
        path = Path(name)
        if path.suffix == ".pkl":
            return path
        return folder / f"{name}.pkl"
