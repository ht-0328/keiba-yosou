"""地方の合成DB（テスト用の小さな DuckDB）の行を作る。列名は地方競馬DATA の表のまま、値は文字列。

中央の合成DB（``synth.py``）の表の作りと行の束（``Sample``）をそのまま使い、地方で違うところ（競馬場コード 30〜61、
競走条件名称でクラスを表す、出走別着度数地方 ``nd``、競走馬マスタ地方 ``nu``、所属が地方）だけをここで作る。
ツールとしても使え、実DB が無い PC で地方の予想や道具の動きを見られる:

    uv run python tools/合成DB/local_synth.py --out reports/local_synth.duckdb
    uv run python -m yosou.local_form_aptitude_top3 predict 2025011144010101 --timing 出馬表 --db reports/local_synth.duckdb --models ...

値はすべて架空。
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 合成DB import synth  # noqa: E402

#: 地方の既定の競馬場（大井）とトラック（ダート・右）。
LOCAL_VENUE_CODE, LOCAL_TRACK_CODE = "44", "24"
#: 地方の東西所属コード（地方所属）。
LOCAL_AREA_CODE = "3"
#: 地方のレースの競走条件コード（すべて 000。クラスは競走条件名称にしか無い）。
LOCAL_CONDITION_CODE = "000"


def local_race(day: str, no: str, *, venue: str = LOCAL_VENUE_CODE, track: str = LOCAL_TRACK_CODE, distance: str = "1600",
               dirt: str = "1", field_size: str = "10", entries: str = "10", condition_name: str = "Ｃ２　一",
               name: str = "", grade: str = " ", stakes_no: str = "", stage: str = "7", **over: str) -> dict[str, str]:
    """地方のレース1行（既定: 大井 ダート・右 1600m 良、Ｃ２の条件戦、10頭）。クラスは ``condition_name``（競走条件名称）で表す。"""
    return synth.race(
        day, no, venue=venue, track=track, distance=distance, turf="0", dirt=dirt, field_size=field_size, entries=entries,
        name=name, condition=LOCAL_CONDITION_CODE, grade=grade, stakes_no=stakes_no, stage=stage,
        **{"競走条件名称": condition_name, "競走種別コード": "49", **over},
    )


def local_runner(race_row: dict[str, str], num: int, pop: int, fin: int, **over: str) -> dict[str, str]:
    """地方の出走1頭（所属は地方）。ほかの引数は ``synth.runner`` と同じ。"""
    return synth.runner(race_row, num, pop, fin, **{"東西所属コード": LOCAL_AREA_CODE, **over})


def nd(race_row: dict[str, str], hid: str, counts: Mapping[str, Sequence[int]] | None = None, *,
       name: str = "") -> dict[str, str]:
    """出走別着度数地方1件（そのレースの出馬表の時点の、馬の通算の着回数）。

    ``counts`` は 項目（``synth.ND_COUNT_ITEMS`` のどれか）→ 1着〜5着と着外の6つの回数。書かない項目は全部 0。
    """
    unknown = set(counts or {}) - set(synth.ND_COUNT_ITEMS)
    if unknown:
        raise ValueError(f"出走別着度数地方に無い項目です: {sorted(unknown)}")
    key = {name_: race_row[name_] for name_ in synth.KEY_COLUMNS}
    values = {"レコード種別ID": "ND", "データ区分": "1", "データ作成年月日": race_row["開催年"] + race_row["開催月日"],
              **key, "血統登録番号": hid, "馬名": name}
    for item in synth.ND_COUNT_ITEMS:
        slots = (counts or {}).get(item, (0,) * synth.CK_SLOTS)
        values.update({f"{item}_{slot}": f"{count:03d}" for slot, count in enumerate(slots, start=1)})
    return synth._row(synth.ND_COLUMNS, values)


def local_horse(hid: str, name: str, *, sex: str = "1", born: str = "20200401",
                trainer: tuple[str, str] = ("00001", "調教師A"), area: str = "大井") -> dict[str, str]:
    """競走馬マスタ地方1頭。``area`` は招待地域名（所属の競馬場）。"""
    return synth._row(synth.NU_COLUMNS, {
        "レコード種別ID": "NU", "データ区分": "1", "データ作成年月日": born, "血統登録番号": hid, "生年月日": born,
        "馬名": name, "性別コード": sex, "品種コード": "1", "毛色コード": "01", "東西所属コード": LOCAL_AREA_CODE,
        "調教師コード": trainer[0], "調教師名略称": trainer[1], "招待地域名": area, "生産者コード": "00000100", "馬主コード": "000001",
    })


def local_pedigree(hid: str, *, sire: str = "父A", dam: str = "母A", grandsire: str = "父父A",
                   damsire: str = "母父A") -> list[dict[str, str]]:
    """競走馬マスタ地方の3代血統情報（父・母・父父・母父の4行。中央の ``um__3代血統情報`` と同じ形）。"""
    return synth.pedigree(hid, sire=sire, dam=dam, grandsire=grandsire, damsire=damsire)


def _finishes(fav_fin: int, field_size: int) -> dict[int, int]:
    """馬番 → 確定着順。1番人気（馬番1）を ``fav_fin`` 着にし、ほかの馬番は小さい順に残りの着順を埋める。"""
    others = [place for place in range(1, field_size + 1) if place != fav_fin]
    return {1: fav_fin, **{num: place for num, place in zip(range(2, field_size + 1), others)}}


def local_simple_race(day: str = "20240406", no: str = "01", *, fav_fin: int = 4, condition_name: str = "Ｃ２　一",
                      distance: str = "1600") -> synth.Sample:
    """地方の確定成績1レース（5頭。1番人気の着順を ``fav_fin`` にする）。ツールの試用のための小さな束。"""
    sample = synth.Sample()
    race_row = local_race(day, no, distance=distance, field_size="05", entries="05", condition_name=condition_name)
    sample.ra.append(race_row)
    finishes = _finishes(fav_fin, 5)
    for num in range(1, 6):
        hid = f"2020{num:06d}"
        sample.se.append(local_runner(race_row, num, num, finishes[num], hid=hid, name=f"ウマ{num:02d}",
                                      odds=f"{15 + 20 * num:04d}"))
        sample.nd.append(nd(race_row, hid, {"総合着回数": (num, 1, 1, 1, 1, 3), "地方合計着回数": (num, 1, 1, 1, 1, 2),
                                            "大井ダ・着回数": (1, 1, 0, 0, 0, 1)}, name=f"ウマ{num:02d}"))
        sample.nu.append(local_horse(hid, f"ウマ{num:02d}"))
        sample.nu_pedigree.extend(local_pedigree(hid, sire=f"父{num % 2}"))
    winner = next(num for num, fin in finishes.items() if fin == 1)
    sample.win.append(synth.payout(race_row, winner, 150 * winner))
    for num, fin in finishes.items():
        if fin <= 3:
            sample.place.append(synth.payout(race_row, num, 110 + 30 * num, seq=fin))
    return sample


def local_card_race(day: str = "20250111", no: str = "01", **race_over: str) -> synth.Sample:
    """地方の確定前の1レース（出馬表。データ区分 2。8頭）。"""
    sample = synth.Sample()
    race_row = local_race(day, no, stage="2", field_size="00", entries="08", dirt="0",
                          **{"天候コード": "0", "入線頭数": "00", "後3ハロン": "000", "後4ハロン": "000", **race_over})
    sample.ra.append(race_row)
    for num in range(1, 9):
        hid = f"2020{num:06d}"
        sample.se.append(local_runner(race_row, num, 0, 0, hid=hid, name=f"ウマ{num:02d}", odds="0000", weight="",
                                      change=("", ""), last3f="000", style="0",
                                      **{"後4ハロンタイム": "000", "タイム差": "", "マイニング区分": "0"}))
        sample.nd.append(nd(race_row, hid, {"総合着回数": (1, 1, 1, 1, 1, 3)}, name=f"ウマ{num:02d}"))
        sample.nu.append(local_horse(hid, f"ウマ{num:02d}"))
        sample.nu_pedigree.extend(local_pedigree(hid))
    return sample


def local_sample() -> synth.Sample:
    """地方の合成DB の既定の束（確定成績 3レースと出馬表 1レース）。"""
    sample = synth.Sample()
    sample.extend(local_simple_race("20240406", "01", fav_fin=1))
    sample.extend(local_simple_race("20240413", "01", fav_fin=4, condition_name="Ｂ１－２", distance="1800"))
    sample.extend(local_simple_race("20240420", "01", fav_fin=2, condition_name="３歳上ＯＰ", distance="1200"))
    sample.extend(local_card_race())
    return sample


def local_db(path: Path) -> Path:
    """地方の合成DB を作る（``local_sample``）。"""
    return synth.build_db(path, local_sample())


def main() -> int:
    """``--out`` に地方の合成DB を書く。"""
    parser = argparse.ArgumentParser(description="テスト用の小さな地方の DuckDB（合成DB）を作る。値はすべて架空。")
    parser.add_argument("--out", type=Path, required=True, help="書き出す DB のパス（あれば作り直す）")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    local_db(args.out)
    print(f"地方の合成DB を作りました: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
