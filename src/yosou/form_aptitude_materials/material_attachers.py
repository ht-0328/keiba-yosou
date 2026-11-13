"""今のモデルの予測用データに足す材料（P・S・T・U・V）の部品を作って、1回の予測の中で使い回す。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from yosou.ability_score import RaceAbilityScoreAttacher
from yosou.development_score import AdvantageTableStore, RaceScoreAttacher, cache_folder_beside
from yosou.race_development.workflow import DevelopmentPaceWorkflow
from yosou.shared.workflow import DataAttachment, PaceSource
from yosou.track_bias import MemoizedPaceForecast, PriorSlopeTableStore, RaceBiasAttacher, bias_cache_folder_beside
from yosou.weight_table import RaceWeightDiscountAttacher, WeightTableStore, weight_cache_folder_beside


class MaterialAttachers:
    """予測用データに材料を足す関数（``PredictionWorkflow`` の ``pace``・``extras``・``win_extras`` に渡す形）を作る。
    ``yosou.shared.workflow`` の ``FormAptitudeMaterials`` を守る。

    - 展開の予想の結果 P: 保存した展開のモデル（``<置き場所>/models/``）で、そのレースの展開を予測する。
    - 展開スコア S: 保存した展開のモデルと表 G（展開の予想の置き場所の隣の ``展開スコア/cache/`` にとっておき、元DB が更新されていれば作り直す）。
    - 能力スコア T: 予測用データの能力指数と斤量から。
    - トラックバイアスの補正 U: 元DB の終わったレースの傾き（``トラックバイアス/cache/``）と、展開の予測④から。
    - 馬体重の表の割引 V: 表 W（``馬体重の表/cache/``）を予測用データの増減・日数・馬齢で引く。

    S と U の部品は作るのに時間がかかる（展開の予測を動かす）ので、1回の予測で1つだけ作り、3着以内と1着のモデルで使い回す。
    ``development_root`` は予想「展開から着順を予想」の置き場所（``reports/展開から着順を予想``）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, development_root: Path) -> None:
        self._con = con
        self._development_root = Path(development_root)
        self._score: RaceScoreAttacher | None = None
        self._bias: RaceBiasAttacher | None = None

    def pace(self) -> PaceSource:
        """P の元になる、そのレースの展開の予測を返す関数。"""
        workflow = DevelopmentPaceWorkflow(self._development_root / "models")
        return lambda race_id, timing, given: workflow.run(self._con, race_id, timing, given)

    def score(self) -> DataAttachment:
        """S を足す関数。"""
        if self._score is None:
            table = AdvantageTableStore(cache_folder_beside(self._development_root)).load(self._con)
            self._score = RaceScoreAttacher(self._con, self._development_root / "models", table)
        return self._score.attach

    def ability_score(self) -> DataAttachment:
        """T を足す関数。"""
        return RaceAbilityScoreAttacher().attach

    def bias(self) -> DataAttachment:
        """U を足す関数（展開の予測は、同じレースで1回だけ動かす）。"""
        if self._bias is None:
            slopes, table = PriorSlopeTableStore(bias_cache_folder_beside(self._development_root)).load(self._con)
            forecast = MemoizedPaceForecast(self._development_root / "models").run
            self._bias = RaceBiasAttacher(self._con, forecast, slopes, table)
        return self._bias.attach

    def weight_discount(self) -> DataAttachment:
        """V を足す関数。"""
        table = WeightTableStore(weight_cache_folder_beside(self._development_root)).load(self._con)
        return RaceWeightDiscountAttacher(table).attach

    def last_scores(self, race_id: str) -> pd.DataFrame | None:
        """S を足した予測のあとに、そのレースの展開スコアの表（予想のペースの確率を含む）。S を作っていなければ None。"""
        return self._score.last_scores(race_id) if self._score is not None else None
