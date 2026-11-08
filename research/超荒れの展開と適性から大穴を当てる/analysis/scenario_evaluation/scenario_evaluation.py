"""段3 の確かめの流れ: 予測を読み、比べる相手と並べ、並べ方・確率・組・抑えの買い目・危険な人気馬の表を作って書く。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import pandas as pd

from 共通 import render
from 共通.render import Table

from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_prediction_store import LongshotPredictionStore
from yosou.shared.feature import PredictionTiming

from ..scenario_forecast.scenario_material_source import ScenarioMaterialSource
from .band_logloss_table import BandLoglossTable
from .band_ranking_table import BandRankingTable
from .comparison_files import CURRENT, CURRENT_DANGER, WILD, WIN5_LONGSHOT, ComparisonFiles
from .danger_file_writer import DangerFileWriter
from .evaluation_frame import NEW, EvaluationFrame
from .favorite_out_table import FavoriteOutTable
from .hedge_settlement import HedgeSettlement
from .hedge_study import HedgeStudy
from .hedge_table import HedgeTable
from .mark_comparison_table import MarkComparisonTable
from .mark_ticket_file import MarkTicketFile
from .pair_calibration_table import PairCalibrationTable
from .pair_probability import PairProbability
from .popularity_band import FAVORITE, LONGSHOT, MIDDLE
from .race_weights_attacher import RaceWeightsAttacher

#: 比べる作り（展開の型を混ぜない同じ作り）の名前。
PLAIN = "展開の型を混ぜない"
_KEYS = ["レースID", "馬番"]


@dataclass(frozen=True)
class ScenarioEvaluation:
    """``root`` は reports/超荒れの展開と適性から大穴を当てる。``marks`` は道具「印の成績」の買い目の表（無ければ抑えの表を作らない）。
    ``mark_files`` は（消の決め方の名前 → 印の成績の買い目の表）。2つ以上あれば、券種ごとの的中率と回収率を並べる。"""

    root: Path
    timing: PredictionTiming
    marks: Path | None = None
    mark_files: dict[str, Path] = field(default_factory=dict)

    def frame(self) -> pd.DataFrame:
        store = LongshotPredictionStore(self.root / "predictions")
        top3, win = store.read("mixed-top3", self.timing.value), store.read("mixed-win", self.timing.value)
        frame = EvaluationFrame(top3, win, ComparisonFiles(self.timing).paths()).build()
        if store.exists("plain-top3", self.timing.value):
            plain = store.read("plain-top3", self.timing.value)
            plain = plain.loc[plain["期間"] == "テスト", [*_KEYS, "確率"]].astype({"レースID": str}).astype({"馬番": int})
            frame = frame.merge(plain.rename(columns={"レースID": "race_id", "馬番": "horse_no", "確率": f"p_top3_{PLAIN}"}),
                                on=["race_id", "horse_no"], how="left")
        danger = pd.read_pickle(CURRENT_DANGER)
        danger = danger.loc[danger["期間"] == "テスト", [*_KEYS, "確率"]].astype({"レースID": str}).astype({"馬番": int})
        frame = frame.merge(danger.rename(columns={"レースID": "race_id", "馬番": "horse_no", "確率": "out_current"}),
                            on=["race_id", "horse_no"], how="left")
        materials = ScenarioMaterialSource(self.root).load(self.timing)
        return RaceWeightsAttacher(materials).attach(frame)

    def write_danger_file(self) -> Path:
        """道具「印の成績」の ``--danger`` に渡す、新しい予想の 4着以下の確率の表を書く。"""
        top3 = LongshotPredictionStore(self.root / "predictions").read("mixed-top3", self.timing.value)
        table = DangerFileWriter(top3, pd.read_pickle(CURRENT_DANGER)).build()
        path = self.root / "predictions" / f"danger-{self.timing.value}.pkl"
        table.to_pickle(path)
        return path

    def sections(self, frame: pd.DataFrame, con: duckdb.DuckDBPyConnection | None) -> list[tuple[str, list[Table]]]:
        sources = (NEW, CURRENT, WILD, WIN5_LONGSHOT)
        ranking = [BandRankingTable(band, sources).build(frame, f"{band.name}が勝ったレースで、{band.name}の中の並べ方") for band in (LONGSHOT, MIDDLE)]
        loss_sources = (NEW, PLAIN, CURRENT, WILD, WIN5_LONGSHOT)
        losses = [BandLoglossTable((FAVORITE, MIDDLE, LONGSHOT), loss_sources).build(frame, target, f"確率の当たり具合（{label}）")
                  for target, label in (("top3", "3着以内"), ("win", "1着"))]
        frame = frame.assign(out_new=1 - frame[f"p_top3_{NEW}"], out_cur_top3=1 - frame[f"p_top3_{CURRENT}"])
        favorite_sources = {NEW: "out_new", "今の消（人気馬が4着以下になるかを予想）": "out_current", f"{CURRENT}（1 − 3着以内）": "out_cur_top3"}
        if f"p_top3_{PLAIN}" in frame:
            frame = frame.assign(out_plain=1 - frame[f"p_top3_{PLAIN}"])
            favorite_sources[PLAIN] = "out_plain"
        favorites = [FavoriteOutTable().build(frame, favorite_sources, "人気馬が4着以下になる確率")]
        pairs = self._pairs(frame)
        pair_tables = [PairCalibrationTable().build(pairs, "中穴・大穴2頭以上の確率と、中穴・大穴2頭の組")]
        sections = [("1. 中穴・大穴の並べ方（荒れる前提の確率）", ranking), ("2. 確率の当たり具合", losses),
                    ("3. 危険な人気馬（4着以下になる確率）", favorites), ("4. 中穴・大穴2頭の組の確率", pair_tables)]
        if len(self.mark_files) >= 2:
            sections.append(("6. 消の決め方を替えたときの印の成績（全券種）", [MarkComparisonTable(self.mark_files).build("券種ごとの的中率と回収率")]))
        if con is not None and self.marks is not None and self.marks.exists():
            market = pairs["市場（オッズから見た3着以内率）"][0]
            sections.append(("5. 抑えの買い目（本線に中穴・大穴2頭の組の 3連複を足す）", self._hedges(frame, pairs[NEW][0], market, con)))
        return sections

    def write(self, sections: list[tuple[str, list[Table]]]) -> Path:
        parts = [f"# 超荒れの展開と適性から大穴を当てる: 段3 の結果（{self.timing.label}）",
                 "テストの半年の行（区切りごとに、その半年より前で学んだモデルの予測）だけを数える。探索 = 2019〜2024年、確認 = 2025年から。"]
        for section, tables in sections:
            parts.append(f"## {section}")
            parts.extend(render.to_markdown(table) for table in tables)
        path = self.root / f"段3の結果-{self.timing.value}.md"
        path.write_bytes(("\n\n".join(parts) + "\n").encode("utf-8"))
        return path

    @staticmethod
    def _pairs(frame: pd.DataFrame) -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]:
        results = {NEW: PairProbability(("s_top3_0", "s_top3_1", "s_top3_2")).races(frame)}
        mixed = f"p_top3_{NEW}"
        results[f"{NEW}（展開の型ごとに分けず、混ぜた確率で）"] = PairProbability((mixed, mixed, mixed)).races(frame)
        results["市場（オッズから見た3着以内率）"] = PairProbability(("m_top3", "m_top3", "m_top3")).races(frame)
        return results

    def _hedges(self, frame: pd.DataFrame, races: pd.DataFrame, market: pd.DataFrame, con: duckdb.DuckDBPyConnection) -> list[Table]:
        marks = MarkTicketFile(self.marks)
        table = marks.frame()
        main = marks.main(table).merge(races[["race_id", "period"]], on="race_id", how="inner")
        favorites = marks.favorites(table)
        popular = frame.loc[frame["popularity"] <= 3].groupby("race_id")["horse_no"].apply(list)
        dates = pd.to_datetime(frame["race_date"])
        settlement = HedgeSettlement(HedgeSettlement.load(con, dates.min().date(), dates.max().date()))
        marked = races.loc[races["race_id"].isin(set(main["race_id"]))]
        candidates, chosen = HedgeStudy(marked, settlement).run(favorites, popular, main)
        shape, share = HedgeStudy.parse(chosen)
        market_marked = market.loc[market["race_id"].isin(set(main["race_id"]))]
        baseline = HedgeStudy(market_marked, settlement).fixed(shape, share, favorites, popular, main)
        everything = HedgeTable().build(candidates, main, "抑えの候補（線 × 組み方）")
        selected = HedgeTable().build({f"{chosen}（探索の期間で選んだもの）": candidates[chosen],
                                       f"{shape}・上位{int(share * 100)}%を市場の組の確率で選んだもの（比べる基準）": baseline},
                                      main, "選んだ抑え（市場の組の確率で同じ買い方をしたものと比べる）")
        return [selected, everything]
