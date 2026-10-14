"""事実とモデルの寄与から、1頭の強み・弱みの文を作る。"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from yosou.shared.feature.ability.ability_columns import PLACE_PRIOR, WIN_PRIOR

from .review_labels import ReviewLabels

#: メンバー内の順位で「上位」「下位」とみなす数。
TOP_RANKS = 3
#: 休み明けとみなす前走からの日数（重賞の傾向と同じ中9週以上）と、「間隔が詰まっている」とみなす日数。
REST_DAYS = 63
#: 前走で「好走」「大敗」とみなす着順。
GOOD_FINISH, BAD_FINISH = 3, 6
#: 率の材料（調教師・血統）を「高い」「低い」とみなす、全体の値との差（ポイント）。
RATE_GAP = 0.03
#: モデルの寄与（ロジットの上げ下げ）を強み・弱みに出す下限と、出す分類の数（今週の予想と同じ線）。
MIN_EFFECT_LOGIT = 0.05
CATEGORIES_SHOWN = 2
DETAILS_SHOWN = 2
#: レースの全馬に同じ値が入る分類（馬どうしの比べにならないので出さない）。
_RACE_CONDITION = "レースの条件"


@dataclass(frozen=True)
class HorsePointsResult:
    """1頭の強み・弱みの文。"""

    strong: list[str]
    weak: list[str]


class HorsePoints:
    """登録馬 1頭の、事実（近走・能力・適性・人・血統・調教）とモデルの寄与から、強み・弱みの文を定型で作る（設計書 15 の 13）。

    事実の文は、メンバー内の順位（能力指数・対戦レーティング・調教のタイム）、前走の着順と人気、同じコース・同じレースでの成績、
    休み明け・距離の変更・クラスの変更、調教師と血統の率（全体の値との差）、中央での出走の有無から決める。
    モデルの寄与は、分類ごとのロジットの上げ下げが ``MIN_EFFECT_LOGIT`` 以上の分類を上げ下げの大きい順に ``CATEGORIES_SHOWN`` まで、根拠の特徴量を添えて出す。
    """

    def __init__(self, labels: ReviewLabels | None = None) -> None:
        self._labels = labels or ReviewLabels()

    def of(self, facts: pd.Series, features: pd.Series, contributions: pd.Series, entries: int,
           previous: pd.Series | None) -> HorsePointsResult:
        """``facts`` は事実の行、``features`` は特徴量の値、``contributions`` は寄与、``entries`` は登録頭数、``previous`` は前走の行（無ければ None）。"""
        strong: list[str] = []
        weak: list[str] = []
        self._ability(features, entries, strong, weak)
        self._previous_run(facts, previous, strong, weak)
        self._aptitude(facts, strong, weak)
        self._condition(facts, strong, weak)
        self._people(features, strong, weak)
        self._workout(features, entries, strong, weak)
        self._contributions(features, contributions, strong, weak)
        return HorsePointsResult(strong, weak)

    def _ability(self, features: pd.Series, entries: int, strong: list[str], weak: list[str]) -> None:
        index = _number(features.get("指数_条件の重み"))
        rank = _number(features.get("能力スコア_順位"))
        if index is not None and rank is not None:
            text = f"能力指数がメンバー中 {rank:.0f}位（{index:.1f}。負担重量で直した能力スコアの順）"
            (strong if rank <= TOP_RANKS else weak if rank >= entries - TOP_RANKS + 1 else []).append(text)
        elif index is None:
            weak.append("スピード指数が無い（中央での過去走が無いか、少ない）")
        rating_rank = _number(features.get("対戦レーティングのレース内順位"))
        rating = _number(features.get("対戦レーティング"))
        if rating_rank is not None and rating is not None:
            text = f"対戦レーティング（誰に勝って誰に負けたか）がメンバー中 {rating_rank:.0f}位（{rating:.0f}）"
            (strong if rating_rank <= TOP_RANKS else weak if rating_rank >= entries - TOP_RANKS + 1 else []).append(text)

    def _previous_run(self, facts: pd.Series, previous: pd.Series | None, strong: list[str], weak: list[str]) -> None:
        runs = _number(facts.get("runs_before")) or 0
        if previous is None or runs == 0:
            weak.append("中央での出走が無い（近走の材料が無く、確率は粗い）")
            return
        finish = _number(previous.get("prev_finish"))
        popularity = _number(previous.get("prev_popularity"))
        gap = _number(previous.get("prev_time_diff"))
        name = previous.get("prev_race_name") or ""
        klass = previous.get("prev_class_name") or ""
        race = f"{name}（{klass}）" if name else klass
        where = f"{previous.get('prev_venue')} {previous.get('prev_surface')}{_int(previous.get('prev_distance_m'))}m"
        if finish is None:
            weak.append(f"前走 {race}・{where} は着順が付かなかった（競走中止など）")
            return
        detail = f"{finish:.0f}着" + (f"・{popularity:.0f}番人気" if popularity is not None else "") + (f"・着差 {gap:+.1f}秒" if gap is not None else "")
        text = f"前走 {race}・{where} で {detail}"
        if finish <= GOOD_FINISH:
            strong.append(text)
        elif finish >= BAD_FINISH:
            weak.append(text)
        else:
            strong.append(text) if popularity is not None and finish < popularity else weak.append(text)
        average = _number(facts.get("prev_last3f_rank"))
        if average is not None and average <= TOP_RANKS:
            strong.append(f"前走の上がり3ハロンは、今回のメンバーの前走の中で {average:.0f}位")

    def _aptitude(self, facts: pd.Series, strong: list[str], weak: list[str]) -> None:
        course_runs = _number(facts.get("course_runs_before")) or 0
        course_wins = _number(facts.get("course_wins_before")) or 0
        course_places = _number(facts.get("course_places_before")) or 0
        where = f"{facts.get('venue')} {facts.get('surface')}{_int(facts.get('distance_m'))}m"
        if course_runs >= 1:
            text = f"同じコース（{where}）で {course_runs:.0f}戦 {course_wins:.0f}勝・3着以内 {course_places:.0f}回"
            (strong if course_places >= 1 else weak).append(text)
        same_runs = _number(facts.get("same_race_runs_before")) or 0
        same_places = _number(facts.get("same_race_places_before")) or 0
        if same_runs >= 1:
            text = f"同じレース（{facts.get('race_name')}）に {same_runs:.0f}回出走し、3着以内 {same_places:.0f}回"
            (strong if same_places >= 1 else weak).append(text)
        dist_wins = _number(facts.get("dist_wins_before")) or 0
        change = facts.get("distance_change")
        if change in ("延長", "短縮"):
            text = f"前走から距離{change}（{_int(facts.get('prev_distance_m'))}m → {_int(facts.get('distance_m'))}m）。今回の距離での勝利は {dist_wins:.0f}勝"
            (strong if dist_wins >= 1 else weak).append(text)
        surface_change = facts.get("surface_change")
        if surface_change not in (None, "同じ", "前走なし") and isinstance(surface_change, str):
            weak.append(f"芝ダ替わり（{surface_change}）")

    def _condition(self, facts: pd.Series, strong: list[str], weak: list[str]) -> None:
        interval = _number(facts.get("interval_days"))
        if interval is not None and interval >= REST_DAYS:
            weak.append(f"休み明け（前走から {interval:.0f}日）")
        klass = facts.get("class_change")
        if klass == "昇級":
            weak.append("前走から昇級（相手が強くなる）")
        elif klass == "降級":
            strong.append("前走から降級（相手が弱くなる）")
        style = facts.get("style_before")
        lead = _number(facts.get("lead_runs_before")) or 0
        if style in ("逃げ", "先行"):
            strong.append(f"先行力がある（推定脚質 {style}。逃げた回数 {lead:.0f}）")

    def _people(self, features: pd.Series, strong: list[str], weak: list[str]) -> None:
        trainer = _number(features.get("調教師_1年_勝率"))
        if trainer is not None:
            text = f"調教師の近1年の勝率 {trainer:.1%}（全体 {WIN_PRIOR:.1%}）"
            if trainer >= WIN_PRIOR + RATE_GAP:
                strong.append(text)
            elif trainer <= WIN_PRIOR - RATE_GAP:
                weak.append(text)
        for name, label in (("父×芝ダ_3着内率", "父の産駒の同じ芝ダでの3着以内率"), ("父×距離_3着内率", "父の産駒の同じ距離での3着以内率"),
                            ("母父_3着内率", "母父の産駒の3着以内率")):
            rate = _number(features.get(name))
            if rate is None:
                continue
            text = f"{label} {rate:.1%}（全体 {PLACE_PRIOR:.1%}）"
            if rate >= PLACE_PRIOR + RATE_GAP:
                strong.append(text)
            elif rate <= PLACE_PRIOR - RATE_GAP:
                weak.append(text)

    def _workout(self, features: pd.Series, entries: int, strong: list[str], weak: list[str]) -> None:
        hill = _number(features.get("坂路_本数30日")) or 0
        wood = _number(features.get("ウッド_本数30日")) or 0
        if hill + wood == 0:
            weak.append("登録日までの 30日に坂路・ウッドの調教の記録が無い")
            return
        for name, label in (("坂路_4F最速14日_順位", "坂路の4ハロン最速（14日）"), ("ウッド_5F最速30日_順位", "ウッドの5ハロン最速（30日）")):
            rank = _number(features.get(name))
            if rank is None:
                continue
            if rank <= TOP_RANKS:
                strong.append(f"{label}がメンバー中 {rank:.0f}位")
            elif rank >= entries - TOP_RANKS + 1 and entries > 2 * TOP_RANKS:
                weak.append(f"{label}がメンバー中 {rank:.0f}位")

    def _contributions(self, features: pd.Series, contributions: pd.Series, strong: list[str], weak: list[str]) -> None:
        """モデルの寄与を分類ごとに足し、上げた分類と下げた分類を、根拠の特徴量を添えて出す。"""
        logits = contributions.astype(float)
        frame = logits.rename("logit").to_frame().assign(category=[self._labels.category(name) for name in logits.index])
        frame = frame[frame["category"] != _RACE_CONDITION]
        totals = frame.groupby("category")["logit"].sum().sort_values(ascending=False)
        for side, chosen in ((strong, totals[totals >= MIN_EFFECT_LOGIT].head(CATEGORIES_SHOWN)),
                             (weak, totals[totals <= -MIN_EFFECT_LOGIT].sort_values().head(CATEGORIES_SHOWN))):
            for category, total in chosen.items():
                members = frame[frame["category"] == category]["logit"]
                same_side = members[members > 0] if total > 0 else members[members < 0]
                names = same_side.abs().sort_values(ascending=False).index[:DETAILS_SHOWN]
                details = "、".join(f"{self._labels.display_name(name)} {self._labels.display_value(name, _plain(features.get(name)))}" for name in names)
                verb = "押し上げ" if total > 0 else "割り引き"
                side.append(f"モデルは「{category}」で{verb}（{total:+.2f}。根拠: {details}）")


def _number(value: object) -> float | None:
    """数にできれば小数、欠損なら None。"""
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else number


def _int(value: object) -> str:
    number = _number(value)
    return "?" if number is None else f"{number:.0f}"


def _plain(value: object) -> object:
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value
