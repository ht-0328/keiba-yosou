"""今の1着の確率を、券種どうしのずれなどの材料で直すモデル（LightGBM。種を変えた数本の平均）。"""

from __future__ import annotations

from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from .win_correction_features import BASE, FEATURES

#: 学習の設定。木を小さくし（葉 4 枚・1枚の葉に 3,000 行以上）、重みに強い罰を付けて、期待値の高い馬の確率を出しすぎないようにする
#: （研究「的中実績の公開ルール」の 02。縛りの弱い作りは、期待値の高い帯で確かめる期間の回収率が崩れた）。
PARAMS: dict[str, object] = {
    "objective": "binary", "learning_rate": 0.03, "num_leaves": 4, "min_data_in_leaf": 3000, "lambda_l2": 100.0,
    "feature_fraction": 0.8, "bagging_fraction": 0.8, "bagging_freq": 1, "verbose": -1, "num_threads": 4,
}
#: 木の数と、平均する本数（種）。
ROUNDS = 300
SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)
#: 保存するファイルの名前（``<置き場所>/win_correction_<種>.txt``）。
_FILE = "win_correction_{seed}.txt"


class WinCorrectionModel:
    """出発点（今の1着の確率のロジット ``base``）からの上げ下げを ``FEATURES`` で学ぶ2値の LightGBM を、種を変えて ``SEEDS`` の本数作り、
    予測は上げ下げの平均を出発点に足して確率にし、レースの中で合計 1 にそろえる。

    ``fit`` の ``frame`` は ``WinCorrectionFeatures.frame`` の表、``won`` は1着か（1/0）。保存は文字の形で書く（置き場所の名前に
    日本語があっても書けるように）。
    """

    def __init__(self, boosters: list[lgb.Booster]) -> None:
        self._boosters = boosters

    @classmethod
    def fit(cls, frame: pd.DataFrame, won: pd.Series, seeds: tuple[int, ...] = SEEDS, rounds: int = ROUNDS) -> WinCorrectionModel:
        boosters = []
        for seed in seeds:
            params = {**PARAMS, "seed": seed, "bagging_seed": seed, "feature_fraction_seed": seed}
            data = lgb.Dataset(frame[list(FEATURES)], won.astype(int).to_numpy(), init_score=frame[BASE].to_numpy())
            boosters.append(lgb.train(params, data, rounds))
        return cls(boosters)

    @classmethod
    def load(cls, folder: Path) -> WinCorrectionModel | None:
        """置き場所のモデルを読む。1本も無ければ None。"""
        paths = sorted(Path(folder).glob(_FILE.format(seed="*"))) if Path(folder).is_dir() else []
        if not paths:
            return None
        return cls([lgb.Booster(model_str=path.read_text(encoding="utf-8")) for path in paths])

    def save(self, folder: Path) -> list[Path]:
        Path(folder).mkdir(parents=True, exist_ok=True)
        paths = []
        for seed, booster in enumerate(self._boosters):
            path = Path(folder) / _FILE.format(seed=seed)
            path.write_text(booster.model_to_string(), encoding="utf-8")
            paths.append(path)
        return paths

    def probabilities(self, frame: pd.DataFrame, race_id: pd.Series) -> pd.Series:
        """直した1着の確率（レースの中で合計 1）。並びと index は ``frame`` と同じ。"""
        shift = np.mean([booster.predict(frame[list(FEATURES)], raw_score=True) for booster in self._boosters], axis=0)
        p = pd.Series(1.0 / (1.0 + np.exp(-(frame[BASE].to_numpy() + shift))), index=frame.index)
        return p / p.groupby(race_id.astype(str).to_numpy()).transform("sum")
