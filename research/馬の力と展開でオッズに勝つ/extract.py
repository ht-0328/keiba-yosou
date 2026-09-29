"""元DB から事実表（1行 = 1頭の出走）を中間データ（parquet）にする（研究「馬の力と展開でオッズに勝つ」の入口①）。

    uv run python research/馬の力と展開でオッズに勝つ/extract.py

事実表は ``tools/共通/facts.py`` の定義そのまま。オッズ・人気の列も入るが、予想の材料には使わず、
比べる相手（市場の当たり具合）と精算にだけ使う。出力は ``reports/馬の力と展開でオッズに勝つ/cache/``（Git 対象外）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db, facts  # noqa: E402

DEFAULT_CACHE = Path("reports/馬の力と展開でオッズに勝つ/cache")


def main() -> None:
    parser = argparse.ArgumentParser(description="事実表を中間データにする", allow_abbrev=False)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--db", type=Path, default=None)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    path = args.cache / "facts.parquet"
    # 元DB は読むだけの設定で開くので、DuckDB から直接ファイルに書けない。いったん表に読んでから書く。
    with db.open_db(args.db) as connection:
        facts.ensure_facts(connection)
        table = connection.execute(f"SELECT * FROM {facts.FACTS_TABLE}").fetch_df()
    table.to_parquet(path, index=False)
    print(f"書き出しました: {path}（{len(table):,} 行、{table['race_date'].min()}〜{table['race_date'].max()}）",
          flush=True)


if __name__ == "__main__":
    main()
