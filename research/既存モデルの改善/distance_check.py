"""距離の変更の傾向（予想のまとまり R）を全頭の予想に足して、時点ごと・目的変数ごとに7つの区切りで今の本番と比べる（研究「既存モデルの改善」の入口⑫）。

    uv run python research/既存モデルの改善/distance_check.py tables                       # 元の表に R を足した表を作る（元DB を開く）
    uv run python research/既存モデルの改善/distance_check.py run                          # 作り方ごとに7つの区切りで学ぶ（1つ 30〜60分。済んだものは飛ばす）
    uv run python research/既存モデルの改善/distance_check.py run --variants dist-day_before  # 1つだけ
    uv run python research/既存モデルの改善/distance_check.py summary                      # 今の本番と比べた表を書く

元の表は、今の本番のモデルを7つの区切りで学んだときの表（木曜は展開の予想を足した ``pace_thursday``、前日は対戦レーティングを足した
``h2h_ability``、当日の3着以内は ``h2h_pool_ability``、当日の1着は研究「回収率100超の施策」の ``finish_pool_ability``）。
R（前走との距離の差と、同じコース・同じ重賞で自分と同じ距離の変更だった馬の市場に対する成績）は、予想のパッケージの
``DistanceChangeRecordsLoader``（事実表から、開催日の前日までの記録だけで数える）で読む。目的変数は1着のモデルなら ``WinTargetData`` で持ち替える。
出るもの（Git 対象外）: ``reports/既存モデルの改善/tables/dist_*``・``predictions/dist_*/dist-<時点>.pkl``・``dist-win-<時点>.pkl``・
``compare/距離の変更の傾向-<日付>.md``。
採用の基準（結果を見る前に決めた。設計書 15 の 16）: テスト期間のログ損失が今の本番のモデルより小さい区切りが 7つのうち 5つ以上あり、
全期間でも小さいこと。満たした時点・目的変数だけ本番に足し、道具「印の成績」で全券種の回収率が悪くなっていないことを見る。
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
from yosou.shared.dataset import HISTORY_FIRST_DAY, WIN, DistanceChangeRecordsLoader  # noqa: E402
from yosou.shared.feature.history import DISTANCE_CHANGE_NAMES  # noqa: E402
from yosou.shared.repository import TargetScope  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 既存モデルの改善.analysis.distance_change import (  # noqa: E402
    DISTANCE_TABLES,
    DISTANCE_VARIANTS,
    DistanceTableBuilder,
    DistanceVariantSpec,
)
from 既存モデルの改善.analysis.head_to_head import MIN_BETTER_WINDOWS, PredictionTruth, TimingComparison  # noqa: E402
from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore, WalkForwardRunner, WindowTrainer  # noqa: E402
from 既存モデルの改善.analysis.win_model import WinPredictionTruth  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS  # noqa: E402
from 既存モデルの改善.win_check import _pin_to_p_cores as pin_to_p_cores  # noqa: E402  学習の下ごしらえは入口⑪と同じ
from 既存モデルの改善.win_check import _with_threads as with_threads  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
#: この研究の出力の置き場所。元の表と今の本番の予測は ``reports/<研究>/``（研究の名前は表ごとに決まっている）。
DEFAULT_ROOT = _REPORTS / "既存モデルの改善"


def main() -> None:
    args = _parser().parse_args()
    {"tables": _tables, "run": _run, "summary": _summary}[args.step](args)


def _tables(args: argparse.Namespace) -> None:
    store = TableStore(args.root / "tables")
    with db.open_db(args.db) as con:
        facts.ensure_facts(con)
        print("事実表から、距離の変更の傾向（コース・重賞ごとの、同じ距離の変更の馬の市場に対する成績）を数えています …", flush=True)
        records = DistanceChangeRecordsLoader(con, HISTORY_FIRST_DAY).read(TargetScope.since(HISTORY_FIRST_DAY))
    for table in DISTANCE_TABLES:
        if args.only and table.name not in args.only:
            continue
        source = TableStore(args.reports / table.base_research / "tables")
        if not source.exists(table.base):
            raise FileNotFoundError(f"{table.label}: 元の表 {args.reports / table.base_research / 'tables' / table.base} がありません")
        print(f"{table.label}: 元の表 {table.base} に距離の変更の傾向を足しています …", flush=True)
        built = DistanceTableBuilder().build(source.read(table.base, table.base_catalog), records)
        folder = store.write(table.name, built)
        filled = " ".join(f"{column}={built.features[column].notna().mean():.3f}" for column in DISTANCE_CHANGE_NAMES)
        print(f"{table.name}: {len(built):,}行・特徴量 {built.features.shape[1]}個 → {folder}\n  値のある行の割合: {filled}", flush=True)


def _run(args: argparse.Namespace) -> None:
    pin_to_p_cores()
    settings = with_threads(HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH), args.threads)
    runner = WalkForwardRunner(WindowTrainer(settings), WINDOWS)
    predictions, tables = PredictionStore(args.root / "predictions"), TableStore(args.root / "tables")
    for spec in [spec for spec in DISTANCE_VARIANTS if not args.variants or spec.key in args.variants]:
        if predictions.exists(spec.table.name, spec.key) and not args.force:
            print(f"{spec.variant.name}: 済んでいるので飛ばします", flush=True)
            continue
        if not tables.exists(spec.table.name):
            raise FileNotFoundError(f"{spec.variant.name}: 表 {args.root / 'tables' / spec.table.name} がありません（distance_check.py tables で作る）")
        print(f"{spec.variant.name}: 表 {spec.table.name} を読んでいます …", flush=True)
        data = tables.read(spec.table.name, spec.table.catalog)
        if spec.label == WIN:
            data = WinTargetData().training(data)
        frame, log = runner.run(data, spec.variant)
        print(f"{spec.variant.name}: {predictions.write(spec.table.name, spec.key, frame, log)}", flush=True)


def _summary(args: argparse.Namespace) -> None:
    lines = [f"# 距離の変更の傾向を足した比べ — 結果（{args.day}）", "", "JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
             f"採用の基準: テスト期間のログ損失が今の本番のモデルより小さい区切りが 7つのうち {MIN_BETTER_WINDOWS}つ以上あり、全期間でも小さいこと。",
             "表の「今の予想」は今の本番のモデル（同じ時点・同じ目的変数）、「足した作り方」はそれに距離の変更の傾向の 7個を足したもの。", ""]
    for spec in DISTANCE_VARIANTS:
        lines += _section(spec, args)
    out = args.out or (args.root / "compare" / f"距離の変更の傾向-{args.day:%Y%m%d}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {out}", flush=True)


def _section(spec: DistanceVariantSpec, args: argparse.Namespace) -> list[str]:
    title = f"## {spec.timing.label}・{'1着' if spec.label == WIN else '3着以内'}"
    if not PredictionStore(args.root / "predictions").exists(spec.table.name, spec.key):
        return [title, "", "予測がまだ無い。", ""]
    truth = WinPredictionTruth if spec.label == WIN else PredictionTruth
    current_root = args.reports / spec.current_research
    current = truth(current_root / "tables", current_root / "predictions").read(spec.current_table, spec.current_key)
    new = truth(args.root / "tables", args.root / "predictions").read(spec.table.name, spec.key)
    comparison = TimingComparison(label=spec.label)
    current, new = comparison.common(current, new)
    table = comparison.by_window(current, new)
    verdict = "採用の基準を満たす" if comparison.adopted(table) else "採用の基準を満たさない"
    print(f"{spec.timing.label}（{spec.key}）: {verdict}", flush=True)
    return [f"{title}: {spec.current_key} と {spec.key}（{spec.variant.name}）", "",
            f"**{verdict}**（両方にある {len(current):,} 行で比べた）", "", table.to_markdown(index=False), ""]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="距離の変更の傾向を全頭の予想に足して比べる", allow_abbrev=False)
    parser.add_argument("step", choices=("tables", "run", "summary"), help="tables（表を作る）・run（学習する）・summary（比べた表を書く）")
    parser.add_argument("--only", nargs="*", default=None, metavar="表", help=f"tables で作る表（{' / '.join(t.name for t in DISTANCE_TABLES)}）")
    parser.add_argument("--variants", nargs="*", default=None, metavar="作り方",
                        help=f"run で回す作り方（{' / '.join(spec.key for spec in DISTANCE_VARIANTS)}。省略すると全部）")
    parser.add_argument("--force", action="store_true", help="run で、済んだ作り方も回し直す")
    parser.add_argument("--threads", type=int, default=6, help="run の学習のスレッド数（既定: 6）")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="表（tables/）と予測（predictions/）と結果（compare/）の置き場所")
    parser.add_argument("--reports", type=Path, default=_REPORTS, help="元の表と今の本番の予測を探す reports の場所（その下の研究ごとのフォルダ）")
    parser.add_argument("--out", type=Path, default=None, help="summary の結果を書くファイル（既定: compare/距離の変更の傾向-<日付>.md）")
    parser.add_argument("--day", type=date.fromisoformat, default=date.today(), help="summary の結果のファイル名と題に付ける日付")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
