"""WIN5で人気薄の勝ち馬を狙う: 人気薄の1着の予想を区切りごとに学び直して予測を作る（段2 の入口①）。

    uv run python research/WIN5で人気薄の勝ち馬を狙う/forecast.py features                         # 型の材料の表を元DB から作る（数分）
    uv run python research/WIN5で人気薄の勝ち馬を狙う/forecast.py train                            # 3つの作り方 × 当日（区切り15。数時間）
    uv run python research/WIN5で人気薄の勝ち馬を狙う/forecast.py train --variants longshot10 --timings 前日
    uv run python research/WIN5で人気薄の勝ち馬を狙う/forecast.py train --variants rank10 --windows 2019年前半  # 1つの区切りだけ試す

学習データは、今のモデルの学習の表（``reports/複勝以外の回収率100超/tables-2012/``。今のモデルの1着の列）に、型の材料
（``reports/WIN5で人気薄の勝ち馬を狙う/型の材料.pkl``）を足したもの。出るもの（Git 対象外）:
``reports/WIN5で人気薄の勝ち馬を狙う/predictions/<作り方>-<race_day|day_before>.pkl`` と ``-log.csv``。
学習は1つずつ走らせる。開催日のレースの時間には動かさない。
"""

from __future__ import annotations

import argparse
import sys
from itertools import product
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools"), str(_REPO_ROOT / "src")]

from 共通 import db  # noqa: E402

from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH  # noqa: E402
from yosou.shared.feature import PredictionTiming  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_dataset import DEFAULT_TABLES, LongshotDataset  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_prediction_store import LongshotPredictionStore  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_variants import VARIANTS, variant_named  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_walk_forward import LongshotWalkForward  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_window_trainer import LongshotWindowTrainer  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_windows import WINDOWS, window_named  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.type_feature_source import TypeFeatureSource  # noqa: E402

DEFAULT_ROOT = _REPO_ROOT / "reports" / "WIN5で人気薄の勝ち馬を狙う"
_TIMINGS = {"当日": PredictionTiming.RACE_DAY, "前日": PredictionTiming.DAY_BEFORE}


def main() -> None:
    args = _parser().parse_args()
    source = TypeFeatureSource(args.root)
    if args.step == "features":
        with db.open_db(args.db, default=db.JRA) as con:
            print(f"書きました: {source.build(con)}", flush=True)
        return
    _train(args, source)


def _train(args: argparse.Namespace, source: TypeFeatureSource) -> None:
    settings = HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH)
    dataset = LongshotDataset(source.load(), args.tables)
    store = LongshotPredictionStore(args.root / "predictions")
    windows = [window_named(name) for name in args.windows] if args.windows else list(WINDOWS)
    variants = [variant_named(key) for key in args.variants] if args.variants else list(VARIANTS)
    runner = LongshotWalkForward(LongshotWindowTrainer(settings, args.threads), windows)
    loaded: dict[tuple[PredictionTiming, int, str], object] = {}
    for label, variant in product(args.timings, variants):
        timing = _TIMINGS[label]
        if store.exists(variant.key, timing.value) and not args.force and not args.windows:
            print(f"{variant.key}-{timing.value}: 済んでいるので飛ばします", flush=True)
            continue
        cache_key = (timing, variant.min_popularity, variant.baseline)
        if cache_key not in loaded:
            loaded.clear()
            loaded[cache_key] = dataset.build(timing, variant.min_popularity, variant.baseline)
        predictions, log = runner.run(loaded[cache_key], variant)
        key = variant.key if not args.windows else f"{variant.key}-試し"
        print(f"書きました: {store.write(key, timing.value, predictions, log)}", flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("step", choices=("features", "train"), help="features（型の材料を作る）・train（区切りごとに学ぶ）")
    parser.add_argument("--variants", nargs="*", default=None, help=f"作り方（{' / '.join(v.key for v in VARIANTS)}。省略すると全部）")
    parser.add_argument("--timings", nargs="*", default=["当日"], choices=tuple(_TIMINGS), help="時点（既定: 当日）")
    parser.add_argument("--windows", nargs="*", default=None, help="区切りの名前（試すとき。結果は <作り方>-試し に書く）")
    parser.add_argument("--threads", type=int, default=14, help="学習のスレッド数（既定: 14）")
    parser.add_argument("--force", action="store_true", help="済んだものも学び直す")
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（features で使う）")
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES, help="今のモデルの学習の表の置き場所")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="出力の置き場所")
    return parser


if __name__ == "__main__":
    main()
