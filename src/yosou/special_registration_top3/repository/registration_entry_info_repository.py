"""1レースの登録馬の、表に出す情報（調教師・負担重量・交流区分）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import keys, registration

from yosou.shared.dataset import HORSE_ID

#: 表に出す列の名前。
TRAINER = "調教師"
CARRIED = "負担重量"
EXCHANGE = "交流区分"
#: 交流区分の表示（0 中央は空）。
_EXCHANGE_NAMES: dict[str, str] = {"1": "地方", "2": "外国"}


class RegistrationEntryInfoRepository:
    """予測の結果の表に添える、登録馬ごとの調教師（略称）・負担重量（kg）・交流区分を、特別登録から読む（1 SQL）。

    事実表の列には調教師の名前と交流区分が無いので、``predict`` と ``registrations`` が予測のあとに突き合わせる（設計書 04 の「コマンドの引数」）。
    使う版は登録馬の行と同じ（月曜の版、無ければ日曜の版）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_id: str) -> pd.DataFrame:
        """列は ``馬ID``・``調教師``・``負担重量``・``交流区分``（地方 / 外国 / 空）。"""
        sql = f"""
        SELECT r.{keys.q(keys.HORSE_KEY)} AS horse_id, trim(r.{keys.q('調教師名略称')}) AS trainer,
               TRY_CAST(NULLIF(r.{keys.q('負担重量')}, '000') AS INTEGER) / 10.0 AS carried, trim(r.{keys.q('交流区分')}) AS exchange
        FROM {registration.chosen_registration_sql(self._con, race_id)} AS t
        JOIN {registration.runner_table_relation(self._con)} AS r USING ({keys.key_list()})
        WHERE nullif(trim(r.{keys.q(keys.HORSE_KEY)}), '') IS NOT NULL
        """
        frame = self._con.execute(sql).df()
        return pd.DataFrame({
            HORSE_ID: frame["horse_id"].astype(str), TRAINER: frame["trainer"], CARRIED: frame["carried"].astype("float64"),
            EXCHANGE: frame["exchange"].map(_EXCHANGE_NAMES).fillna(""),
        })
