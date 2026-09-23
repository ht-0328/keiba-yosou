"""荒れ具合を、馬ごとの着順の確率から計算で出す（研究「既存モデルの改善」の入口③）。

    uv run python research/既存モデルの改善/upset_calc.py
    uv run python research/既存モデルの改善/upset_calc.py --windows 2025年後半   # 1つの区切りだけ試す

先に walk_forward.py で、3つの予想（全頭・穴馬・人気馬）の変更版（improved）の予測を作っておく。
出すもの: reports/既存モデルの改善/predictions/upset_level/ の calc_market.pkl（オッズだけの勝率から計算）と
calc_model.pkl（3つの予想を組み合わせた勝率から計算）、calc-fit.csv（区切りごとの材料の重みと Stern の補正）。
元DB は、区切りごとにテスト期間の券種ごとの確定オッズを読む間だけ開く。
"""

from __future__ import annotations

import sys
from itertools import chain
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.upset_level.dataset import BetType, UpsetLevelRule  # noqa: E402

from 馬券の買い方の検証.analysis.ticket import TicketType  # noqa: E402

from 既存モデルの改善.analysis.combined import HorseTableBuilder, RaceProbabilityBuilder, StrengthFeatures  # noqa: E402
from 既存モデルの改善.analysis.combined.strength_features import SHIFT_COLUMNS  # noqa: E402
from 既存モデルの改善.analysis.market import CombinationTableReader  # noqa: E402
from 既存モデルの改善.analysis.tables import TableStore, spec_named  # noqa: E402
from 既存モデルの改善.analysis.upset import UpsetCalculationRunner, UpsetClassCalculator  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS, window_named  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_TABLES = _REPO_ROOT / "reports" / "既存モデルの改善" / "tables"
_DEFAULT_PREDICTIONS = _REPO_ROOT / "reports" / "既存モデルの改善" / "predictions"
#: 組み合わせに使う3つの予想と、その作り方（変更版）。
_HORSE_MODELS = ("form_aptitude_top3", "longshots_in_top3", "favorites_out_of_top3")
_VARIANT = "improved"
#: 計算の方法（保存する名前, 表に出す名前, 勝率の材料）。
_METHODS = (
    ("calc_market", "計算（オッズだけの勝率）", SHIFT_COLUMNS["市場だけ"]),
    ("calc_model", "計算（3つの予想を組み合わせた勝率）", SHIFT_COLUMNS["3つの予想"]),
)
#: 荒れ具合の券種 → 確定オッズを読む券種。
_TICKETS = {BetType.WIN: TicketType.WIN, BetType.QUINELLA: TicketType.QUINELLA,
            BetType.TRIO: TicketType.TRIO, BetType.TRIFECTA: TicketType.TRIFECTA}


def main(args) -> None:
    form_spec = spec_named("form_aptitude_top3")
    form = TableStore(args.tables).read(form_spec.name, form_spec.catalog)
    store = PredictionStore(args.predictions)
    builder = HorseTableBuilder(form, {name: store.read(name, _VARIANT) for name in _HORSE_MODELS})
    windows = [window_named(name) for name in args.windows] if args.windows else list(WINDOWS)
    runners = [(key, UpsetCalculationRunner(UpsetClassCalculator(UpsetLevelRule()),
                                             RaceProbabilityBuilder(StrengthFeatures(shifts)), name))
               for key, name, shifts in _METHODS]
    results = [_window(builder, runners, window, args) for window in windows]
    rows = [_write(store, key, [frames[key] for frames, _ in results]) for key, _, _ in _METHODS]
    fits = pd.DataFrame(list(chain.from_iterable(records for _, records in results)))
    fits.to_csv(args.predictions / "upset_level" / "calc-fit.csv", index=False, encoding="utf-8-sig")
    cli.emit([Table(["方法", "予測の行数", "ファイル"], rows, title="荒れ具合（計算）"),
              Table(list(fits.columns), fits.round(4).values.tolist(), title="区切りごとの勝率の出し方")], args)


def _window(builder: HorseTableBuilder, runners, window, args):
    """1つの区切り: 1頭ごとの表を作り、テスト期間の確定オッズを読み、方法ごとに計算する。"""
    print(f"荒れ具合（計算） / {window.name}: 確定オッズを読んでいます …", file=sys.stderr, flush=True)
    horses = builder.build(window)
    with db.open_db(args.db) as con:
        reader = CombinationTableReader(con)
        tables = {bet: reader.read(ticket, window.test_first_day, window.test_last_day) for bet, ticket in _TICKETS.items()}
    print(f"荒れ具合（計算） / {window.name}: 計算しています …", file=sys.stderr, flush=True)
    outputs = {key: runner.run(horses, window, tables) for key, runner in runners}
    frames = {key: frame for key, (frame, _) in outputs.items()}
    records = [record for _, record in outputs.values()]
    return frames, records


def _write(store: PredictionStore, key: str, frames: list[pd.DataFrame]) -> list[object]:
    predictions = pd.concat(frames, ignore_index=True)
    path = store.write("upset_level", key, predictions, pd.DataFrame())
    return [key, len(predictions), str(path)]


def _parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--windows", nargs="*", default=None, metavar="区切り", help="回す区切り（省略すると7つ全部）")
    parser.add_argument("--tables", type=Path, default=_DEFAULT_TABLES, help="学習データの表の置き場所")
    parser.add_argument("--predictions", type=Path, default=_DEFAULT_PREDICTIONS, help="予測の表の置き場所")
    return parser


if __name__ == "__main__":
    cli.run(_parser(), main)
