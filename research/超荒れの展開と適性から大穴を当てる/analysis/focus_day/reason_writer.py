"""馬ごとの理由の文: 展開・馬場・ハンデのどれで得（オッズのわりに来やすい）か損かを、事実を添えて短く書く。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .material_groups import DEVELOPMENT, FORM, HANDICAP, TRACK

#: 文にする寄与の大きさの下限（ロジット）。これより小さいまとまりは書かない。展開・馬場・ハンデは寄与がもともと小さいので低い線にする。
MIN_EFFECT = {DEVELOPMENT: 0.01, TRACK: 0.01, HANDICAP: 0.01, FORM: 0.05}
_PACE_NAMES = {0: "スロー", 1: "平均", 2: "ハイ"}


@dataclass(frozen=True)
class ReasonWriter:
    """``row`` は1頭の材料（予想のペースの確率・位置の確率・推定脚質・ハンデ・先のレースの傾き）と、まとまりごとの寄与（列名がまとまりの名前）。
    寄与の大きい順に、得か損かと、その元の事実を「；」でつなぐ。どのまとまりも小さければ「展開・馬場・ハンデの上げ下げは小さい」。"""

    def write(self, row: pd.Series) -> str:
        effects = {group: float(row.get(group, 0.0)) for group in (DEVELOPMENT, TRACK, HANDICAP, FORM)}
        parts = []
        for group, effect in sorted(effects.items(), key=lambda item: -abs(item[1])):
            if abs(effect) < MIN_EFFECT[group]:
                continue
            fact = self._fact(group, row, effect > 0)
            parts.append(f"{group}で{'得' if effect > 0 else '損'}（{fact}）" if fact else f"{group}で{'得' if effect > 0 else '損'}")
        return "；".join(parts) if parts else "展開・馬場・ハンデの上げ下げは小さい"

    def _fact(self, group: str, row: pd.Series, good: bool) -> str:
        if group == DEVELOPMENT:
            return self._development(row, good)
        if group == TRACK:
            return self._track(row)
        if group == HANDICAP:
            return self._handicap(row)
        return ""

    @staticmethod
    def _development(row: pd.Series, good: bool) -> str:
        shares = [row.get("予想_スロー"), row.get("予想_平均"), row.get("予想_ハイ")]
        if any(pd.isna(value) for value in shares):
            return ""
        pace = max(range(3), key=lambda index: shares[index])
        front, back = row.get("位置_前"), row.get("位置_後ろ")
        place = "前の見込み" if pd.notna(front) and front >= 0.5 else "後ろの見込み" if pd.notna(back) and back >= 0.5 else "中の見込み"
        text = f"{_PACE_NAMES[pace]}ペース予想（{shares[pace]:.2f}）で{place}"
        if pace == 2 and place == "前の見込み":
            return text + "。前が苦しい展開" if not good else text + "。前で粘れる見込み"
        if pace == 2 and place == "後ろの見込み":
            return text + "。差しが届く展開" if good else text + "。後ろからでは届きにくい"
        if pace == 0 and place == "後ろの見込み":
            return text + "。後ろからでは届きにくい展開" if not good else text
        if pace == 0 and place == "前の見込み":
            return text + "。前が楽な展開" if good else text
        return text

    @staticmethod
    def _track(row: pd.Series) -> str:
        inner, side = row.get("先のレースの内の傾き"), row.get("馬番の位置")
        if pd.isna(inner) or pd.isna(side):
            return "枠の位置" if pd.notna(side) else ""
        tilt = "内が来ている" if inner > 0.1 else "外が来ている" if inner < -0.1 else "内外の差は小さい"
        frame = "内枠" if side <= 1 / 3 else "外枠" if side > 2 / 3 else "真ん中の枠"
        return f"先のレースは{tilt}（{inner:+.2f}）で{frame}"

    @staticmethod
    def _handicap(row: pd.Series) -> str:
        facts = []
        if row.get("ハンデ戦か") == 1:
            top = row.get("トップとの差")
            facts.append("ハンデ戦でトップハンデ" if top == 0 else f"ハンデ戦でトップより {abs(top):.1f}kg 軽い" if pd.notna(top) else "ハンデ戦")
        change = row.get("斤量の前走との差")
        if pd.notna(change) and change != 0:
            facts.append(f"前走より {abs(change):.1f}kg {'軽い' if change < 0 else '重い'}")
        if row.get("昇級か") == 1:
            facts.append("昇級")
        return "・".join(facts)
