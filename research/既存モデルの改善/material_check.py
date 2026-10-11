"""新しい材料（予想のまとまり）を全頭の予想に足して、時点ごと・目的変数（3着以内・1着）ごとに7つの区切りで今の本番と比べる（研究「既存モデルの改善」の入口⑭）。

    uv run python research/既存モデルの改善/material_check.py tables  --material 能力スコア                    # 今の本番の表に材料を足した表を作る（材料によっては元DB を開く）
    uv run python research/既存モデルの改善/material_check.py run     --material 能力スコア                    # 足した作り方を、時点と目的変数ごとに7つの区切りで学習する（1つ 10〜30分。済んだものは飛ばす）
    uv run python research/既存モデルの改善/material_check.py run     --material 能力スコア --variants ascore-day_before   # 1つだけ（1着のモデルは <材料>-win-<時点>）
    uv run python research/既存モデルの改善/material_check.py summary --material 能力スコア                    # 時点ごとの採否の表を書く
    uv run python research/既存モデルの改善/material_check.py --list                                          # 確かめられる材料の一覧

展開スコアの確かめ（入口⑬）と同じ流れを、材料を差し替えられる形にしたもの。元の表は入口⑬が作った、今の本番の列を全部持つ表（``tables/dscore_*``）。
比べる相手（今の本番の6つのモデルの列と、7つの区切りで学んだ予測）は ``analysis/material_check/current_production.py`` にだけ書いてある。
目的変数は1着のモデルなら ``WinTargetData`` で持ち替える。
出るもの（Git 対象外）: ``reports/既存モデルの改善/tables/<材料>_*``・``predictions/<材料>_*``・``compare/<材料>-<日付>.md``。
採用の基準（結果を見る前に決めた。設計書「買うレースと買い目を決める」07 の 1）: テスト期間のログ損失が今の予想より小さい区切りが 7つのうち 5つ以上あり、
全期間でも小さいこと。満たした時点・目的変数だけ本番に足し、道具「印の成績」で全券種の回収率が悪くなっていないことを見る。
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

from yosou.form_aptitude_top3.dataset import WinTargetData  # noqa: E402
from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH  # noqa: E402
from yosou.shared.dataset import WIN  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 一番人気を疑う.analysis.evaluation import TopPickSummary, TopPickTable  # noqa: E402
from 既存モデルの改善.analysis.head_to_head import MIN_BETTER_WINDOWS, PredictionTruth, TimingComparison  # noqa: E402
from 既存モデルの改善.analysis.material_check import (  # noqa: E402
    MATERIALS,
    Material,
    MaterialComparisonSpec,
    material_comparisons,
    material_named,
    material_table_named,
    material_tables,
)
from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore, WalkForwardRunner, WindowTrainer  # noqa: E402
from 既存モデルの改善.analysis.win_model import WinPredictionTruth  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS  # noqa: E402
from 既存モデルの改善.win_check import _pin_to_p_cores as pin_to_p_cores  # noqa: E402  学習の下ごしらえは入口⑪と同じ
from 既存モデルの改善.win_check import _with_threads as with_threads  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
DEFAULT_ROOT = _REPORTS / "既存モデルの改善"


def main() -> None:
    args = _parser().parse_args()
    if args.list:
        for name, material in MATERIALS.items():
            print(f"{name}: まとまり {material.group}・{len(material.names)}個（{'・'.join(t.label for t in material.timings)}）。{material.design}")
        return
    if args.step is None or args.material is None:
        raise SystemExit("step と --material を指定してください（--list で材料の一覧）")
    material = material_named(args.material)
    {"tables": _tables, "run": _run, "summary": _summary}[args.step](args, material)


def _tables(args: argparse.Namespace, material: Material) -> None:
    store = TableStore(args.root / "tables")
    builder = material.builder()
    with db.open_db(args.db) as con:
        print(f"{material.label}: 材料の元になる記録を読んでいます …", flush=True)
        builder.prepare(con)
    for table in (table for table in material_tables(material) if not args.only or table.name in args.only):
        source = TableStore(args.reports / table.base_research / "tables")
        if not source.exists(table.base):
            raise FileNotFoundError(f"{table.label}: 元の表 {args.reports / table.base_research / 'tables' / table.base} がありません（development_score_check.py tables で作る）")
        print(f"{table.label}: 元の表 {table.base} に{material.label}を足しています …", flush=True)
        built = builder.build(source.read(table.base, table.base_catalog), table.timing)
        folder = store.write(table.name, built)
        filled = " ".join(f"{column}={built.features[column].notna().mean():.3f}" for column in material.names)
        print(f"{table.name}: {len(built):,}行・特徴量 {built.features.shape[1]}個 → {folder}\n  値のある行の割合: {filled}", flush=True)


def _run(args: argparse.Namespace, material: Material) -> None:
    pin_to_p_cores()
    settings = with_threads(HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH), args.threads)
    runner = WalkForwardRunner(WindowTrainer(settings), WINDOWS)
    predictions, tables = PredictionStore(args.root / "predictions"), TableStore(args.root / "tables")
    for spec in [spec for spec in material_comparisons(material) if not args.variants or spec.key in args.variants]:
        variant = spec.added
        if predictions.exists(variant.model, variant.key) and not args.force:
            print(f"{variant.name}: 済んでいるので飛ばします", flush=True)
            continue
        if not tables.exists(variant.model):
            raise FileNotFoundError(f"{variant.name}: 表 {args.root / 'tables' / variant.model} がありません（material_check.py tables で作る）")
        print(f"{variant.name}: 表 {variant.model} を読んでいます …", flush=True)
        data = tables.read(variant.model, material_table_named(material, variant.model).catalog)
        if spec.label == WIN:
            data = WinTargetData().training(data)
        frame, log = runner.run(data, variant)
        print(f"{variant.name}: {predictions.write(variant.model, variant.key, frame, log)}", flush=True)


def _summary(args: argparse.Namespace, material: Material) -> None:
    store = PredictionStore(args.root / "predictions")
    lines = [f"# {material.label}を足した比べ — 結果（{args.day}）", "", "JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
             f"採用の基準: テスト期間のログ損失が今の予想より小さい区切りが 7つのうち {MIN_BETTER_WINDOWS}つ以上あり、全期間でも小さいこと。",
             f"今の予想は本番と同じ材料（設計書 07 の表）。足した作り方はそれに{material.label}（{material.group} の {len(material.names)}個）を足したもの。{material.design}", ""]
    for spec in material_comparisons(material):
        current_root = args.reports / spec.current.research
        current_store = PredictionStore(current_root / "predictions")
        if not (current_store.exists(spec.current.table, spec.current.key) and store.exists(spec.added.model, spec.added.key)):
            lines += [f"## {spec.timing.label}・{spec.current.target}", "", "予測がまだ無い。", ""]
            continue
        truth_type = WinPredictionTruth if spec.label == WIN else PredictionTruth
        current = truth_type(current_root / "tables", current_root / "predictions").read(spec.current.table, spec.current.key)
        added = truth_type(args.root / "tables", args.root / "predictions").read(spec.added.model, spec.added.key)
        lines += _timing_section(spec, current, added)
    out = args.out or (args.root / "compare" / f"{material.label}-{args.day:%Y%m%d}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {out}", flush=True)


def _timing_section(spec: MaterialComparisonSpec, current: pd.DataFrame, added: pd.DataFrame) -> list[str]:
    comparison = TimingComparison(label=spec.label)
    current, added = comparison.common(current, added)
    table = comparison.by_window(current, added)
    verdict = "採用の基準を満たす" if comparison.adopted(table) else "採用の基準を満たさない"
    print(f"{spec.timing.label}・{spec.current.target}: {verdict}", flush=True)
    lines = [f"## {spec.timing.label}・{spec.current.target}: {spec.current_name} と {spec.added.name}", "",
             f"**{verdict}**（両方にある {len(current):,} 行で比べた）", "",
             "### 区切りごとのログ損失（テスト期間）", "", table.to_markdown(index=False), ""]
    if spec.label == WIN:
        return lines
    rows = [TopPickSummary().row(TopPickTable().build(frame), name)
            for frame, name in ((current, spec.current_name), (added, spec.added.name))]
    return lines + ["### ◎と1番人気（研究「一番人気を疑う」と同じ指標）", "", pd.DataFrame(rows).to_markdown(index=False), ""]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="新しい材料を全頭の予想に足して、7つの区切りで今の本番と比べる", allow_abbrev=False)
    parser.add_argument("step", nargs="?", choices=("tables", "run", "summary"), help="tables（表を作る）・run（学習する）・summary（比べた表を書く）")
    parser.add_argument("--material", choices=tuple(MATERIALS), default=None, help="確かめる材料（--list で一覧）")
    parser.add_argument("--list", action="store_true", help="確かめられる材料の一覧を出して終わる")
    parser.add_argument("--only", nargs="*", default=None, metavar="表", help="tables で作る表（省略すると全部）")
    parser.add_argument("--variants", nargs="*", default=None, metavar="作り方", help="run で回す作り方（<材料>-<時点>・<材料>-win-<時点>。省略すると全部）")
    parser.add_argument("--force", action="store_true", help="run で、済んだ作り方も回し直す")
    parser.add_argument("--threads", type=int, default=6, help="run の学習のスレッド数（既定: 6）")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="表（tables/）と予測（predictions/）と結果（compare/）の置き場所")
    parser.add_argument("--out", type=Path, default=None, help="summary の結果を書くファイル（既定: compare/<材料>-<日付>.md）")
    parser.add_argument("--day", type=date.fromisoformat, default=date.today(), help="summary の結果のファイル名と題に付ける日付")
    parser.add_argument("--reports", type=Path, default=_REPORTS, help="元の表と今の本番の予測を探す reports の場所（その下の研究ごとのフォルダ）")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
