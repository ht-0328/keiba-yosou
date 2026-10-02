"""決着の切り口の目録。決着の表（``race_table``）の列から、レースごとの値（帯の名前）を作る。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from 決着の型.race_table import OUT_OF_MONEY

#: 「上位人気」の線（この人気以内）。ALL-08 の 5番人気以内。
TOP_POPULARITY = 5
#: 1〜6番人気の線（SRF-P19）。
TOP6 = 6
#: 値の無いレース（3着以内が3頭そろわない、人気が無い）の名前。
UNKNOWN = "不明"


@dataclass(frozen=True)
class OutcomeDimension:
    """1つの切り口。``label`` が決着の表から値の列を作り、``labels`` が値の並び順。"""

    name: str
    title: str
    label: Callable[[pd.DataFrame], pd.Series]
    labels: tuple[str, ...]
    note: str = ""

    def values(self, races: pd.DataFrame) -> pd.Series:
        """レースごとの値。値の無いレースは「不明」。"""
        return self.label(races).fillna(UNKNOWN).astype(str)

    def order(self, value: str) -> int:
        """値の並び順（目録に無い値は最後）。"""
        return self.labels.index(value) if value in self.labels else len(self.labels)


def _bins(series: pd.Series, edges: tuple[float, ...], labels: tuple[str, ...]) -> pd.Series:
    """数を帯に分ける。``edges`` の各値を「その値未満」の境目にする（``labels`` は1つ多い）。NULL は NULL のまま。"""
    bins = [float("-inf"), *edges, float("inf")]
    return pd.cut(series.astype(float), bins=bins, labels=list(labels), right=False).astype(object)


def _top3_pops(races: pd.DataFrame) -> pd.DataFrame:
    return races[["pop_1st", "pop_2nd", "pop_3rd"]]


def _complete(races: pd.DataFrame) -> pd.Series:
    """3着以内の3頭の人気がそろっているか。"""
    return _top3_pops(races).notna().all(axis=1)


def _yes_no(condition: pd.Series, complete: pd.Series, yes: str, no: str) -> pd.Series:
    return pd.Series(pd.NA, index=condition.index, dtype=object).mask(complete & condition, yes).mask(complete & ~condition, no)


_MIX_LABELS = ("上位人気3頭", "上位人気2頭+穴馬1頭", "上位人気1頭+穴馬2頭", "穴馬3頭")


def _top5_mix(races: pd.DataFrame) -> pd.Series:
    top_count = _top3_pops(races).le(TOP_POPULARITY).sum(axis=1)
    return pd.Series([_MIX_LABELS[3 - int(n)] for n in top_count], index=races.index, dtype=object).where(_complete(races))


def _pop_sum(races: pd.DataFrame) -> pd.Series:
    return _bins(_top3_pops(races).sum(axis=1, min_count=3), (9, 13, 17), ("6〜8", "9〜12", "13〜16", "17以上"))


def _top3_any(races: pd.DataFrame) -> pd.Series:
    placed = races[["fav1_finish", "fav2_finish", "fav3_finish"]].lt(OUT_OF_MONEY).any(axis=1)
    return _yes_no(placed, _complete(races), "どれかが3着以内", "3頭とも4着以下")


def _fav2_out(races: pd.DataFrame) -> pd.Series:
    both_out = races[["fav1_finish", "fav2_finish"]].ge(OUT_OF_MONEY).all(axis=1)
    return _yes_no(both_out, _complete(races), "そろって4着以下", "どちらかが3着以内")


def _fav_pair(races: pd.DataFrame) -> pd.Series:
    both_in = races[["fav1_finish", "fav2_finish"]].lt(OUT_OF_MONEY).all(axis=1)
    return _yes_no(both_in, _complete(races), "2頭とも3着以内", "それ以外")


def _top6_all(races: pd.DataFrame) -> pd.Series:
    within = _top3_pops(races).le(TOP6).all(axis=1)
    return _yes_no(within, _complete(races), "3頭とも1〜6番人気", "7番人気以下を含む")


def _odds_spread(races: pd.DataFrame) -> pd.Series:
    narrow = races["n_under10"].le(3) & races["n_under30"].le(5)
    complete = races["n_under10"].notna()
    return _yes_no(narrow, complete, "10倍以下3頭以下かつ30倍以下5頭以下", "それ以外")


def _fav1_finish(races: pd.DataFrame) -> pd.Series:
    return _bins(races["fav1_finish"], (2, 3, 4), ("1着", "2着", "3着", "4着以下"))


_POP_BAND_LABELS = ("1番人気", "2〜3番人気", "4〜5番人気", "6〜9番人気", "10番人気以下")


def _winner_pop(races: pd.DataFrame) -> pd.Series:
    return _bins(races["pop_1st"], (2, 4, 6, 10), _POP_BAND_LABELS)


def _second_pop(races: pd.DataFrame) -> pd.Series:
    return _bins(races["pop_2nd"], (2, 4, 6, 10), _POP_BAND_LABELS)


def _winner_odds(races: pd.DataFrame) -> pd.Series:
    return _bins(races["odds_1st"], (10, 30.05), ("10倍未満", "10〜30倍", "30倍超"))


def _second_odds(races: pd.DataFrame) -> pd.Series:
    return _bins(races["odds_2nd"], (20,), ("20倍未満", "20倍以上"))


def _year(races: pd.DataFrame) -> pd.Series:
    return races["year"].astype(int).astype(str)


_POPS_NOTE = "人気は確定の単勝人気。同着で3着以内が4頭以上いるときは、着順 → 人気の順の先頭3頭で見る。"

DIMENSIONS: dict[str, OutcomeDimension] = {
    dimension.name: dimension for dimension in (
        OutcomeDimension("year", "開催年", _year, ()),
        OutcomeDimension("top5-mix", "3着以内の上位人気（5番人気以内）と穴馬（6番人気以下）の組", _top5_mix, _MIX_LABELS, _POPS_NOTE),
        OutcomeDimension("top3-any", "1〜3番人気のどれかが3着以内か", _top3_any, ("どれかが3着以内", "3頭とも4着以下"), _POPS_NOTE),
        OutcomeDimension("fav2-out", "1・2番人気がそろって4着以下か", _fav2_out, ("そろって4着以下", "どちらかが3着以内"), _POPS_NOTE),
        OutcomeDimension("fav-pair", "1・2番人気が2頭とも3着以内か", _fav_pair, ("2頭とも3着以内", "それ以外"), _POPS_NOTE),
        OutcomeDimension("pop-sum", "1〜3着の人気の和", _pop_sum, ("6〜8", "9〜12", "13〜16", "17以上"), _POPS_NOTE),
        OutcomeDimension("top6-all", "3着以内の3頭が全部1〜6番人気か", _top6_all, ("3頭とも1〜6番人気", "7番人気以下を含む"), _POPS_NOTE),
        OutcomeDimension("odds-spread", "単勝オッズの散らばり", _odds_spread, ("10倍以下3頭以下かつ30倍以下5頭以下", "それ以外"),
                         "出走した馬のうち、確定の単勝オッズが 10倍以下の頭数と 30倍以下の頭数で分ける（WID-05 の条件）。"),
        OutcomeDimension("fav1-finish", "1番人気の着順", _fav1_finish, ("1着", "2着", "3着", "4着以下")),
        OutcomeDimension("winner-pop", "1着馬の人気", _winner_pop, _POP_BAND_LABELS),
        OutcomeDimension("second-pop", "2着馬の人気", _second_pop, _POP_BAND_LABELS),
        OutcomeDimension("winner-odds", "1着馬の単勝オッズ", _winner_odds, ("10倍未満", "10〜30倍", "30倍超"), "30倍超 = 30.1倍以上。"),
        OutcomeDimension("second-odds", "2着馬の単勝オッズ", _second_odds, ("20倍未満", "20倍以上")),
    )
}


def dimension(name: str) -> OutcomeDimension:
    """名前から切り口を引く。無い名前は、選べる名前を添えて落とす。"""
    try:
        return DIMENSIONS[name]
    except KeyError:
        raise LookupError(f"知らない切り口です: {name}\n選べるもの: {', '.join(DIMENSIONS)}") from None
