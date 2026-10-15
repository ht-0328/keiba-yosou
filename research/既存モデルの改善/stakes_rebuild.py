"""重賞の予想を作り直したあと、7つの区切り（1年ずつ）で比べる（研究「既存モデルの改善」の入口⑨）。

    uv run python research/既存モデルの改善/stakes_rebuild.py tables                                  # 学習データの表を作る（元DB を開く。15分ほど）
    uv run python research/既存モデルの改善/stakes_rebuild.py tables --only stakes_ability stakes_race_day
    uv run python research/既存モデルの改善/stakes_rebuild.py run                                     # 作り方ごとに7つの区切りで学習する（1時間ほど。済んだものは飛ばす）
    uv run python research/既存モデルの改善/stakes_rebuild.py run --variants general-race_day       # 1つだけ
    uv run python research/既存モデルの改善/compare.py --only stakes_tendency_top3                  # 比べ方の表（時点ごとの採否）
    uv run python research/既存モデルの改善/stakes_rebuild.py stakes_rows                          # 手本の予測から重賞の行だけを取り出して保存する（数秒）
    uv run python tools/印の成績/mark_stats.py --form stakes_race_day/default-race_day --win h2h_pool_ability/win-race_day --timing 当日 --no-danger --out-dir reports/印の成績/重賞   # 専用モデルの印と買い目の成績（当日）
    uv run python tools/印の成績/mark_stats.py --form form_race_day/general-race_day-stakes --win h2h_pool_ability/win-race_day --timing 当日 --no-danger --out-dir reports/印の成績/重賞  # 手本を同じ重賞だけに使ったとき

``stakes_rows`` は、全レースで学んだ手本の予測（general-*）から重賞の行だけを取り出し、``<表>/general-<時点>-stakes.pkl`` に書く。
道具「印の成績」に専用モデルの予測と並べて渡すと、同じ重賞のレースについて印ごとの成績と全券種の買い目の回収率を比べられる
（危険な人気馬の判定は、区切りが半年ずつの人気馬の予想と区切りの名前が合わないので使わない）。
学習データは予想のパッケージ（``src/yosou/stakes_tendency_top3``・``src/yosou/form_aptitude_top3``）の組み立て関数で作る。
重賞だけの表（作り直した専用モデル）と全レースの表（手本を重賞だけに使ったときの比べ先）の4つで、どれも 2012年から。
区切りと区切りごとの学習（LightGBM と CatBoost。ハイパーパラメータは予想の初期値）はこの研究のもの。
出るもの（Git 対象外）: ``reports/既存モデルの改善/tables/<表>/``・``predictions/<表>/<作り方>.pkl``。
学習は、同じマシンのほかの学習とぶつからないように1つずつ走らせ、Windows では P コア（論理 CPU 0〜11）に絞る。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db  # noqa: E402

from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH as FORM_SETTINGS  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402
from yosou.stakes_tendency_top3.setting import DEFAULT_SETTINGS_PATH as STAKES_SETTINGS  # noqa: E402

from 既存モデルの改善.analysis.stakes_rebuild import (  # noqa: E402
    FORM_ABILITY,
    FORM_RACE_DAY,
    REBUILD_TABLES,
    REBUILD_VARIANTS,
    STAKES_ABILITY,
    STAKES_RACE_DAY,
    STAKES_ROWS_SUFFIX,
    StakesRowFilter,
    rebuild_table_named,
)
from 既存モデルの改善.analysis.tables import ModelTableSpec, TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore, WalkForwardRunner, WindowTrainer  # noqa: E402
from 既存モデルの改善.analysis.windows import STAKES_WINDOWS  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_TABLES = _REPO_ROOT / "reports" / "既存モデルの改善" / "tables"
_DEFAULT_PREDICTIONS = _REPO_ROOT / "reports" / "既存モデルの改善" / "predictions"
#: P コア（論理 CPU 0〜11）のマスク。LightGBM と CatBoost が E コアに載ると止まったように遅くなることがある。
_P_CORES = 0xFFF
#: 表 → その表で学ぶときのハイパーパラメータの初期値（重賞だけの表は重賞の予想の、全レースの表は手本の初期値）。
_SETTINGS_OF = {STAKES_ABILITY: STAKES_SETTINGS, STAKES_RACE_DAY: STAKES_SETTINGS,
                FORM_ABILITY: FORM_SETTINGS, FORM_RACE_DAY: FORM_SETTINGS}


def main() -> None:
    args = _parser().parse_args()
    {"tables": _tables, "run": _run, "stakes_rows": _stakes_rows}[args.step](args)


def _tables(args: argparse.Namespace) -> None:
    store = TableStore(args.tables)
    for table in (table for table in REBUILD_TABLES if not args.only or table.name in args.only):
        _build(table, store, args)


def _build(table: ModelTableSpec, store: TableStore, args: argparse.Namespace) -> None:
    """元DB を開いて1つの表を作り、保存する。元DB を開くのは特徴量を作る間だけ。"""
    started = time.perf_counter()
    print(f"{table.label}: 学習データを作っています …", flush=True)
    with db.open_db(args.db) as con:
        data = table.builder_factory(con).build_training_data(table.period)
    folder = store.write(table.name, data)
    print(f"{table.label}: {len(data):,}行・特徴量 {data.features.shape[1]}個・{time.perf_counter() - started:.0f}秒 → {folder}", flush=True)


def _run(args: argparse.Namespace) -> None:
    _pin_to_p_cores()
    predictions = PredictionStore(args.predictions)
    tables = TableStore(args.tables)
    chosen = [variant for variant in REBUILD_VARIANTS if not args.variants or variant.key in args.variants]
    for variant in chosen:
        if predictions.exists(variant.model, variant.key) and not args.force:
            print(f"{variant.model} / {variant.name}: 済んでいるので飛ばします", flush=True)
            continue
        settings = _with_threads(HyperparameterSettings.load(None, defaults=_SETTINGS_OF[variant.model]), args.threads)
        runner = WalkForwardRunner(WindowTrainer(settings), STAKES_WINDOWS)
        data = tables.read(variant.model, rebuild_table_named(variant.model).catalog)
        frame, log = runner.run(data, variant)
        print(f"{variant.model} / {variant.name}: {predictions.write(variant.model, variant.key, frame, log)}", flush=True)


def _stakes_rows(args: argparse.Namespace) -> None:
    """全レースで学んだ手本の予測（general-*）から重賞の行だけを取り出し、``-stakes`` を付けた名前で保存する。学習の記録はそのまま写す。"""
    predictions, tables = PredictionStore(args.predictions), TableStore(args.tables)
    stakes = tables.read(STAKES_RACE_DAY, rebuild_table_named(STAKES_RACE_DAY).catalog)
    rows = StakesRowFilter(stakes.ids)
    for variant in (variant for variant in REBUILD_VARIANTS if variant.key.startswith("general-")):
        if not predictions.exists(variant.model, variant.key):
            print(f"{variant.model} / {variant.name}: 予測が無いので飛ばします（先に run）", flush=True)
            continue
        kept = rows.apply(predictions.read(variant.model, variant.key))
        path = predictions.write(variant.model, f"{variant.key}{STAKES_ROWS_SUFFIX}", kept, predictions.read_log(variant.model, variant.key))
        print(f"{variant.model} / {variant.name}: 重賞の行 {len(kept):,} → {path}", flush=True)


def _with_threads(settings: HyperparameterSettings, threads: int) -> HyperparameterSettings:
    """学習のスレッド数を ``threads`` にした設定（ほかのハイパーパラメータは予想の初期値のまま）。

    同じマシンでほかの学習が全部のコアを使っていると、スレッドの取り合いで止まったように遅くなるため、数を絞る。
    スレッド数は、木の作り方（学習の結果）を変えない。
    """
    values = settings.to_dict()
    values["lightgbm"]["params"]["n_jobs"] = threads
    values["catboost"]["params"]["thread_count"] = threads
    return HyperparameterSettings.from_dict(values)


def _pin_to_p_cores() -> None:
    """Windows では、このプロセスを P コアだけで動かす（学習のスレッドも従う）。ほかの OS では何もしない。"""
    if sys.platform != "win32":
        return
    import ctypes

    kernel = ctypes.windll.kernel32
    kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), _P_CORES)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="重賞の予想の作り直しの確かめ", allow_abbrev=False)
    parser.add_argument("step", choices=("tables", "run", "stakes_rows"),
                        help="tables（表を作る）・run（学習する）・stakes_rows（手本の予測から重賞の行だけを取り出す）")
    parser.add_argument("--only", nargs="*", default=None, metavar="表",
                        help="tables で作る表（stakes_ability / stakes_race_day / form_ability / form_race_day。省略すると全部）")
    parser.add_argument("--variants", nargs="*", default=None, metavar="作り方", help="run で回す作り方（省略すると全部）")
    parser.add_argument("--force", action="store_true", help="run で、済んだ作り方も回し直す")
    parser.add_argument("--threads", type=int, default=6, help="run の学習のスレッド数（既定: 6）")
    parser.add_argument("--tables", type=Path, default=_DEFAULT_TABLES, help="学習データの表の置き場所")
    parser.add_argument("--predictions", type=Path, default=_DEFAULT_PREDICTIONS, help="予測の表の置き場所")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
