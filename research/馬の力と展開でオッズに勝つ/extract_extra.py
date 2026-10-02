"""調教・馬主・生産者・母（兄弟）の中間データを作る（研究「馬の力と展開でオッズに勝つ」の入口③）。

    uv run python research/馬の力と展開でオッズに勝つ/extract_extra.py

- workouts.parquet: 出走ごとに、レースの前日までの 14日・30日の調教（坂路・ウッド）をまとめた値
- connections.parquet: 出走ごとの馬主コード、馬ごとの生産者コードと母の繁殖登録番号
出力は ``reports/馬の力と展開でオッズに勝つ/cache/``（Git 対象外）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db, facts  # noqa: E402

DEFAULT_CACHE = Path("reports/馬の力と展開でオッズに勝つ/cache")

#: 調教のタイムは 0.1秒単位の文字列（例: '0528' は 52.8秒）。0 は記録なし。
_SECONDS = "nullif(try_cast({column} as double), 0) / 10.0"

_WORKOUTS_SQL = f"""
with 出走 as (
    select race_id, horse_no, horse_id, cast(race_date as date) as race_date from {facts.FACTS_TABLE} where ran
),
坂路 as (
    select 血統登録番号 as horse_id, strptime(調教年月日, '%Y%m%d')::date as day,
        {_SECONDS.format(column='"4ハロンタイム合計(800M～0M)"')} as f4,
        {_SECONDS.format(column='"ラップタイム(200M～0M)"')} as f1
    from hc
),
ウッド as (
    select 血統登録番号 as horse_id, strptime(調教年月日, '%Y%m%d')::date as day,
        {_SECONDS.format(column='"5ハロンタイム合計(1000M～0M)"')} as f5,
        {_SECONDS.format(column='"4ハロンタイム合計(800M～0M)"')} as f4,
        {_SECONDS.format(column='"ラップタイム(200M～0M)"')} as f1
    from wc
),
坂路の集計 as (
    select 出走.race_id, 出走.horse_no,
        count(*) filter (where 坂路.day >= 出走.race_date - 14) as "坂路_本数14日",
        count(*) as "坂路_本数30日",
        min(坂路.f4) filter (where 坂路.day >= 出走.race_date - 14) as "坂路_4F最速14日",
        min(坂路.f1) filter (where 坂路.day >= 出走.race_date - 14) as "坂路_1F最速14日",
        arg_max(坂路.f4, 坂路.day) as "坂路_直前4F", arg_max(坂路.f1, 坂路.day) as "坂路_直前1F",
        min(出走.race_date - 坂路.day) as "坂路_直前からの日数"
    from 出走 join 坂路 on 坂路.horse_id = 出走.horse_id
        and 坂路.day between 出走.race_date - 30 and 出走.race_date - 1
    group by all
),
ウッドの集計 as (
    select 出走.race_id, 出走.horse_no,
        count(*) as "ウッド_本数30日",
        min(ウッド.f5) as "ウッド_5F最速30日", min(ウッド.f4) as "ウッド_4F最速30日",
        min(ウッド.f1) as "ウッド_1F最速30日", arg_max(ウッド.f1, ウッド.day) as "ウッド_直前1F"
    from 出走 join ウッド on ウッド.horse_id = 出走.horse_id
        and ウッド.day between 出走.race_date - 30 and 出走.race_date - 1
    group by all
)
select 出走.race_id, 出走.horse_no, 坂路の集計.* exclude (race_id, horse_no), ウッドの集計.* exclude (race_id, horse_no)
from 出走
left join 坂路の集計 on 坂路の集計.race_id = 出走.race_id and 坂路の集計.horse_no = 出走.horse_no
left join ウッドの集計 on ウッドの集計.race_id = 出走.race_id and ウッドの集計.horse_no = 出走.horse_no
"""

_CONNECTIONS_SQL = f"""
with 馬主 as (
    select 開催年 || 開催月日 || 競馬場コード || "開催回[第N回]" || "開催日目[N日目]" || レース番号 as race_id,
        try_cast(馬番 as integer) as horse_no, any_value(馬主コード) as owner
    from se where 競馬場コード between '01' and '10' group by all
),
馬 as (
    select 血統登録番号 as horse_id, any_value(生産者コード) as breeder,
        any_value("3代血統 繁殖登録番号_02") as dam
    from sk group by all
)
select f.race_id, f.horse_no, 馬主.owner, 馬.breeder, 馬.dam
from {facts.FACTS_TABLE} f
left join 馬主 on 馬主.race_id = f.race_id and 馬主.horse_no = f.horse_no
left join 馬 on 馬.horse_id = f.horse_id
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="調教・馬主・生産者・母の中間データを作る", allow_abbrev=False)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--db", type=Path, default=None)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    with db.open_db(args.db) as connection:
        facts.ensure_facts(connection)
        for name, sql in (("workouts", _WORKOUTS_SQL), ("connections", _CONNECTIONS_SQL)):
            table = connection.execute(sql).fetch_df()
            table.to_parquet(args.cache / f"{name}.parquet", index=False)
            print(f"書き出しました: {name}.parquet（{len(table):,} 行）", flush=True)


if __name__ == "__main__":
    main()
