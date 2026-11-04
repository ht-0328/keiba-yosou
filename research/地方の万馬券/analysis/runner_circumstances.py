"""馬の事情: 1頭の出走に、レースの前に分かる「事情」（遠征・転入初戦・連闘・昇級 など）を 真偽の列で付ける。

人気馬が崩れた理由、穴馬が来た理由の候補を、事実表の列から機械的に作る。結果側の情報（着順・タイム・通過順）は使わない。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .jockey_venue_rank import JOCKEY_VENUE_RANK
from .venue_area import UNKNOWN_AREA, VenueArea

#: 事情の列の名前 → 意味。表の行の順でもある。
CIRCUMSTANCES: dict[str, str] = {
    "中央所属": "所属が中央（美浦・栗東）の馬（交流競走）",
    "遠征": "調教師の所属の地区が今回の競馬場の地区と違う（中央所属は除く）",
    "転入初戦": "この DB に地方の出走が無い 3歳以上の馬（中央や他地区から移ってきた直後、または長く走っていない）",
    "地方で2走以下": "この DB にある地方の出走が 2走以下の 3歳以上の馬",
    "連闘": "前走から 8日以内",
    "中1〜2週": "前走から 9〜21日",
    "休み明け": "前走から 90日以上",
    "昇級": "前走よりクラスが上",
    "降級": "前走よりクラスが下",
    "乗り替わり": "前走と騎手が違う",
    "騎手が場の上位3": "騎手が、その競馬場の前の年の勝利数で 3位以内",
    "騎手が場の10位以内": "同じく 10位以内",
    "騎手が場の圏外": "騎手が、その競馬場で前の年に勝っていないか 11位以下",
    "前走3着以内": "前走が 1〜3着",
    "前走6着以下": "前走が 6着以下",
    "前走大敗": "前走の着差が 1.0秒以上",
    "前走1〜3番人気": "前走が 1〜3番人気",
    "前走6番人気以下": "前走が 6番人気以下",
    "前走は前にいた": "前走の4コーナーの順位が頭数の 1/3 以内",
    "前走は後ろにいた": "前走の4コーナーの順位が頭数の 2/3 より後ろ",
    "内枠": "1〜2枠",
    "外枠": "7〜8枠",
    "同じ場から": "前走と同じ競馬場",
    "別の場から": "前走と違う競馬場（遠征・転入を含む）",
    "距離延長": "前走より距離が長い",
    "距離短縮": "前走より距離が短い",
    "斤量が重い": "斤量がそのレースの平均より 1kg 以上重い",
    "斤量が軽い": "斤量がそのレースの平均より 1kg 以上軽い",
    "馬体重の増減が大きい": "馬体重の増減が ±10kg 以上",
    "減量騎手": "騎手に減量がある",
    "ブリンカー": "ブリンカーあり",
    "牝馬（牡牝混合）": "牡馬と一緒に走る牝馬",
    "高齢": "8歳以上",
    "持ち時計1位": "同じ競馬場・コース・距離・馬場状態の持ち時計がそのレースで1位",
    "このコース初めて": "同じ競馬場・コース・距離の出走が無い",
    "単勝支持が薄い人気": "単勝オッズから見た支持率が、人気の順位のわりに低い（同じ人気の中央値より 2割以上低い）",
}
_MATURE_AGE = 3
_SHORT_INTERVAL, _MIDDLE_INTERVAL_HIGH, _LAYOFF = 8, 21, 90
_TOP_JOCKEYS, _TOP10_JOCKEYS = 3, 10
_BIG_DEFEAT_SECONDS = 1.0
_FRONT_SHARE, _BACK_SHARE = 1 / 3, 2 / 3
_INNER_FRAME, _OUTER_FRAME = 2, 7
_WEIGHT_GAP_KG = 1.0
_BODY_WEIGHT_CHANGE_KG = 10
_OLD_AGE = 8
_THIN_SUPPORT_RATIO = 0.8
#: 単勝支持の比（支持率 ÷ 同じ人気の中央値）の列。
SUPPORT_RATIO = "support_ratio"


@dataclass(frozen=True)
class RunnerCircumstances:
    """事実表の行（``runners``。騎手の場内順位と調教師の地区が付いたもの）に、``CIRCUMSTANCES`` の列を足す。"""

    areas: VenueArea = VenueArea()

    def attach(self, runners: pd.DataFrame) -> pd.DataFrame:
        """``runners`` に事情の列（bool）と ``support_ratio``（単勝支持の比）を足して返す。欠損値は「事情なし」（False）にする。"""
        table = runners.copy()
        table[SUPPORT_RATIO] = self._support_ratio(table)
        for name, flag in self._flags(table).items():
            table[name] = flag.fillna(False).astype(bool)
        return table

    def _flags(self, t: pd.DataFrame) -> dict[str, pd.Series]:
        venue_area = t["venue"].map(self.areas.area_of)
        trainer_area = t["trainer_area"].map(self.areas.area_of)
        jra = t["affiliation"].ne("招待")
        mature = t["age"] >= _MATURE_AGE
        prev_position = t["prev_corner4"] / t["prev_field_size"]
        carried_gap = t["carried"] - t.groupby("race_id")["carried"].transform("mean")
        rank = t[JOCKEY_VENUE_RANK]
        return {
            "中央所属": jra,
            "遠征": ~jra & venue_area.ne(UNKNOWN_AREA) & trainer_area.ne(UNKNOWN_AREA) & venue_area.ne(trainer_area),
            "転入初戦": mature & t["runs_before"].eq(0),
            "地方で2走以下": mature & t["runs_before"].le(2),
            "連闘": t["interval_days"] <= _SHORT_INTERVAL,
            "中1〜2週": t["interval_days"].between(_SHORT_INTERVAL + 1, _MIDDLE_INTERVAL_HIGH),
            "休み明け": t["interval_days"] >= _LAYOFF,
            "昇級": t["class_change"].eq("昇級"),
            "降級": t["class_change"].eq("降級"),
            "乗り替わり": t["jockey_change"].eq("乗り替わり"),
            "騎手が場の上位3": rank <= _TOP_JOCKEYS,
            "騎手が場の10位以内": rank <= _TOP10_JOCKEYS,
            "騎手が場の圏外": rank.isna() | (rank > _TOP10_JOCKEYS),
            "前走3着以内": t["prev_finish"] <= 3,
            "前走6着以下": t["prev_finish"] >= 6,
            "前走大敗": t["prev_time_diff"] >= _BIG_DEFEAT_SECONDS,
            "前走1〜3番人気": t["prev_popularity"] <= 3,
            "前走6番人気以下": t["prev_popularity"] >= 6,
            "前走は前にいた": prev_position <= _FRONT_SHARE,
            "前走は後ろにいた": prev_position > _BACK_SHARE,
            "内枠": t["frame_no"] <= _INNER_FRAME,
            "外枠": t["frame_no"] >= _OUTER_FRAME,
            "同じ場から": t["venue_change"].eq("同じ"),
            "別の場から": t["venue_change"].eq("別"),
            "距離延長": t["distance_change"].eq("延長"),
            "距離短縮": t["distance_change"].eq("短縮"),
            "斤量が重い": carried_gap >= _WEIGHT_GAP_KG,
            "斤量が軽い": carried_gap <= -_WEIGHT_GAP_KG,
            "馬体重の増減が大きい": t["weight_change"].abs() >= _BODY_WEIGHT_CHANGE_KG,
            "減量騎手": t["apprentice"].eq("減量あり"),
            "ブリンカー": t["blinker"].eq("あり"),
            "牝馬（牡牝混合）": t["sex"].eq("牝") & t["mixed_sex"].astype("boolean").fillna(False),
            "高齢": t["age"] >= _OLD_AGE,
            "持ち時計1位": t["best_time_unit_rank"].eq(1),
            "このコース初めて": t["course_runs_before"].eq(0),
            "単勝支持が薄い人気": t[SUPPORT_RATIO] < _THIN_SUPPORT_RATIO,
        }

    def _support_ratio(self, t: pd.DataFrame) -> pd.Series:
        """単勝オッズから見た支持率（1/オッズ をレース内で合計 1 に）÷ 同じ人気の馬の支持率の中央値。1 より小さいほど、人気の順位のわりに支持が薄い。"""
        inverse = 1.0 / t["win_odds"].replace(0, np.nan)
        support = inverse / inverse.groupby(t["race_id"]).transform("sum")
        median = support.groupby(t["popularity"]).transform("median")
        return support / median
