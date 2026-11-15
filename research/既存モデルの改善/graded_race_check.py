"""重賞に特化して3着以内と1着を予想する（設計書「重賞に特化して3着以内と1着を予想」）を、1年ずつの7つの区切りで確かめる（研究「既存モデルの改善」の入口⑮）。

    uv run python research/既存モデルの改善/graded_race_check.py tables                       # W を元DB から読み、手本の表に W と K を付ける表を作る（元DB を開く。2分ほど）
    uv run python research/既存モデルの改善/graded_race_check.py run                          # 作り方ごとに7つの区切りで学習する（1つ 30〜40分。済んだものは飛ばす）
    uv run python research/既存モデルの改善/graded_race_check.py run --variants graded-top3 general-top3
    uv run python research/既存モデルの改善/graded_race_check.py summary                      # 重賞の行だけの確率の誤差を、作り方ごと・区切りごとに比べる
    uv run python research/既存モデルの改善/graded_race_check.py daybias-tables               # D（その日の馬場の傾向）を元DB から読み、手本の表に付ける表を作る（元DB を開く）

学習の行は中央の平地の全レース（今の本番の当日の表 ``tables/dscore_race_day``、1着は勝ち切る材料 Q 入りの ``tables/dscore_finish_race_day``）。
重賞の行には作り方ごとの重み（この予想は 5）を付け、W（重賞の格と実績）と K（その重賞の傾向。引退した予想の重賞だけの表 ``tables/stakes_race_day`` の列）を足す。
測るのは、テストの年の重賞の行だけ（設計書 16 の 4）。区切りは重賞の予想と同じ1年ずつの7つ（``STAKES_WINDOWS``）。
出るもの（Git 対象外）: ``reports/既存モデルの改善/tables/graded_extra/``・``predictions/graded_race_day/<作り方>.pkl``・``compare/重賞に特化-<日付>.md``。
学習は、同じマシンのほかの学習とぶつからないように1つずつ走らせ、Windows では P コア（論理 CPU 0〜11）に絞る。
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db  # noqa: E402

from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH  # noqa: E402
from yosou.shared.dataset import HORSE_ID, RACE_ID, TOP3, WIN  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402
from yosou.stakes_tendency_top3.feature import RACE_DAY_CATALOG as STAKES_RACE_DAY_CATALOG  # noqa: E402

from 既存モデルの改善.analysis.development_score.score_tables import score_table_named  # noqa: E402
from 既存モデルの改善.analysis.graded_race import (  # noqa: E402
    D_FEATURES,
    GRADED_VARIANTS,
    IS_GRADED,
    K_NAMES,
    PREDICTION_TABLE,
    TOP3_TABLE,
    WIN_TABLE,
    DayBiasReader,
    GradedMaterialReader,
    GradedTableBuilder,
    graded_variant_keyed,
)
from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from yosou.shared.feature import FeatureCatalog  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore, WalkForwardRunner, WindowTrainer  # noqa: E402
from 既存モデルの改善.analysis.windows import STAKES_WINDOWS, TestWindow  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPORTS = _REPO_ROOT / "reports" / "既存モデルの改善"
_DEFAULT_TABLES = _REPORTS / "tables"
_DEFAULT_PREDICTIONS = _REPORTS / "predictions"
#: W・K の表の置き場所（tables/ の下）と、W を付ける学習データの最初の開催日。
_EXTRA_FOLDER = "graded_extra"
#: D（その日の馬場の傾向）の表の置き場所（tables/ の下）。
_DAY_BIAS_FOLDER = "day_bias_extra"
_FIRST_DAY = date(2012, 1, 1)
#: K の元にする表（引退した重賞の予想の当日の表）。
_STAKES_TABLE = "stakes_race_day"
#: 前の年の区切り（1年ずつ。テスト 2015〜2019年）。学習の始まりは表の始まり（前日の表は 2012年）。当日の表（2017年から）では使えない。
EARLY_WINDOWS: tuple[TestWindow, ...] = tuple(
    TestWindow(f"{year}年", date(year - 1, 1, 1), date(year, 1, 1), date(year, 12, 31)) for year in range(2015, 2020)
)
#: 区切りの並びの名前 → （区切り, 予測を保存する名前に付ける字）。
_WINDOW_SETS = {"stakes": (STAKES_WINDOWS, ""), "early": (EARLY_WINDOWS, "-early")}
#: P コア（論理 CPU 0〜11）のマスク。
_P_CORES = 0xFFF
#: Windows の優先度「通常以下」（BELOW_NORMAL_PRIORITY_CLASS）。
_BELOW_NORMAL = 0x4000
#: ログ損失で確率を 0・1 から離す幅。
_EPS = 1e-15


def main() -> None:
    args = _parser().parse_args()
    {"tables": _tables, "daybias-tables": _day_bias_tables, "run": _run, "summary": _summary}[args.step](args)


def _tables(args: argparse.Namespace) -> None:
    """W を元DB から読み、K を重賞だけの表から取り出して、元の表ごとに同じ行の並びの W・K の表を書く。"""
    started = time.perf_counter()
    with db.open_db(args.db) as con:
        materials = GradedMaterialReader(con).read(_FIRST_DAY)
    print(f"W: {len(materials):,}行・{time.perf_counter() - started:.0f}秒", flush=True)
    store = TableStore(args.tables)
    stakes = store.read(_STAKES_TABLE, STAKES_RACE_DAY_CATALOG)
    tendency = pd.DataFrame({"race_id": stakes.ids[RACE_ID].astype(str).to_numpy(),
                             "horse_id": stakes.ids[HORSE_ID].astype(str).to_numpy(),
                             **{name: stakes.features[name].to_numpy() for name in K_NAMES}})
    folder = args.tables / _EXTRA_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    for table in (TOP3_TABLE, WIN_TABLE):
        base = store.read(table, score_table_named(table).catalog)
        extra = GradedTableBuilder().extra(base, materials, tendency)
        extra.reset_index(drop=True).to_pickle(folder / f"{table}.pkl")
        graded = extra[IS_GRADED].eq(1.0)
        share = extra.loc[graded, K_NAMES[0]].notna().mean()
        print(f"{table}: {len(extra):,}行・重賞の行 {graded.sum():,}・重賞の行で K のある割合 {share:.3f}", flush=True)


def _day_bias_tables(args: argparse.Namespace) -> None:
    """D を元DB から読み、元の表ごとに同じ行の並びの D の表を書く。"""
    started = time.perf_counter()
    with db.open_db(args.db) as con:
        materials = DayBiasReader(con).read(_FIRST_DAY)
    print(f"D: {len(materials):,}行・{time.perf_counter() - started:.0f}秒", flush=True)
    store = TableStore(args.tables)
    folder = args.tables / _DAY_BIAS_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    names = [feature.name for feature in D_FEATURES]
    for table in (TOP3_TABLE, WIN_TABLE):
        base = store.read(table, score_table_named(table).catalog)
        keys = pd.DataFrame({"race_id": base.ids[RACE_ID].astype(str).to_numpy(), "horse_id": base.ids[HORSE_ID].astype(str).to_numpy()})
        aligned = keys.merge(materials, on=["race_id", "horse_id"], how="left")
        if len(aligned) != len(keys):
            raise ValueError("D の表に、同じ（レースID, 馬ID）の行が2つ以上あります")
        aligned[names].astype("float64").to_pickle(folder / f"{table}.pkl")
        print(f"{table}: {len(aligned):,}行・D のある割合 {aligned[names[1]].notna().mean():.3f}", flush=True)


def _run(args: argparse.Namespace) -> None:
    """作り方ごとに7つの区切りで学習し、予測を残す。同じ元の表の作り方は、表を1回だけ読む。"""
    _pin_to_p_cores()
    predictions, tables = PredictionStore(args.predictions), TableStore(args.tables)
    settings = _with_threads(HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH), args.threads)
    windows, suffix = _WINDOW_SETS[args.windows]
    runner = WalkForwardRunner(WindowTrainer(settings), windows)
    chosen = [graded_variant_keyed(key) for key in args.variants] if args.variants else list(GRADED_VARIANTS)
    loaded: dict[str, object] = {}
    for variant in chosen:
        if predictions.exists(PREDICTION_TABLE, variant.key + suffix) and not args.force:
            print(f"{variant.name}: 済んでいるので飛ばします", flush=True)
            continue
        if variant.model not in loaded:
            loaded.clear()
            loaded[variant.model] = _with_extra(tables, args.tables, variant.model)
        frame, log = runner.run(loaded[variant.model], variant)
        print(f"{variant.name}: {predictions.write(PREDICTION_TABLE, variant.key + suffix, frame, log)}", flush=True)


def _with_extra(tables: TableStore, root: Path, table: str):
    """元の表に W・K の列（と、あれば D の列）を付けた学習データ。W・K の表の無い元の表（前日の表）は、そのまま。"""
    base = tables.read(table, score_table_named(table).catalog)
    if not (root / _EXTRA_FOLDER / f"{table}.pkl").exists():
        return base
    extra = pd.read_pickle(root / _EXTRA_FOLDER / f"{table}.pkl").set_axis(base.features.index)
    attached = GradedTableBuilder().attach(base, extra)
    day_bias = root / _DAY_BIAS_FOLDER / f"{table}.pkl"
    if not day_bias.exists():
        return attached
    added = pd.read_pickle(day_bias).set_axis(base.features.index)
    return replace(attached, features=pd.concat([attached.features, added], axis=1),
                   catalog=FeatureCatalog(attached.catalog.features + D_FEATURES))


def _summary(args: argparse.Namespace) -> None:
    """テストの年の重賞の行だけのログ損失を、作り方ごと・区切りごとに出す（設計書 16 の 4）。"""
    predictions, tables = PredictionStore(args.predictions), TableStore(args.tables)
    labels = {label: _graded_labels(tables, args.tables, table, label) for table, label in ((TOP3_TABLE, TOP3), (WIN_TABLE, WIN))}
    windows = [window.name for window in STAKES_WINDOWS]
    lines = [f"# 重賞に特化した予想: テストの年の重賞の行だけのログ損失（{date.today().isoformat()}）", "",
             "小さいほど良い。「手本より小さい区切り」は、手本を重賞だけに使ったときより小さかった区切りの数。", ""]
    for label in (TOP3, WIN):
        rows = [_loss_row(predictions, variant, labels[label]) for variant in GRADED_VARIANTS
                if variant.label == label and predictions.exists(PREDICTION_TABLE, variant.key)]
        if not rows:
            continue
        general = next((row for row in rows if row[0].startswith("手本")), None)
        lines += [f"## {'3着以内' if label == TOP3 else '1着'}", "",
                  "| 作り方 | 行数 | 全体 | 手本より小さい区切り | " + " | ".join(windows) + " |",
                  "|---|---|---|---|" + "---|" * len(windows)]
        for name, total, per, count in rows:
            wins = "―" if general is None or name == general[0] else f"{int((per < general[2]).sum())}/{len(per)}"
            values = " | ".join(f"{per.get(window, np.nan):.5f}" for window in windows)
            lines.append(f"| {name} | {count:,} | {total:.5f} | {wins} | {values} |")
        lines.append("")
    out = _REPORTS / "compare" / f"重賞に特化-{date.today().isoformat()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"→ {out}")


def _graded_labels(tables: TableStore, root: Path, table: str, label: str) -> pd.DataFrame:
    """元の表の重賞の行の（レースID, 馬ID, 目的変数）。"""
    base = tables.read(table, score_table_named(table).catalog)
    extra = pd.read_pickle(root / _EXTRA_FOLDER / f"{table}.pkl")
    keyed = pd.DataFrame({"race_id": base.ids[RACE_ID].astype(str).to_numpy(), "horse_id": base.ids[HORSE_ID].astype(str).to_numpy(),
                          "y": base.targets[label].to_numpy(), "graded": extra[IS_GRADED].to_numpy()})
    return keyed[keyed["graded"].eq(1.0)].dropna(subset=["y"])


def _loss_row(predictions: PredictionStore, variant, labels: pd.DataFrame):
    """（作り方の名前, 全体のログ損失, 区切りごとのログ損失, 行数）。"""
    frame = predictions.read(PREDICTION_TABLE, variant.key)
    test = frame[frame["期間"].eq("テスト")]
    keyed = test.assign(race_id=test[RACE_ID].astype(str), horse_id=test[HORSE_ID].astype(str))
    joined = keyed.merge(labels, on=["race_id", "horse_id"], how="inner")
    per = joined.groupby("区切り").apply(lambda group: _logloss(group["y"], group["確率"]), include_groups=False)
    return variant.name, _logloss(joined["y"], joined["確率"]), per, len(joined)


def _logloss(y: pd.Series, p: pd.Series) -> float:
    actual, prob = y.to_numpy(dtype=float), np.clip(p.to_numpy(dtype=float), _EPS, 1 - _EPS)
    return float(-np.mean(actual * np.log(prob) + (1 - actual) * np.log(1 - prob)))


def _with_threads(settings: HyperparameterSettings, threads: int) -> HyperparameterSettings:
    """学習のスレッド数を ``threads`` にした設定（木の作り方は変わらない）。"""
    values = settings.to_dict()
    values["lightgbm"]["params"]["n_jobs"] = threads
    values["catboost"]["params"]["thread_count"] = threads
    return HyperparameterSettings.from_dict(values)


def _pin_to_p_cores() -> None:
    """Windows では、このプロセスを P コアだけで、ふつうより低い優先度で動かす（開催日の発走前の通知の予想を先に動かすため）。
    ほかの OS では何もしない。"""
    if sys.platform != "win32":
        return
    import ctypes

    kernel = ctypes.windll.kernel32
    kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), _P_CORES)
    kernel.SetPriorityClass(kernel.GetCurrentProcess(), _BELOW_NORMAL)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="重賞に特化した予想の確かめ", allow_abbrev=False)
    parser.add_argument("step", choices=("tables", "daybias-tables", "run", "summary"),
                        help="tables（W・K の表を作る）・daybias-tables（D の表を作る）・run（学習する）・summary（比べる）")
    parser.add_argument("--variants", nargs="*", default=None, metavar="作り方",
                        help="run で回す作り方（並べた順に回す。省略すると全部）")
    parser.add_argument("--windows", choices=tuple(_WINDOW_SETS), default="stakes",
                        help="run の区切り（stakes: テスト 2020〜2026年、early: テスト 2015〜2019年。前日の表だけ。予測の名前に -early が付く）")
    parser.add_argument("--force", action="store_true", help="run で、済んだ作り方も回し直す")
    parser.add_argument("--threads", type=int, default=6, help="run の学習のスレッド数（既定: 6）")
    parser.add_argument("--tables", type=Path, default=_DEFAULT_TABLES, help="学習データの表の置き場所")
    parser.add_argument("--predictions", type=Path, default=_DEFAULT_PREDICTIONS, help="予測の表の置き場所")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
