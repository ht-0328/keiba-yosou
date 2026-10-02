"""特徴量の名前を、人が読む分類と名前と値の書き方にする。"""

from __future__ import annotations

import math
import re
from collections.abc import Callable

#: レースの全馬に同じ値が入る特徴量の分類。馬ごとの良い点・悪い点には出さない。
RACE_CONDITION = "レースの条件"
#: 分類の並び（画面に出す順）。
CATEGORIES: tuple[str, ...] = (
    "能力", "近走の成績", "相手関係", "位置取り・末脚", "展開", "コース適性", "騎手", "調教師", "血統", "馬主・生産者",
    "調教", "状態", "枠・斤量", "市場の評価", RACE_CONDITION,
)
#: 分類ごとの中身の説明（画面の凡例）。
CATEGORY_NOTES: dict[str, str] = {
    "能力": "スピード指数（走破タイムを馬場とペースで補正した速さ）と持ち時計",
    "近走の成績": "前走・近5走の着順と着差、通算の成績",
    "相手関係": "対戦レーティング（誰に勝って誰に負けたか）、過去走の相手の強さ、クラスの上げ下げ",
    "位置取り・末脚": "序盤と4コーナーの位置、上がりの速さ、逃げた割合",
    "展開": "展開の予想（先頭・位置・上がり・ペースの確率）と、過去走のペース・展開の不利",
    "コース適性": "同じコース・距離・馬場での成績、距離や芝ダの替わり",
    "騎手": "騎手の成績（通算・近1年・競馬場別・調教師との組）、乗り替わり、減量",
    "調教師": "調教師の成績（通算・近1年・近60日・距離別）、所属",
    "血統": "父・母父・母の産駒の成績（芝ダ別・距離別）",
    "馬主・生産者": "馬主・生産者の成績、セリの価格",
    "調教": "坂路とウッドの調教の本数とタイム",
    "状態": "前走からの間隔、馬体重とその増減、馬齢、性別、ブリンカー",
    "枠・斤量": "枠番・馬番と枠の傾向、斤量",
    "市場の評価": "単勝オッズと人気、券種ごとのオッズから見た支持（前日・当日だけ）",
    RACE_CONDITION: "距離・頭数・競馬場など、レースの全馬に同じ値が入るもの（馬ごとの良い点・悪い点には出さない）",
}
#: 英字の列名（事実表の列そのまま）の日本語の名前。
_ENGLISH_NAMES: dict[str, str] = {
    "distance_m": "距離", "field_size": "出走頭数", "class_order": "クラス", "age": "馬齢", "sex_order": "性別",
    "carried": "斤量", "interval_days": "前走からの日数", "surface_order": "芝ダ", "month": "開催月",
    "runs_before": "通算の出走数", "wins_before": "通算の勝利数", "lead_runs_before": "逃げた回数",
    "course_runs_before": "同じコースの出走数", "course_wins_before": "同じコースの勝利数",
    "course_places_before": "同じコースの3着以内の数", "venue_wins_before": "同じ競馬場の勝利数",
    "dist_wins_before": "同じ距離の勝利数", "same_race_runs_before": "同じレースの出走数",
    "same_race_wins_before": "同じレースの勝利数", "best_time_unit_rank": "持ち時計のレース内順位（コース単位）",
    "best_time_dist_rank": "持ち時計のレース内順位（距離単位）", "frame_no": "枠番", "condition_order": "馬場状態",
    "cond_places_before": "同じ馬場状態の3着以内の数", "body_weight": "馬体重", "weight_change": "馬体重の増減",
}
#: 名前の頭の言葉の言い換え（「指数_前走」→「スピード指数・前走」）。
_HEAD_WORDS: dict[str, str] = {"指数": "スピード指数", "坂路": "坂路調教", "ウッド": "ウッド調教", "carried": "斤量"}
#: 名前の途中の言葉の言い換え。
_MIDDLE_WORDS: dict[str, str] = {"1年": "近1年", "60日": "近60日", "3着内率": "3着以内率"}
#: 名前の終わりの言葉（レース内の比べ）の言い換え。
_TAIL_WORDS: dict[str, str] = {"順位": "（レース内順位）", "最良との差": "（レース内の最良との差）", "偏差": "（レース内の偏差）"}

