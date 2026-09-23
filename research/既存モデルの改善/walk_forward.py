"""区切りごとに学習して、検証とテストの予測を残す（研究「既存モデルの改善」の入口②）。

    uv run python research/既存モデルの改善/walk_forward.py --model form_aptitude_top3                 # その予想の作り方を全部
    uv run python research/既存モデルの改善/walk_forward.py --model longshots_in_top3 --variants current improved
    uv run python research/既存モデルの改善/walk_forward.py --model form_aptitude_top3 --windows 2025年後半  # 1つの区切りだけ試す
    uv run python research/既存モデルの改善/walk_forward.py --model upset_level                        # 荒れ具合（現行の作り方・券種ごと）

出るもの: reports/既存モデルの改善/predictions/<予想の名前>/<作り方>.pkl（予測の表）と <作り方>-log.csv（木の数・秒）。
学習データは build_tables.py で保存した表を読む（元DB は開かない）。ハイパーパラメータは予想の初期値のまま。
"""

from __future__ import annotations

import importlib
import sys
from itertools import chain
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 既存モデルの改善.analysis.tables import TableStore, spec_named  # noqa: E402
from 既存モデルの改善.analysis.variants import variants_of  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import (  # noqa: E402
    PredictionStore,
    UpsetWindowTrainer,
    WalkForwardRunner,
    WindowTrainer,
)
from 既存モデルの改善.analysis.windows import WINDOWS, window_named  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_TABLES = _REPO_ROOT / "reports" / "既存モデルの改善" / "tables"
_DEFAULT_PREDICTIONS = _REPO_ROOT / "reports" / "既存モデルの改善" / "predictions"


#: 荒れ具合の予想の名前と、その現行の作り方の予測を保存するときの名前。
_UPSET = "upset_level"
_UPSET_KEY = "current"


def main(args) -> None:
    spec = spec_named(args.model)
    data = TableStore(args.tables).read(spec.name, spec.catalog)
    settings = HyperparameterSettings.load(None, defaults=_default_settings_path(spec.name))
    windows = [window_named(name) for name in args.windows] if args.windows else list(WINDOWS)
    if spec.name == _UPSET:
        _run_upset(data, settings, windows, args)
        return
    runner = WalkForwardRunner(WindowTrainer(settings), windows)
    variants = [variant for variant in variants_of(spec.name) if not args.variants or variant.key in args.variants]
    store = PredictionStore(args.predictions)
    rows = [_run(runner, store, data, variant) for variant in variants]
    cli.emit(Table(["作り方", "予測の行数", "ファイル"], rows, title=f"{spec.label}: 区切りごとの予測"), args)


def _run(runner: WalkForwardRunner, store: PredictionStore, data, variant) -> list[object]:
    predictions, log = runner.run(data, variant)
    path = store.write(variant.model, variant.key, predictions, log)
    return [variant.name, len(predictions), str(path)]


def _run_upset(data, settings, windows, args) -> None:
    """荒れ具合の予想の現行の作り方を、区切りごとに券種ごとに学習して、予測を残す。"""
    trainer = UpsetWindowTrainer(settings)
    results = [_upset_window(trainer, data, window) for window in windows]
    predictions = pd.concat([frame for frame, _ in results], ignore_index=True)
    log = pd.DataFrame(list(chain.from_iterable(rows for _, rows in results)))
    path = PredictionStore(args.predictions).write(_UPSET, _UPSET_KEY, predictions, log)
    cli.emit(Table(["作り方", "予測の行数", "ファイル"], [["現行", len(predictions), str(path)]],
                   title="レースの荒れ具合: 区切りごとの予測"), args)


def _upset_window(trainer: UpsetWindowTrainer, data, window):
    print(f"upset_level / 現行 / {window.name}: 学習しています …", file=sys.stderr, flush=True)
    return trainer.run(data, window)


#: 材料の実験の表 → ハイパーパラメータの初期値を借りる予想（全頭）。
_SETTINGS_OF = {"form_experiments": "form_aptitude_top3"}


def _default_settings_path(model: str) -> Path:
    """予想のハイパーパラメータの初期値のファイル（``yosou.<予想>.setting.DEFAULT_SETTINGS_PATH``）。
    材料の実験の表は、全頭の予想の初期値を使う。"""
    package = _SETTINGS_OF.get(model, model)
    return importlib.import_module(f"yosou.{package}.setting").DEFAULT_SETTINGS_PATH


def _parser():
    parser = cli.build_parser(__doc__, limit=None)
    parser.add_argument("--model", required=True, help="予想の名前（form_aptitude_top3 / longshots_in_top3 / favorites_out_of_top3 / upset_level）")
    parser.add_argument("--variants", nargs="*", default=None, metavar="作り方", help="回す作り方（省略すると全部）")
    parser.add_argument("--windows", nargs="*", default=None, metavar="区切り", help="回す区切り（例 2025年後半。省略すると7つ全部）")
    parser.add_argument("--tables", type=Path, default=_DEFAULT_TABLES, help="学習データの表の置き場所")
    parser.add_argument("--predictions", type=Path, default=_DEFAULT_PREDICTIONS, help="予測の表の置き場所")
    return parser


if __name__ == "__main__":
    cli.run(_parser(), main)
