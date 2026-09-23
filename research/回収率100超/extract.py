"""元DB から中間データ（parquet）を作る（研究「回収率100超」の入口①）。

    uv run python research/回収率100超/extract.py

元DB を長く握ると、ほかの道具が DB を開けなくなる。ここでまとめて読み出し、以後の学習と検証は
parquet だけを使う。出力は ``reports/回収率100超/cache/``（Git 対象外）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db  # noqa: E402

from 回収率100超.analysis.repository import (  # noqa: E402
    POOL_MARGINALS,
    POSITION_MARGINALS,
    VOTE_SHARES,
    HorseFactRepository,
    MiningRepository,
    PoolMarginalRepository,
    PoolSizeRepository,
    PositionMarginalRepository,
    RunnerMarketRepository,
    VoteShareRepository,
)

#: 中間データの置き場。Git の対象外。
DEFAULT_CACHE = Path("reports/回収率100超/cache")


def main() -> None:
    parser = argparse.ArgumentParser(description="元DB から中間データを作る", allow_abbrev=False)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="中間データの置き場")
    parser.add_argument("--from-year", type=int, default=2016, help="いつからのデータを取るか")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)

    with db.open_db(args.db) as connection:
        print("出走・オッズ・払戻を読み出し中...", flush=True)
        _write(RunnerMarketRepository(connection, args.from_year).read(),
               args.cache / "runners.parquet")

        pools = PoolMarginalRepository(connection, args.from_year)
        for marginal in POOL_MARGINALS:
            print(f"{marginal.column} を集計中...", flush=True)
            _write(pools.read(marginal), args.cache / f"pool_{marginal.key}.parquet")

        positions = PositionMarginalRepository(connection, args.from_year)
        for key in POSITION_MARGINALS:
            print(f"{key} を集計中...", flush=True)
            _write(positions.read(key), args.cache / f"pool_{key}.parquet")

        votes = VoteShareRepository(connection, args.from_year)
        for column, (_, key) in VOTE_SHARES.items():
            print(f"{column} を集計中...", flush=True)
            _write(votes.read(column), args.cache / f"pool_{key}.parquet")

        print("プールの大きさを集計中...", flush=True)
        _write(PoolSizeRepository(connection, args.from_year).read(), args.cache / "pool_size.parquet")

        print("マイニング予想を読み出し中...", flush=True)
        _write(MiningRepository(connection, args.from_year).read(), args.cache / "mining.parquet")

        print("馬の実力（事実表）を読み出し中...", flush=True)
        _write(HorseFactRepository(connection, args.from_year).read(), args.cache / "horse_facts.parquet")


def _write(frame: pd.DataFrame, path: Path) -> None:
    frame.to_parquet(path, index=False)
    print(f"  {path.name}: {len(frame):,} 行", flush=True)


if __name__ == "__main__":
    main()
