"""4つの予想モデルの当日時点の予測を、期間の全レースぶん一括で出して CSV に残す（研究「馬券の買い方の検証」の入口①）。

    uv run python research/馬券の買い方の検証/predict_all.py                                   # 2025-07-01〜2026-09-30
    uv run python research/馬券の買い方の検証/predict_all.py --from 2025-07-01 --to 2025-07-31   # 短い期間で試す
    uv run python research/馬券の買い方の検証/predict_all.py --only form_aptitude_top3          # 1つのモデルだけ

出るもの: reports/馬券の買い方の検証/predictions/<モデル名>.csv（4つ）と manifest.json。標準出力にはモデルごとの行数・レース数の表。
学習データを作る部品（各モデルの dataset_builder）で期間ぶんの特徴量を作り、保存済みの当日モデルで予測する。
前日・当日のオッズの特徴量は確定オッズなので、実運用より楽観側にぶれる（docs/03-protocol.md）。
元DB を開くのは特徴量を作る間だけ（モデルごとに開いて閉じる）。1モデルにつき数分かかる。
"""

from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import cli, db  # noqa: E402
from 共通.render import Table  # noqa: E402

from yosou.shared.dataset import RACE_ID, TrainingPeriod  # noqa: E402
from yosou.shared.feature import PredictionTiming  # noqa: E402

from 馬券の買い方の検証.analysis import periods  # noqa: E402
from 馬券の買い方の検証.analysis.prediction import (  # noqa: E402
    MANIFEST_NAME,
    SOURCE_NAMES,
    SOURCES,
    PredictionFile,
    PredictionManifest,
    PredictionSource,
)

#: リポジトリ直下（research/馬券の買い方の検証/ から2つ上）。
_REPO_ROOT = Path(__file__).resolve().parents[2]
#: 出力の既定の置き場と、保存済みモデルの親（どちらも Git 対象外の reports/）。
_DEFAULT_OUT_DIR = _REPO_ROOT / "reports" / "馬券の買い方の検証" / "predictions"
_DEFAULT_REPORTS = _REPO_ROOT / "reports"
#: 使う時点。前日・当日のオッズは確定オッズ（学習と同じ）。
_TIMING = PredictionTiming.RACE_DAY


def main(args) -> None:
    sources = [source for source in SOURCES if not args.only or source.name in args.only]
    period = _period(args.from_day, args.to_day, args.warmup_from)
    manifest = PredictionManifest(args.from_day, args.to_day, _TIMING.value)
    rows = [_run(source, period, args, manifest) for source in sources]
    manifest.write(args.out_dir / MANIFEST_NAME)
    note = f"期間 {args.from_day}〜{args.to_day}・時点 {_TIMING.label}・記録 {args.out_dir / MANIFEST_NAME}"
    cli.emit(Table(["モデル", "行数", "レース数", "ファイル"], rows, title="一括予測", note=note), args)


def _period(first_day: date, last_day: date, warmup_first_day: date) -> TrainingPeriod:
    """学習データを作る部品に渡す期間。使われるのはウォームアップと学習の始まりだけなので、検証・テストの始まりは期間の後のダミー。"""
    if last_day < first_day:
        raise ValueError(f"--to（{last_day}）は --from（{first_day}）以降の日にしてください")
    valid_first_day = periods.day_after(last_day)
    return TrainingPeriod.starting(first_day, valid_first_day, periods.day_after(valid_first_day),
                                   warmup_first_day=warmup_first_day)


def _run(source: PredictionSource, period: TrainingPeriod, args, manifest: PredictionManifest) -> list[object]:
    """1モデルぶん: 元DB を開いて期間の特徴量を作る → 閉じる → 当日モデルで予測 → CSV に書く。"""
    started = time.perf_counter()
    print(f"{source.label}: 特徴量を作っています…", file=sys.stderr, flush=True)
    with db.open_db(args.db) as con:
        data = source.builder_factory(con).build_training_data(period)
    data = data.between(args.from_day, periods.day_after(args.to_day))
    print(f"  {len(data):,} 行の特徴量（{time.perf_counter() - started:.0f} 秒）。予測しています…", file=sys.stderr, flush=True)
    table = source.predictor(args.reports).predict(data)
    file = PredictionFile(args.out_dir / f"{source.name}.csv")
    file.write(table)
    races = int(table[RACE_ID].nunique())
    manifest.add(source.name, file.path, source.models_root(args.reports), len(table), races)
    print(f"  {len(table):,} 行・{races:,} レースを書きました（{time.perf_counter() - started:.0f} 秒）", file=sys.stderr, flush=True)
    return [source.label, len(table), races, str(file.path)]


def build_parser():
    parser = cli.build_parser(__doc__, filters=False, limit=None)
    period = parser.add_argument_group("期間")
    period.add_argument("--from", dest="from_day", type=date.fromisoformat, default=periods.PREDICTION_FIRST_DAY,
                        help=f"予測を出す最初の開催日（既定: {periods.PREDICTION_FIRST_DAY}）")
    period.add_argument("--to", dest="to_day", type=date.fromisoformat, default=periods.PREDICTION_LAST_DAY,
                        help=f"予測を出す最後の開催日（既定: {periods.PREDICTION_LAST_DAY}）")
    period.add_argument("--warmup-from", type=date.fromisoformat, default=periods.WARMUP_FIRST_DAY,
                        help=f"過去走の計算にだけ使う出走を読み始める日（既定: {periods.WARMUP_FIRST_DAY}。予想モデルの学習と同じ）")
    target = parser.add_argument_group("対象と置き場")
    target.add_argument("--only", action="append", choices=SOURCE_NAMES, metavar="名前",
                        help=f"このモデルだけ出す（繰り返せる。{' / '.join(SOURCE_NAMES)}）")
    target.add_argument("--out-dir", type=Path, default=_DEFAULT_OUT_DIR,
                        help=f"CSV と manifest.json を書くフォルダ（既定: {_DEFAULT_OUT_DIR.relative_to(_REPO_ROOT)}）")
    target.add_argument("--reports", type=Path, default=_DEFAULT_REPORTS,
                        help="保存済みモデルの親フォルダ（既定: reports/。その下の <モデル名>/models を読む）")
    return parser


if __name__ == "__main__":
    cli.run(build_parser(), main)
