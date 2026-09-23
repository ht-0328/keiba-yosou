"""レースごとの払戻を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts, keys

#: 払戻の親の表（券種ごとの不成立・特払・返還のフラグ）。
_HEADER_TABLE = "hr"
#: 券種の英語の鍵 → （払戻の子の表、組み合わせの列、フラグの列名に使う券種の名前）。
#: 鍵は、この表の列の名前（``win_yen`` など）の頭になる。呼ぶ側（券種の値）は、この鍵で列を引く。
PAYOUT_TABLES: dict[str, tuple[str, str, str]] = {
    "win": ("hr__単勝払戻", "馬番", "単勝"),
    "quinella": ("hr__馬連払戻", "組番", "馬連"),
    "trio": ("hr__3連複払戻", "組番", "3連複"),
    "trifecta": ("hr__3連単払戻", "組番", "3連単"),
}
#: 払戻の列の名前の後ろ（払戻の額（円）、その組み合わせの人気順、成立しなかったか）。
YEN, POPULARITY, VOID = "yen", "pop", "void"
#: フラグの列名は「不成立フラグ　単勝」のように、全角スペースで券種の名前をつなぐ（JV-Data の列名のまま）。
_FLAG_KINDS: tuple[str, ...] = ("不成立フラグ", "特払フラグ")
_FLAG_SEPARATOR = "　"
_FLAG_ON = "1"
#: 払戻の確定した行のデータ区分（1 速報成績（払戻確定）・2 成績（月曜））。
_PAYOUT_STAGES: tuple[str, ...] = ("1", "2")


class RacePayoutRepository:
    """レースごとの4券種（単勝・馬連・3連複・3連単）の払戻と、成立したかどうかを、1行 = 1レースで読む（荒れ具合の設計書 04 の 2）。

    対象は、事実表（中央の確定成績）にあるレースのうち、開催日が ``first_day`` 以降のもの。学習では目的変数と
    評価用の列の元に、予測では過去の荒れ率（まとまり E）の材料になる。
    同着で払戻が複数あれば最大の額（荒れ具合の設計書 10）。払戻の表が無い DB（取得前・合成DB）では、額は欠損値になる。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, first_day: date) -> pd.DataFrame:
        """列は ``race_id``・``race_date``・レースの条件（``venue_code``・``surface``・``distance_m``・``class_order``・``field_size``）と、
        券種ごとの ``<鍵>_yen``（円）・``<鍵>_pop``（人気順）・``<鍵>_void``（不成立か特払なら True）。開催日・レースID の順。
        """
        payout_joins = "\n".join(f"LEFT JOIN {key}_payout USING (race_id)" for key in PAYOUT_TABLES)
        payout_columns = ", ".join(self._payout_select(key) for key in PAYOUT_TABLES)
        sql = f"""
        WITH race AS (
            SELECT race_id, min(CAST(race_date AS DATE)) AS race_date,
                   any_value(venue_code) AS venue_code, any_value(surface) AS surface,
                   any_value(distance_m) AS distance_m, any_value(class_order) AS class_order,
                   any_value(field_size) AS field_size
            FROM {facts.FACTS_TABLE}
            WHERE CAST(race_date AS DATE) >= ?
            GROUP BY race_id
        ), {", ".join(self._payout_cte(key) for key in PAYOUT_TABLES)},
        header AS (
            SELECT {keys.rid_expr()} AS race_id, {self._flag_columns()}
            FROM {self._header_table()}
            WHERE {keys.q('データ区分')} IN {keys.sql_list(_PAYOUT_STAGES)}
            {keys.latest_qualify(keys.RACE_KEY)}
        )
        SELECT race.*, {payout_columns}
        FROM race
        {payout_joins}
        LEFT JOIN header USING (race_id)
        ORDER BY race_date, race_id
        """
        return self._con.execute(sql, [first_day.isoformat()]).df()

    def _payout_cte(self, key: str) -> str:
        """1つの券種の、レースごとの払戻（同着は最大）と人気順（最小）。"""
        table, _, _ = PAYOUT_TABLES[key]
        columns = (*keys.RACE_KEY, "払戻金", "人気順")
        yen = f"TRY_CAST({keys.q('払戻金')} AS BIGINT)"
        return f"""{key}_payout AS (
            SELECT {keys.rid_expr()} AS race_id, max({yen}) AS {key}_{YEN},
                   min(TRY_CAST({keys.q('人気順')} AS INTEGER)) AS {key}_{POPULARITY}
            FROM {facts.optional_relation(self._con, table, columns)}
            WHERE {yen} > 0
            GROUP BY ALL
        )"""

    def _payout_select(self, key: str) -> str:
        """結果に出す、1つの券種の列。成立しなかったか（不成立か特払）は、フラグが無ければ False。"""
        _, _, bet_name = PAYOUT_TABLES[key]
        flags = " OR ".join(f"{self._flag_alias(kind, bet_name)} = '{_FLAG_ON}'" for kind in _FLAG_KINDS)
        return f"{key}_{YEN}, {key}_{POPULARITY}, coalesce({flags}, FALSE) AS {key}_{VOID}"

    def _flag_columns(self) -> str:
        """親の表から読むフラグの列（券種 × 不成立・特払）。"""
        return ", ".join(
            f"{keys.q(self._flag_name(kind, bet_name))} AS {self._flag_alias(kind, bet_name)}"
            for kind in _FLAG_KINDS for _, _, bet_name in PAYOUT_TABLES.values()
        )

    def _header_table(self) -> str:
        """親の表。無い DB では、同じ列を持つ空の関係。"""
        flag_names = [self._flag_name(kind, bet_name) for kind in _FLAG_KINDS for _, _, bet_name in PAYOUT_TABLES.values()]
        columns = (*keys.RACE_KEY, "データ区分", "データ作成年月日", *flag_names)
        return facts.optional_relation(self._con, _HEADER_TABLE, columns)

    def _flag_name(self, kind: str, bet_name: str) -> str:
        return f"{kind}{_FLAG_SEPARATOR}{bet_name}"

    def _flag_alias(self, kind: str, bet_name: str) -> str:
        """SQL の中で使う、フラグの短い名前。"""
        key = next(key for key, (_, _, name) in PAYOUT_TABLES.items() if name == bet_name)
        return f"{key}_{_FLAG_KINDS.index(kind)}"
