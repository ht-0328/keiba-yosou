"""evaluate: 学習に使っていない期間の重賞で、買い方の成績を確かめる。"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from 共通 import db
from 共通.render import Table

from yosou.form_aptitude_top3.command.figure_cache_argument import FigureCacheArgument
from yosou.shared.command import CommonArguments
from yosou.shared.dataset import DatasetBuilder, TrainingData, TrainingPeriod
from yosou.shared.dataset import column_names as names
from yosou.shared.evaluation.value_bands import ValueBands
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.odds import TOP2_RATE, TOP3_RATE
from yosou.shared.place_value import PlaceHitProbability, PlacePriceEstimator
from yosou.shared.repository import PlacePriceRepository
from yosou.shared.workflow import ModelSegments, SegmentedHoldoutPrediction

from ..dataset import ability_dataset_builder, race_day_dataset_builder
from ..workflow import ABILITY_TIMINGS
from .train_command import TEST_FIRST_DAY, TRAIN_FIRST_DAY, VALID_FIRST_DAY
from .yosou_name import YOSOU_NAME

#: 「期待値がこれ以上なら買う」の線の候補。表に1行ずつ出す。
VALUE_LINES: tuple[float, ...] = (1.0, 1.1, 1.2)


class EvaluateCommand:
    """``evaluate``: 保存したモデルで、学習に使っていない期間（検証・テスト）の重賞を予測し直し、
    「複勝を期待値で買ったときの回収率」（期待値の帯別と、線ごとの合計）と、
    「モデルの本命と1番人気の比べ方」（1番人気を疑えているか）を出す（設計書 16）。

    期間の区切りは ``train`` と同じ引数で、既定も同じ。学習と同じ区切りで実行しないと、
    学習に使った行を「学習に使っていない」として測ってしまうので、``train`` と同じ引数で使う。
    学習データは、測る時点のモデルの材料（木曜・前日は馬の力の材料＋K、当日は当日の材料＋K）で作る。
    """

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(
            "evaluate", help="学習に使っていない期間の重賞で、複勝の期待値買いと本命の成績を出す", allow_abbrev=False,
        )
        parser.add_argument(
            "--timing", type=PredictionTiming.parse, default=PredictionTiming.RACE_DAY,
            help="測る時点（既定: 当日。期待値は確定オッズで計算する）",
        )
        group = parser.add_argument_group("学習データの期間（train と同じ値にする）")
        group.add_argument("--warmup-from", type=_iso_date, default=None, help="train と同じ")
        group.add_argument("--train-from", type=_iso_date, default=TRAIN_FIRST_DAY, help="train と同じ")
        group.add_argument("--valid-from", type=_iso_date, default=VALID_FIRST_DAY, help="train と同じ")
        group.add_argument("--test-from", type=_iso_date, default=TEST_FIRST_DAY, help="train と同じ")
        FigureCacheArgument().add_to(parser)
        CommonArguments(YOSOU_NAME).add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        period = TrainingPeriod.starting(
            args.train_from, args.valid_from, args.test_from, warmup_first_day=args.warmup_from,
        )
        with db.open_db(args.db) as con:
            data = self._dataset_builder(con, args.timing, args.figure_cache).build_training_data(period)
        predictor = SegmentedHoldoutPrediction(ModelSegments(), args.models)
        estimator = self._place_price(args)
        tables: list[Table] = []
        for name, part in (("検証", data.between(args.valid_from, args.test_from)),
                           ("テスト", data.between(args.test_from, None))):
            if len(part) == 0:
                continue
            probability = predictor.predict(part, args.timing)
            tables.extend(self._period_tables(name, part, probability, estimator))
        if not tables:
            raise LookupError("検証・テストの期間に重賞の行がありません（--valid-from・--test-from を確かめてください）")
        return tables

    def _dataset_builder(self, con: duckdb.DuckDBPyConnection, timing: PredictionTiming, figure_cache: Path) -> DatasetBuilder:
        """測る時点のモデルの材料の組み立て（``train`` と同じ分け方）。"""
        if timing in ABILITY_TIMINGS:
            return ability_dataset_builder(con, figure_cache)
        return race_day_dataset_builder(con, figure_cache)

    def _place_price(self, args: argparse.Namespace) -> PlacePriceEstimator:
        state = PlacePriceRepository(args.models).load()
        if state is None:
            raise FileNotFoundError(f"複勝の見込みの倍率がありません。先に train を実行してください: {args.models}")
        return PlacePriceEstimator.from_state(state)

    def _period_tables(self, period_name: str, part: TrainingData, probability: pd.Series,
                       estimator: PlacePriceEstimator) -> list[Table]:
        evaluation = part.evaluation
        hit_probability = PlaceHitProbability().of(
            probability, evaluation[names.FIELD_SIZE], evaluation[TOP2_RATE], evaluation[TOP3_RATE])
        price = estimator.estimate(evaluation[names.PLACE_ODDS_LOW])
        value = hit_probability * price
        payout = evaluation[names.PLACE_PAYOUT]
        races = part.ids[names.RACE_ID].nunique()
        bands = ValueBands()
        band_table = bands.table(value, hit_probability, payout)
        lines = [self._line_row(bands, value, hit_probability, payout, line) for line in VALUE_LINES]
        return [
            Table(list(band_table.columns), band_table.values.tolist(),
                  title=f"{period_name}データ（{races} レース）: 複勝の期待値の帯ごとの成績",
                  note="期待値 1 で元返し。「実際の的中率」と「回収率」が「予想の的中率」「期待値の平均」と近いほど、確率と倍率が合っている。"),
            Table(["買う線（期待値）", "点数", "期待値の平均", "予想の的中率", "実際の的中率", "回収率"], lines,
                  title=f"{period_name}データ: 期待値が線以上の複勝を全部 100円ずつ買ったとき"),
            self._favorite_table(period_name, part, probability),
        ]

    def _line_row(self, bands: ValueBands, value: pd.Series, hit_probability: pd.Series,
                  payout: pd.Series, line: float) -> list[object]:
        summary = bands.at_least(value, hit_probability, payout, line)
        return [f"{line:.1f} 以上", *summary.values()]

    def _favorite_table(self, period_name: str, part: TrainingData, probability: pd.Series) -> Table:
        """モデルの本命（確率1位）と1番人気の比べ方。1番人気を疑えているかを見る。"""
        frame = pd.DataFrame({
            "race_id": part.ids[names.RACE_ID].to_numpy(), "probability": probability.to_numpy(),
            "finish": pd.to_numeric(part.evaluation[names.FINISH], errors="coerce").to_numpy(),
            "popularity": pd.to_numeric(part.evaluation[names.POPULARITY], errors="coerce").to_numpy(),
            "place_payout": pd.to_numeric(part.evaluation[names.PLACE_PAYOUT], errors="coerce").fillna(0.0).to_numpy(),
        })
        picks = frame.loc[frame.groupby("race_id")["probability"].idxmax()]
        favorites = frame[frame["popularity"] == 1]
        differs = picks[picks["popularity"] != 1]
        rows = [
            self._pick_row("モデルの本命（確率1位）", picks),
            self._pick_row("1番人気（市場の本命）", favorites),
            self._pick_row("本命が1番人気でないレースの、その本命", differs),
        ]
        return Table(["1頭の選び方", "レース数", "3着以内率", "複勝回収率"], rows,
                     title=f"{period_name}データ: モデルの本命と1番人気",
                     note="3行目が「1番人気を疑って別の馬を選んだ」ケース。ここの回収率が高いほど、疑いが当たっている。")

    def _pick_row(self, label: str, picks: pd.DataFrame) -> list[object]:
        if len(picks) == 0:
            return [label, 0, "―", "―"]
        place_rate = (picks["finish"] <= 3).mean() * 100
        roi = picks["place_payout"].mean()
        return [label, len(picks), f"{place_rate:.1f}%", f"{roi:.1f}%"]


def _iso_date(text: str) -> date:
    return date.fromisoformat(text)
