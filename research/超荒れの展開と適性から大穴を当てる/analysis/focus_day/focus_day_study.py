"""詳しく見る日の研究の流れ: 学び直し → その日の予測用データ → 予想と順位 → 馬名と結果を足す → 表と CSV を書く。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from 共通 import render

from yosou.form_aptitude_materials import MaterialAttachers
from yosou.form_aptitude_win5_tickets.command.form_models_argument import DEFAULT_FORM_MODELS
from yosou.shared.command.development_root_argument import DEFAULT_DEVELOPMENT_ROOT
from yosou.shared.feature import PredictionTiming
from yosou.shared.setting import HyperparameterSettings
from yosou.shared.workflow import FormAptitudePrediction

from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_data import HORSE_NO, RACE_ID
from WIN5で人気薄の勝ち馬を狙う.analysis.repository import Win5LegRepository

from ..repository import RunnerFactsRepository
from ..scenario_evaluation.pair_probability import PairProbability
from ..scenario_forecast.scenario_dataset import ScenarioDataset
from ..scenario_forecast.scenario_material_source import ScenarioMaterialSource
from ..scenario_forecast.scenario_variant import variant_named
from ..scenario_forecast.scenario_window_trainer import ScenarioWindowTrainer
from .contribution_lightgbm import ContributionLightGbm
from .day_pace_forecast import DayPaceForecast
from .focus_day_data import FocusDayData
from .focus_day_report import FocusDayReport
from .focus_day_runner import FINAL_WINDOW, FocusDayRunner

#: 注目の馬（WIN5 の何レース目の勝ち馬か）。
FOCUS_LEGS: tuple[int, ...] = (1, 4)


@dataclass(frozen=True)
class FocusDayStudy:
    """``root`` は reports/超荒れの展開と適性から大穴を当てる。当日の時点で予想する。"""

    root: Path
    settings: HyperparameterSettings
    threads: int
    tables: Path

    def run(self, con: duckdb.DuckDBPyConnection, race_date: str) -> Path:
        timing = PredictionTiming.RACE_DAY
        materials = ScenarioMaterialSource(self.root).load(timing)
        dataset = ScenarioDataset(materials, self.tables)
        trainer = ScenarioWindowTrainer(self.settings, self.threads, ContributionLightGbm)
        members, columns, categorical = {}, {}, {}
        for target, key in (("top3", "mixed-top3"), ("win", "mixed-win")):
            data = dataset.build(timing, variant_named(key))
            fitted, weights, _ = trainer.fit(data, FINAL_WINDOW)
            members[target] = (fitted, weights)
            columns[target], categorical[target] = list(data.features.columns), data.categorical
        runner = FocusDayRunner(members)
        race_ids = list(runner.race_ids(materials, race_date))
        prediction = FormAptitudePrediction(DEFAULT_FORM_MODELS, lambda c: MaterialAttachers(c, DEFAULT_DEVELOPMENT_ROOT))
        pace_races, pace_horses = DayPaceForecast().predict(con, race_ids, timing)
        focus, current = FocusDayData(prediction, materials, columns, categorical, pace_races, pace_horses).build(con, race_ids, timing)
        horses = self._with_facts(runner.ranks(runner.table(focus), current), con, race_date)
        pairs, _ = PairProbability(("s_top3_0", "s_top3_1", "s_top3_2")).races(self._pair_frame(horses))
        report = FocusDayReport(horses, pairs)
        tables = [report.focus(self._picks(con, race_date, horses), f"{race_date} の注目の馬"),
                  report.races(f"{race_date} の全レース")]
        path = self.root / f"段3の詳しく見る日-{race_date}.md"
        parts = [f"# 超荒れの展開と適性から大穴を当てる: {race_date} の予想（当日の時点）",
                 "最後の区切り（学習の表の最後の日 2026-10-12 まで）で学び直したモデルで予想した。予想のペースと位置の確率は、"
                 "予想「展開から着順を予想」の学習済みモデルでその日に予測した値。その日の先のレースの傾きは、傾きの表がその日まで無いので使っていない。",
                 *[render.to_markdown(table) for table in tables]]
        path.write_bytes(("\n\n".join(parts) + "\n").encode("utf-8"))
        horses.to_csv(self.root / f"段3の詳しく見る日-{race_date}.csv", index=False, encoding="utf-8-sig")
        return path

    @staticmethod
    def _with_facts(horses: pd.DataFrame, con: duckdb.DuckDBPyConnection, race_date: str) -> pd.DataFrame:
        facts = RunnerFactsRepository(con).load(date.fromisoformat(race_date))
        facts = facts.loc[facts["race_date"] == race_date, ["race_id", "horse_no", "horse_name", "finish", "popularity", "race_name"]]
        facts = facts.rename(columns={"race_id": RACE_ID, "horse_no": HORSE_NO, "popularity": "final_popularity"})
        return horses.merge(facts.astype({RACE_ID: str}).astype({HORSE_NO: int}), on=[RACE_ID, HORSE_NO], how="left")

    @staticmethod
    def _pair_frame(horses: pd.DataFrame) -> pd.DataFrame:
        return horses.rename(columns={RACE_ID: "race_id", HORSE_NO: "horse_no"}).assign(
            y_top3=(horses["finish"] <= 3).astype(float), period="")

    @staticmethod
    def _picks(con: duckdb.DuckDBPyConnection, race_date: str, horses: pd.DataFrame) -> list[tuple[str, str, int]]:
        legs = Win5LegRepository(con).load(date.fromisoformat(race_date))
        legs = legs.loc[legs["race_date"] == race_date]
        picks = []
        for leg in FOCUS_LEGS:
            found = legs.loc[legs["leg"] == leg, "race_id"]
            if found.empty:
                continue
            race_id = str(found.iloc[0])
            winner = horses.loc[(horses[RACE_ID] == race_id) & (horses["finish"] == 1), HORSE_NO]
            if not winner.empty:
                picks.append((f"WIN5 の{leg}レース目の勝ち馬", race_id, int(winner.iloc[0])))
        return picks
