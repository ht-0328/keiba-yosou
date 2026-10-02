"""予測の結果を表にする。"""

import pandas as pd

from 共通.render import Table

from ..setting import ModelSettings


class PredictionTable:
    """``PredictionWorkflow.run()`` の結果（確率の高い順）を、そのままの列の並びで表にする。対象がいなければ「対象なし」。"""

    def __init__(self, settings: ModelSettings) -> None:
        self._settings = settings

    def table(self, result: pd.DataFrame) -> Table:
        settings = self._settings
        # pandasの欠損値を、CSV・JSONでも扱えるNoneへそろえる。
        records = result.astype(object).where(result.notna(), None).to_dict(orient="records")
        return Table.from_records(records, columns=list(result.columns), title="予想" if len(result) else "対象なし", note=(
            f"目的: {settings.target} / 時点: {settings.timing.label} / 特徴量: {len(settings.selected)}項目。"
            "人気は今回取得・指定した値。木曜の想定人気は実際の発売後の人気とは異なります。"
            "期待値は、勝利なら確率×単勝オッズ、馬券内・馬券外なら3着以内の確率×複勝の想定払戻倍率（今のオッズで計算。オッズは締め切りまで動く）。"
        ))
