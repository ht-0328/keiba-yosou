"""研究「馬の力と展開でオッズに勝つ」が保存した表（オッズを使わない197個の材料）を読む。"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pandas as pd

from .runner_frame import RunnerFrame

#: 表の列 → この研究の列の名前。
_RENAMES = {"race_id": "レースID", "race_date": "開催日", "horse_no": "馬番", "popularity": "確定の単勝人気",
            "placed": "3着以内", "finish": "確定着順", "win_odds": "確定の単勝オッズ"}
#: 条件ごとに分けて見るときに使う列（材料ではない）。
INFO_COLUMNS: tuple[str, ...] = ("horse_id", "class_name", "surface", "runs_before", "prev_popularity")
#: JRA-VAN のマイニング予想の列（オッズではないが、よその予想なので、材料に入れるかを分けて確かめる）。
MINING_COLUMNS: tuple[str, ...] = ("dm_rank", "tm_rank", "tm_score")
#: 木曜には分からない材料（馬体重・枠・馬番・当日の馬場状態と、それを使うもの）。
_NOT_ON_THURSDAY: tuple[str, ...] = (
    "body_weight", "weight_change", "frame_no", "condition_order", "体重_近走の平均との差", "馬番の位置",
    "枠の傾向_勝率", "枠の傾向_3着内率", "枠の傾向_出走数", "cond_places_before",
)
#: 学習に使う最初の開催日（表の2011年は過去走を作るためだけに使われている）。
FIRST_DAY = date(2012, 1, 1)
#: 材料のまとまり → そのまとまりの列かを決める規則（1つずつ外して効き目を見るのに使う）。
GROUPS: dict[str, Callable[[str], bool]] = {
    "指数": lambda column: column.startswith("指数"),
    "展開と位置": lambda column: column.startswith(("序盤の位置", "4角の位置", "末脚", "先頭", "ペース", "展開の不利"))
    or column in ("先頭率の合計", "ほかの馬の先頭率の合計"),
    "相手の強さ": lambda column: column.startswith("相手の強さ"),
    "人": lambda column: column.startswith(("騎手", "調教師")),
    "馬主・生産者・母": lambda column: column.startswith(("馬主", "生産者", "母_")),
    "調教": lambda column: column.startswith(("坂路", "ウッド")),
    "血統": lambda column: column.startswith(("父", "母父")),
    "レース内の比較": lambda column: column.endswith(("_順位", "_最良との差", "_偏差")),
}


class AbilityTableSource:
    """``reports/馬の力と展開でオッズに勝つ/cache/`` の ``dataset.parquet`` と、材料の一覧 ``dataset_features.json`` を読む。

    材料の組は ``race_day``（197個。当日に分かるものすべて）と ``thursday``（そこから木曜に分からないものを外したもの）。
    """

    def __init__(self, cache: Path) -> None:
        self._cache = Path(cache)

    def features(self) -> list[str]:
        return json.loads((self._cache / "dataset_features.json").read_text(encoding="utf-8"))

    def read(self) -> pd.DataFrame:
        features = self.features()
        wanted = list(dict.fromkeys([*_RENAMES, *INFO_COLUMNS, *MINING_COLUMNS, *features]))
        frame = pd.read_parquet(self._cache / "dataset.parquet", columns=wanted).rename(columns=_RENAMES)
        frame = frame[pd.to_datetime(frame["開催日"]).dt.date >= FIRST_DAY]
        return RunnerFrame().shape(frame, features)

    def columns(self, name: str) -> list[str]:
        """材料の組の列。知らない名前なら ``KeyError``。"""
        features = self.features()
        sets = {"race_day": features, "thursday": [column for column in features if column not in _NOT_ON_THURSDAY],
                "mining": list(MINING_COLUMNS), "past_popularity": ["prev_popularity"]}
        return list(sets[name])

    @staticmethod
    def without(columns: list[str], group: str) -> list[str]:
        """``columns`` から、まとまり ``group`` の列を外す。知らないまとまりなら ``KeyError``。"""
        belongs = GROUPS[group]
        return [column for column in columns if not belongs(column)]
