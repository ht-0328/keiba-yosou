"""馬の条件を、切り口ごとの帯（同じ条件とみなすまとまり）に分ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 共通.stakes import FRONT_STYLES, INNER_FRAME_NO, NO_PREV_KEY, REST_INTERVAL_DAYS

#: 帯の名前。
FRONT, BACK, UNKNOWN_STYLE = "前", "後ろ", "不明"
INNER, MIDDLE, OUTER = "内", "中", "外"
RESTED, NOT_RESTED = "休み明け", "休み明けでない"
WEST, EAST, OTHER_AREA = "栗東", "美浦", "その他"
WITH_EXPERIENCE, WITHOUT_EXPERIENCE = "あり", "なし"
FILLY, COLT = "牝", "牡・セン"
#: 後ろから行く脚質判定。
_BACK_STYLES: tuple[str, ...] = ("差し", "追込")
#: 「中」とみなす枠番の上限（内は ``INNER_FRAME_NO`` まで、外はそれより大きい枠）。
_MIDDLE_FRAME_NO = 5
#: 単勝オッズの帯の境（未満で区切る）と名前。
_ODDS_EDGES = (3.0, 6.0, 10.0, 20.0, 50.0)
_ODDS_LABELS = ("3倍未満", "3〜6倍", "6〜10倍", "10〜20倍", "20〜50倍", "50倍以上")
#: 人気の帯の境（以下で区切る）と名前。
_POPULARITY_EDGES = (1, 3, 5, 9)
_POPULARITY_LABELS = ("1番人気", "2〜3番人気", "4〜5番人気", "6〜9番人気", "10番人気以下")
#: 前走の着順の帯。
_PREV_FINISH_EDGES = (1, 3, 9)
_PREV_FINISH_LABELS = ("1着", "2〜3着", "4〜9着", "10着以下")
#: 前走の人気の帯。
_PREV_POPULARITY_EDGES = (1, 3, 9)
_PREV_POPULARITY_LABELS = ("1番人気", "2〜3番人気", "4〜9番人気", "10番人気以下")
#: 年齢の帯。
_AGE_EDGES = (2, 3, 4, 5)
_AGE_LABELS = ("2歳", "3歳", "4歳", "5歳", "6歳以上")


class ConditionBands:
    """切り口ごとに、馬の条件の値を帯の名前にする（設計書 09 の K の「帯の分け方」）。

    どのメソッドも、値の Series を受け取り、同じ index の帯の名前（文字列）の Series を返す。
    帯が決められない値（枠番が未定の木曜の枠など）は欠損値（NaN）になり、その馬のその切り口の K は欠損値になる。
    過去の開催の出走馬と、予測する馬の両方を同じ決まりで分けるので、ここ以外に帯の境を書かない。
    """

    def prev_race(self, keys: pd.Series) -> pd.Series:
        """前走のレースの鍵（``prev_key``）。無ければ「前走なし」。"""
        return keys.astype("object").where(keys.notna(), NO_PREV_KEY)

    def prev_finish(self, finish: pd.Series) -> pd.Series:
        return self._stepped(finish, _PREV_FINISH_EDGES, _PREV_FINISH_LABELS, missing=NO_PREV_KEY)

    def prev_popularity(self, popularity: pd.Series) -> pd.Series:
        return self._stepped(popularity, _PREV_POPULARITY_EDGES, _PREV_POPULARITY_LABELS, missing=NO_PREV_KEY)

    def frame(self, frame_no: pd.Series) -> pd.Series:
        """内（1〜3枠）・中（4〜5枠）・外（6枠から）。枠が未定なら欠損値。"""
        return self._stepped(frame_no, (INNER_FRAME_NO, _MIDDLE_FRAME_NO), (INNER, MIDDLE, OUTER))

    def odds(self, win_odds: pd.Series) -> pd.Series:
        """単勝オッズの帯。オッズが無ければ欠損値。"""
        values = self._numbers(win_odds)
        index = np.searchsorted(np.array(_ODDS_EDGES), values.to_numpy(), side="right")
        return self._labelled(values, index, _ODDS_LABELS)

    def popularity(self, popularity: pd.Series) -> pd.Series:
        """人気の帯。人気が無ければ欠損値。"""
        return self._stepped(popularity, _POPULARITY_EDGES, _POPULARITY_LABELS)

    def popularity_of_odds(self, win_odds: pd.Series, race_id: pd.Series) -> pd.Series:
        """予測する馬の人気の帯。単勝オッズの低い順の順位（同じレースの中。同じオッズは同じ順位）から決める。"""
        odds = self._numbers(win_odds)
        return self.popularity(odds.groupby(race_id).rank(method="min"))

    def style(self, style: pd.Series) -> pd.Series:
        """前（逃げ・先行）・後ろ（差し・追込）・不明。過去の開催は確定した脚質判定、予測する馬は推定脚質で見る。"""
        values = style.astype("object")
        labels = np.select([values.isin(FRONT_STYLES), values.isin(_BACK_STYLES)], [FRONT, BACK], default=UNKNOWN_STYLE)
        return pd.Series(labels, index=style.index, dtype="object")

    def interval(self, interval_days: pd.Series) -> pd.Series:
        """休み明け（中9週以上）か、そうでないか。前走が無ければ「前走なし」。"""
        days = self._numbers(interval_days)
        labels = np.where(days >= REST_INTERVAL_DAYS, RESTED, NOT_RESTED)
        return pd.Series(np.where(days.isna(), NO_PREV_KEY, labels), index=interval_days.index, dtype="object")

    def affiliation(self, affiliation: pd.Series) -> pd.Series:
        values = affiliation.astype("object")
        labels = np.select([values == WEST, values == EAST], [WEST, EAST], default=OTHER_AREA)
        return pd.Series(labels, index=affiliation.index, dtype="object")

    def experience(self, same_race_places_before: pd.Series) -> pd.Series:
        """同じレースで3着以内の経験があるか。"""
        places = self._numbers(same_race_places_before).fillna(0.0)
        return pd.Series(np.where(places >= 1, WITH_EXPERIENCE, WITHOUT_EXPERIENCE), index=places.index, dtype="object")

    def age(self, age: pd.Series) -> pd.Series:
        return self._stepped(age, _AGE_EDGES, _AGE_LABELS)

    def sex(self, sex: pd.Series) -> pd.Series:
        values = sex.astype("object")
        return pd.Series(np.where(values == FILLY, FILLY, COLT), index=sex.index, dtype="object")

    def _stepped(self, values: pd.Series, edges: tuple[int, ...], labels: tuple[str, ...],
                 missing: str | None = None) -> pd.Series:
        """``edges`` 以下で区切る帯。欠損値は ``missing``（省略すると欠損値のまま）。"""
        numbers = self._numbers(values)
        index = np.searchsorted(np.array(edges, dtype="float64"), numbers.to_numpy(), side="left")
        return self._labelled(numbers, index, labels, missing)

    def _numbers(self, values: pd.Series) -> pd.Series:
        """数値の Series（float64）。欠損値つきの整数（pandas の NA）も NaN にそろえる。"""
        return pd.to_numeric(values, errors="coerce").astype("float64")

    def _labelled(self, numbers: pd.Series, index: np.ndarray, labels: tuple[str, ...],
                  missing: str | None = None) -> pd.Series:
        names = np.array(labels, dtype="object")[np.clip(index, 0, len(labels) - 1)]
        filled = np.where(numbers.isna(), missing if missing is not None else np.nan, names)
        return pd.Series(filled, index=numbers.index, dtype="object")
