"""レースと馬の鍵、中央だけ・確定成績の条件、最新行の選び方。

元DB（jvdata-store の DuckDB）の列名は JV-Data 仕様書の日本語そのままで、
``"開催回[第N回]"`` のように角括弧を含む。SQL に埋めるときは必ず :func:`q` で二重引用符に包む。
値はすべて文字列（仕様書の桁のまま）なので、数にしたいときは読む側で ``try_cast`` する。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

#: レースの鍵6列。レース単位の表（ra・se・hr・o1〜o6・dm・tm …）はすべてこの6列を持つ。
RACE_KEY: tuple[str, ...] = (
    "開催年", "開催月日", "競馬場コード", "開催回[第N回]", "開催日目[N日目]", "レース番号",
)
#: 鍵6列の桁数。連結すると rid（16桁）になる。
RACE_KEY_WIDTHS: tuple[int, ...] = (4, 4, 2, 2, 2, 2)
#: 馬の鍵。10桁（生年4 + 品種1 + 連番5）。
HORSE_KEY = "血統登録番号"
RID_LENGTH = sum(RACE_KEY_WIDTHS)
HID_LENGTH = 10

#: 確定成績のデータ区分（速報 5・6 と月曜の成績 7）。出走馬名表（1・2）や地方（A）・海外（B）は含めない。
FINAL_STAGES: tuple[str, ...] = ("5", "6", "7")
#: 出走しなかった異常区分（出走取消・発走除外・競走除外）。出走数に数えない。
NOT_RAN_CODES: tuple[str, ...] = ("1", "2", "3")
#: 出走したが着順が付かない異常区分（競走中止・失格）。「出走して馬券外」と数える。
OUT_OF_RACE_CODES: tuple[str, ...] = ("4", "5")
#: 中央競馬の競馬場コードの範囲（札幌 01 〜 小倉 10）。地方（30〜）と海外（A4 など）を除く。
JRA_VENUE_RANGE: tuple[str, str] = ("01", "10")


def q(column: str) -> str:
    """列名を二重引用符で包む。角括弧や空白を含む列名をそのまま SQL に書けるようにする。"""
    return '"' + column.replace('"', '""') + '"'


def col(column: str, alias: str = "") -> str:
    """別名付きの列の参照。``col("距離", "r")`` は ``r."距離"``。"""
    return f"{alias}.{q(column)}" if alias else q(column)


def key_list(alias: str = "") -> str:
    """鍵6列をカンマで並べたもの。``USING (...)``・``PARTITION BY ...`` に使う。"""
    return ", ".join(col(name, alias) for name in RACE_KEY)


def rid_expr(alias: str = "") -> str:
    """鍵6列を連結して rid（16桁）にする式。"""
    return " || ".join(col(name, alias) for name in RACE_KEY)


def race_date_expr(alias: str = "") -> str:
    """開催年と開催月日から ``YYYY-MM-DD`` を作る式。"""
    year, mmdd = col("開催年", alias), col("開催月日", alias)
    return f"{year} || '-' || substr({mmdd}, 1, 2) || '-' || substr({mmdd}, 3, 2)"


def sql_list(values: Iterable[str]) -> str:
    """文字列の並びを ``('5', '6', '7')`` の形にする。"""
    return "(" + ", ".join(f"'{value}'" for value in values) + ")"


def jra_only(alias: str = "") -> str:
    """中央競馬だけに絞る条件。"""
    low, high = JRA_VENUE_RANGE
    return f"{col('競馬場コード', alias)} BETWEEN '{low}' AND '{high}'"


def final_only(alias: str = "") -> str:
    """確定成績だけに絞る条件。"""
    return f"{col('データ区分', alias)} IN {sql_list(FINAL_STAGES)}"


def latest_qualify(partition: Sequence[str], alias: str = "") -> str:
    """同じ鍵に複数のデータ区分の行があるとき、最新の1行だけを残す ``QUALIFY`` 句。

    速報（5・6）のあとに月曜の成績（7）が届くので、データ区分の大きいもの、
    同じなら作成日の新しいものを選ぶ。
    """
    keys = ", ".join(col(name, alias) for name in partition)
    order = f"{col('データ区分', alias)} DESC, {col('データ作成年月日', alias)} DESC"
    return f"QUALIFY row_number() OVER (PARTITION BY {keys} ORDER BY {order}) = 1"


def split_rid(rid: str) -> dict[str, str]:
    """rid（16桁）を鍵6列の値に分ける。桁が違えば ``ValueError``。"""
    text = str(rid).strip()
    if len(text) != RID_LENGTH or not text.isdigit():
        raise ValueError(f"rid は16桁の数字です: {rid!r}")
    values: dict[str, str] = {}
    position = 0
    for name, width in zip(RACE_KEY, RACE_KEY_WIDTHS):
        values[name] = text[position:position + width]
        position += width
    return values


def rid_condition(rid: str, alias: str = "") -> tuple[str, list[str]]:
    """rid に一致する行を選ぶ WHERE 句の条件と、その引数。"""
    values = split_rid(rid)
    clause = " AND ".join(f"{col(name, alias)} = ?" for name in RACE_KEY)
    return clause, [values[name] for name in RACE_KEY]


def validate_hid(hid: str) -> str:
    """血統登録番号（10桁の数字）を確かめて返す。"""
    text = str(hid).strip()
    if len(text) != HID_LENGTH or not text.isdigit():
        raise ValueError(f"血統登録番号は10桁の数字です: {hid!r}")
    return text
