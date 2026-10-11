"""展開スコア（予想のまとまり S）を全頭の予想に足して、時点ごと・目的変数（3着以内・1着）ごとに7つの区切りで今の本番と比べる（研究「既存モデルの改善」の入口⑬）。

    uv run python research/既存モデルの改善/development_score_check.py tables                      # 展開の予想を足した表に S を足した表を、時点ごとに作る（元DB を開く。2分ほど）
    uv run python research/既存モデルの改善/development_score_check.py run                         # S を足した作り方を、時点と目的変数ごとに7つの区切りで学習する（1つ 12分ほど。済んだものは飛ばす）
    uv run python research/既存モデルの改善/development_score_check.py run --variants dscore-day_before  # 1つだけ（1着のモデルは dscore-win-<時点>）
    uv run python research/既存モデルの改善/development_score_check.py summary                     # 時点ごとの採否の表を書く

元の表は、展開の予想の確かめ（入口⑩ ``pace_check.py tables``）が時点ごとに作った表（``tables/pace_*``。P の 20列を持つ）と、当日の1着は
今の本番と同じ勝ち切る材料（Q）入りの表（研究「回収率100超の施策」の ``tables/finish_pool_ability``。P は無いので、展開の年ごとの確かめの予測から S を作る）。
S（展開スコアと脚質ごとの内訳の 5個）は、P のうち先頭・先団・中団・後方・ハイ・スローの確率と、元DB から作る表 G の材料
（``yosou.development_score``。表 G はレースの年ごとに、その年より前のレースだけで作る）から足す。
今の予想の予測は、木曜は入口⑩の展開の予想を足した作り方（本番）、前日は入口⑧の対戦レーティングを足した作り方（本番）、当日は入口⑧の今の作り方。1着のモデルは入口⑪の予測。目的変数は1着のモデルなら ``WinTargetData`` で持ち替える。
出るもの（Git 対象外）: ``reports/既存モデルの改善/tables/dscore_*``・``predictions/dscore_*``・``compare/展開スコア-<日付>.md``。
採用の基準（結果を見る前に決めた。設計書「買うレースと買い目を決める」07 の 1）: テスト期間のログ損失が今の予想より小さい区切りが 7つのうち 5つ以上あり、
全期間でも小さいこと。学習は、同じマシンのほかの学習とぶつからないように1つずつ走らせ、Windows では P コア（論理 CPU 0〜11）に絞る。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db  # noqa: E402

from yosou.development_score import DEVELOPMENT_SCORE_NAMES, AdvantageRuns, DevelopmentRunRepository  # noqa: E402
from yosou.form_aptitude_top3.dataset import WinTargetData  # noqa: E402
from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH  # noqa: E402
from yosou.race_development.workflow import PaceForecastHistory  # noqa: E402
from yosou.shared.dataset import WIN  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 一番人気を疑う.analysis.evaluation import TopPickSummary, TopPickTable  # noqa: E402
from 既存モデルの改善.analysis.development_score import (  # noqa: E402
    SCORE_COMPARISONS,
    SCORE_TABLES,
    SCORE_VARIANTS,
    ScoreComparisonSpec,
    ScoreTableBuilder,
    score_table_named,
)
from 既存モデルの改善.analysis.head_to_head import MIN_BETTER_WINDOWS, PredictionTruth, TimingComparison  # noqa: E402
from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore, WalkForwardRunner, WindowTrainer  # noqa: E402
from 既存モデルの改善.analysis.win_model import WinPredictionTruth  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS  # noqa: E402
from 既存モデルの改善.win_check import _pin_to_p_cores as pin_to_p_cores  # noqa: E402  学習の下ごしらえは入口⑪と同じ
from 既存モデルの改善.win_check import _with_threads as with_threads  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
DEFAULT_ROOT = _REPORTS / "既存モデルの改善"
DEFAULT_DEVELOPMENT_ROOT = _REPORTS / "展開から着順を予想"


def main() -> None:
    args = _parser().parse_args()
    {"tables": _tables, "run": _run, "summary": _summary}[args.step](args)


def _tables(args: argparse.Namespace) -> None:
    store = TableStore(args.root / "tables")
    with db.open_db(args.db) as con:
        print("2011年からの全出走を読んで、表 G の材料（脚質・ペース・市場の見立て）を作っています …", flush=True)
        prepared = AdvantageRuns().build(DevelopmentRunRepository(con).read())
    for table in (table for table in SCORE_TABLES if not args.only or table.name in args.only):
        source = TableStore(args.reports / table.base_research / "tables")
        if not source.exists(table.base):
            raise FileNotFoundError(f"{table.label}: 元の表 {args.reports / table.base_research / 'tables' / table.base} がありません")
        forecasts = None if table.has_pace else PaceForecastHistory(args.development_root).read(table.timing)
        print(f"{table.label}: 元の表 {table.base} に展開スコアを足しています …", flush=True)
        built = ScoreTableBuilder().build(source.read(table.base, table.base_catalog), prepared, forecasts)
        folder = store.write(table.name, built)
        filled = built.features[list(DEVELOPMENT_SCORE_NAMES)].notna().all(axis=1)
        print(f"{table.name}: {len(built):,}行・特徴量 {built.features.shape[1]}個 → {folder}\n  S のある行の割合 {filled.mean():.3f}", flush=True)


def _run(args: argparse.Namespace) -> None:
    pin_to_p_cores()
    settings = with_threads(HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH), args.threads)
    runner = WalkForwardRunner(WindowTrainer(settings), WINDOWS)
    predictions, tables = PredictionStore(args.root / "predictions"), TableStore(args.root / "tables")
    for spec in [spec for spec in SCORE_VARIANTS if not args.variants or spec.key in args.variants]:
        variant = spec.scored
        if predictions.exists(variant.model, variant.key) and not args.force:
            print(f"{variant.name}: 済んでいるので飛ばします", flush=True)
            continue
        if not tables.exists(variant.model):
            raise FileNotFoundError(f"{variant.name}: 表 {args.root / 'tables' / variant.model} がありません（development_score_check.py tables で作る）")
        print(f"{variant.name}: 表 {variant.model} を読んでいます …", flush=True)
        data = tables.read(variant.model, score_table_named(variant.model).catalog)
        if spec.label == WIN:
            data = WinTargetData().training(data)
        frame, log = runner.run(data, variant)
        print(f"{variant.name}: {predictions.write(variant.model, variant.key, frame, log)}", flush=True)


def _summary(args: argparse.Namespace) -> None:
    store = PredictionStore(args.root / "predictions")
    lines = [f"# 展開スコアを足した比べ — 結果（{args.day}）", "", "JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
             f"採用の基準: テスト期間のログ損失が今の予想より小さい区切りが 7つのうち {MIN_BETTER_WINDOWS}つ以上あり、全期間でも小さいこと。",
             "今の予想は本番と同じ材料（木曜は M・O・P、前日は M・O・J、当日は A〜L・N・M）。足した作り方はそれに展開スコア（S の 5個）を足したもの。", ""]
    for spec in SCORE_COMPARISONS:
        current_root = args.reports / spec.current_research
        current_store = PredictionStore(current_root / "predictions")
        if not (current_store.exists(spec.current_table, spec.current.key) and store.exists(spec.scored.model, spec.scored.key)):
            lines += [f"## {spec.timing.label}・{spec.target}", "", "予測がまだ無い。", ""]
            continue
        truth_type = WinPredictionTruth if spec.label == WIN else PredictionTruth
        current = truth_type(current_root / "tables", current_root / "predictions").read(spec.current_table, spec.current.key)
        scored = truth_type(args.root / "tables", args.root / "predictions").read(spec.scored.model, spec.scored.key)
        lines += _timing_section(spec, current, scored)
    out = args.out or (args.root / "compare" / f"展開スコア-{args.day:%Y%m%d}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {out}", flush=True)


def _timing_section(spec: ScoreComparisonSpec, current: pd.DataFrame, scored: pd.DataFrame) -> list[str]:
    comparison = TimingComparison(label=spec.label)
    current, scored = comparison.common(current, scored)
    table = comparison.by_window(current, scored)
    verdict = "採用の基準を満たす" if comparison.adopted(table) else "採用の基準を満たさない"
    print(f"{spec.timing.label}・{spec.target}: {verdict}", flush=True)
    lines = [f"## {spec.timing.label}・{spec.target}: {spec.current.name} と {spec.scored.name}", "",
             f"**{verdict}**（両方にある {len(current):,} 行で比べた）", "",
             "### 区切りごとのログ損失（テスト期間）", "", table.to_markdown(index=False), ""]
    if spec.label == WIN:
        return lines
    rows = [TopPickSummary().row(TopPickTable().build(frame), variant.name)
            for frame, variant in ((current, spec.current), (scored, spec.scored))]
    return lines + ["### ◎と1番人気（研究「一番人気を疑う」と同じ指標）", "", pd.DataFrame(rows).to_markdown(index=False), ""]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="展開スコアを全頭の予想に足して比べる", allow_abbrev=False)
    parser.add_argument("step", choices=("tables", "run", "summary"), help="tables（表を作る）・run（学習する）・summary（比べた表を書く）")
    parser.add_argument("--only", nargs="*", default=None, metavar="表", help=f"tables で作る表（{' / '.join(t.name for t in SCORE_TABLES)}）")
    parser.add_argument("--variants", nargs="*", default=None, metavar="作り方",
                        help=f"run で回す作り方（{' / '.join(spec.key for spec in SCORE_VARIANTS)}。省略すると全部）")
    parser.add_argument("--force", action="store_true", help="run で、済んだ作り方も回し直す")
    parser.add_argument("--threads", type=int, default=6, help="run の学習のスレッド数（既定: 6）")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="表（tables/）と予測（predictions/）と結果（compare/）の置き場所")
    parser.add_argument("--out", type=Path, default=None, help="summary の結果を書くファイル（既定: compare/展開スコア-<日付>.md）")
    parser.add_argument("--day", type=date.fromisoformat, default=date.today(), help="summary の結果のファイル名と題に付ける日付")
    parser.add_argument("--reports", type=Path, default=_REPORTS, help="元の表と今の本番の予測を探す reports の場所（その下の研究ごとのフォルダ）")
    parser.add_argument("--development-root", type=Path, default=DEFAULT_DEVELOPMENT_ROOT,
                        help="予想「展開から着順を予想」の置き場所（P の無い元の表に S を足すときに、年ごとの確かめの予測を読む）")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
