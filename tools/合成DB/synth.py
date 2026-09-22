"""テスト用の小さな DuckDB（合成DB）を作る。列名は JV-Data 仕様書のまま、値は文字列。

実DB に触らずにツールと共通部品を試すためのもの。テストはここの関数で表を組み立てる。
ツールとしても使え、実DB が無い PC でほかのツールの動きを見られる:

    uv run python tools/合成DB/synth.py --out reports/synth.duckdb
    uv run python tools/DBの状態/db_info.py --db reports/synth.duckdb

値はすべて架空。列は実DB の一部だけ（各ツールが読む列）。確定成績の6レースと、確定前の2レース（出馬表を試すため）が入る。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import keys  # noqa: E402

KEY_COLUMNS: tuple[str, ...] = keys.RACE_KEY
_HEADER: tuple[str, ...] = ("レコード種別ID", "データ区分", "データ作成年月日")
_LAPS: tuple[str, ...] = tuple(f"ラップタイム_{i:02d}" for i in range(1, 26))

RA_COLUMNS: tuple[str, ...] = (
    *_HEADER, *KEY_COLUMNS,
    "競走名本題", "競走名略称10文字", "グレードコード", "競走種別コード", "競走記号コード", "重量種別コード",
    "競走条件コード 最若年条件", "競走条件名称", "距離", "トラックコード", "コース区分", "発走時刻",
    "登録頭数", "出走頭数", "入線頭数", "天候コード", "芝馬場状態コード", "ダート馬場状態コード",
    *_LAPS, "前3ハロン", "前4ハロン", "後3ハロン", "後4ハロン",
)
SE_COLUMNS: tuple[str, ...] = (
    *_HEADER, *KEY_COLUMNS,
    "枠番", "馬番", "血統登録番号", "馬名", "性別コード", "馬齢", "東西所属コード", "調教師コード", "調教師名略称",
    "負担重量", "ブリンカー使用区分", "騎手コード", "騎手名略称", "騎手見習コード", "馬体重", "増減符号", "増減差",
    "異常区分コード", "入線順位", "確定着順", "走破タイム", "着差コード",
    "1コーナーでの順位", "2コーナーでの順位", "3コーナーでの順位", "4コーナーでの順位",
    "単勝オッズ", "単勝人気順", "後4ハロンタイム", "後3ハロンタイム", "タイム差",
    "マイニング区分", "マイニング予想順位", "今回レース脚質判定",
)
PAYOUT_COLUMNS: tuple[str, ...] = (*KEY_COLUMNS, "_連番", "馬番", "払戻金", "人気順")
#: 組み合わせの券種（馬連・3連複・3連単）の払戻。組番は馬番を並べた文字列（馬連 ``0104``、3連単 ``040102``）。
COMBO_PAYOUT_COLUMNS: tuple[str, ...] = (*KEY_COLUMNS, "_連番", "組番", "払戻金", "人気順")
#: 払戻の親（``hr``）のフラグの券種。列名は「不成立フラグ　単勝」のように全角スペースでつなぐ（実DB と同じ）。
HR_FLAG_BETS: tuple[str, ...] = ("単勝", "複勝", "枠連", "馬連", "ワイド", "馬単", "3連複", "3連単")
HR_FLAG_KINDS: tuple[str, ...] = ("不成立フラグ", "特払フラグ", "返還フラグ")
HR_COLUMNS: tuple[str, ...] = (
    *_HEADER, *KEY_COLUMNS, "登録頭数", "出走頭数",
    *(f"{kind}　{bet}" for kind in HR_FLAG_KINDS for bet in HR_FLAG_BETS),
)
CORNER_COLUMNS: tuple[str, ...] = (*KEY_COLUMNS, "_連番", "コーナー", "周回数", "各通過順位")
TM_COLUMNS: tuple[str, ...] = (*KEY_COLUMNS, "_連番", "馬番", "予測スコア")
DM_COLUMNS: tuple[str, ...] = (*KEY_COLUMNS, "_連番", "馬番", "予想走破タイム", "予想誤差(信頼度)＋", "予想誤差(信頼度)－")
UM_COLUMNS: tuple[str, ...] = (
    *_HEADER, "血統登録番号", "生年月日", "馬名", "性別コード", "毛色コード", "東西所属コード",
    "調教師コード", "調教師名略称", "生産者名(法人格無)", "産地名", "馬主名(法人格無)",
)
PEDIGREE_COLUMNS: tuple[str, ...] = ("血統登録番号", "_連番", "繁殖登録番号", "馬名")

#: 出走別着度数の着回数の項目（中央の合計、芝ダ×距離帯、芝ダ×馬場状態、競馬場×芝ダ）。1着〜5着と着外の6つずつ。
CK_DISTANCE_BANDS: tuple[str, ...] = (
    "1200以下", "1201-1400", "1401-1600", "1601-1800", "1801-2000", "2001-2200", "2201-2400", "2401-2800", "2801以上",
)
CK_COUNT_ITEMS: tuple[str, ...] = (
    "中央合計着回数",
    *(f"{surface}{band}・着回数" for surface in ("芝", "ダ") for band in CK_DISTANCE_BANDS),
    *(f"{surface}{going}・着回数" for surface in ("芝", "ダ") for going in ("良", "稍", "重", "不")),
    *(f"{venue}{surface}・着回数" for venue in ("札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉")
      for surface in ("芝", "ダ")),
)
#: 着回数の数（1着〜5着と着外）。列名は「項目_1」〜「項目_6」。
CK_SLOTS = 6
CK_COLUMNS: tuple[str, ...] = (
    *_HEADER, *KEY_COLUMNS, "血統登録番号", "馬名",
    *(f"{item}_{slot}" for item in CK_COUNT_ITEMS for slot in range(1, CK_SLOTS + 1)),
)
_WORKOUT_TIMES: tuple[str, ...] = (
    "4ハロンタイム合計(800M～0M)", "ラップタイム(800M～600M)", "3ハロンタイム合計(600M～0M)", "ラップタイム(600M～400M)",
    "2ハロンタイム合計(400M～0M)", "ラップタイム(400M～200M)", "ラップタイム(200M～0M)",
)
HC_COLUMNS: tuple[str, ...] = (*_HEADER, "トレセン区分", "調教年月日", "調教時刻", "血統登録番号", *_WORKOUT_TIMES)
WC_COLUMNS: tuple[str, ...] = (*_HEADER, "トレセン区分", "調教年月日", "調教時刻", "血統登録番号", "コース", "馬場周り", *_WORKOUT_TIMES)
#: 天候馬場状態。変更後・変更前の同じ名前の列は、実DB と同じく2つ目に「#2」が付く。
WE_COLUMNS: tuple[str, ...] = (
    *_HEADER, *KEY_COLUMNS[:-1], "発表月日時分", "変更識別",
    "天候状態", "馬場状態・芝", "馬場状態・ダート", "天候状態#2", "馬場状態・芝#2", "馬場状態・ダート#2",
)
WH_COLUMNS: tuple[str, ...] = (*_HEADER, *KEY_COLUMNS, "発表月日時分")
WH_WEIGHT_COLUMNS: tuple[str, ...] = (*KEY_COLUMNS, "_連番", "馬番", "馬名", "馬体重", "増減符号", "増減差")
AV_COLUMNS: tuple[str, ...] = (*_HEADER, *KEY_COLUMNS, "発表月日時分", "馬番", "馬名", "事由区分")

#: 表の名前と列。実DB と同じ名前・同じ列名（の一部）。
TABLES: dict[str, tuple[str, ...]] = {
    "ra": RA_COLUMNS, "se": SE_COLUMNS,
    "hr__単勝払戻": PAYOUT_COLUMNS, "hr__複勝払戻": PAYOUT_COLUMNS,
    "ra__コーナー通過順位": CORNER_COLUMNS,
    "tm__マイニング予想": TM_COLUMNS, "dm__マイニング予想": DM_COLUMNS,
    "um": UM_COLUMNS, "um__3代血統情報": PEDIGREE_COLUMNS,
}
#: 取得していない DB もある表と列。``Sample`` に行があるときだけ作る（行が無ければ、実DB の取得前と同じく表が無い）。
OPTIONAL_TABLES: dict[str, tuple[str, ...]] = {
    "ck": CK_COLUMNS, "hc": HC_COLUMNS, "wc": WC_COLUMNS,
    "we": WE_COLUMNS, "wh": WH_COLUMNS, "wh__馬体重情報": WH_WEIGHT_COLUMNS, "av": AV_COLUMNS,
    "hr": HR_COLUMNS, "hr__馬連払戻": COMBO_PAYOUT_COLUMNS, "hr__3連複払戻": COMBO_PAYOUT_COLUMNS,
    "hr__3連単払戻": COMBO_PAYOUT_COLUMNS,
}
#: 親の表の表題（実DB の ``_tables`` と同じ）。
TITLES: dict[str, str] = {
    "ra": "レース詳細", "se": "馬毎レース情報", "hr": "払戻", "tm": "対戦型マイニング予想",
    "dm": "タイム型マイニング予想", "um": "競走馬マスタ", "ck": "出走別着度数", "hc": "坂路調教",
    "wc": "ウッドチップ調教", "we": "天候馬場状態", "wh": "馬体重", "av": "出走取消・競走除外",
}
#: 親の表の鍵（実DB の ``_tables`` の keys）。書いていない表は血統登録番号。
_TABLE_KEYS: dict[str, tuple[str, ...]] = {
    **{name: KEY_COLUMNS for name in ("ra", "se", "hr", "tm", "dm", "wh")},
    "ck": (*KEY_COLUMNS, "血統登録番号"), "av": (*KEY_COLUMNS, "馬番"),
    "hc": ("トレセン区分", "調教年月日", "調教時刻", "血統登録番号"),
    "wc": ("トレセン区分", "調教年月日", "調教時刻", "血統登録番号"),
    "we": (*KEY_COLUMNS[:-1], "発表月日時分", "変更識別"),
}
#: 文字列でない列。
INTEGER_COLUMNS: frozenset[str] = frozenset({"_連番"})

#: 3代血統情報の連番。1 父・2 母・3 父父・4 父母・5 母父・6 母母。
SIRE, DAM, GRANDSIRE, DAMSIRE = 1, 2, 3, 5


def _row(columns: tuple[str, ...], values: dict[str, str]) -> dict[str, str]:
    """列をすべて持つ1行。指定しない列は空文字。"""
    row = dict.fromkeys(columns, "")
    row.update(values)
    return row


def race_key(day: str, no: str, *, venue: str = "05", kai: str = "01", nichi: str = "01") -> dict[str, str]:
    """鍵6列の値。``day`` は ``YYYYMMDD``、``no`` はレース番号（``'01'``）。"""
    return {
        "開催年": day[:4], "開催月日": day[4:], "競馬場コード": venue,
        "開催回[第N回]": kai, "開催日目[N日目]": nichi, "レース番号": no,
    }


def race(day: str, no: str, *, venue: str = "05", track: str = "11", distance: str = "1600",
         turf: str = "1", dirt: str = "0", field_size: str = "05", entries: str = "06",
         name: str = "", condition: str = "005", grade: str = " ", stage: str = "7",
         laps: tuple[str, ...] = (), **over: str) -> dict[str, str]:
    """レース1行（既定: 東京 芝・左 1600m 良、条件 1勝クラス、5頭出走）。"""
    values = {
        "レコード種別ID": "RA", "データ区分": stage, "データ作成年月日": day,
        **race_key(day, no, venue=venue),
        "競走名本題": name, "グレードコード": grade, "競走種別コード": "13", "競走記号コード": "000",
        "重量種別コード": "3", "競走条件コード 最若年条件": condition, "距離": distance, "トラックコード": track,
        "コース区分": "A ", "発走時刻": "1500", "登録頭数": entries, "出走頭数": field_size, "入線頭数": field_size,
        "天候コード": "1", "芝馬場状態コード": turf, "ダート馬場状態コード": dirt,
        "前3ハロン": "350", "前4ハロン": "470", "後3ハロン": "350", "後4ハロン": "470",
    }
    for index, lap in enumerate(laps, start=1):
        values[f"ラップタイム_{index:02d}"] = lap
    values.update(over)
    return _row(RA_COLUMNS, values)


def runner(race_row: dict[str, str], num: int, pop: int, fin: int, *, hid: str | None = None,
           name: str | None = None, abnormal: str = "0", odds: str = "0035", corner4: int | None = None,
           jockey: tuple[str, str] = ("00001", "騎手A"), trainer: tuple[str, str] = ("00001", "調教師A"),
           weight: str = "480", change: tuple[str, str] = ("+", "002"), last3f: str = "350",
           mining_rank: int | None = None, style: str = "2", sex: str = "1", age: str = "04",
           time: str = "1340", stage: str | None = None, **over: str) -> dict[str, str]:
    """出走1頭。馬番・人気・着順を指定する（着順 0 は着順なし。取消・中止のとき）。"""
    key = {name_: race_row[name_] for name_ in KEY_COLUMNS}
    day = race_row["開催年"] + race_row["開催月日"]
    corner = corner4 if corner4 is not None else fin
    values = {
        "レコード種別ID": "SE", "データ区分": stage or race_row["データ区分"], "データ作成年月日": day, **key,
        "枠番": str(min(8, num)), "馬番": f"{num:02d}", "血統登録番号": hid or f"2020{num:06d}",
        "馬名": name or f"ウマ{num:02d}", "性別コード": sex, "馬齢": age, "東西所属コード": "1",
        "調教師コード": trainer[0], "調教師名略称": trainer[1], "負担重量": "570", "ブリンカー使用区分": "0",
        "騎手コード": jockey[0], "騎手名略称": jockey[1], "騎手見習コード": "0",
        "馬体重": weight, "増減符号": change[0], "増減差": change[1], "異常区分コード": abnormal,
        "入線順位": f"{fin:02d}", "確定着順": f"{fin:02d}", "走破タイム": time if fin else "0000",
        "着差コード": "", "1コーナーでの順位": f"{corner:02d}", "2コーナーでの順位": f"{corner:02d}",
        "3コーナーでの順位": f"{corner:02d}", "4コーナーでの順位": f"{corner:02d}",
        "単勝オッズ": odds, "単勝人気順": f"{pop:02d}", "後4ハロンタイム": "470", "後3ハロンタイム": last3f,
        "タイム差": f"{max(0, fin - 1) * 2:03d}" if fin else "9999", "マイニング区分": "3",
        "マイニング予想順位": f"{mining_rank if mining_rank is not None else pop:02d}", "今回レース脚質判定": style,
    }
    values.update(over)
    return _row(SE_COLUMNS, values)


def payout(race_row: dict[str, str], num: int, yen: int, *, seq: int = 1, pop: int = 1) -> dict[str, str]:
    """払戻1件（単勝・複勝で同じ形）。``払戻金`` は9桁ゼロ埋めの円。"""
    key = {name: race_row[name] for name in KEY_COLUMNS}
    return _row(PAYOUT_COLUMNS, {**key, "_連番": str(seq), "馬番": f"{num:02d}", "払戻金": f"{yen:09d}", "人気順": f"{pop:02d}"})


def combo_payout(race_row: dict[str, str], combo: str, yen: int, *, seq: int = 1, pop: int = 1,
                 table: str = "hr__3連単払戻") -> dict[str, str]:
    """組み合わせの券種（馬連・3連複・3連単）の払戻1件。``combo`` は組番（馬番を2桁ずつ並べた文字列）。"""
    if table not in OPTIONAL_TABLES or OPTIONAL_TABLES[table] is not COMBO_PAYOUT_COLUMNS:
        raise ValueError(f"組み合わせの払戻の表ではありません: {table}")
    key = {name: race_row[name] for name in KEY_COLUMNS}
    return _row(COMBO_PAYOUT_COLUMNS, {**key, "_連番": str(seq), "組番": combo, "払戻金": f"{yen:09d}", "人気順": f"{pop:03d}"})


def payout_header(race_row: dict[str, str], *, void: Sequence[str] = (), special: Sequence[str] = (),
                  refund: Sequence[str] = ()) -> dict[str, str]:
    """払戻の親（``hr``）1件。``void``・``special``・``refund`` に、不成立・特払・返還にする券種（``HR_FLAG_BETS``）を並べる。"""
    flags = {"不成立フラグ": void, "特払フラグ": special, "返還フラグ": refund}
    key = {name: race_row[name] for name in KEY_COLUMNS}
    values = {
        "レコード種別ID": "HR", "データ区分": "2", "データ作成年月日": race_row["開催年"] + race_row["開催月日"], **key,
        "登録頭数": race_row["登録頭数"], "出走頭数": race_row["出走頭数"],
        **{f"{kind}　{bet}": "1" if bet in bets else "0" for kind, bets in flags.items() for bet in HR_FLAG_BETS},
    }
    return _row(HR_COLUMNS, values)


def corner(race_row: dict[str, str], seq: int, corner_no: int, order: str) -> dict[str, str]:
    """コーナー通過順位1件。``order`` は ``'4,1,2,3,5'`` のような並び。"""
    key = {name: race_row[name] for name in KEY_COLUMNS}
    return _row(CORNER_COLUMNS, {**key, "_連番": str(seq), "コーナー": str(corner_no), "周回数": "1", "各通過順位": order})


def tm(race_row: dict[str, str], num: int, score: int) -> dict[str, str]:
    """対戦型の予測スコア1件（10倍の整数。``750`` = 75.0）。"""
    key = {name: race_row[name] for name in KEY_COLUMNS}
    return _row(TM_COLUMNS, {**key, "_連番": str(num), "馬番": f"{num:02d}", "予測スコア": str(score)})


def dm(race_row: dict[str, str], num: int, time: str) -> dict[str, str]:
    """タイム型の予想走破タイム1件（``'13405'`` = 1分34秒05）。"""
    key = {name: race_row[name] for name in KEY_COLUMNS}
    return _row(DM_COLUMNS, {**key, "_連番": str(num), "馬番": f"{num:02d}", "予想走破タイム": time})


def horse(hid: str, name: str, *, sex: str = "1", born: str = "20200401",
          trainer: tuple[str, str] = ("00001", "調教師A")) -> dict[str, str]:
    """競走馬マスタ1頭。"""
    return _row(UM_COLUMNS, {
        "レコード種別ID": "UM", "データ区分": "1", "データ作成年月日": born, "血統登録番号": hid, "生年月日": born,
        "馬名": name, "性別コード": sex, "毛色コード": "01", "東西所属コード": "1",
        "調教師コード": trainer[0], "調教師名略称": trainer[1], "生産者名(法人格無)": "生産者A", "産地名": "産地A",
        "馬主名(法人格無)": "馬主A",
    })


def pedigree(hid: str, *, sire: str = "父A", dam: str = "母A", grandsire: str = "父父A",
             damsire: str = "母父A") -> list[dict[str, str]]:
    """3代血統情報（父・母・父父・母父の4行）。"""
    names = {SIRE: sire, DAM: dam, GRANDSIRE: grandsire, DAMSIRE: damsire}
    return [
        _row(PEDIGREE_COLUMNS, {"血統登録番号": hid, "_連番": str(seq), "繁殖登録番号": f"{seq:010d}", "馬名": name})
        for seq, name in names.items()
    ]


def ck(race_row: dict[str, str], hid: str, counts: Mapping[str, Sequence[int]] | None = None, *,
       name: str = "") -> dict[str, str]:
    """出走別着度数1件（そのレースの出走馬名表の時点の、馬の通算の着回数）。

    ``counts`` は 項目（``CK_COUNT_ITEMS`` のどれか）→ 1着〜5着と着外の6つの回数。書かない項目は全部 0。
    """
    unknown = set(counts or {}) - set(CK_COUNT_ITEMS)
    if unknown:
        raise ValueError(f"出走別着度数に無い項目です: {sorted(unknown)}")
    key = {name_: race_row[name_] for name_ in KEY_COLUMNS}
    values = {"レコード種別ID": "CK", "データ区分": "1", "データ作成年月日": race_row["開催年"] + race_row["開催月日"],
              **key, "血統登録番号": hid, "馬名": name}
    for item in CK_COUNT_ITEMS:
        slots = (counts or {}).get(item, (0,) * CK_SLOTS)
        values.update({f"{item}_{slot}": f"{count:03d}" for slot, count in enumerate(slots, start=1)})
    return _row(CK_COLUMNS, values)


def hill_workout(hid: str, day: str, *, time: str = "0600", four_furlongs: str = "0540",
                 last_furlong: str = "128") -> dict[str, str]:
    """坂路調教1本。``day`` は ``YYYYMMDD``。タイムは 0.1秒単位（``'0540'`` = 54.0秒、``'128'`` = 12.8秒。``'0000'`` は測定不良）。"""
    return _row(HC_COLUMNS, {
        "レコード種別ID": "HC", "データ区分": "1", "データ作成年月日": day, "トレセン区分": "0", "調教年月日": day,
        "調教時刻": time, "血統登録番号": hid, "4ハロンタイム合計(800M～0M)": four_furlongs, "ラップタイム(200M～0M)": last_furlong,
    })


def wood_workout(hid: str, day: str, *, time: str = "0700", four_furlongs: str = "0520",
                 last_furlong: str = "118") -> dict[str, str]:
    """ウッドチップ調教1本。値の形は ``hill_workout`` と同じ。"""
    return _row(WC_COLUMNS, {
        "レコード種別ID": "WC", "データ区分": "1", "データ作成年月日": day, "トレセン区分": "0", "調教年月日": day,
        "調教時刻": time, "血統登録番号": hid, "コース": "0", "馬場周り": "0",
        "4ハロンタイム合計(800M～0M)": four_furlongs, "ラップタイム(200M～0M)": last_furlong,
    })


def going_report(race_row: dict[str, str], *, announced: str, turf: str, dirt: str, change: str = "1") -> dict[str, str]:
    """天候馬場状態の速報1件（そのレースの開催日・競馬場）。``announced`` は発表月日時分（``'04181700'``）。

    ``change`` は変更識別（1 初期状態・2 天候変更・3 馬場状態変更）。
    """
    key = {name: race_row[name] for name in KEY_COLUMNS[:-1]}
    return _row(WE_COLUMNS, {
        "レコード種別ID": "WE", "データ区分": "1", "データ作成年月日": race_row["開催年"] + race_row["開催月日"], **key,
        "発表月日時分": announced, "変更識別": change, "天候状態": "1", "馬場状態・芝": turf, "馬場状態・ダート": dirt,
    })


def weight_report(race_row: dict[str, str], weights: Mapping[int, tuple[str, str, str]], *,
                  announced: str) -> tuple[dict[str, str], list[dict[str, str]]]:
    """馬体重の速報（親1件と、馬番ごとの子）。``weights`` は 馬番 → （馬体重, 増減符号, 増減差）。"""
    key = {name: race_row[name] for name in KEY_COLUMNS}
    parent = _row(WH_COLUMNS, {"レコード種別ID": "WH", "データ区分": "1",
                               "データ作成年月日": race_row["開催年"] + race_row["開催月日"], **key, "発表月日時分": announced})
    children = [
        _row(WH_WEIGHT_COLUMNS, {**key, "_連番": str(seq), "馬番": f"{num:02d}", "馬名": f"ウマ{num:02d}",
                                 "馬体重": weight, "増減符号": sign, "増減差": diff})
        for seq, (num, (weight, sign, diff)) in enumerate(sorted(weights.items()), start=1)
    ]
    return parent, children


def scratch_report(race_row: dict[str, str], num: int, *, announced: str, stage: str = "1") -> dict[str, str]:
    """出走取消（``stage`` 1）・競走除外（2）の速報1件。"""
    key = {name: race_row[name] for name in KEY_COLUMNS}
    return _row(AV_COLUMNS, {"レコード種別ID": "AV", "データ区分": stage, "データ作成年月日": race_row["開催年"] + race_row["開催月日"],
                             **key, "発表月日時分": announced, "馬番": f"{num:02d}", "馬名": f"ウマ{num:02d}", "事由区分": "001"})


@dataclass
class Sample:
    """合成DB に入れる行の束。表ごとの行のリスト。"""

    ra: list[dict[str, str]] = field(default_factory=list)
    se: list[dict[str, str]] = field(default_factory=list)
    win: list[dict[str, str]] = field(default_factory=list)
    place: list[dict[str, str]] = field(default_factory=list)
    corners: list[dict[str, str]] = field(default_factory=list)
    tm: list[dict[str, str]] = field(default_factory=list)
    dm: list[dict[str, str]] = field(default_factory=list)
    um: list[dict[str, str]] = field(default_factory=list)
    pedigree: list[dict[str, str]] = field(default_factory=list)
    ck: list[dict[str, str]] = field(default_factory=list)
    hill: list[dict[str, str]] = field(default_factory=list)
    wood: list[dict[str, str]] = field(default_factory=list)
    going: list[dict[str, str]] = field(default_factory=list)
    weight: list[dict[str, str]] = field(default_factory=list)
    weights: list[dict[str, str]] = field(default_factory=list)
    scratches: list[dict[str, str]] = field(default_factory=list)
    #: 払戻の親（券種ごとのフラグ）と、組み合わせの券種の払戻。荒れ具合の予想のテストに使う。
    headers: list[dict[str, str]] = field(default_factory=list)
    quinella: list[dict[str, str]] = field(default_factory=list)
    trio: list[dict[str, str]] = field(default_factory=list)
    trifecta: list[dict[str, str]] = field(default_factory=list)

    def extend(self, other: "Sample") -> "Sample":
        """別の束を足す。"""
        for name in vars(self):
            getattr(self, name).extend(getattr(other, name))
        return self

    def tables(self) -> dict[str, list[dict[str, str]]]:
        """表の名前ごとの行。馬マスタと血統は鍵ごとに1行（実DB の主キーと同じ）。``OPTIONAL_TABLES`` は行があるときだけ。"""
        optional = {
            "ck": self.ck, "hc": self.hill, "wc": self.wood,
            "we": self.going, "wh": self.weight, "wh__馬体重情報": self.weights, "av": self.scratches,
            "hr": self.headers, "hr__馬連払戻": self.quinella, "hr__3連複払戻": self.trio, "hr__3連単払戻": self.trifecta,
        }
        return {
            "ra": self.ra, "se": self.se, "hr__単勝払戻": self.win, "hr__複勝払戻": self.place,
            "ra__コーナー通過順位": self.corners, "tm__マイニング予想": self.tm, "dm__マイニング予想": self.dm,
            "um": _unique(self.um, ("血統登録番号",)), "um__3代血統情報": _unique(self.pedigree, ("血統登録番号", "_連番")),
            **{name: rows for name, rows in optional.items() if rows},
        }


def _unique(rows: list[dict[str, str]], key: tuple[str, ...]) -> list[dict[str, str]]:
    """鍵が同じ行は最初の1行だけ残す。"""
    seen: set[tuple[str, ...]] = set()
    out: list[dict[str, str]] = []
    for row in rows:
        marker = tuple(row[c] for c in key)
        if marker not in seen:
            seen.add(marker)
            out.append(row)
    return out


#: 4頭の既定の着順（馬番 → 着順）。1番人気が4着、4番人気（穴）が1着。
_DEFAULT_FINISHES: dict[int, int] = {1: 4, 2: 2, 3: 3, 4: 1}


def _finishes(fav_fin: int) -> dict[int, int]:
    """1番人気の着順を ``fav_fin`` にし、その着順を持っていた馬に4着を回す。着順は必ず 1〜4 の並べ替え。"""
    if fav_fin not in _DEFAULT_FINISHES.values():
        raise ValueError(f"1番人気の着順は 1〜4 です: {fav_fin}")
    finishes = dict(_DEFAULT_FINISHES)
    displaced = next(num for num, fin in finishes.items() if fin == fav_fin)
    finishes[displaced] = finishes[1]
    finishes[1] = fav_fin
    return finishes


def simple_race(day: str = "20240406", no: str = "01", *, fav_fin: int = 4, fav_odds: str = "0020",
                **race_over: str) -> Sample:
    """6頭登録・5頭出走の1レース。

    馬番1 = 1番人気（既定 4着・2.0倍）、2 = 2番人気 2着、3 = 3番人気 3着、
    4 = 4番人気 1着（15.0倍の穴。脚質は逃げ）、5 = 5番人気 競走中止、6 = 出走取消（人気・オッズなし）。
    """
    ra = race(day, no, **race_over)
    finishes = _finishes(fav_fin)
    se = [
        runner(ra, 1, 1, finishes[1], odds=fav_odds, jockey=("00001", "騎手A"), mining_rank=1),
        runner(ra, 2, 2, finishes[2], odds="0045", jockey=("00002", "騎手B")),
        runner(ra, 3, 3, finishes[3], odds="0080", jockey=("00003", "騎手C")),
        runner(ra, 4, 4, finishes[4], odds="0150", jockey=("00004", "騎手D"), mining_rank=4, style="1"),
        runner(ra, 5, 5, 0, odds="0300", abnormal="4", corner4=5),
        runner(ra, 6, 0, 0, odds="0000", abnormal="1", corner4=0),
    ]
    finish_of = {int(r["馬番"]): int(r["確定着順"]) for r in se if r["異常区分コード"] not in keys.NOT_RAN_CODES}
    winner = next(num for num, fin in finish_of.items() if fin == 1)
    placed = sorted((num for num, fin in finish_of.items() if 1 <= fin <= 3), key=lambda n: finish_of[n])
    win_yen = {1: 200, 2: 450, 3: 800, 4: 1500}[winner]
    place_yen = {1: 110, 2: 180, 3: 250, 4: 400}
    return Sample(
        ra=[ra], se=se,
        win=[payout(ra, winner, win_yen, pop=int(se[winner - 1]["単勝人気順"]))],
        place=[payout(ra, num, place_yen[num], seq=seq, pop=int(se[num - 1]["単勝人気順"]))
               for seq, num in enumerate(placed, start=1)],
        corners=[corner(ra, 1, 4, ",".join(str(n) for n in sorted(finish_of, key=lambda n: finish_of[n] or 99)))],
        tm=[tm(ra, num, 800 - 60 * (num - 1)) for num in range(1, 6)],
        um=[horse(r["血統登録番号"], r["馬名"], sex=r["性別コード"]) for r in se],
        pedigree=pedigree(se[0]["血統登録番号"]),
    )


#: 確定前のレースで、まだ決まっていない値（実DB の出走馬名表と同じ形）。
_UNDECIDED_RACE: dict[str, str] = {
    "天候コード": "0", "入線頭数": "00", "前3ハロン": "000", "前4ハロン": "000", "後3ハロン": "000", "後4ハロン": "000",
}
_UNDECIDED_RUNNER: dict[str, str] = {"後4ハロンタイム": "000", "タイム差": "", "マイニング区分": "0"}
_CARD_STAGES: tuple[str, ...] = ("1", "2")
#: 確定前のレースに出す馬番。1〜5 は ``simple_race`` と同じ馬（過去走がある）、7 は初出走。
_CARD_HORSE_NUMBERS: tuple[int, ...] = (1, 2, 3, 4, 5, 7)


def card_race(day: str = "20250419", no: str = "01", *, stage: str = "1", **race_over: str) -> Sample:
    """確定前の1レース（6頭登録）。結果・オッズ・馬体重・払戻は無い。

    ``stage`` が ``'1'``（木曜の出走馬名表）なら枠番・馬番は未定、``'2'``（金土の出馬表）なら決まっていて、
    直前のマイニング予想（対戦型は馬番の小さい順、タイム型は馬番の大きい順に上位）も付く。
    馬は ``simple_race`` と血統登録番号が同じなので、同じ DB に入れると近走が付く。馬番7 だけ初出走。
    """
    if stage not in _CARD_STAGES:
        raise ValueError(f"確定前のデータ区分は {_CARD_STAGES} のどちらかです: {stage}")
    entries = f"{len(_CARD_HORSE_NUMBERS):02d}"
    ra = race(day, no, stage=stage, field_size="00", entries=entries, turf="0", dirt="0", **{**_UNDECIDED_RACE, **race_over})
    is_numbered = stage == "2"
    numbering = {} if is_numbered else {"枠番": "0", "馬番": "00"}
    se = [
        runner(ra, num, 0, 0, odds="0000", weight="", change=("", ""), last3f="000", mining_rank=0, style="0",
               jockey=(f"{num:05d}", f"騎手{num}"), **{**_UNDECIDED_RUNNER, **numbering})
        for num in _CARD_HORSE_NUMBERS
    ]
    sample = Sample(ra=[ra], se=se, um=[horse(r["血統登録番号"], r["馬名"], sex=r["性別コード"]) for r in se])
    if is_numbered:
        sample.tm = [tm(ra, num, 800 - 60 * num) for num in _CARD_HORSE_NUMBERS]
        sample.dm = [dm(ra, num, f"1{3500 - 10 * num:04d}") for num in _CARD_HORSE_NUMBERS]
    return sample


def sample() -> Sample:
    """ツールを試すための行の束。東京 芝1600 良 の4レースと、中山 芝1600 稍重・東京 ダ1600 良 の各1レース。"""
    rows = Sample()
    for day, no, fav_fin in (("20240406", "01", 4), ("20240406", "02", 1), ("20240407", "01", 2), ("20250412", "01", 4)):
        rows.extend(simple_race(day, no, fav_fin=fav_fin))
    rows.extend(simple_race("20240407", "03", fav_fin=1, venue="06", track="17", turf="2"))
    rows.extend(simple_race("20240406", "05", fav_fin=3, track="23", turf="0", dirt="1"))
    return rows


def card_sample() -> Sample:
    """確定前の2レース（2025-04-19 東京）。1R は出走馬名表（枠番・馬番が未定）、2R は出馬表。"""
    return card_race("20250419", "01", stage="1").extend(card_race("20250419", "02", stage="2", name="合成特別"))


#: 傾向スコアの合成DB で、過去のレースを置く開催日。後ろの2つは競走名を「合成特別」にして、同レースの過去にする。
_TREND_DAYS: tuple[str, ...] = ("20240406", "20240413", "20240420", "20240427", "20240504", "20240511")
_TREND_NAMED_DAYS: tuple[str, ...] = _TREND_DAYS[-2:]
TREND_RACE_NAME = "合成特別"


def trend_sample() -> Sample:
    """傾向スコアを試すための行の束。傾向がはっきり出るように、同じ結果のレースを重ねる。

    東京 芝・左 1600m 良 の6レースで、いつも馬番4（4番人気・逃げ）が勝ち、馬番1（1番人気）が4着。
    確定前の2レース（``card_sample``。2R は「合成特別」の出馬表）を足すので、2R の同レースの過去は2つになる。
    """
    rows = Sample()
    for day in _TREND_DAYS:
        rows.extend(simple_race(day, "01", name=TREND_RACE_NAME if day in _TREND_NAMED_DAYS else ""))
    return rows.extend(card_sample())


def sample_db(path: Path) -> Path:
    """確定成績だけの DB（``sample``）。集計のテストはこれを使う。"""
    return build_db(path, sample())


def card_db(path: Path) -> Path:
    """確定成績（``sample``）に、確定前の2レース（``card_sample``）を足した DB。出馬表のテストと、ツールの試用に使う。"""
    return build_db(path, sample().extend(card_sample()))


def trend_db(path: Path) -> Path:
    """傾向スコアのテスト用の DB（``trend_sample``）。"""
    return build_db(path, trend_sample())


def build_db(path: Path, sample: Sample | None = None, *, tables: dict[str, list[dict[str, str]]] | None = None,
             with_meta: bool = True) -> Path:
    """表を作って行を入れる。``tables`` を渡すと、その表だけを作る（無い表の動きを試すため）。

    列はすべて VARCHAR、``_連番`` だけ INTEGER。実DB と同じく ``_tables``・``_meta`` も作る。
    """
    rows_by_table = tables if tables is not None else (sample or Sample()).tables()
    path = Path(path)
    if path.exists():
        path.unlink()
    con = duckdb.connect(str(path))
    try:
        for name, rows in rows_by_table.items():
            columns = {**TABLES, **OPTIONAL_TABLES}[name]
            defs = ", ".join(f'{keys.q(c)} {"INTEGER" if c in INTEGER_COLUMNS else "VARCHAR"}' for c in columns)
            con.execute(f"CREATE TABLE {keys.q(name)} ({defs})")
            if rows:
                # 1行ずつの INSERT は列の多い表（出走別着度数）で遅いので、表ごとにまとめて入れる
                values = pd.DataFrame([[r.get(c, "") for c in columns] for r in rows], columns=list(columns), dtype=object)
                con.register("_synth_rows", values)
                con.execute(f"INSERT INTO {keys.q(name)} SELECT * FROM _synth_rows")
                con.unregister("_synth_rows")
        if with_meta:
            _create_meta(con, list(rows_by_table))
    finally:
        con.close()
    return path


def _create_meta(con: duckdb.DuckDBPyConnection, names: list[str]) -> None:
    """実DB と同じ形の ``_tables``（表の一覧）と ``_meta``（同期の記録）。"""
    con.execute("CREATE TABLE _tables (record_id VARCHAR, table_name VARCHAR, title VARCHAR, keys VARCHAR, columns INTEGER, children VARCHAR)")
    con.execute("CREATE TABLE _meta (key VARCHAR, value VARCHAR)")
    parents = sorted({name.partition("__")[0] for name in names})
    for parent in parents:
        children = ",".join(name for name in names if name.startswith(parent + "__"))
        columns = len({**TABLES, **OPTIONAL_TABLES}.get(parent, ()))
        key_names = ",".join(_TABLE_KEYS.get(parent, (keys.HORSE_KEY,)))
        con.execute("INSERT INTO _tables VALUES (?, ?, ?, ?, ?, ?)",
                    [parent.upper(), parent, TITLES.get(parent, parent.upper()), key_names, columns, children])
    con.execute("INSERT INTO _meta VALUES ('sync:RACE', '20260912000000')")


def main() -> int:
    """``--out`` に合成DB を書く。"""
    parser = argparse.ArgumentParser(description="テスト用の小さな DuckDB（合成DB）を作る。値はすべて架空。")
    parser.add_argument("--out", type=Path, required=True, help="書き出す DB のパス（あれば作り直す）")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    card_db(args.out)
    print(f"合成DB を作りました: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
