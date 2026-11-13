"""選んだ事例を1頭ずつ並べた表（来た大穴と、比べる1番人気）。馬名が入るので reports/ にだけ書く。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table


def _number(value: object, digits: int = 0) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.{digits}f}"


def _signed(value: object, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):+.{digits}f}"


def _passing(row: pd.Series) -> str:
    corners = [_number(row[f"corner{no}"]) for no in (1, 2, 3, 4)]
    return "-".join(corner for corner in corners if corner)


def _recent(row: pd.Series) -> str:
    parts = []
    for finish, popularity in (("prev_finish", "prev_popularity"), ("prev2_finish", "prev2_popularity"), ("prev3_finish", "prev3_popularity")):
        if pd.notna(row[finish]):
            parts.append(f"{_number(row[finish])}着({_number(row[popularity])}人)")
    return " ".join(parts)


#: 列（見出し → 1行から値を作る関数）。
COLUMNS = {
    "事例": lambda r: r["case_no"], "決着": lambda r: r["outcome"], "区分": lambda r: r["role"],
    "開催日": lambda r: r["race_date"], "競馬場": lambda r: r["venue"], "コース": lambda r: f"{r['course']}{_number(r['distance_m'])}m",
    "馬場": lambda r: r["condition"], "クラス": lambda r: r["class_name"], "重量種別": lambda r: r["weight_type"],
    "頭数": lambda r: _number(r["field_size"]),
    "結果のペース": lambda r: r["pace"] if pd.notna(r["pace"]) else "",
    "前半3F-後半3F": lambda r: f"{_number(r['first3f'], 1)}-{_number(r['last3f_race'], 1)}",
    "予想（ハイ/スローの確率）": lambda r: f"{_number(r['p_high'], 2)}/{_number(r['p_slow'], 2)}" if pd.notna(r["p_high"]) else "",
    "予想との違い": lambda r: r["pace_vs_forecast"] if pd.notna(r["pace_vs_forecast"]) else "",
    "その日の傾き（内/前）": lambda r: f"{_signed(r['tilt_inner'], 2)}/{_signed(r['tilt_front'], 2)}",
    "着順": lambda r: _number(r["finish"]), "馬名": lambda r: r["horse_name"],
    "人気（確定/締め切り前）": lambda r: f"{_number(r['popularity'])}/{_number(r['pre_close_popularity'])}",
    "単勝": lambda r: _number(r["win_odds"], 1), "馬番（枠の側）": lambda r: f"{_number(r['horse_no'])}（{r['horse_side']}）",
    "通過順": _passing, "結果の脚質": lambda r: r["result_style"] or "", "上がり順位": lambda r: _number(r["last3f_rank"]),
    "推定脚質": lambda r: r["style_before"] if pd.notna(r["style_before"]) else "",
    "位置の見込み（前/後ろ）": lambda r: f"{_number(r['p_front'], 2)}/{_number(r['p_back'], 2)}" if pd.notna(r["p_front"]) else "",
    "いつもとの位置": lambda r: r["position_shift"] if pd.notna(r["position_shift"]) else "",
    "コース実績（3着内/出走）": lambda r: f"{_number(r['course_places_before'])}/{_number(r['course_runs_before'])}",
    "同じ馬場状態の3着内": lambda r: _number(r["cond_places_before"]), "同じ距離の勝ち": lambda r: _number(r["dist_wins_before"]),
    "近3走（着順・人気）": _recent, "前走のクラス（替わり）": lambda r: f"{r['prev_class_name'] or ''}（{r['class_change'] or ''}）",
    "斤量": lambda r: _number(r["carried"], 1), "平均との差": lambda r: _signed(r["carried_vs_mean"]),
    "トップとの差": lambda r: _signed(r["carried_vs_top"]), "前走との差": lambda r: _signed(r["carried_change"]),
    "同じ斤量（3着内/出走）": lambda r: f"{_number(r['same_carried_places'])}/{_number(r['same_carried_runs'])}",
    "重い斤量で3着内": lambda r: _number(r["heavier_places"]), "回顧の不利": lambda r: r["disadvantage_text"] or "",
}


@dataclass(frozen=True)
class CaseDetailTable:
    """``frame`` で選んだ事例の行（来た大穴の全部と、そのレースの1番人気）を作り、``table`` で Markdown の表にする。"""

    def frame(self, runners: pd.DataFrame, races: pd.DataFrame, chosen: list[str], notes: pd.DataFrame) -> pd.DataFrame:
        selected = runners.loc[runners["race_id"].isin(chosen)].copy()
        selected["case_no"] = selected["race_id"].map({race_id: no for no, race_id in enumerate(chosen, start=1)})
        selected["outcome"] = selected["race_id"].map(races["outcome"])
        placed = selected["longshot"] & (selected["top3"] > 0)
        favorite = selected["popularity"] == 1
        selected = selected.loc[placed | favorite].copy()
        selected["role"] = selected["longshot"].map({True: "来た大穴", False: "1番人気"})
        text = (notes["disadvantage"].astype(str) + "・" + notes["degree"].astype(str)).groupby(
            [notes["race_id"], notes["horse_id"]]).agg("、".join)
        keys = pd.MultiIndex.from_frame(selected[["race_id", "horse_id"]].astype(str))
        selected["disadvantage_text"] = text.reindex(keys).to_numpy() if len(text) else None
        selected = selected.sort_values(["case_no", "longshot", "finish"], ascending=[True, False, True])
        return pd.DataFrame({name: selected.apply(make, axis=1) for name, make in COLUMNS.items()}).reset_index(drop=True)

    @staticmethod
    def table(frame: pd.DataFrame, title: str) -> Table:
        return Table(list(frame.columns), frame.astype(object).where(frame.notna(), "").values.tolist(), title=title)