#: 分類の決め方（上から順に当てはめ、最初に当たった分類にする）。
_RULES: tuple[tuple[str, Callable[[str], bool]], ...] = (
    ("市場の評価", lambda n: n in ("単勝オッズ", "人気順位") or n.startswith("オッズから見た") or "と単勝の比" in n),
    ("展開", lambda n: n.startswith(("展開の予想_", "ペース_", "展開の不利_")) or n in (
        "先頭率の合計", "ほかの馬の先頭率の合計", "逃げそうな馬の数", "lead_runs_before")),
    # 「クラス」「class_order」はそのレースのクラス（全馬に同じ値）なので、ここには入れない
    ("相手関係", lambda n: n.startswith(("対戦レーティング", "相手の強さ", "クラス_", "クラスの"))),
    ("騎手", lambda n: n.startswith(("騎手", "減量騎手")) or n == "乗り替わり"),
    ("調教師", lambda n: n.startswith(("調教師", "所属"))),
    ("血統", lambda n: n.startswith(("父", "母"))),
    ("馬主・生産者", lambda n: n.startswith(("馬主", "生産者", "セリ"))),
    ("調教", lambda n: n.startswith(("坂路", "ウッド", "直近の調教", "14日以内の調教"))),
    ("能力", lambda n: n.startswith(("指数_", "持ち時計")) or n.startswith("best_time_")),
    ("位置取り・末脚", lambda n: n.startswith(("序盤の位置", "4角の位置", "末脚", "先頭_", "先頭率_", "前走の上がり",
                                              "前走の4コーナー", "推定脚質"))
     or n in ("近5走の平均上がり順位", "近5走の平均4コーナー位置")),
    ("コース適性", lambda n: n.startswith(("course_", "same_race_", "同じ", "距離の変", "芝ダ替わり"))
     or n in ("venue_wins_before", "dist_wins_before", "cond_places_before", "前走と芝ダが同じ", "前走と同じ競馬場か")),
    ("近走の成績", lambda n: n.startswith(("着順_", "相対着順_", "着差_", "前走の", "近5走の", "通算の"))
     or n in ("runs_before", "wins_before", "出走数")),
    ("状態", lambda n: n.startswith(("体重_", "馬体重", "休み明け", "ブリンカー"))
     or n in ("interval_days", "前走からの日数", "body_weight", "weight_change", "age", "馬齢", "sex_order", "性別")),
    ("枠・斤量", lambda n: n.startswith(("carried", "斤量", "枠", "馬番")) or n in ("frame_no",)),
)


class FeatureLabels:
    """特徴量の名前から、分類（``CATEGORIES`` のどれか）・人が読む名前・値の書き方を決める。

    分類は、予想の理由を「能力」「近走の成績」「騎手」のようなまとまりで見せるためのもの。どの分類にも当たらない名前は
    「レースの条件」（距離・頭数・競馬場など、レースの全馬に同じ値が入るもの）にする。
    """

    def category(self, name: str) -> str:
        for category, matches in _RULES:
            if matches(name):
                return category
        return RACE_CONDITION

    def display_name(self, name: str) -> str:
        """人が読む名前（「指数_前走_順位」→「スピード指数・前走（レース内順位）」）。"""
        if name in _ENGLISH_NAMES:
            return _ENGLISH_NAMES[name]
        parts = name.split("_")
        tail = _TAIL_WORDS.get(parts[-1], "") if len(parts) > 1 else ""
        if tail:
            parts = parts[:-1]
        words = [_HEAD_WORDS.get(parts[0], parts[0])] + [_MIDDLE_WORDS.get(part, part) for part in parts[1:]]
        return "・".join(words) + tail

    def display_value(self, name: str, value: object) -> str:
        """値を人が読む形にする（率は %、順位は「n位」、欠損は「なし」）。"""
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return "なし"
        if not isinstance(value, (int, float)):
            return str(value)
        number = float(value)
        if name.endswith("順位") or "順位（" in name or name.endswith("_rank"):
            return f"{number:.0f}位"
        if name.endswith("偏差"):
            return f"{number:+.2f}"
        if _is_rate(name) and abs(number) <= 1.0:
            if name.endswith("差"):
                return f"{number * 100:+.1f}ポイント"
            return f"{number * 100:.1f}%"
        if number.is_integer():
            return f"{number:.0f}"
        return f"{number:.2f}"


def _is_rate(name: str) -> bool:
    """割合（0〜1）で入っている特徴量か。"""
    return bool(re.search(r"(勝率|3着内率|3着以内率|割合|確率)(_|$|（|の)", name)) and "比" not in name
