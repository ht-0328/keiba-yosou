"""展開の予想の結果（予想のまとまり P）を全頭の3着以内の予想に足して、時点ごとに7つの区切りで比べる（研究「既存モデルの改善」の入口⑨）。

    uv run python research/既存モデルの改善/pace_check.py fill                         # 展開の予想の年ごとの予測の抜け（2026年の木曜など）を作り足す（学習する）
    uv run python research/既存モデルの改善/pace_check.py tables                       # 今の予想の表に P を足した表を、時点ごとに作る（元DB は開かない）
    uv run python research/既存モデルの改善/pace_check.py run                          # P を足した作り方を、時点ごとに7つの区切りで学習する（済んだものは飛ばす）
    uv run python research/既存モデルの改善/pace_check.py run --variants pace-thursday  # 1つだけ
    uv run python research/既存モデルの改善/pace_check.py summary                      # 時点ごとの採否と、◎と1番人気の表を書く

元の表は、対戦レーティングの確かめ（入口⑧ ``h2h_check.py tables``）が作った今の本番と同じ材料の表（``tables/h2h_ability``・
``tables/h2h_pool_ability``）。P は、予想「展開から着順を予想」の年ごとの確かめの予測（``reports/展開から着順を予想/out_of_sample/``。
その年より前だけで学習した展開のモデルの予測）から、予想のパッケージと同じ部品で作る。今の予想の予測は、入口⑧で同じ区切り・同じ設定で
学習したもの（木曜・前日は対戦レーティングを足した作り方、当日は今の作り方）をそのまま使う。
出るもの（Git 対象外）: ``reports/既存モデルの改善/tables/pace_*``・``predictions/pace_*``・``compare/展開の予想-<日付>.md``。
学習は、同じマシンのほかの学習とぶつからないように1つずつ走らせ、Windows では P コア（論理 CPU 0〜11）に絞る。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH  # noqa: E402
from yosou.race_development.setting import BACKTEST_SETTINGS_PATH  # noqa: E402
from yosou.race_development.workflow import PaceForecastHistory  # noqa: E402
from yosou.race_development.setting import DEFAULT_SETTINGS_PATH as DEVELOPMENT_SETTINGS_PATH  # noqa: E402
from yosou.shared.feature import PredictionTiming  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 一番人気を疑う.analysis.evaluation import TopPickSummary, TopPickTable  # noqa: E402
from 既存モデルの改善.analysis.head_to_head import MIN_BETTER_WINDOWS, PredictionTruth, TimingComparison  # noqa: E402
from 既存モデルの改善.analysis.pace_forecast import (  # noqa: E402
    PACE_COMPARISONS,
    PACE_NAMES,
    PACE_TABLES,
    PACE_VARIANTS,
    ForecastFiller,
    PaceComparisonSpec,
    PaceTableBuilder,
    pace_table_named,
)
from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore, WalkForwardRunner, WindowTrainer  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = _REPO_ROOT / "reports" / "既存モデルの改善"
DEFAULT_DEVELOPMENT_ROOT = _REPO_ROOT / "reports" / "展開から着順を予想"
#: 作り足すときの最後の年（7つの区切りの最後のテスト期間の年）。
LAST_YEAR = 2026
#: P コア（論理 CPU 0〜11）のマスク。LightGBM と CatBoost が E コアに載ると止まったように遅くなることがある。
_P_CORES = 0xFFF


def main() -> None:
    args = _parser().parse_args()
    {"fill": _fill, "tables": _tables, "run": _run, "summary": _summary}[args.step](args)


def _fill(args: argparse.Namespace) -> None:
    """展開の予想の年ごとの予測の抜けを、年ごとの確かめと同じ設定（速さのために学習率を上げたもの）で作り足す。"""
    _pin_to_p_cores()
    settings = _with_threads(HyperparameterSettings.load(BACKTEST_SETTINGS_PATH, defaults=DEVELOPMENT_SETTINGS_PATH), args.threads)
    filler = ForecastFiller(args.development_root, settings, lambda message: print(message, flush=True))
    for timing in PredictionTiming:
        print(f"{timing.label}: 抜けている年 {filler.missing(timing, LAST_YEAR)}", flush=True)
        made = filler.fill(timing, LAST_YEAR)
        print(f"{timing.label}: 作り足した {made or 'なし'}", flush=True)


def _tables(args: argparse.Namespace) -> None:
    store = TableStore(args.root / "tables")
    reader = PaceForecastHistory(args.development_root)
    for table in (table for table in PACE_TABLES if not args.only or table.name in args.only):
        print(f"{table.label}: 展開の予測の年 {reader.years(table.timing)}・{table.base} を読んでいます …", flush=True)
        base = store.read(table.base, table.base_catalog)
        paced = PaceTableBuilder().build(base, reader.read(table.timing), table.catalog)
        folder = store.write(table.name, paced)
        filled = paced.features[list(PACE_NAMES)].notna().any(axis=1)
        years = paced.ids[filled.to_numpy()]["開催日"].dt.year
        print(f"{table.name}: {len(paced):,}行・特徴量 {paced.features.shape[1]}個 → {folder}\n"
              f"  P のある行の割合 {filled.mean():.3f}（{int(years.min())}〜{int(years.max())}年）", flush=True)


def _run(args: argparse.Namespace) -> None:
    _pin_to_p_cores()
    settings = _with_threads(HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH), args.threads)
    runner = WalkForwardRunner(WindowTrainer(settings), WINDOWS)
    predictions = PredictionStore(args.root / "predictions")
    tables = TableStore(args.root / "tables")
    chosen = [variant for variant in PACE_VARIANTS if not args.variants or variant.key in args.variants]
    for variant in chosen:
        if predictions.exists(variant.model, variant.key) and not args.force:
            print(f"{variant.name}: 済んでいるので飛ばします", flush=True)
            continue
        data = tables.read(variant.model, pace_table_named(variant.model).catalog)
        frame, log = runner.run(data, variant)
        print(f"{variant.name}: {predictions.write(variant.model, variant.key, frame, log)}", flush=True)


def _summary(args: argparse.Namespace) -> None:
    truth = PredictionTruth(args.root / "tables", args.root / "predictions")
    store = PredictionStore(args.root / "predictions")
    lines = [f"# 展開の予想を足した比べ — 結果（{args.day}）", "", "JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
             f"採用の基準: テスト期間のログ損失が今の予想より小さい区切りが 7つのうち {MIN_BETTER_WINDOWS}つ以上あり、全期間でも小さいこと。",
             "今の予想は本番と同じ材料（木曜・前日は馬の力の材料 M・対戦レーティング O・市場の評価 J、当日は今の材料 A〜L・券種の支持 N・M）。", ""]
    for spec in PACE_COMPARISONS:
        if not (store.exists(spec.current.model, spec.current.key) and store.exists(spec.paced.model, spec.paced.key)):
            lines += [f"## {spec.timing.label}", "", "予測がまだ無い。", ""]
            continue
        lines += _timing_section(spec, truth)
    out = args.out or (args.root / "compare" / f"展開の予想-{args.day:%Y%m%d}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {out}", flush=True)


def _timing_section(spec: PaceComparisonSpec, truth: PredictionTruth) -> list[str]:
    comparison = TimingComparison()
    current, paced = comparison.common(truth.read(spec.current.model, spec.current.key),
                                       truth.read(spec.paced.model, spec.paced.key))
    table = comparison.by_window(current, paced)
    rows = [TopPickSummary().row(TopPickTable().build(frame), variant.name)
            for frame, variant in ((current, spec.current), (paced, spec.paced))]
    verdict = "採用の基準を満たす" if comparison.adopted(table) else "採用の基準を満たさない"
    return [f"## {spec.timing.label}: {spec.current.name} と {spec.paced.name}", "",
            f"**{verdict}**（両方にある {len(current):,} 行で比べた）", "",
            "### 区切りごとのログ損失（テスト期間）", "", table.to_markdown(index=False), "",
            "### ◎と1番人気（研究「一番人気を疑う」と同じ指標）", "", pd.DataFrame(rows).to_markdown(index=False), ""]


def _with_threads(settings: HyperparameterSettings, threads: int) -> HyperparameterSettings:
    """学習のスレッド数を ``threads`` にした設定（ほかのハイパーパラメータはそのまま）。

    同じマシンでほかの学習が全部のコアを使っていると、スレッドの取り合いで止まったように遅くなるため、数を絞る。
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
    parser = argparse.ArgumentParser(description="展開の予想を足した比べ", allow_abbrev=False)
    parser.add_argument("step", choices=("fill", "tables", "run", "summary"),
                        help="fill（展開の予測の抜けを作る）・tables（表を作る）・run（学習する）・summary（表を書く）")
    parser.add_argument("--only", nargs="*", default=None, metavar="表", help="tables で作る表（pace_thursday / pace_day_before / pace_race_day）")
    parser.add_argument("--variants", nargs="*", default=None, metavar="作り方", help="run で回す作り方（省略すると全部）")
    parser.add_argument("--force", action="store_true", help="run で、済んだ作り方も回し直す")
    parser.add_argument("--threads", type=int, default=6, help="fill と run の学習のスレッド数（既定: 6）")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="表（tables/）と予測（predictions/）と結果（compare/）の置き場所")
    parser.add_argument("--development-root", type=Path, default=DEFAULT_DEVELOPMENT_ROOT,
                        help="予想「展開から着順を予想」の途中の結果の置き場所（out_of_sample/・datasets/）")
    parser.add_argument("--out", type=Path, default=None, help="summary の結果を書くファイル（既定: compare/展開の予想-<日付>.md）")
    parser.add_argument("--day", type=date.fromisoformat, default=date.today(), help="summary の結果のファイル名と題に付ける日付")
    return parser


if __name__ == "__main__":
    main()
