"""predict: WIN5 の日を予測する。"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import date

from 共通 import db
from 共通.render import Table

from yosou.form_aptitude_materials import MaterialAttachers
from yosou.shared.command import CommonArguments, DevelopmentRootArgument, FigureCacheArgument
from yosou.shared.workflow import FormAptitudePrediction

from ..formation import (
    DEFAULT_MIN_VALUE,
    DEFAULT_ORDERING,
    FAVORITE_PRODUCT_LINE,
    JUDGE_BUDGET,
    LARGE_BUDGET,
    SMALL_BUDGET,
    BudgetTiers,
    FormationSearch,
    FormationValue,
    LegOrdering,
)
from ..leg import LegWinPredictor
from ..payout import PayoutEstimator
from ..repository import PayoutEstimatorRepository, Win5ForecastRecordRepository
from ..workflow import Win5PredictionWorkflow
from .form_models_argument import FormModelsArgument
from .win5_forecast_tables import Win5ForecastTables
from .yosou_name import YOSOU_NAME

#: 今のモデルの予測を作る関数（引数 → ``FormAptitudePrediction``）。テストは学習済みモデルの代わりを渡す。
PredictionFactory = Callable[[argparse.Namespace], FormAptitudePrediction]


class PredictCommand:
    """``predict``: WIN5 の日を予測する（設計書 05 の図2）。保存した配当の見積もりの式を読み、段階の予算（判断用・少なく買う日・多く買う日の
    予算と多く買う日の線。既定は ``formation/buying_defaults.py``）と買う日の線を ``Win5PredictionWorkflow`` に渡す。
    結果は ``Win5ForecastRecordRepository`` で ``記録/<開催日>.json`` に自動で記録し、日のまとめ・買う買い目・対象レースごとの
    全頭の表・予算の候補ごとの表を返す。

    今のモデルの予測は、道具「今週の予想」と同じ ``FormAptitudePrediction`` に、材料を作る部品 ``MaterialAttachers`` を渡して行う。
    ``prediction_factory`` を渡すと、その関数で作った予測を使う（テストが学習済みモデルの代わりを渡す）。
    """

    def __init__(self, prediction_factory: PredictionFactory | None = None) -> None:
        self._prediction_factory = prediction_factory or self._form_prediction

    def add_parser(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser("predict", help="WIN5 の日の買い目と、買う（多く・少なく）か見送りかを出す", allow_abbrev=False)
        parser.add_argument("--date", type=date.fromisoformat, default=None, help="WIN5 の開催日（YYYY-MM-DD。省略すると今日）")
        parser.add_argument("--judge-budget", type=int, default=JUDGE_BUDGET,
                            help=f"判断用の買い目の予算（点数。この買い目の日の期待値で買うか見送りかを決める。既定: {JUDGE_BUDGET}）")
        parser.add_argument("--min-value", type=float, default=DEFAULT_MIN_VALUE,
                            help=f"買う日の線（判断用の買い目の日の期待値がこの値以上なら買う。既定: {DEFAULT_MIN_VALUE}）")
        parser.add_argument("--small-budget", type=int, default=SMALL_BUDGET,
                            help=f"少なく買う日の予算（点数。見送りの日もこの予算の買い目を参考に出す。既定: {SMALL_BUDGET}）")
        parser.add_argument("--large-budget", type=int, default=LARGE_BUDGET, help=f"多く買う日の予算（点数。既定: {LARGE_BUDGET}）")
        parser.add_argument("--favorite-product-line", type=float, default=FAVORITE_PRODUCT_LINE,
                            help=f"多く買う日の線（本命の確率の積がこの値以上なら多く買う。既定: {FAVORITE_PRODUCT_LINE}）")
        parser.add_argument("--ordering", type=LegOrdering.parse, default=DEFAULT_ORDERING,
                            help=f"各レースの馬を選ぶ順: 上乗せの順・1着の確率の順（既定: {DEFAULT_ORDERING.label}）")
        FormModelsArgument().add_to(parser)
        FigureCacheArgument().add_to(parser)
        DevelopmentRootArgument().add_to(parser)
        CommonArguments(YOSOU_NAME, models_folder="").add_to(parser)
        parser.set_defaults(handler=self.run)

    def run(self, args: argparse.Namespace) -> list[Table]:
        race_date = args.date or date.today()
        tiers = BudgetTiers(args.judge_budget, args.small_budget, args.large_budget, args.favorite_product_line)
        estimator = PayoutEstimator.from_dict(PayoutEstimatorRepository(args.models).load())
        search = FormationSearch(args.ordering, FormationValue(estimator))
        predictor = LegWinPredictor(self._prediction_factory(args))
        with db.open_db(args.db) as con:
            forecast = Win5PredictionWorkflow(con, predictor, search, estimator.count).run(race_date, tiers, args.min_value)
        Win5ForecastRecordRepository(args.models).save(forecast.to_dict(), race_date)
        return Win5ForecastTables(forecast).tables()

    def _form_prediction(self, args: argparse.Namespace) -> FormAptitudePrediction:
        """今のモデルの学習済みモデルで予測する部品。置き場所が無ければ ``FileNotFoundError``（今のモデルの ``train`` を案内する）。"""
        if not args.form_models.exists():
            raise FileNotFoundError(
                f"今のモデルの学習済みモデルがありません: {args.form_models}\n"
                "`uv run python -m yosou.form_aptitude_top3 train` で今のモデルを学んでください"
            )
        return FormAptitudePrediction(args.form_models, lambda con: MaterialAttachers(con, args.development_root), args.figure_cache)
