"""試す作り方1つ（どの表の・どの材料で・どのモデルで学習するか）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Experiment:
    """試す作り方1つ。

    - ``key``: 予測を保存するファイルの名前（例 ``21_木曜_研究の材料``）。
    - ``source``: 読む表。``form`` は今の予想の材料の表、``ability`` はオッズを使わない197個の材料の表。
    - ``sets``: 使う材料の組の名前（表ごとの ``columns()`` で引く）。
    - ``relative``: 数値の材料を、同じレースの馬と比べた値にした列も足すか。
    - ``sales``: セリの価格の列を足すか（``ability`` の表だけ）。
    - ``without``: 外す材料のまとまり（``ability`` の表だけ。効き目を見るため）。
    - ``params``: LightGBM の初期値に上書きする値。``models`` は ``lightgbm``・``catboost`` の組。2つなら確率を平均する。
    - ``first_day``: 学習に使う最初の開催日（None なら表の始まりから）。
    """

    key: str
    label: str
    source: str
    sets: tuple[str, ...]
    relative: bool = False
    sales: bool = False
    without: tuple[str, ...] = ()
    params: dict[str, object] = field(default_factory=dict)
    models: tuple[str, ...] = ("lightgbm",)
    first_day: date | None = None
