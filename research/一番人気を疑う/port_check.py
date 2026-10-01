"""研究で良かった2つの直し方を予想に移したあと、7つの区切りで今の予想と比べる（研究「一番人気を疑う」の入口⑤）。

    uv run python research/一番人気を疑う/port_check.py tables                       # 学習データの表を作る（元DB を開く。数十分）
    uv run python research/一番人気を疑う/port_check.py run                          # 作り方ごとに7つの区切りで学習する（数時間。済んだものは飛ばす）
    uv run python research/一番人気を疑う/port_check.py run --variants pool-race_day  # 1つだけ
    uv run --with tabulate python research/一番人気を疑う/port_check.py summary      # 時点ごとの採否と、◎と1番人気の表を書く

学習データは予想のパッケージ（``src/yosou/form_aptitude_top3``）の ``pool_dataset_builder``・``ability_dataset_builder`` で作る。
区切りと区切りごとの学習（LightGBM と CatBoost。ハイパーパラメータは予想の初期値）は研究「既存モデルの改善」のもの。
出るもの（Git 対象外）: ``reports/一番人気を疑う/移したあとの確かめ/`` の ``tables/``・``predictions/``・``結果.md``。
学習は、同じマシンのほかの学習とぶつからないように1つずつ走らせ、Windows では P コア（論理 CPU 0〜11）に絞る。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 共通 import db  # noqa: E402

from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 一番人気を疑う.analysis.evaluation import TopPickSummary, TopPickTable  # noqa: E402
from 一番人気を疑う.analysis.port import (  # noqa: E402
    PORT_COMPARISONS,
    PORT_TABLES,
    PORT_VARIANTS,
    PortComparison,
    PortPredictionSource,
    port_table_named,
)
from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore, WalkForwardRunner, WindowTrainer  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = _REPO_ROOT / "reports" / "一番人気を疑う" / "移したあとの確かめ"
#: P コア（論理 CPU 0〜11）のマスク。LightGBM と CatBoost が E コアに載ると止まったように遅くなることがある。
_P_CORES = 0xFFF


def main() -> None:
    args = _parser().parse_args()
    {"tables": _tables, "run": _run, "summary": _summary}[args.step](args)


def _tables(args: argparse.Namespace) -> None:
    store = TableStore(args.root / "tables")
    for table in (table for table in PORT_TABLES if not args.only or table.name in args.only):
        print(f"{table.label}: 学習データを作っています …", flush=True)
        with db.open_db(args.db) as con:
            data = table.builder(con).build_training_data(table.period)
        folder = store.write(table.name, data)
        print(f"{table.label}: {len(data):,}行・特徴量 {data.features.shape[1]}個 → {folder}", flush=True)


def _run(args: argparse.Namespace) -> None:
    _pin_to_p_cores()
    settings = _with_threads(HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH), args.threads)
    runner = WalkForwardRunner(WindowTrainer(settings), WINDOWS)
    predictions = PredictionStore(args.root / "predictions")
    tables = TableStore(args.root / "tables")
    chosen = [variant for variant in PORT_VARIANTS if not args.variants or variant.key in args.variants]
    for variant in chosen:
        if predictions.exists(variant.model, variant.key) and not args.force:
            print(f"{variant.name}: 済んでいるので飛ばします", flush=True)
            continue
        data = tables.read(variant.model, port_table_named(variant.model).catalog)
        frame, log = runner.run(data, variant)
        print(f"{variant.name}: {predictions.write(variant.model, variant.key, frame, log)}", flush=True)


def _summary(args: argparse.Namespace) -> None:
    source = PortPredictionSource(args.root / "tables", args.root / "predictions")
    store = PredictionStore(args.root / "predictions")
    lines = ["# 移したあとの確かめ — 結果", "", "JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
             "採用の基準: テスト期間のログ損失が今の予想より小さい区切りが 7つのうち 5つ以上あり、全期間でも小さいこと。", ""]
    for spec in PORT_COMPARISONS:
        if not (store.exists(spec.current.model, spec.current.key) and store.exists(spec.ported.model, spec.ported.key)):
            lines += [f"## {spec.timing.label}", "", "予測がまだ無い。", ""]
            continue
        lines += _timing_section(spec, source)
    out = args.root / "結果.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {out}", flush=True)


def _timing_section(spec, source: PortPredictionSource) -> list[str]:
    comparison = PortComparison()
    current, ported = comparison.common(source.read(spec.current.model, spec.current.key),
                                        source.read(spec.ported.model, spec.ported.key))
    table = comparison.by_window(current, ported)
    rows = [TopPickSummary().row(TopPickTable().build(frame), variant.name)
            for frame, variant in ((current, spec.current), (ported, spec.ported))]
    verdict = "採用の基準を満たす" if comparison.adopted(table) else "採用の基準を満たさない"
    return [f"## {spec.timing.label}: {spec.current.name} と {spec.ported.name}", "",
            f"**{verdict}**（両方にある {len(current):,} 行で比べた）", "",
            "### 区切りごとのログ損失", "", table.to_markdown(index=False), "",
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
    """Windows では、このプロセスを P コアだけで動かす（学習のスレッドも従う）。ほかの OS では何もしない。"""
    if sys.platform != "win32":
        return
    import ctypes

    kernel = ctypes.windll.kernel32
    kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), _P_CORES)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="移したあとの確かめ", allow_abbrev=False)
    parser.add_argument("step", choices=("tables", "run", "summary"), help="tables（表を作る）・run（学習する）・summary（表を書く）")
    parser.add_argument("--only", nargs="*", default=None, metavar="表", help="tables で作る表（form_pool / form_ability）")
    parser.add_argument("--variants", nargs="*", default=None, metavar="作り方", help="run で回す作り方（省略すると全部）")
    parser.add_argument("--force", action="store_true", help="run で、済んだ作り方も回し直す")
    parser.add_argument("--threads", type=int, default=6, help="run の学習のスレッド数（既定: 6）")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="表と予測と結果の置き場所")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
