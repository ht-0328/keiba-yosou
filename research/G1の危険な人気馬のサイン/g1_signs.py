"""G1の危険な人気馬の10のサインを、人気馬の予想に足して確かめる（研究「G1の危険な人気馬のサイン」の入口）。

    uv run python research/G1の危険な人気馬のサイン/g1_signs.py signs     # 1. 全出走のサインの表を作る（元DB を開く。1分ほど）
    uv run python research/G1の危険な人気馬のサイン/g1_signs.py cases     # 2. G1の人気馬で、サインごとの成績を数える（数秒）
    uv run python research/G1の危険な人気馬のサイン/g1_signs.py base      # 3. 人気馬の予想の学習データを 2012年から作る（元DB を開く。30分ほど）
    uv run python research/G1の危険な人気馬のサイン/g1_signs.py run       # 4. 作り方ごとに7つの区切りで学習する（済んだものは飛ばす）
    uv run python research/G1の危険な人気馬のサイン/g1_signs.py run --variants g1-signs   # 1つだけ
    uv run python research/G1の危険な人気馬のサイン/g1_signs.py summary   # 5. G1の人気馬で比べる表（数秒）
    uv run python research/G1の危険な人気馬のサイン/g1_signs.py marks     # 6. 道具「印の成績」に渡す、G1だけの予測を書く（数秒）
    uv run python research/G1の危険な人気馬のサイン/g1_signs.py rule_flags      # 7'. サインで消を決める決まりの表を書く（1つでも当てはまったら全部・いちばん多い1頭。数秒）
    uv run python research/G1の危険な人気馬のサイン/g1_signs.py marks_summary   # 8. 作り方ごとの印の成績を1つの表に並べる（数秒）

6 のあと、作り方ごとに道具「印の成績」で印と全券種の買い目の成績を出し（7。README の「動かし方」）、8 で並べる。
出るもの（Git 対象外）: ``reports/G1の危険な人気馬のサイン/`` の ``signs.pkl``・``事例.md``・``tables/``・``predictions/``・``結果.md``・``印の成績/``。
学習は、同じマシンのほかの学習とぶつからないように1つずつ走らせ、Windows では P コア（論理 CPU 0〜11）に絞る。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_RESEARCH = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RESEARCH.parent
sys.path[:0] = [str(_RESEARCH), str(_REPO_ROOT / "tools")]

import pandas as pd  # noqa: E402

from 共通 import db, render  # noqa: E402

from yosou.favorites_out_of_top3.dataset import dataset_builder as favorites_builder  # noqa: E402
from yosou.favorites_out_of_top3.feature import CATALOG as FAVORITES_CATALOG  # noqa: E402
from yosou.favorites_out_of_top3.setting import DEFAULT_SETTINGS_PATH as FAVORITES_SETTINGS  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.tables.model_tables import STAKES_TABLE_PERIOD  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore, WalkForwardRunner  # noqa: E402
from 既存モデルの改善.analysis.windows import STAKES_WINDOWS  # noqa: E402

from G1の危険な人気馬のサイン.analysis.mark_inputs import MARKS_FOLDER, MarkInputs  # noqa: E402
from G1の危険な人気馬のサイン.analysis.mark_summary import MarkSummary  # noqa: E402
from G1の危険な人気馬のサイン.analysis.most_signs_rule_flags import MOST_RULE_KEY, MOST_RULE_NAME, MostSignsRuleFlags  # noqa: E402
from G1の危険な人気馬のサイン.analysis.race_scope import EVALUATION_SCOPES  # noqa: E402
from G1の危険な人気馬のサイン.analysis.run_history_repository import RunHistoryRepository  # noqa: E402
from G1の危険な人気馬のサイン.analysis.scope_comparison import ScopeComparison  # noqa: E402
from G1の危険な人気馬のサイン.analysis.scoped_window_trainer import ScopedWindowTrainer  # noqa: E402
from G1の危険な人気馬のサイン.analysis.sign_case_report import SignCaseReport  # noqa: E402
from G1の危険な人気馬のサイン.analysis.sign_rule_flags import RULE_KEY, RULE_NAME, SignRuleFlags  # noqa: E402
from G1の危険な人気馬のサイン.analysis.sign_table_builder import SignTableBuilder  # noqa: E402
from G1の危険な人気馬のサイン.analysis.sign_training_table import SignTrainingTable  # noqa: E402
from G1の危険な人気馬のサイン.analysis.sign_variants import SIGN_VARIANTS, TABLE_NAME  # noqa: E402

#: 消を使わない印の成績の置き場所の名前（``印の成績/<名前>/``）。
NO_DANGER = "no_danger"
_OUT = _REPO_ROOT / "reports" / "G1の危険な人気馬のサイン"
#: 人気馬の予想の学習データ（2012年から。サインを足す前）の表の名前。
_BASE_TABLE = "favorites_2012"
#: P コア（論理 CPU 0〜11）のマスク。LightGBM と CatBoost が E コアに載ると止まったように遅くなることがある。
_P_CORES = 0xFFF


def main() -> None:
    args = _parser().parse_args()
    {"signs": _signs, "cases": _cases, "base": _base, "run": _run, "summary": _summary, "marks": _marks,
     "rule_flags": _rule_flags, "marks_summary": _marks_summary}[args.step](args)


def _signs(args: argparse.Namespace) -> None:
    started = time.perf_counter()
    with db.open_db(args.db) as con:
        runs = RunHistoryRepository().read(con)
    table = SignTableBuilder().build(runs)
    path = args.out / "signs.pkl"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_pickle(path)
    print(f"サインの表: {len(table):,}行・{time.perf_counter() - started:.0f}秒 → {path}", flush=True)


def _cases(args: argparse.Namespace) -> None:
    signs = _read_signs(args)
    _write([table for scope in EVALUATION_SCOPES for table in SignCaseReport(scope).tables(signs)], args.out / "事例.md")


def _base(args: argparse.Namespace) -> None:
    started = time.perf_counter()
    print("人気馬の予想の学習データを 2012年から作っています …", flush=True)
    with db.open_db(args.db) as con:
        data = favorites_builder(con).build_training_data(STAKES_TABLE_PERIOD)
    folder = TableStore(args.out / "tables").write(_BASE_TABLE, data)
    print(f"{len(data):,}行・特徴量 {data.features.shape[1]}個・{time.perf_counter() - started:.0f}秒 → {folder}", flush=True)


def _run(args: argparse.Namespace) -> None:
    _pin_to_p_cores()
    data = SignTrainingTable().attach(TableStore(args.out / "tables").read(_BASE_TABLE, FAVORITES_CATALOG), _read_signs(args))
    predictions = PredictionStore(args.out / "predictions")
    settings = _with_threads(HyperparameterSettings.load(None, defaults=FAVORITES_SETTINGS), args.threads)
    for chosen in (variant for variant in SIGN_VARIANTS if not args.variants or variant.key in args.variants):
        if predictions.exists(TABLE_NAME, chosen.key) and not args.force:
            print(f"{chosen.name}: 済んでいるので飛ばします", flush=True)
            continue
        # 学ぶのは作り方の範囲のレースだけ、予測は全部のレースに出す（G1 で学んだモデルを G2・G3 にも当てるため）
        runner = WalkForwardRunner(ScopedWindowTrainer(settings, chosen.scope), STAKES_WINDOWS)
        frame, log = runner.run(data, chosen.variant)
        print(f"{chosen.name}: {predictions.write(TABLE_NAME, chosen.key, frame, log)}", flush=True)


def _summary(args: argparse.Namespace) -> None:
    data = SignTrainingTable().attach(TableStore(args.out / "tables").read(_BASE_TABLE, FAVORITES_CATALOG), _read_signs(args))
    predictions = PredictionStore(args.out / "predictions")
    made = {variant.key: predictions.read(TABLE_NAME, variant.key) for variant in SIGN_VARIANTS
            if predictions.exists(TABLE_NAME, variant.key)}
    _write([table for scope in EVALUATION_SCOPES for table in ScopeComparison(scope).tables(data, made)], args.out / "結果.md")


def _marks(args: argparse.Namespace) -> None:
    data = SignTrainingTable().attach(TableStore(args.out / "tables").read(_BASE_TABLE, FAVORITES_CATALOG), _read_signs(args))
    inputs = MarkInputs(args.out / "predictions", _REPO_ROOT / "reports" / "既存モデルの改善" / "predictions")
    for path in inputs.write(data, SIGN_VARIANTS):
        print(path, flush=True)


def _rule_flags(args: argparse.Namespace) -> None:
    data = SignTrainingTable().attach(TableStore(args.out / "tables").read(_BASE_TABLE, FAVORITES_CATALOG), _read_signs(args))
    folder = args.out / "predictions" / MARKS_FOLDER / "rule"
    folder.mkdir(parents=True, exist_ok=True)
    for key, rule in ((RULE_KEY, SignRuleFlags()), (MOST_RULE_KEY, MostSignsRuleFlags())):
        path = folder / f"{key}.pkl"
        rule.build(data).to_pickle(path)
        print(path, flush=True)


def _marks_summary(args: argparse.Namespace) -> None:
    names = {NO_DANGER: "消を使わない", RULE_KEY: RULE_NAME, MOST_RULE_KEY: MOST_RULE_NAME} | {variant.key: variant.name for variant in SIGN_VARIANTS}
    tables = [table for scope in EVALUATION_SCOPES for table in MarkSummary(scope).tables(args.out / "印の成績" / scope.key, names)]
    _write(tables, args.out / "印の成績のまとめ.md")


def _read_signs(args: argparse.Namespace) -> pd.DataFrame:
    path = args.out / "signs.pkl"
    if not path.is_file():
        raise FileNotFoundError(f"サインの表がありません（先に signs）: {path}")
    return pd.read_pickle(path)


def _write(tables: list, path: Path) -> None:
    text = render.render(tables, "markdown")
    path.parent.mkdir(parents=True, exist_ok=True)
    render.write(text, path, fmt="markdown")
    print(text)
    print(f"\n保存先: {path}", file=sys.stderr)


def _with_threads(settings: HyperparameterSettings, threads: int) -> HyperparameterSettings:
    """学習のスレッド数を ``threads`` にした設定（ほかのハイパーパラメータは予想の初期値のまま。木の作り方は変わらない）。"""
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
    parser = argparse.ArgumentParser(description="G1の危険な人気馬のサインの確かめ", allow_abbrev=False)
    parser.add_argument("step", choices=("signs", "cases", "base", "run", "summary", "marks", "rule_flags", "marks_summary"),
                        help="signs（サインの表）・cases（サインごとの成績）・base（学習データ）・run（学習）・summary（比べる表）・"
                             "marks（印の成績に渡す予測）・rule_flags（サインで消を決める表）・marks_summary（印の成績を並べる）")
    parser.add_argument("--variants", nargs="*", default=None, metavar="作り方", help="run で回す作り方（省略すると全部）")
    parser.add_argument("--force", action="store_true", help="run で、済んだ作り方も回し直す")
    parser.add_argument("--threads", type=int, default=6, help="run の学習のスレッド数（既定: 6）")
    parser.add_argument("--out", type=Path, default=_OUT, help="出力の置き場所")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
