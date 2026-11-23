"""ばんえいの予想: 元DB の確定した成績の全部で2つのモデル（勝つ確率の予想・世間の見立て）を学び、保存する。

    uv run python tools/ばんえいの予想/train.py                 # 地方の元DB（../nvdata-store/nvdata.duckdb）で学ぶ
    uv run python tools/ばんえいの予想/train.py --db <写し>     # 元DB の写しで学ぶ（開催中に元DB を使わないため）

保存先は reports/ばんえいの予想/models/。数分かかる。開催が進んだら（月に1回ほど）学び直す。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[0])]

from 共通 import db  # noqa: E402

from ばんえいの予想.banei_feature_builder import BaneiFeatureBuilder  # noqa: E402
from ばんえいの予想.banei_model import BaneiModel  # noqa: E402
from ばんえいの予想.banei_runs_repository import BaneiRunsRepository  # noqa: E402
from ばんえいの予想.folders import MODEL_FOLDER  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", help=db.LOCAL.help())
    parser.add_argument("--out", default=str(MODEL_FOLDER), help="学習済みモデルの保存先")
    args = parser.parse_args()
    with db.open_db(args.db, default=db.LOCAL) as con:
        runs = BaneiRunsRepository(con).confirmed()
    builder = BaneiFeatureBuilder()
    features = builder.build(runs)
    until = f"{features['date'].max():%Y-%m-%d}"
    print(f"確定した出走 {len(features):,} 頭（{features['rid'].nunique():,} レース、{until} まで）で学びます", file=sys.stderr)
    BaneiModel.fit(features, builder.names()).save(Path(args.out), until)
    print(f"保存しました: {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
