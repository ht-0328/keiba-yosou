"""組の確率の直しの研究の流れ: 全部の組に確定オッズ・市場の確率・的中を付け、最初の年で直しを当てはめ、年ごとに
（1）係数と「直した期待値が線以上の組」の割合（2）直した期待値で買ったときの成績 を出す。

3連単は 1着の確率、3連複は 1着の確率と 3着以内に合わせた勝つ力 で組の確率を出す。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from 共通.render import Table

from ..case_report import CaseReport
from ..popularity_band import PopularityBand
from ..repository import TrifectaOddsRepository, TrifectaResultRepository, TrioOddsRepository, TrioResultRepository
from ..runner_enrichment import RunnerEnrichment
from .combo_calibration import COEFFICIENTS, ComboCalibration
from .combo_market import MARKET, ComboMarket
from .fitted_strength import Top3FittedStrength
from .harville_combos import HarvilleCombos
from .prediction_repository import P1, P3, PredictionRepository
from .simulator import RESULT_COLUMNS, TrifectaSimulator
from .strategy import STRENGTH_TOP3_FIT, STRENGTH_WIN, TRIFECTA, TRIO
from .ticket_plan import TICKET_COLUMNS

_KEYS = ["race_id", "first", "second", "third"]
_STRENGTH_LABELS = {STRENGTH_WIN: "1着の確率", STRENGTH_TOP3_FIT: "3着以内に合わせた勝つ力"}
#: 組の確率の出し方（券種 × 勝つ力）。
SUBJECTS: tuple[tuple[str, str], ...] = ((TRIFECTA, STRENGTH_WIN), (TRIO, STRENGTH_WIN), (TRIO, STRENGTH_TOP3_FIT))
SHARE_COLUMNS: tuple[str, ...] = ("券種", "勝つ力", "年", "組の数", "直した期待値 1.0 以上の組", "割合", "直した期待値 1.1 以上の組", *COEFFICIENTS)


@dataclass(frozen=True)
class CalibrationStudySettings:
    """期間・予測の表の置き場所・当てはめる年・買うときの線。"""

    test_from: date
    predictions: Path
    fit_year: int
    lines: tuple[float, ...] = (1.0, 1.1, 1.2)
    max_points: int = 30
    min_heads: int = 11
    popularity: PopularityBand = PopularityBand()
    report_name: str = "組の確率の直し"


@dataclass(frozen=True)
class CalibrationStudy:
    con: duckdb.DuckDBPyConnection
    settings: CalibrationStudySettings

    def run(self, out_dir: Path) -> Path:
        s = self.settings
        runners = self._runners()
        races = runners.groupby("race_id")[["race_date"]].first()
        races["period"] = pd.to_datetime(races["race_date"]).dt.year.astype(str) + "年"
        ids = races.index.to_series()
        odds = {TRIFECTA: TrifectaOddsRepository(self.con).load(ids), TRIO: TrioOddsRepository(self.con).load(ids)}
        results = {TRIFECTA: TrifectaResultRepository(self.con).load(), TRIO: TrioResultRepository(self.con).load()}
        share_rows, result_rows = [], []
        for ticket, strength in SUBJECTS:
            table = self._table(runners, races, ticket, strength, odds[ticket], results[ticket])
            fit = table["period"] == f"{s.fit_year}年"
            beta = ComboCalibration().fit(table.loc[fit, "probability"], table.loc[fit, MARKET], table.loc[fit, "hit"])
            table["calibrated"] = ComboCalibration().apply(beta, table["probability"], table[MARKET])
            table["ev"] = table["calibrated"] * table["odds"]
            label = f"{ticket}／{_STRENGTH_LABELS[strength]}"
            share_rows.extend(self._share_rows(ticket, strength, table, beta))
            simulator = TrifectaSimulator(results[ticket])
            for line in s.lines:
                chosen = self._choose(table, line)
                settled = simulator.settle(chosen, races.reset_index())
                result_rows.extend(simulator.summarize_by_year(f"{label}／直した期待値 {line} 以上・{s.max_points}点まで", settled, races.reset_index()))
        tables = [
            Table.from_records(share_rows, SHARE_COLUMNS, title="1. 直しの係数と、直した期待値が線以上の組の割合",
                               note=f"直しは {s.fit_year}年の全部の組（{s.min_heads}頭以上）で当てはめ、ほかの年にそのまま使う。log p の係数が 1・log m の係数が 0 なら予想の組の確率がそのまま正しい。"),
            Table.from_records(result_rows, RESULT_COLUMNS, title="2. 直した期待値で買ったときの年ごとの成績",
                               note="買い目は、直した期待値が線以上の組を期待値の高い順に 1レースの上限まで（帯の役や型は使わない）。的中の実際÷見込み は直した確率で見る。"),
        ]
        intro = (f"対象: {s.test_from} 以降の地方の確定レース（{s.min_heads}頭以上。全頭の予想の当日の予測があるもの）。"
                 f"組の確率を「当たった／外れた」で直す（ロジスティック回帰: 的中 ~ log(予想の組の確率) + log(市場の組の確率)）。{s.fit_year}年で当てはめ、ほかの年で確かめる。")
        return CaseReport(out_dir).write(s.report_name, f"地方の万馬券: {s.report_name}", intro, tables)

    def _runners(self) -> pd.DataFrame:
        s = self.settings
        rows = RunnerEnrichment(self.con, s.test_from, s.min_heads, s.popularity).load()
        predictions = PredictionRepository(s.predictions / "race_day.pkl", s.predictions / "race_day-1着.pkl").load()
        predictions = predictions.drop_duplicates(["race_id", "horse_no"], keep="last")
        rows = rows.merge(predictions, on=["race_id", "horse_no"], how="inner")
        return rows.assign(race_id=rows["race_id"].astype("int64"))

    def _table(self, runners: pd.DataFrame, races: pd.DataFrame, ticket: str, strength: str, odds: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
        """全部の組に、予想の組の確率・市場の組の確率・オッズ・的中・年 を付けた表。"""
        power = runners[P1] if strength == STRENGTH_WIN else Top3FittedStrength().fit(runners["race_id"], runners[P1], runners[P3])
        horses = runners.assign(strength=power)[["race_id", "horse_no", "strength"]]
        combos = HarvilleCombos().all_races(horses, trio=(ticket == TRIO))
        table = combos.merge(ComboMarket().attach(odds)[_KEYS + ["odds", MARKET]], on=_KEYS, how="inner")
        table = table.merge(results[_KEYS + ["payout"]], on=_KEYS, how="left")
        table["hit"] = table["payout"].fillna(0).gt(0).astype(float)
        table["period"] = table["race_id"].map(races["period"])
        return table.drop(columns=["payout"])

    def _share_rows(self, ticket: str, strength: str, table: pd.DataFrame, beta: np.ndarray) -> list[dict]:
        rows = []
        for period, group in table.groupby("period", sort=True):
            above = int((group["ev"] >= 1.0).sum())
            rows.append({"券種": ticket, "勝つ力": _STRENGTH_LABELS[strength], "年": period, "組の数": len(group),
                         "直した期待値 1.0 以上の組": above, "割合": f"{above / len(group):.3%}",
                         "直した期待値 1.1 以上の組": int((group["ev"] >= 1.1).sum()),
                         **{name: round(float(value), 3) for name, value in zip(COEFFICIENTS, beta)}})
        return rows

    def _choose(self, table: pd.DataFrame, line: float) -> pd.DataFrame:
        """直した期待値が線以上の組を、期待値の高い順に 1レースの上限まで。買い目の表の形（確率は直した確率）にする。"""
        chosen = table[table["ev"] >= line].sort_values(["race_id", "ev"], ascending=[True, False]).groupby("race_id").head(self.settings.max_points)
        chosen = chosen.assign(probability=chosen["calibrated"], pattern="—")
        return chosen[list(TICKET_COLUMNS)].reset_index(drop=True)
