"""◎ の選び方 × 期待度の重みを比べ、「どの等級でも ◎ の単勝回収率が 100% を超え、S → C の順に勝率と単勝回収率が上がる」組を探す。

    uv run python research/中央の期待度/rules.py    # 2023〜2024年で選び、2025〜2026年で確かめる

全頭の行は expectation.py が reports/中央の期待度/cache/ にとっておいたもの（無ければ先に expectation.py を動かす）。元DB は開かない。
出るものは Git 対象外の reports/中央の期待度/◎の選び方-当日.md。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 中央の期待度.analysis.rule_study import RuleStudy  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "中央の期待度"
DEFAULT_ROWS = OUT / "cache" / "全頭-h2h_pool_ability_h2h-race_day.pkl"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--rows", type=Path, default=DEFAULT_ROWS, help=f"全頭の行の pickle（既定: {DEFAULT_ROWS}）")
    parser.add_argument("--decide-years", type=int, nargs="+", default=[2023, 2024], help="線と組を決める年（既定: 2023 2024）")
    parser.add_argument("--out-dir", type=Path, default=OUT, help=f"結果を書く場所（既定: {OUT}）")
    args = parser.parse_args()
    if not args.rows.is_file():
        raise SystemExit(f"全頭の行がありません: {args.rows}（先に research/中央の期待度/expectation.py を動かす）")
    rows = pd.read_pickle(args.rows)
    rows["year"] = pd.to_datetime(rows["race_date"]).dt.year
    RuleStudy(rows, args.decide_years).write(args.out_dir / "◎の選び方-当日.md")


if __name__ == "__main__":
    main()
