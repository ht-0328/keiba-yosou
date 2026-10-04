"""1着のモデルの出発点を「3連単から見た勝率」に替えて、当日の7つの区切りで今の1着のモデルと比べる（研究「回収率100超の施策」の入口①。施策 1-B）。

    uv run python research/回収率100超の施策/pool_baseline_check.py run        # 7つの区切りで学ぶ（30〜60分。済んでいれば飛ばす）
    uv run python research/回収率100超の施策/pool_baseline_check.py summary    # 今の1着のモデル（win-race_day）と比べた表を書く

学習データの表は、研究「既存モデルの改善」の対戦レーティングの確かめが作った当日の表（``h2h_pool_ability``）をそのまま読み、
予想のパッケージの ``WinTargetData`` で目的変数を「1着」にしたあと、基準だけを ``TrifectaWinBaseline`` で3連単から見た勝率のロジットに替える。
列は今の1着のモデル（当日）と同じ。区切り・区切りごとの学習・比べ方は研究「既存モデルの改善」のもの。
出るもの（Git 対象外）: ``reports/回収率100超の施策/predictions/h2h_pool_ability/win-pool-race_day.pkl``・``compare/3連単の出発点-<日付>.md``。
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

from yosou.form_aptitude_top3.dataset import WinTargetData  # noqa: E402
from yosou.form_aptitude_top3.setting import DEFAULT_SETTINGS_PATH  # noqa: E402
from yosou.shared.dataset import WIN  # noqa: E402
from yosou.shared.setting import HyperparameterSettings  # noqa: E402

from 回収率100超の施策.analysis import POOL_CURRENT, POOL_TABLE, POOL_VARIANT, TrifectaWinBaseline  # noqa: E402
from 既存モデルの改善.analysis.head_to_head import MIN_BETTER_WINDOWS, TimingComparison, base_table_rated  # noqa: E402
from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore, WalkForwardRunner, WindowTrainer  # noqa: E402
from 既存モデルの改善.analysis.win_model import WinPredictionTruth  # noqa: E402
from 既存モデルの改善.analysis.windows import WINDOWS  # noqa: E402
from 既存モデルの改善.win_check import _pin_to_p_cores as pin_to_p_cores  # noqa: E402  学習の下ごしらえは入口⑪と同じ
from 既存モデルの改善.win_check import _with_threads as with_threads  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
#: この研究の出力の置き場所と、読む表・比べる相手の置き場所（研究「既存モデルの改善」）。
DEFAULT_ROOT = _REPO_ROOT / "reports" / "回収率100超の施策"
DEFAULT_SOURCE = _REPO_ROOT / "reports" / "既存モデルの改善"


def main() -> None:
    args = _parser().parse_args()
    {"run": _run, "summary": _summary}[args.step](args)


def _run(args: argparse.Namespace) -> None:
    predictions = PredictionStore(args.root / "predictions")
    if predictions.exists(POOL_TABLE, POOL_VARIANT.key) and not args.force:
        print(f"{POOL_VARIANT.name}: 済んでいるので飛ばします", flush=True)
        return
    tables = TableStore(args.source / "tables")
    if not tables.exists(POOL_TABLE):
        raise FileNotFoundError(f"学習データの表 {args.source / 'tables' / POOL_TABLE} がありません（既存モデルの改善の h2h_check.py tables で作る）")
    pin_to_p_cores()
    settings = with_threads(HyperparameterSettings.load(None, defaults=DEFAULT_SETTINGS_PATH), args.threads)
    print(f"{POOL_VARIANT.name}: 表 {POOL_TABLE} を読んで、目的変数を「1着」に、出発点を3連単から見た勝率に替えています …", flush=True)
    data = TrifectaWinBaseline().apply(WinTargetData().training(tables.read(POOL_TABLE, base_table_rated(POOL_TABLE).rated_catalog)))
    frame, log = WalkForwardRunner(WindowTrainer(settings), WINDOWS).run(data, POOL_VARIANT)
    print(f"{POOL_VARIANT.name}: {predictions.write(POOL_TABLE, POOL_VARIANT.key, frame, log)}", flush=True)


def _summary(args: argparse.Namespace) -> None:
    current_table, current_key = POOL_CURRENT
    current = WinPredictionTruth(args.source / "tables", args.source / "predictions").read(current_table, current_key)
    new = WinPredictionTruth(args.source / "tables", args.root / "predictions").read(POOL_TABLE, POOL_VARIANT.key)
    comparison = TimingComparison(label=WIN)
    current, new = comparison.common(current, new)
    table = comparison.by_window(current, new)
    verdict = "採用の基準を満たす" if comparison.adopted(table) else "採用の基準を満たさない"
    lines = [f"# 1着のモデルの出発点を3連単から見た勝率に替えた比べ — 結果（{args.day}）", "",
             "JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
             f"採用の基準: テスト期間のログ損失が今の1着のモデル（{current_key}）より小さい区切りが 7つのうち {MIN_BETTER_WINDOWS}つ以上あり、全期間でも小さいこと。",
             "表の「今の予想」は今の1着のモデル（出発点はオッズから見た勝率）、「足した作り方」は出発点を3連単から見た勝率に替えたもの。材料は同じ。", "",
             f"## 当日: {current_key} と {POOL_VARIANT.key}", "", f"**{verdict}**（両方にある {len(current):,} 行で比べた）", "",
             table.to_markdown(index=False), ""]
    out = args.out or (args.root / "compare" / f"3連単の出発点-{args.day:%Y%m%d}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {out}（{verdict}）", flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="1着のモデルの出発点を3連単から見た勝率に替えて比べる", allow_abbrev=False)
    parser.add_argument("step", choices=("run", "summary"), help="run（学習する）・summary（比べた表を書く）")
    parser.add_argument("--force", action="store_true", help="run で、済んでいても回し直す")
    parser.add_argument("--threads", type=int, default=6, help="run の学習のスレッド数（既定: 6）")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="予測（predictions/）と結果（compare/）の置き場所")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="学習データの表と今の1着のモデルの予測の置き場所（研究「既存モデルの改善」）")
    parser.add_argument("--out", type=Path, default=None, help="summary の結果を書くファイル（既定: compare/3連単の出発点-<日付>.md）")
    parser.add_argument("--day", type=date.fromisoformat, default=date.today(), help="summary の結果のファイル名と題に付ける日付")
    return parser


if __name__ == "__main__":
    main()
