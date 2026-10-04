"""勝ち切る材料を1着のモデルに足して、時点ごとに7つの区切りで今の1着のモデルと比べる（研究「回収率100超の施策」の入口②。施策3）。

    uv run python research/回収率100超の施策/finish_check.py tables                          # 元の表に勝ち切る材料を足した表を作る（元DB を開く）
    uv run python research/回収率100超の施策/finish_check.py run                             # 時点ごとに7つの区切りで学ぶ（1つ 30〜60分。済んだものは飛ばす）
    uv run python research/回収率100超の施策/finish_check.py run --variants finish-win-day_before   # 1つだけ（finish-pool-win-race_day は施策 1-B と重ねたもの）
    uv run python research/回収率100超の施策/finish_check.py summary                         # 今の1着のモデルと比べた表を書く

元の表は、研究「既存モデルの改善」の対戦レーティングの確かめが作った今の本番と同じ材料の表（前日 ``h2h_ability``・当日 ``h2h_pool_ability``）。
勝ち切る材料（馬の近10走の1着数・2着数・勝ち切り率・惜敗数・勝ち着差・人気で負けた数、騎手と調教師の近1年の勝ち切り率と1番人気のときの勝率）は、
予想のパッケージの ``FinishRecordsLoader``（事実表から、開催日の前日までの記録だけで数える）で読む（採用して移した）。目的変数は予想のパッケージの ``WinTargetData`` で「1着」に持ち替える。
区切り・区切りごとの学習・比べ方は研究「既存モデルの改善」のもの。
出るもの（Git 対象外）: ``reports/回収率100超の施策/tables/finish_*``・``predictions/finish_*/finish-win-<時点>.pkl``・``compare/勝ち切る材料-<日付>.md``。
採用の基準: テスト期間のログ損失が今の1着のモデルより小さい区切りが 7つのうち 5つ以上あり、全期間でも小さいこと。
満たしたら、道具「印の成績」に予測の pkl のパスを ``--win`` で渡して、◎ の単勝回収率と全券種の回収率を見る。
学習は、同じマシンのほかの学習とぶつからないように1つずつ走らせ、Windows では P コア（論理 CPU 0〜11）に絞る。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db, facts  # noqa: E402

from yosou.form_aptitude_top3.dataset import WinTargetData  # noqa: E402
from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH  # noqa: E402
from yosou.shared.dataset import HISTORY_FIRST_DAY, WIN, FinishRecordsLoader  # noqa: E402
from yosou.shared.repository import TargetScope  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 回収率100超の施策.analysis import (  # noqa: E402
    FINISH_NAMES,
    FINISH_TABLES,
    FINISH_VARIANTS,
    FinishTableBuilder,
    FinishVariantSpec,
    TrifectaWinBaseline,
)
from 既存モデルの改善.analysis.head_to_head import MIN_BETTER_WINDOWS, PredictionTruth, TimingComparison  # noqa: E402
from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore, WalkForwardRunner, WindowTrainer  # noqa: E402
from 既存モデルの改善.analysis.win_model import WinPredictionTruth  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS  # noqa: E402
from 既存モデルの改善.win_check import _pin_to_p_cores as pin_to_p_cores  # noqa: E402  学習の下ごしらえは入口⑪と同じ
from 既存モデルの改善.win_check import _with_threads as with_threads  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
#: この研究の出力の置き場所と、元の表・今の1着のモデルの予測の置き場所（研究「既存モデルの改善」）。
DEFAULT_ROOT = _REPO_ROOT / "reports" / "回収率100超の施策"
DEFAULT_SOURCE = _REPO_ROOT / "reports" / "既存モデルの改善"


def main() -> None:
    args = _parser().parse_args()
    {"tables": _tables, "run": _run, "summary": _summary}[args.step](args)


def _tables(args: argparse.Namespace) -> None:
    source, store = TableStore(args.source / "tables"), TableStore(args.root / "tables")
    with db.open_db(args.db) as con:
        facts.ensure_facts(con)
        print("事実表から、馬の近10走と騎手・調教師の近1年の勝ち切る材料を数えています …", flush=True)
        records = FinishRecordsLoader(con).read(TargetScope.since(HISTORY_FIRST_DAY))
    for table in FINISH_TABLES:
        if args.only and table.name not in args.only:
            continue
        if not source.exists(table.base):
            raise FileNotFoundError(f"{table.label}: 元の表 {args.source / 'tables' / table.base} がありません（既存モデルの改善の h2h_check.py tables で作る）")
        print(f"{table.label}: 元の表 {table.base} に勝ち切る材料を足しています …", flush=True)
        built = FinishTableBuilder().build(source.read(table.base, table.base_catalog), records)
        folder = store.write(table.name, built)
        filled = " ".join(f"{column}={built.features[column].notna().mean():.3f}" for column in FINISH_NAMES)
        print(f"{table.name}: {len(built):,}行・特徴量 {built.features.shape[1]}個 → {folder}\n  値のある行の割合: {filled}", flush=True)


def _run(args: argparse.Namespace) -> None:
    pin_to_p_cores()
    settings = with_threads(HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH), args.threads)
    runner = WalkForwardRunner(WindowTrainer(settings), WINDOWS)
    predictions, tables = PredictionStore(args.root / "predictions"), TableStore(args.root / "tables")
    for spec in [spec for spec in FINISH_VARIANTS if not args.variants or spec.key in args.variants]:
        if predictions.exists(spec.table.name, spec.key) and not args.force:
            print(f"{spec.variant.name}: 済んでいるので飛ばします", flush=True)
            continue
        if not tables.exists(spec.table.name):
            raise FileNotFoundError(f"{spec.variant.name}: 表 {args.root / 'tables' / spec.table.name} がありません（finish_check.py tables で作る）")
        print(f"{spec.variant.name}: 表 {spec.table.name} を読んで、目的変数を「{spec.label}」にしています …", flush=True)
        data = tables.read(spec.table.name, spec.table.catalog)
        if spec.label == WIN:
            data = WinTargetData().training(data)
        if spec.pool_baseline:
            data = TrifectaWinBaseline().apply(data)
        frame, log = runner.run(data, spec.variant)
        print(f"{spec.variant.name}: {predictions.write(spec.table.name, spec.key, frame, log)}", flush=True)


def _summary(args: argparse.Namespace) -> None:
    lines = [f"# 1着のモデルに勝ち切る材料を足した比べ — 結果（{args.day}）", "", "JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
             f"採用の基準: テスト期間のログ損失が今の1着のモデルより小さい区切りが 7つのうち {MIN_BETTER_WINDOWS}つ以上あり、全期間でも小さいこと。",
             "表の「今の予想」は今の1着のモデル（finish-top3 の行は今の3着以内のモデル）、「足した作り方」はそれに勝ち切る材料の 10個を足したもの。", ""]
    for spec in FINISH_VARIANTS:
        lines += _section(spec, args)
    out = args.out or (args.root / "compare" / f"勝ち切る材料-{args.day:%Y%m%d}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {out}", flush=True)


def _section(spec: FinishVariantSpec, args: argparse.Namespace) -> list[str]:
    if not PredictionStore(args.root / "predictions").exists(spec.table.name, spec.key):
        return [f"## {spec.timing.label}", "", "予測がまだ無い。", ""]
    truth = WinPredictionTruth if spec.label == WIN else PredictionTruth
    current = truth(args.source / "tables", args.source / "predictions").read(spec.current_table, spec.current_key)
    new = truth(args.root / "tables", args.root / "predictions").read(spec.table.name, spec.key)
    comparison = TimingComparison(label=spec.label)
    current, new = comparison.common(current, new)
    table = comparison.by_window(current, new)
    verdict = "採用の基準を満たす" if comparison.adopted(table) else "採用の基準を満たさない"
    print(f"{spec.timing.label}（{spec.key}）: {verdict}", flush=True)
    return [f"## {spec.timing.label}: {spec.current_key} と {spec.key}（{spec.variant.name}）", "",
            f"**{verdict}**（両方にある {len(current):,} 行で比べた）", "",
            table.to_markdown(index=False), ""]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="勝ち切る材料を1着のモデルに足して比べる", allow_abbrev=False)
    parser.add_argument("step", choices=("tables", "run", "summary"), help="tables（表を作る）・run（学習する）・summary（比べた表を書く）")
    parser.add_argument("--only", nargs="*", default=None, metavar="表", help=f"tables で作る表（{' / '.join(table.name for table in FINISH_TABLES)}）")
    parser.add_argument("--variants", nargs="*", default=None, metavar="作り方",
                        help=f"run で回す作り方（{' / '.join(spec.key for spec in FINISH_VARIANTS)}。省略すると全部）")
    parser.add_argument("--force", action="store_true", help="run で、済んだ作り方も回し直す")
    parser.add_argument("--threads", type=int, default=6, help="run の学習のスレッド数（既定: 6）")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="表（tables/）と予測（predictions/）と結果（compare/）の置き場所")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="元の表と今の1着のモデルの予測の置き場所（研究「既存モデルの改善」）")
    parser.add_argument("--out", type=Path, default=None, help="summary の結果を書くファイル（既定: compare/勝ち切る材料-<日付>.md）")
    parser.add_argument("--day", type=date.fromisoformat, default=date.today(), help="summary の結果のファイル名と題に付ける日付")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
