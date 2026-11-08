"""詳しく見る日（例 2026-11-08）の WIN5 の対象レースの勝ち馬を、判断時点の材料・今のモデル・結果側に分けて縦に並べる表と、その馬の過去走の表。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from ..theory.race_type_catalog import RACE_TYPES
from ..theory.runner_type_flags import TYPE_LABELS
from .cells import number

#: 縦に並べる項目（見出し → 行から文字を作る関数）。
_ITEMS: dict[str, object] = {
    "WIN5 の何レース目": lambda r: f"{int(r['win5_leg'])}",
    "レース": lambda r: f"{r['venue']}{int(r['race_no'])}R {r['surface']}{int(r['distance_m'])}m {r['condition']} {r['class_name']} {r['weight_type']} {int(r['field_size'])}頭",
    "馬": lambda r: f"{int(r['horse_no'])}番 {r['horse_name']}（{int(r['age'])}歳{r['sex']}・{int(r['frame_no'])}枠）",
    "人気（確定）・単勝": lambda r: f"{int(r['popularity'])}番人気・{r['win_odds']}倍",
    "人気（WIN5 の予想をしたときの締め切り前のオッズ）": lambda r: r["record_popularity"],
    "当てはまった型（馬の側）": lambda r: r[TYPE_LABELS] or "なし",
    "当てはまったレースの型": lambda r: r["race_types"] or "なし",
    "前走": lambda r: (f"{number(r['prev_finish'], 0)}着（{number(r['prev_popularity'], 0)}番人気・着差 {number(r['prev_time_diff'], 1)}秒・"
                     f"4角 {number(r['prev_corner4'], 0)}番手・{r['prev_condition']}・{number(r['prev_distance_m'], 0)}m・脚質 {r['prev_style']}）"),
    "2走前・近5走の最高": lambda r: f"2走前 {number(r['prev2_finish'], 0)}着・近5走の最高 {number(r['best_recent_finish'], 0)}着",
    "間隔・クラス・距離の替わり": lambda r: f"{number(r['interval_days'], 0)}日・{r['class_change']}・{r['distance_change']}・{r['surface_change']}",
    "実績": lambda r: (f"3着以内の最高クラス(順) {number(r['best_placed_class'], 0)}（今回 {number(r['class_order'], 0)}）・"
                     f"勝った最高クラス(順) {number(r['best_win_class'], 0)}・同コース3着内 {number(r['course_places_before'], 0)}・"
                     f"同芝ダ3着内 {number(r['surface_places_before'], 0)}"),
    "人": lambda r: (f"騎手の前年勝率 {number(r['jockey_rate'], 3)}（前走の騎手 {number(r['prev_jockey_rate'], 3)}・{r['jockey_change']}）・"
                    f"調教師 {number(r['trainer_rate'], 3)}"),
    "展開の材料": lambda r: (f"推定脚質 {r['style_before']}・逃げ候補 {number(r['lead_candidates'], 0)}頭・枠 {int(r['frame_no'])}・"
                         f"逃げ先行での3着内 {number(r['front_places_before'], 0)}・差し追込での3着内 {number(r['back_places_before'], 0)}"),
    "斤量・馬体": lambda r: f"斤量の平均との差 {number(r['carried_gap'], 1)}kg・馬体重 {number(r['weight_change'], 0)}kg",
    "レースの人気の割れ方": lambda r: (f"1番人気 {r['favorite_odds']}倍・10倍未満 {number(r['contenders'], 0)}頭・"
                               f"人気薄の市場合計 {number(r['longshot_market'], 3)}"),
    "今のモデル": lambda r: (f"1着の確率 {number(r['model'], 3)}・オッズから見た勝率 {number(r['market'], 3)}・上乗せ {number(r['uplift'], 2)}・"
                        f"順位 {number(r['model_rank'], 0)}"),
    "結果側（理解のため）": lambda r: (f"4角 {number(r['corner4'], 0)}番手・脚質 {r['style']}・上がり {number(r['last3f_rank'], 0)}位・"
                              f"ペースの差 {number(r['pace_gap'], 1)}・2着との差 {number(r['second_gap'], 1)}・1番人気 {number(r['favorite_finish'], 0)}着"),
}
_PAST_COLUMNS: dict[str, str] = {
    "race_date": "開催日", "venue": "競馬場", "surface": "芝ダ", "distance_m": "距離", "condition": "馬場", "class_name": "クラス",
    "weight_type": "重量種別", "field_size": "頭数", "frame_no": "枠", "popularity": "人気", "finish": "着順", "time_diff": "着差",
    "corner4": "4角", "last3f_rank": "上がり順位", "style": "脚質", "carried": "斤量",
}
#: 過去走を何走まで出すか。
PAST_RUNS = 10


@dataclass(frozen=True)
class FocusCaseTable:
    """``runners`` は出走の表（型の列つき）、``history`` は事実表の全部の出走（過去走を出すため）。"""

    def build(self, runners: pd.DataFrame, history: pd.DataFrame, race_date: str, longshot_from: int) -> list[Table]:
        legs = runners.loc[(runners["race_date"] == race_date) & runners["win5_leg"].notna()].copy()
        legs["record_rank"] = self._record_rank(legs)
        legs["record_popularity"] = legs["record_rank"].map(lambda value: "記録なし" if pd.isna(value) else f"{int(value)}番人気")
        winners = legs.loc[legs["finish"] == 1].sort_values("win5_leg")
        if winners.empty:
            return []
        winners["race_types"] = self._race_types(winners)
        labels = [f"{int(r['win5_leg'])}レース目" for _, r in winners.iterrows()]
        records = [r for _, r in winners.iterrows()]
        rows = [[item, *map(make, records)] for item, make in _ITEMS.items()]
        tables = [Table(["項目", *labels], rows, title=f"詳しく見る日 {race_date} の WIN5 の勝ち馬")]
        longshot = (winners["popularity"] >= longshot_from) | (winners["record_rank"] >= longshot_from)
        for _, r in winners.loc[longshot].iterrows():
            tables.append(self._past(history, r))
        return tables

    @staticmethod
    def _record_rank(legs: pd.DataFrame) -> pd.Series:
        """WIN5 の予想の記録にある締め切り前の単勝オッズでの人気（記録が無ければ欠損値）。"""
        if "record_odds" not in legs.columns:
            return pd.Series(float("nan"), index=legs.index)
        return legs.groupby("race_id")["record_odds"].rank(method="min")

    @staticmethod
    def _race_types(winners: pd.DataFrame) -> pd.Series:
        flags = pd.DataFrame({rule.name: rule.flags(winners) for rule in RACE_TYPES[:4]}, index=winners.index)
        return flags.apply(lambda row: "・".join(name for name, hit in row.items() if hit), axis=1)

    @staticmethod
    def _past(history: pd.DataFrame, winner: pd.Series) -> Table:
        past = history.loc[(history["horse_id"] == winner["horse_id"]) & (history["race_date"] < winner["race_date"])]
        past = past.sort_values("race_date").tail(PAST_RUNS)[list(_PAST_COLUMNS)].rename(columns=_PAST_COLUMNS)
        frame = past.astype(object).where(past.notna(), None)
        return Table(list(frame.columns), frame.values.tolist(),
                     title=f"{int(winner['win5_leg'])}レース目の勝ち馬（{int(winner['popularity'])}番人気）の過去走（新しい走が下）")
