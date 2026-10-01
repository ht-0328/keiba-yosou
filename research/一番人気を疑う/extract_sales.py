"""セリの取引価格を元DB から読んで、中間データにする（研究「一番人気を疑う」の入口①）。

    uv run python research/一番人気を疑う/extract_sales.py

出力は ``reports/一番人気を疑う/cache/sales.parquet``（Git 対象外）。元DB は読むだけ。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 共通 import db  # noqa: E402

from 一番人気を疑う.analysis.repository import SalePriceRepository  # noqa: E402

DEFAULT_OUT = Path("reports/一番人気を疑う/cache/sales.parquet")


def main() -> None:
    parser = argparse.ArgumentParser(description="セリの取引価格を中間データにする", allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    with db.open_db(args.db) as connection:
        sales = SalePriceRepository(connection).read()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sales.to_parquet(args.out)
    print(f"書き出しました: {args.out}（{len(sales):,} 件・{sales['horse_id'].nunique():,} 頭）", flush=True)


if __name__ == "__main__":
    main()
