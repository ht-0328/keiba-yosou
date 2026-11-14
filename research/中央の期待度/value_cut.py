"""◎ の単勝の期待値が線以上のレースだけに等級を付ける形で、全等級の ◎ の単勝回収率が 100% を超える組を探し、本番の決まりの年ごとの成績を出す。

    uv run python research/中央の期待度/value_cut.py    # 2023〜2024年で線を決め、2025〜2026年で確かめる

◎ の行は expectation.py が reports/中央の期待度/cache/ にとっておいたもの。元DB は開かない。
出るものは Git 対象外の reports/中央の期待度/見送りの線-当日.md。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 中央の期待度.analysis.value_cut_study import ValueCutStudy  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "reports" / "中央の期待度"


def main() -> None:
    tops = pd.read_pickle(OUT / "cache" / "◎-h2h_pool_ability_h2h-race_day.pkl")
    ValueCutStudy(tops, [2023, 2024]).write(OUT / "見送りの線-当日.md")


if __name__ == "__main__":
    main()
