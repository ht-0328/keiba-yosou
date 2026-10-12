"""手順3・6: 区切りごとに学んで、レース選びと荒れる前提の予想の予測を作る（研究「百万馬券を当てる」の入口②）。

    uv run python research/百万馬券を当てる/walk.py race       # 第1段: 帯になる確率（レース単位。木曜・前日・当日）
    uv run python research/百万馬券を当てる/walk.py big        # 第1段: 3連単が 1,000倍以上になる確率（レース単位。木曜・前日・当日）
    uv run python research/百万馬券を当てる/walk.py baseline   # 比べる目安: 荒れ具合の予想（4券種 × 4段階）を同じ区切りで学び直す
    uv run python research/百万馬券を当てる/walk.py horses     # 第2段: 荒れたレースだけで学ぶ 3着以内と1着（当日）

区切りは、まだ見ていない 2021年前半〜2022年後半の4つ（研究「複勝以外の回収率100超」の ``EARLY_WINDOWS``）と、
参考の 2023年前半〜2026年の7つ（研究「既存モデルの改善」の ``WINDOWS``）。学習はどれも、テストより前の期間だけを使う。
出るもの（Git 対象外）: ``reports/百万馬券を当てる/predictions/<予想>/<作り方>.pkl`` と学習の記録。済んだものは飛ばす（``--force`` で回し直す）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from yosou.form_aptitude_top3.dataset import WinTargetData  # noqa: E402
from yosou.shared.dataset import TrainingData  # noqa: E402
from yosou.shared.feature import PredictionTiming  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402
from yosou.upset_level.setting import DEFAULT_SETTINGS_PATH as UPSET_SETTINGS  # noqa: E402

from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward.upset_window_trainer import UpsetWindowTrainer  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS  # noqa: E402
from 既存モデルの改善.win_check import _pin_to_p_cores as pin_to_p_cores  # noqa: E402
from 既存モデルの改善.win_check import _with_threads as with_threads  # noqa: E402
from 複勝以外の回収率100超.analysis.early_windows import EARLY_WINDOWS  # noqa: E402
from 複勝以外の回収率100超.analysis.retrain_targets import retrain_target_named  # noqa: E402
from 百万馬券を当てる.analysis.obi_rules import BIG_YEN  # noqa: E402
from 百万馬券を当てる.analysis.race_obi_window_trainer import RaceObiWindowTrainer  # noqa: E402
from 百万馬券を当てる.analysis.race_table_loader import BIG_LABEL, OBI_LABEL, TRIFECTA_YEN, RaceTableLoader  # noqa: E402
from 百万馬券を当てる.analysis.wild_only_window_trainer import WildOnlyWindowTrainer  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
DEFAULT_ROOT = _REPORTS / "百万馬券を当てる"
DEFAULT_HORSE_TABLES = _REPORTS / "既存モデルの改善" / "tables"
#: 学ぶ区切り（まだ見ていない4つと、参考の7つ）。
RESEARCH_WINDOWS = (*EARLY_WINDOWS, *WINDOWS)
#: 予測の置き場所の名前（予想の名前, 作り方の名前）。
RACE_OBI = "race_obi"
RACE_BIG = "race_big"
#: レース単位の二値のモデルの、置き場所の名前 → 目的変数の列。
RACE_LABELS: dict[str, str] = {RACE_OBI: OBI_LABEL, RACE_BIG: BIG_LABEL}
UPSET_BASELINE = ("upset_level", "current")
#: 第2段で学ぶ馬ごとの予想（今の本番の表と列のまま、学ぶ行だけ荒れたレースにする）と、置き場所の作り方の名前。
HORSE_TARGETS: dict[str, str] = {"当日・3着以内": "wild-top3-race_day", "当日・1着": "wild-win-race_day"}


def main() -> None:
    args = _parser().parse_args()
    pin_to_p_cores()
    store = PredictionStore(args.root / "predictions")
    {"race": _race, "big": _big, "baseline": _baseline, "horses": _horses}[args.step](args, store)


def _race(args: argparse.Namespace, store: PredictionStore) -> None:
    _race_model(args, store, RACE_OBI)


def _big(args: argparse.Namespace, store: PredictionStore) -> None:
    _race_model(args, store, RACE_BIG)


def _race_model(args: argparse.Namespace, store: PredictionStore, model: str) -> None:
    """レース単位の二値のモデル（帯になる確率か、1,000倍以上になる確率）を、3つの時点で学ぶ。"""
    data = RaceTableLoader(args.root / "tables").read()
    for timing in PredictionTiming:
        _race_timing(args, store, data, timing, model)


def _race_timing(args: argparse.Namespace, store: PredictionStore, data: TrainingData, timing: PredictionTiming,
                 model: str) -> None:
    """1つの時点の、レース単位の二値のモデルを区切りごとに学ぶ（済んでいれば飛ばす）。"""
    if _done(store, model, timing.value, args):
        return
    trainer = RaceObiWindowTrainer(_settings(UPSET_SETTINGS, args.threads), timing, RACE_LABELS[model])
    results = [_progress(f"{model} {timing.label} {window.name}", trainer.run(data, window)) for window in RESEARCH_WINDOWS]
    _write(store, model, timing.value, results)


def _baseline(args: argparse.Namespace, store: PredictionStore) -> None:
    model, key = UPSET_BASELINE
    if _done(store, model, key, args):
        return
    data = RaceTableLoader(args.root / "tables").read()
    trainer = UpsetWindowTrainer(_settings(UPSET_SETTINGS, args.threads))
    results = [_progress(window.name, trainer.run(data, window)) for window in RESEARCH_WINDOWS]
    _write(store, model, key, results)


def _horses(args: argparse.Namespace, store: PredictionStore) -> None:
    races = RaceTableLoader(args.root / "tables").read()
    wild = set(races.ids.loc[races.evaluation[TRIFECTA_YEN].ge(BIG_YEN), "レースID"])
    for label, key in HORSE_TARGETS.items():
        _horse_target(args, store, wild, label, key)


def _horse_target(args: argparse.Namespace, store: PredictionStore, wild: set[str], label: str, key: str) -> None:
    """1つの馬ごとの予想（当日の 3着以内か1着）を、荒れたレースだけで区切りごとに学ぶ（済んでいれば飛ばす）。"""
    target = retrain_target_named(label)
    if _done(store, target.variant.model, key, args):
        return
    print(f"{label}: 表 {target.variant.model} を読んでいます …", flush=True)
    data = TableStore(args.horse_tables).read(target.variant.model, target.catalog)
    data = WinTargetData().training(data) if target.win else data
    trainer = WildOnlyWindowTrainer(_settings(target.settings, args.threads), wild)
    results = [_progress(f"{label} {window.name}", trainer.run(data, window, target.variant)) for window in RESEARCH_WINDOWS]
    _write(store, target.variant.model, key, results)


def _settings(defaults: Path, threads: int) -> HyperparameterSettings:
    return with_threads(HyperparameterSettings.load(None, defaults=defaults), threads)


def _done(store: PredictionStore, model: str, key: str, args: argparse.Namespace) -> bool:
    done = store.exists(model, key) and not args.force
    if done:
        print(f"{model}/{key}: 済んでいるので飛ばします", flush=True)
    return done


def _progress(name: str, result: tuple[pd.DataFrame, list[dict[str, object]]]) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    print(f"{name}: {len(result[0]):,}行", flush=True)
    return result


def _write(store: PredictionStore, model: str, key: str, results: list[tuple[pd.DataFrame, list[dict[str, object]]]]) -> None:
    frame = pd.concat([frame for frame, _ in results], ignore_index=True)
    log = pd.DataFrame([row for _, rows in results for row in rows])
    print(f"{model}/{key}: {store.write(model, key, frame, log)}", flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="区切りごとに学んで、レース選びと荒れる前提の予想の予測を作る", allow_abbrev=False)
    parser.add_argument("step", choices=("race", "big", "baseline", "horses"),
                        help="race（第1段: 帯）・big（第1段: 1,000倍以上）・baseline（比べる目安）・horses（第2段）")
    parser.add_argument("--force", action="store_true", help="済んだものも回し直す")
    parser.add_argument("--threads", type=int, default=6, help="学習のスレッド数（既定: 6）")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="この研究の置き場所（tables/ と predictions/）")
    parser.add_argument("--horse-tables", type=Path, default=DEFAULT_HORSE_TABLES, help="馬ごとの表の置き場所")
    return parser


if __name__ == "__main__":
    main()
