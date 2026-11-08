"""超荒れの展開と適性から大穴を当てる: 展開の型で混ぜる着順の予想を、区切りごとに学び直して予測を作る（段3 の入口①）。

    uv run python research/超荒れの展開と適性から大穴を当てる/forecast.py features                     # 足す材料の表を元DB から作る（1分）
    uv run python research/超荒れの展開と適性から大穴を当てる/forecast.py train                        # 作り方ごと × 前日・当日（区切り15。数時間）
    uv run python research/超荒れの展開と適性から大穴を当てる/forecast.py train --variants mixed-top3 --timings 当日
    uv run python research/超荒れの展開と適性から大穴を当てる/forecast.py train --variants mixed-top3 --windows 2024年前半   # 1つの区切りだけ試す

学習データは、今のモデルの学習の表（``reports/複勝以外の回収率100超/tables-2012/``）に、展開・展開の型・その日の馬場の傾向・ハンデの材料
（``reports/超荒れの展開と適性から大穴を当てる/材料-<時点>.pkl``）を足した、12頭以上のレースの全頭。出るもの（Git 対象外）:
``reports/超荒れの展開と適性から大穴を当てる/predictions/<作り方>-<day_before|race_day>.pkl`` と ``-log.csv``（検証とテストの半年の、
展開の型ごとの確率と混ぜた確率）。学習は1つずつ走らせる。開催日のレースの時間には動かさない（features は元DB を読む）。
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

from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_prediction_store import LongshotPredictionStore  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_walk_forward import LongshotWalkForward  # noqa: E402
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_windows import WINDOWS, window_named  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_forecast.scenario_dataset import DEFAULT_TABLES, ScenarioDataset  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_forecast.scenario_material_source import ScenarioMaterialSource  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_forecast.scenario_variant import VARIANTS, variant_named  # noqa: E402
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_forecast.scenario_window_trainer import ScenarioWindowTrainer  # noqa: E402

DEFAULT_ROOT = _REPO_ROOT / "reports" / "超荒れの展開と適性から大穴を当てる"
_TIMINGS = {"当日": PredictionTiming.RACE_DAY, "前日": PredictionTiming.DAY_BEFORE}


def main() -> None:
    args = _parser().parse_args()
    source = ScenarioMaterialSource(args.root)
    if args.step == "features":
        with db.open_db(args.db, default=db.JRA) as con:
            print(f"書きました: {source.build(con)}", flush=True)
        return
    settings = HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH)
    store = LongshotPredictionStore(args.root / "predictions")
    windows = [window_named(name) for name in args.windows] if args.windows else list(WINDOWS)
    variants = [variant_named(key) for key in args.variants] if args.variants else list(VARIANTS)
    runner = LongshotWalkForward(ScenarioWindowTrainer(settings, args.threads), windows)
    for label, variant in product(args.timings, variants):
        timing = _TIMINGS[label]
        if store.exists(variant.key, timing.value) and not args.force and not args.windows:
            print(f"{variant.key}-{timing.value}: 済んでいるので飛ばします", flush=True)
            continue
        data = ScenarioDataset(source.load(timing), args.tables).build(timing, variant)
        predictions, log = runner.run(data, variant)
        key = variant.key if not args.windows else f"{variant.key}-試し"
        print(f"書きました: {store.write(key, timing.value, predictions, log)}", flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("step", choices=("features", "train"), help="features（足す材料の表を作る）・train（区切りごとに学ぶ）")
    parser.add_argument("--variants", nargs="*", default=None, help=f"作り方（{' / '.join(v.key for v in VARIANTS)}。省略すると全部）")
    parser.add_argument("--timings", nargs="*", default=["当日", "前日"], choices=tuple(_TIMINGS), help="時点（既定: 当日と前日）")
    parser.add_argument("--windows", nargs="*", default=None, help="区切りの名前（試すとき。結果は <作り方>-試し に書く）")
    parser.add_argument("--threads", type=int, default=14, help="学習のスレッド数（既定: 14）")
    parser.add_argument("--force", action="store_true", help="済んだものも学び直す")
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（features で使う）")
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES, help="今のモデルの学習の表の置き場所")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="出力の置き場所")
    return parser


if __name__ == "__main__":
    main()
