"""事例の一覧（1行 = 勝った人気薄1頭）。CSV と Markdown の表の両方に使う。馬名などの実値を含むので reports/ にだけ書く。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from ..theory.runner_type_flags import TYPE_LABELS

#: 出す列（出走の表の列 → 見出し）。左から、レース・馬・判断時点の手がかり・今のモデル・結果側の順。
COLUMNS: dict[str, str] = {
    "race_date": "開催日", "win5_leg": "WIN5の何レース目", "venue": "競馬場", "race_no": "R", "surface": "芝ダ", "distance_m": "距離",
    "condition": "馬場", "class_name": "クラス", "weight_type": "重量種別", "field_size": "頭数", "horse_no": "馬番", "horse_name": "馬名",
    "popularity": "人気", "win_odds": "単勝", "age": "年齢", "sex": "性", "frame_no": "枠", "carried_gap": "斤量の平均との差",
    TYPE_LABELS: "当てはまった型",
    "prev_finish": "前走着順", "prev_popularity": "前走人気", "prev_time_diff": "前走着差", "prev_corner4": "前走4角", "prev2_finish": "2走前着順",
    "interval_days": "間隔(日)", "class_change": "クラスの変更", "distance_change": "距離の変更", "prev_distance_m": "前走距離",
    "surface_change": "芝ダ替わり", "prev_condition": "前走馬場", "best_recent_finish": "近5走の最高着順",
    "best_placed_class": "3着以内の最高クラス(順)", "class_order": "今回のクラス(順)", "course_places_before": "同コース3着内",
    "surface_places_before": "同芝ダ3着内", "best_time_dist_rank": "持ち時計順位(距離)", "jockey_rate": "騎手前年勝率",
    "prev_jockey_rate": "前走騎手前年勝率", "trainer_rate": "調教師前年勝率", "style_before": "推定脚質", "lead_candidates": "逃げ候補数",
    "prev_style": "前走脚質", "front_places_before": "逃げ先行での3着内", "back_places_before": "差し追込での3着内",
    "blinker": "ブリンカー", "weight_change": "馬体重増減", "dm_rank": "マイニング順位",
    "longshot_market": "人気薄の市場合計", "favorite_odds": "1番人気の単勝",
    "market": "オッズから見た勝率", "model": "今のモデルの1着の確率", "uplift": "上乗せ", "model_rank": "モデルの順位",
    "corner4": "4角(結果)", "style": "脚質(結果)", "last3f_rank": "上がり順位(結果)", "pace_gap": "ペースの差(結果)",
    "second_gap": "2着との差(結果)", "favorite_finish": "1番人気の着順(結果)",
}
_ROUNDED = ("carried_gap", "prev_time_diff", "jockey_rate", "prev_jockey_rate", "trainer_rate", "longshot_market", "market", "model",
            "uplift", "pace_gap", "second_gap")


@dataclass(frozen=True)
class CaseList:
    """``cases`` は勝った人気薄の行（型の列つき）。"""

    def frame(self, cases: pd.DataFrame) -> pd.DataFrame:
        picked = cases.sort_values(["race_date", "race_id"])[list(COLUMNS)].copy()
        picked[list(_ROUNDED)] = picked[list(_ROUNDED)].round(3)
        return picked.rename(columns=COLUMNS)

    def table(self, cases: pd.DataFrame, title: str, note: str = "") -> Table:
        frame = self.frame(cases).astype(object).where(lambda f: f.notna(), None)
        return Table(list(frame.columns), frame.values.tolist(), title=title, note=note)
