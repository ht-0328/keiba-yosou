"""券種オッズの SQL に共通の前半。対象のレースの、確定（無ければ最新）の断面の買い目ごとの 1/オッズ。"""

import duckdb

from 共通 import facts, keys

from .pool_spec import PoolSpec

_ANNOUNCED = "発表月日時分"
_HEADER_COLUMNS = (*keys.RACE_KEY, "データ区分", _ANNOUNCED)
#: 使う断面のデータ区分（1 中間・2 前日売最終・3 最終・4 確定・5 確定(月曜)）。9 中止は使わない。
_STAGES = ("1", "2", "3", "4", "5")
_FINAL_STAGES = ("4", "5")


def pool_odds_rows(con: duckdb.DuckDBPyConnection, spec: PoolSpec, scope_relation: str) -> str:
    """``WITH`` の中身。``odds``（race_id・combo・inverse）と ``totals``（race_id・total）を作る。

    ``scope_relation`` は ``race_id`` の列を持つ関係。表が無い DB では空になる。
    """
    child_columns = (*keys.RACE_KEY, _ANNOUNCED, spec.combo, "オッズ", "最低オッズ", "最高オッズ")
    header = facts.optional_relation(con, spec.header, _HEADER_COLUMNS)
    child = facts.optional_relation(con, spec.table, child_columns)
    join = " AND ".join(f"{keys.col(name, 'o')} = {keys.col(name, 'h')}" for name in (*keys.RACE_KEY, _ANNOUNCED))
    is_final = f"{keys.col('データ区分', 'h')} IN {keys.sql_list(_FINAL_STAGES)}"
    return f"""
        wanted AS (
            SELECT DISTINCT race_id FROM {scope_relation}
        ), latest AS (
            SELECT {keys.key_list('h')}, {keys.col(_ANNOUNCED, 'h')}, {keys.rid_expr('h')} AS race_id
            FROM {header} AS h
            WHERE {keys.rid_expr('h')} IN (SELECT race_id FROM wanted)
              AND {keys.col('データ区分', 'h')} IN {keys.sql_list(_STAGES)}
            QUALIFY row_number() OVER (
                PARTITION BY {keys.key_list('h')} ORDER BY ({is_final}) DESC, {keys.col(_ANNOUNCED, 'h')} DESC
            ) = 1
        ), odds AS (
            SELECT h.race_id, {keys.col(spec.combo, 'o')} AS combo, 1.0 / ({spec.price}) AS inverse
            FROM {child} AS o
            JOIN latest AS h ON {join}
            WHERE ({spec.price}) > 0
        ), totals AS (
            SELECT race_id, sum(inverse) AS total FROM odds GROUP BY race_id
        )"""
