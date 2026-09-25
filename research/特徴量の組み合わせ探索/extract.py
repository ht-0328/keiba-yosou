"""元DB から、全頭・全特徴量の表を作る（研究「特徴量の組み合わせ探索」の入口①）。

    uv run python research/特徴量の組み合わせ探索/extract.py

custom_binary に登録された特徴量を、当日の時点ですべて計算する。以後の探索は、この表だけを使い元DB に触らない。
出力は ``reports/特徴量の組み合わせ探索/cache/``（Git 対象外）。
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "research"), str(ROOT / "tools"), str(ROOT / "src")]

from 共通 import db  # noqa: E402

from yosou.custom_binary.feature.registrations import default_registry  # noqa: E402

from 特徴量の組み合わせ探索.analysis.feature_table import FeatureTable  # noqa: E402
from 特徴量の組み合わせ探索.analysis.search_periods import SearchPeriods  # noqa: E402

DEFAULT_CACHE = ROOT / "reports" / "特徴量の組み合わせ探索" / "cache"


def main() -> None:
    parser = argparse.ArgumentParser(description="全頭・全特徴量の表を作る", allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（読むだけ）")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="表の置き場")
    args = parser.parse_args()
    started = time.time()
    with db.open_db(args.db) as con:
        table = FeatureTable.build(con, default_registry(), SearchPeriods())
    table.save(args.cache)
    print(f"{len(table.rows)}行 × {table.frame.shape[1]}特徴量を {args.cache} に保存（{time.time() - started:.0f}秒）")


if __name__ == "__main__":
    main()
