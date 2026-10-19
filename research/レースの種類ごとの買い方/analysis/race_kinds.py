"""レースごとの種類（芝ダ・クラス・頭数・ハンデ戦）を、事実表から読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通.facts import FACTS_TABLE, ensure_facts

#: 種類ごとの差に使う6つの印の列（docs/01 の 3。どれにも当てはまらないのが「芝・1〜2勝・14頭以上・ハンデ以外」）。
KIND_DUMMIES: tuple[str, ...] = ("kind_dirt", "kind_low_class", "kind_high_class", "kind_small_field", "kind_mid_field", "kind_handicap")
#: 決まりを種類ごとに選ぶときの種類（芝ダ × クラス）の列。
KIND_GROUP = "kind_group"
#: 芝ダ × クラスの6つの種類の名前（並び順）。
KIND_GROUPS: tuple[str, ...] = tuple(f"{surface}・{grade}" for surface in ("芝", "ダート") for grade in ("新馬・未勝利", "1〜2勝", "上のクラス"))
#: クラス名 → クラスの分け方。
_CLASS_GROUP = {"新馬": "新馬・未勝利", "未出走": "新馬・未勝利", "未勝利": "新馬・未勝利", "1勝クラス": "1〜2勝", "2勝クラス": "1〜2勝"}


class RaceKinds:
    """事実表（``ensure_facts``）のレース単位の列から、``start`` 以降の平地のレースの種類を1行 = 1レースで返す。

    列は ``race_id``（16桁の文字列）・``race_date``・``surface``・``class_group``・``field_size``・``weight_type``・``handicap``・``KIND_GROUP`` と ``KIND_DUMMIES``（0 か 1）。
    クラスは新馬・未勝利／1〜2勝／上のクラス（3勝・オープン・L・重賞）。例: ダートの未勝利・12頭・馬齢 → kind_dirt 1・kind_low_class 1・kind_mid_field 1。
    """

    def read(self, con: duckdb.DuckDBPyConnection, start: str) -> pd.DataFrame:
        ensure_facts(con)
        races = con.execute(f"""
            SELECT race_id, any_value(race_date) AS race_date, any_value(surface) AS surface, any_value(class_name) AS class_name,
                   any_value(field_size) AS field_size, any_value(weight_type) AS weight_type
            FROM {FACTS_TABLE}
            WHERE race_date >= ? AND surface IN ('芝', 'ダート')
            GROUP BY race_id""", [start]).df()
        return self.label(races)

    def label(self, races: pd.DataFrame) -> pd.DataFrame:
        """列 ``race_id``・``race_date``・``surface``・``class_name``・``field_size``・``weight_type`` の表に、種類の列を付ける。"""
        table = races.assign(race_id=races["race_id"].astype(str), race_date=pd.to_datetime(races["race_date"]))
        table["class_group"] = table["class_name"].map(_CLASS_GROUP).fillna("上のクラス")
        table["handicap"] = table["weight_type"] == "ハンデ"
        table[KIND_GROUP] = table["surface"] + "・" + table["class_group"]
        field = table["field_size"].astype(float)
        dummies = {
            "kind_dirt": table["surface"] == "ダート", "kind_low_class": table["class_group"] == "新馬・未勝利",
            "kind_high_class": table["class_group"] == "上のクラス", "kind_small_field": field <= 10,
            "kind_mid_field": (field >= 11) & (field <= 13), "kind_handicap": table["handicap"],
        }
        for name in KIND_DUMMIES:
            table[name] = dummies[name].astype(float)
        return table[["race_id", "race_date", "surface", "class_group", "field_size", "weight_type", "handicap", KIND_GROUP,
                      *KIND_DUMMIES]].reset_index(drop=True)
