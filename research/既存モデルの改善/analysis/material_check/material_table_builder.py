"""元の表に材料を足す部品の形。材料ごとに、この形のクラスを1つ作る。"""

from __future__ import annotations

from typing import Protocol

import duckdb

from yosou.shared.dataset import TrainingData
from yosou.shared.feature import PredictionTiming


class MaterialTableBuilder(Protocol):
    """元の表（今の本番の列を持つ学習データ）に、材料の列を足す。

    ``prepare`` は元DB を開いているあいだに1回だけ呼ばれ、材料の元になる記録を読む（要らなければ何もしない）。
    ``build`` は時点ごとの表に材料を足す。**レースより前の記録だけで作ること**（学習データの各レースの材料に、そのレース以降の
    結果が混ざらないように。年ごとに「その年の1月1日より前」で作り直す、開催日の前日までで数える、など）。
    同じ名前の列がもうあれば置き換え、特徴量の一覧（``catalog``）にも足す。
    """

    def prepare(self, con: duckdb.DuckDBPyConnection) -> None: ...

    def build(self, base: TrainingData, timing: PredictionTiming) -> TrainingData: ...
