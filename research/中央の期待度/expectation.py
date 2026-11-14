"""中央の期待度: 中央の予想に添える「期待度」（◎ の1着の確率 ＋ 重み ×（単勝の期待値 − 1）の S・A・B・C）の重みと線を、未見の予測で決め直す。

    uv run python research/中央の期待度/expectation.py              # 当日の予測。2023〜2024年で線と重みを決め、2025〜2026年で確かめる
    uv run python research/中央の期待度/expectation.py --rebuild    # ◎ の行を元DB から作り直す（数分）

◎ の行は研究「既存モデルの改善」の当日の予測（7つの区切りのテスト期間）に、道具「印の成績」の表13 と同じ決め方で印を付けて作り、
reports/中央の期待度/cache/ にとっておく（2回目からは元DB を開かない）。
出るものは Git 対象外の reports/中央の期待度/重みの候補-当日.md（まとめと、候補ごとの期間 × 等級の ◎ の単勝・複勝の成績）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from yosou.form_aptitude_top3.command.yosou_name import YOSOU_NAME  # noqa: E402

from 中央の期待度.analysis.jra_top_picks import JraTopPicks  # noqa: E402
from 中央の期待度.analysis.weight_study import WeightStudy  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "中央の期待度"
#: 当日の本番と同じ作りの予測（印の成績の当日の例と同じ）と、危険な人気馬の予測。
DEFAULT_FORM = "h2h_pool_ability/h2h-race_day"
DEFAULT_WIN = "h2h_pool_ability/win-race_day"
DEFAULT_DANGER = "favorites_out_of_top3/people_market"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--form", default=DEFAULT_FORM, help=f"全頭の予想の予測（既定: {DEFAULT_FORM}）")
    parser.add_argument("--win", default=DEFAULT_WIN, help=f"1着の予想の予測（既定: {DEFAULT_WIN}）")
    parser.add_argument("--danger", default=DEFAULT_DANGER, help=f"危険な人気馬の予測（既定: {DEFAULT_DANGER}）")
    parser.add_argument("--decide-years", type=int, nargs="+", default=[2023, 2024], help="線と重みを決める年（既定: 2023 2024。残りの年で確かめる）")
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（省略すると jvdata-store の既定）")
    parser.add_argument("--rebuild", action="store_true", help="◎ の行を元DB から作り直す")
    parser.add_argument("--out-dir", type=Path, default=OUT, help=f"結果を書く場所（既定: {OUT}）")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    picks = JraTopPicks(args.form, args.win, args.danger, ROOT / "reports" / YOSOU_NAME / "models", args.out_dir / "cache")
    tops = picks.load(args.db, args.rebuild)
    WeightStudy(tops, args.decide_years).write(args.out_dir / "重みの候補-当日.md")


if __name__ == "__main__":
    main()
