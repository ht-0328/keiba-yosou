"""対戦レーティング（予想のまとまり O）を全頭の3着以内の予想に足して、時点ごとに7つの区切りで比べる（研究「既存モデルの改善」の入口⑧）。

    uv run python research/既存モデルの改善/h2h_check.py tables                      # 元の表に対戦レーティングを足した表を作る（元DB を開く）
    uv run python research/既存モデルの改善/h2h_check.py run                         # 作り方ごとに7つの区切りで学習する（1つ 30〜60分。済んだものは飛ばす）
    uv run python research/既存モデルの改善/h2h_check.py run --variants h2h-thursday  # 1つだけ
    uv run python research/既存モデルの改善/h2h_check.py summary                     # 時点ごとの採否と、◎と1番人気の表を書く

元の表は、研究「一番人気を疑う」の移したあとの確かめ（``port_check.py tables``）が予想のパッケージの組み立て関数で作った今の本番と同じ
学習データ（--base-tables）。無ければ同じ組み立て関数でここに作る。対戦レーティングは予想のパッケージと同じ部品で作る。
区切りと区切りごとの学習（LightGBM と CatBoost。ハイパーパラメータは予想の初期値）はこの研究のもの。
出るもの（Git 対象外）: ``reports/既存モデルの改善/tables/h2h_*``・``predictions/h2h_*``・``compare/対戦レーティング-<日付>.md``。
学習は、同じマシンのほかの学習とぶつからないように1つずつ走らせ、Windows では P コア（論理 CPU 0〜11）に絞る。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db  # noqa: E402

from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH  # noqa: E402
from yosou.shared.dataset import HISTORY_FIRST_DAY, TrainingData  # noqa: E402
from yosou.shared.repository import FactTableRepository, HeadToHeadRunRepository, TargetScope  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 一番人気を疑う.analysis.evaluation import TopPickSummary, TopPickTable  # noqa: E402
from 既存モデルの改善.analysis.head_to_head import (  # noqa: E402
    BASE_TABLES,
    H2H_COMPARISONS,
    H2H_NAMES,
    H2H_VARIANTS,
    MIN_BETTER_WINDOWS,
    BaseTable,
    PredictionTruth,
    RatedTableBuilder,
    TimingComparison,
    TimingComparisonSpec,
    base_table_rated,
)
from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore, WalkForwardRunner, WindowTrainer  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = _REPO_ROOT / "reports" / "既存モデルの改善"
DEFAULT_BASE_TABLES = _REPO_ROOT / "reports" / "一番人気を疑う" / "移したあとの確かめ" / "tables"
#: P コア（論理 CPU 0〜11）のマスク。LightGBM と CatBoost が E コアに載ると止まったように遅くなることがある。
_P_CORES = 0xFFF


def main() -> None:
    args = _parser().parse_args()
    {"tables": _tables, "run": _run, "summary": _summary}[args.step](args)


def _tables(args: argparse.Namespace) -> None:
    store = TableStore(args.root / "tables")
    with db.open_db(args.db) as con:
        FactTableRepository(con).ensure()
        print("元DB から 2011年からの平地の全出走の着順を読んでいます …", flush=True)
        runs = HeadToHeadRunRepository(con, HISTORY_FIRST_DAY).read(TargetScope.since(HISTORY_FIRST_DAY))
        bases = {table.name: _base(table, store, args, con) for table in BASE_TABLES
                 if not args.only or table.rated_name in args.only}
    for name, base in bases.items():
        table = next(table for table in BASE_TABLES if table.name == name)
        print(f"{table.label}: 対戦レーティングを足しています …", flush=True)
        rated = RatedTableBuilder().build(base, runs)
        folder = store.write(table.rated_name, rated)
        filled = " ".join(f"{column}={rated.features[column].notna().mean():.3f}" for column in H2H_NAMES)
        print(f"{table.rated_name}: {len(rated):,}行・特徴量 {rated.features.shape[1]}個 → {folder}\n  値のある行の割合: {filled}", flush=True)


def _base(table: BaseTable, store: TableStore, args: argparse.Namespace, con) -> TrainingData:
    """元の表。``--base-tables`` にあれば読み、無ければ予想のパッケージの組み立て関数で作ってこの研究の表の置き場所に保存する。"""
    if TableStore(args.base_tables).exists(table.name):
        print(f"{table.label}: {args.base_tables / table.name} を読んでいます …", flush=True)
        return TableStore(args.base_tables).read(table.name, table.catalog)
    print(f"{table.label}: 学習データを作っています …", flush=True)
    base = table.builder(con).build_training_data(table.period)
    store.write(table.name, base)
    return base


def _run(args: argparse.Namespace) -> None:
    _pin_to_p_cores()
    settings = _with_threads(HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH), args.threads)
    runner = WalkForwardRunner(WindowTrainer(settings), WINDOWS)
    predictions = PredictionStore(args.root / "predictions")
    tables = TableStore(args.root / "tables")
    chosen = [variant for variant in H2H_VARIANTS if not args.variants or variant.key in args.variants]
    for variant in chosen:
        if predictions.exists(variant.model, variant.key) and not args.force:
            print(f"{variant.name}: 済んでいるので飛ばします", flush=True)
            continue
        data = tables.read(variant.model, base_table_rated(variant.model).rated_catalog)
        frame, log = runner.run(data, variant)
        print(f"{variant.name}: {predictions.write(variant.model, variant.key, frame, log)}", flush=True)


def _summary(args: argparse.Namespace) -> None:
    truth = PredictionTruth(args.root / "tables", args.root / "predictions")
    store = PredictionStore(args.root / "predictions")
    lines = [f"# 対戦レーティングを足した比べ — 結果（{args.day}）", "", "JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
             f"採用の基準: テスト期間のログ損失が今の予想より小さい区切りが 7つのうち {MIN_BETTER_WINDOWS}つ以上あり、全期間でも小さいこと。",
             "今の予想は本番と同じ材料（木曜・前日は馬の力の材料 M と J、当日は今の材料 A〜L と券種の支持 N）。", ""]
    for spec in H2H_COMPARISONS:
        if not (store.exists(spec.current.model, spec.current.key) and store.exists(spec.rated.model, spec.rated.key)):
            lines += [f"## {spec.timing.label}", "", "予測がまだ無い。", ""]
            continue
        lines += _timing_section(spec, truth)
    out = args.out or (args.root / "compare" / f"対戦レーティング-{args.day:%Y%m%d}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {out}", flush=True)


def _timing_section(spec: TimingComparisonSpec, truth: PredictionTruth) -> list[str]:
    comparison = TimingComparison()
    current, rated = comparison.common(truth.read(spec.current.model, spec.current.key),
                                       truth.read(spec.rated.model, spec.rated.key))
    table = comparison.by_window(current, rated)
    rows = [TopPickSummary().row(TopPickTable().build(frame), variant.name)
            for frame, variant in ((current, spec.current), (rated, spec.rated))]
    verdict = "採用の基準を満たす" if comparison.adopted(table) else "採用の基準を満たさない"
    return [f"## {spec.timing.label}: {spec.current.name} と {spec.rated.name}", "",
            f"**{verdict}**（両方にある {len(current):,} 行で比べた）", "",
            "### 区切りごとのログ損失（テスト期間）", "", table.to_markdown(index=False), "",
            "### ◎と1番人気（研究「一番人気を疑う」と同じ指標）", "", pd.DataFrame(rows).to_markdown(index=False), ""]


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
    """Windows では、このプロセスを P コアだけで動かす（学習のスレッドも従う）。ほかの OS では何もしない。

    ハンドルとマスクは 64 ビットなので、ctypes に型を教えてから呼ぶ（教えないと 32 ビットに切られ、黙って失敗する）。
    失敗したら止める（全コアで走ると、同じマシンのほかの学習とぶつかる）。
    """
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    kernel.SetProcessAffinityMask.restype = wintypes.BOOL
    if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), _P_CORES):
        raise OSError(f"P コアへの割り当てに失敗しました（エラー {ctypes.get_last_error()}）")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="対戦レーティングを足した比べ", allow_abbrev=False)
    parser.add_argument("step", choices=("tables", "run", "summary"), help="tables（表を作る）・run（学習する）・summary（表を書く）")
    parser.add_argument("--only", nargs="*", default=None, metavar="表", help="tables で作る表（h2h_ability / h2h_pool）")
    parser.add_argument("--variants", nargs="*", default=None, metavar="作り方", help="run で回す作り方（省略すると全部）")
    parser.add_argument("--force", action="store_true", help="run で、済んだ作り方も回し直す")
    parser.add_argument("--threads", type=int, default=6, help="run の学習のスレッド数（既定: 6）")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="表（tables/）と予測（predictions/）と結果（compare/）の置き場所")
    parser.add_argument("--base-tables", type=Path, default=DEFAULT_BASE_TABLES,
                        help="元の表の置き場所（研究「一番人気を疑う」の移したあとの確かめの表。無ければ作る）")
    parser.add_argument("--out", type=Path, default=None, help="summary の結果を書くファイル（既定: compare/対戦レーティング-<日付>.md）")
    parser.add_argument("--day", type=date.fromisoformat, default=date.today(), help="summary の結果のファイル名と題に付ける日付")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
