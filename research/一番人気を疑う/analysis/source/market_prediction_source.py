"""研究「既存モデルの改善」が保存した、オッズを使う作り方の予測を読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

#: 予測の表の名前と、そのときの学習データの表の名前。
_TABLE_OF = {"form_aptitude_top3": "form_aptitude_top3", "form_experiments": "form_experiments"}


class MarketPredictionSource:
    """``reports/既存モデルの改善/predictions/<予想>/<作り方>.pkl`` のテスト期間の行を、この研究の予測の表の形にする。

    予測の表には人気と着順が無いので、学習データの表（``tables/<予想>/``）の同じ行から付ける。
    列は ``レースID``・``馬番``・``確定の単勝人気``・``3着以内``・``score``・``区切り``。
    """

    def __init__(self, tables: Path, predictions: Path) -> None:
        self._tables = Path(tables)
        self._predictions = Path(predictions)

    def read(self, model: str, key: str) -> pd.DataFrame:
        folder = self._tables / _TABLE_OF[model]
        ids, evaluation, targets = (pd.read_pickle(folder / f"{part}.pkl") for part in ("ids", "evaluation", "targets"))
        truth = pd.concat([ids[["レースID", "馬番"]], evaluation[["確定の単勝人気", "確定の単勝オッズ"]], targets[["3着以内"]]], axis=1)
        predictions = pd.read_pickle(self._predictions / model / f"{key}.pkl")
        predictions = predictions[predictions["期間"] == "テスト"]
        frame = predictions[["レースID", "馬番", "確率", "区切り"]].merge(truth, on=["レースID", "馬番"], how="left")
        frame["レースID"] = frame["レースID"].astype(str)
        return frame.rename(columns={"確率": "score"}).dropna(subset=["3着以内"])
