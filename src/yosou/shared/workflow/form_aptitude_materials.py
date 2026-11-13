"""今のモデルの予測用データに足す材料（P・S・T・U・V）を作る部品の決まり（インターフェース）。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

import duckdb

from .prediction_workflow import DataAttachment, PaceSource


class FormAptitudeMaterials(Protocol):
    """今のモデルの予測の流れ（``FormAptitudePrediction``）に、材料を足す関数を渡す部品の決まり。

    材料を作る部品は、予想「展開から着順を予想」（``yosou.race_development``）の保存したモデルを使うので、``shared`` には置けない
    （``shared`` から予想のパッケージを参照しない決まり）。守るクラスは ``yosou.form_aptitude_materials`` の ``MaterialAttachers``。
    どの時点でどの材料を足すかは ``FormAptitudePrediction`` が決め、ここはそれぞれの材料の関数を返すだけ。

    - ``pace()``: 展開の予想の結果（P）の元になる、そのレースの展開の予測を返す関数（木曜）。
    - ``score()``: 展開スコア（S）を足す関数。
    - ``ability_score()``: 能力スコア（T）を足す関数。
    - ``bias()``: トラックバイアスの補正（U）を足す関数。
    - ``weight_discount()``: 馬体重の表の割引（V）を足す関数。
    """

    def pace(self) -> PaceSource: ...

    def score(self) -> DataAttachment: ...

    def ability_score(self) -> DataAttachment: ...

    def bias(self) -> DataAttachment: ...

    def weight_discount(self) -> DataAttachment: ...


#: 元DB への接続から、材料を作る部品を1つ作る関数（1回の予測ごとに作り直し、その予測の中で使い回す）。
MaterialsFactory = Callable[[duckdb.DuckDBPyConnection], FormAptitudeMaterials]
