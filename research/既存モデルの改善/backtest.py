"""直した予想を組み合わせた買い方を、過去のレースで確かめる（研究「既存モデルの改善」の入口⑤）。

    uv run python research/既存モデルの改善/backtest.py
    uv run python research/既存モデルの改善/backtest.py --windows 2025年後半   # 1つの区切りだけ試す

先に walk_forward.py で、3つの予想（全頭・穴馬・人気馬）の変更版（improved）の予測を作っておく。
区切りごとに、検証期間（テストの直前の半年）で勝率の出し方と券種ごとの買い方を決め、テスト期間で買う。
出すもの: reports/既存モデルの改善/backtest/結果.md（表）と、買った買い目・参考の買い目・選んだ買い方の CSV。
元DB は、区切りごとに券種ごとの確定オッズと払戻を読む間だけ開く。
"""

from __future__ import annotations

import sys
from datetime import timedelta
from itertools import chain
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db, render  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.shared.dataset import RACE_DATE  # noqa: E402
from yosou.shared.dataset.column_names import PLACE_ODDS_LOW, PLACE_PAYOUT  # noqa: E402
from yosou.shared.place_value import PlacePriceEstimator  # noqa: E402

from 馬券の買い方の検証.analysis.ticket import TicketType  # noqa: E402

from 既存モデルの改善.analysis.betting import (  # noqa: E402
    BacktestSummary,
    PayoutTable,
    RuleChooser,
    WindowBacktest,
)
from 既存モデルの改善.analysis.betting.wide_price_history import LOWEST_ODDS, PAYOUT_YEN, WidePriceHistory  # noqa: E402
from 既存モデルの改善.analysis.combined import HorseTableBuilder, RaceProbabilityBuilder, StrengthFeatures  # noqa: E402
from 既存モデルの改善.analysis.combined.strength_features import SHIFT_COLUMNS  # noqa: E402
from 既存モデルの改善.analysis.market import CombinationTableReader  # noqa: E402
from 既存モデルの改善.analysis.tables import TableStore, spec_named  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS, TestWindow, window_named  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_TABLES = _REPO_ROOT / "reports" / "既存モデルの改善" / "tables"
_DEFAULT_PREDICTIONS = _REPO_ROOT / "reports" / "既存モデルの改善" / "predictions"
_DEFAULT_RESULTS = _REPO_ROOT / "reports" / "既存モデルの改善" / "backtest"
#: 組み合わせる3つの予想と、その作り方（変更版）。
_HORSE_MODELS = ("form_aptitude_top3", "longshots_in_top3", "favorites_out_of_top3")
_VARIANT = "improved"
#: ワイドの見込みの倍率を決めるのに使う、検証期間の前の日数（2年）。
_WIDE_HISTORY_DAYS = 730


def main(args) -> None:
    form_spec = spec_named("form_aptitude_top3")
    form = TableStore(args.tables).read(form_spec.name, form_spec.catalog)
    store = PredictionStore(args.predictions)
    predictions = {name: store.read(name, args.variant) for name in _HORSE_MODELS}
    backtest = WindowBacktest(HorseTableBuilder(form, predictions),
                              RaceProbabilityBuilder(StrengthFeatures(SHIFT_COLUMNS[args.shifts])), RuleChooser())
    history = pd.concat([form.ids, form.evaluation], axis=1)
    windows = [window_named(name) for name in args.windows] if args.windows else list(WINDOWS)
    results = [_window(backtest, history, window, args) for window in windows]
    summary = BacktestSummary(
        pd.concat([result.bought for result in results], ignore_index=True),
        pd.concat([result.reference for result in results], ignore_index=True),
        pd.DataFrame(list(chain.from_iterable(result.choices for result in results))),
        pd.DataFrame([result.fit for result in results]),
        _test_races(history, windows),
    )
    _write(results, summary.tables(), args)


def _window(backtest: WindowBacktest, history: pd.DataFrame, window: TestWindow, args):
    print(f"買い方の検証 / {window.name}: 確定オッズと払戻を読んでいます …", file=sys.stderr, flush=True)
    wide_first = window.valid_first_day - timedelta(days=_WIDE_HISTORY_DAYS)
    with db.open_db(args.db) as con:
        reader = CombinationTableReader(con)
        tables = {ticket: reader.read(ticket, window.valid_first_day, window.test_last_day) for ticket in TicketType}
        payouts = PayoutTable(con).read(window.valid_first_day, window.test_last_day)
        wide = WidePriceHistory(con).read(wide_first, window.valid_first_day - timedelta(days=1))
    before = history[history[RACE_DATE] < pd.Timestamp(window.valid_first_day)]
    prices = {
        TicketType.PLACE: PlacePriceEstimator().fit(before[PLACE_ODDS_LOW], before[PLACE_PAYOUT].fillna(0.0)),
        TicketType.WIDE: PlacePriceEstimator().fit(wide[LOWEST_ODDS], wide[PAYOUT_YEN]),
    }
    print(f"買い方の検証 / {window.name}: 買い目を作っています …", file=sys.stderr, flush=True)
    return backtest.run(window, tables, payouts, prices)


def _test_races(history: pd.DataFrame, windows: list[TestWindow]) -> pd.DataFrame:
    """区切りのテスト期間の全出走（対象レース数と人気を引くのに使う）。"""
    days = history[RACE_DATE]
    inside = pd.Series(False, index=history.index)
    for window in windows:
        inside |= (days >= pd.Timestamp(window.test_first_day)) & (days <= pd.Timestamp(window.test_last_day))
    return history[inside]


def _write(results, tables: list[Table], args) -> None:
    args.results.mkdir(parents=True, exist_ok=True)
    (args.results / "結果.md").write_text(render.render(tables, "markdown"), encoding="utf-8")
    pd.concat([result.bought for result in results]).to_csv(args.results / "買った買い目.csv", index=False, encoding="utf-8-sig")
    pd.concat([result.reference for result in results]).to_csv(args.results / "参考の買い目.csv", index=False, encoding="utf-8-sig")
    cli.emit(tables, args)


def _parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--windows", nargs="*", default=None, metavar="区切り", help="回す区切り（省略すると7つ全部）")
    parser.add_argument("--variant", default=_VARIANT, help="使う予測の作り方（既定: improved = 変更版）")
    parser.add_argument("--shifts", default="3つの予想", choices=list(SHIFT_COLUMNS), help="勝率の材料（既定: 3つの予想）")
    parser.add_argument("--tables", type=Path, default=_DEFAULT_TABLES, help="学習データの表の置き場所")
    parser.add_argument("--predictions", type=Path, default=_DEFAULT_PREDICTIONS, help="予測の表の置き場所")
    parser.add_argument("--results", type=Path, default=_DEFAULT_RESULTS, help="結果を書く場所")
    return parser


if __name__ == "__main__":
    cli.run(_parser(), main)
