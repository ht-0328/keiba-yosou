"""理論の一覧: 事例から立てた理論①〜⑤と、確かめたが同じ人気の馬と差が無かった材料、そのほかに確かめた材料。

条件はどれも ``FinalRunners`` の表（レースの前に分かる材料の列）に当てる。線（0.3 や 15% など）は事例を見て置いたもので、
成績に合わせて動かしてはいない。
"""

from __future__ import annotations

from .final_runners import FRONT_POSITION
from .theory import Theory

#: 区分の名前（表の見出し。この順に並べる）。
PREV_FINAL = "① 前走がファイナルで3着以内だった馬は買われすぎ"
RECENT_FORM = "② 近走の着順が良く見える中穴は買われすぎ"
FRONT_LONGSHOT = "③ 前に行ける大穴は来る"
JOCKEY = "④ 騎手の成績が下位の大穴は来ない・その日勝っている騎手の人気馬は来る"
FIRST_FINAL = "⑤ ファイナル初出走の人気馬は来る"
NO_GAP = "確かめたが差が無かった材料"
OTHER = "そのほかに確かめた材料"
GROUPS: tuple[str, ...] = (PREV_FINAL, RECENT_FORM, FRONT_LONGSHOT, JOCKEY, FIRST_FINAL, NO_GAP, OTHER)

#: 位置の線（近3走の4コーナーの相対位置。0 = 先頭、1 = 最後方）。
_FRONT_WIDE, _BACK, _FAR_BACK = 0.35, 0.6, 0.7
#: 騎手の線（直近 365日の高知での3着以内率・人気とくらべた来やすさ・4コーナーの位置・数えるのに要る騎乗数）。
_JOCKEY_HIGH, _JOCKEY_LOW = 0.35, 0.15
_LIFT_HIGH, _LIFT_LOW, _LIFT_MIN_RIDES = 1.15, 0.85, 100
_JOCKEY_FRONT = 0.38
#: その日の傾向の線（3着以内の馬の4コーナーの相対位置の平均・枠の平均）。
_DAY_FRONT, _DAY_BACK, _DAY_OUTSIDE, _DAY_INSIDE = 0.25, 0.33, 5.0, 4.2
_HEAVY_GOING = ("重", "不良")
#: 事実表の値（騎手の乗り替わり・騎手の減量）。
_JOCKEY_CHANGED, _APPRENTICE = "乗り替わり", "減量あり"


def _front(t):
    return t["corner4_rel_recent3"] <= FRONT_POSITION


def _front_wide(t):
    return t["corner4_rel_recent3"] <= _FRONT_WIDE


def _back(t):
    return t["corner4_rel_recent3"] >= _BACK


def _final_place_rate(t):
    return t["final_places_before"] / t["final_runs_before"].clip(lower=1)


def _heavy(t):
    return t["condition"].isin(_HEAVY_GOING)


def _jockey_changed(t):
    return t["jockey_change"] == _JOCKEY_CHANGED


THEORIES: tuple[Theory, ...] = (
    # ① 前走がファイナル
    Theory(PREV_FINAL, "前走ファイナルで3着以内", lambda t: t["prev_run_final"] & (t["prev_finish"] <= 3)),
    Theory(PREV_FINAL, "前走ファイナル", lambda t: t["prev_run_final"]),
    Theory(PREV_FINAL, "前走ファイナルで4着以下・着差1.0秒以内",
           lambda t: t["prev_run_final"] & (t["prev_finish"] >= 4) & (t["prev_time_diff"] <= 1.0)),
    # ② 近走の着順
    Theory(RECENT_FORM, "近5走に3着以内2回以上", lambda t: t["places_recent5"] >= 2),
    Theory(RECENT_FORM, "近5走に3着以内なし", lambda t: t["places_recent5"] == 0),
    Theory(RECENT_FORM, "前走着差0.5秒以内", lambda t: t["prev_time_diff"] <= 0.5),
    Theory(RECENT_FORM, "前走着差3.0秒以上", lambda t: t["prev_time_diff"] >= 3.0),
    Theory(RECENT_FORM, "近3走の着差平均 レース内1〜2位", lambda t: t["time_diff_rank_in_race"] <= 2),
    Theory(RECENT_FORM, "近5走の最小着差0.2秒以内", lambda t: t["time_diff_best5"] <= 0.2),
    # ③ 前に行けるか
    Theory(FRONT_LONGSHOT, "4角の前らしさ レース内1〜2位", lambda t: t["corner4_rank_in_race"] <= 2),
    Theory(FRONT_LONGSHOT, "1角の前らしさ レース内1〜2位", lambda t: t["corner1_rank_in_race"] <= 2),
    Theory(FRONT_LONGSHOT, "1角の前らしさ レース内1位", lambda t: t["corner1_rank_in_race"] == 1),
    Theory(FRONT_LONGSHOT, "近3走の4角が前（0.3以下）", _front),
    Theory(FRONT_LONGSHOT, "近3走の4角が後ろ（0.7以上）", lambda t: t["corner4_rel_recent3"] >= _FAR_BACK),
    Theory(FRONT_LONGSHOT, "前走4角3番手以内", lambda t: t["prev_corner4"] <= 3),
    Theory(FRONT_LONGSHOT, "前走4角10番手以下", lambda t: t["prev_corner4"] >= 10),
    Theory(FRONT_LONGSHOT, "前に行く馬が少ない（2頭以下）で自分は前", lambda t: (t["front_runners"] <= 2) & _front(t)),
    Theory(FRONT_LONGSHOT, "前に行く馬が多い（5頭以上）で自分は前", lambda t: (t["front_runners"] >= 5) & _front(t)),
    Theory(FRONT_LONGSHOT, "前に行く馬が多い（5頭以上）で自分は後ろ", lambda t: (t["front_runners"] >= 5) & _back(t)),
    # ④ 騎手
    Theory(JOCKEY, "騎手 3着以内率15%以下", lambda t: t["jockey_place_rate_365"] <= _JOCKEY_LOW),
    Theory(JOCKEY, "騎手 その日2勝以上", lambda t: t["jockey_day_wins"] >= 2),
    Theory(JOCKEY, "騎手 3着以内率35%以上", lambda t: t["jockey_place_rate_365"] >= _JOCKEY_HIGH),
    Theory(JOCKEY, "騎手 人気より来る（1.15以上）",
           lambda t: (t["jockey_lift_365"] >= _LIFT_HIGH) & (t["jockey_rides_365"] >= _LIFT_MIN_RIDES)),
    Theory(JOCKEY, "騎手 人気より来ない（0.85以下）",
           lambda t: (t["jockey_lift_365"] <= _LIFT_LOW) & (t["jockey_rides_365"] >= _LIFT_MIN_RIDES)),
    Theory(JOCKEY, "騎手 前に行く（4角0.38以下）", lambda t: t["jockey_corner4_rel_365"] <= _JOCKEY_FRONT),
    Theory(JOCKEY, "騎手 その日3着以内なし（4鞍以上）", lambda t: (t["jockey_day_rides"] >= 4) & (t["jockey_day_places"] == 0)),
    Theory(JOCKEY, "乗り替わり", _jockey_changed),
    Theory(JOCKEY, "乗り替わりで上位騎手へ", lambda t: _jockey_changed(t) & (t["jockey_place_rate_365"] >= _JOCKEY_HIGH)),
    Theory(JOCKEY, "減量騎手", lambda t: t["apprentice"] == _APPRENTICE),
    # ⑤ ファイナル初出走
    Theory(FIRST_FINAL, "ファイナル初出走", lambda t: t["final_runs_before"] == 0),
    # 差が無かった材料（枠・馬場状態・距離の延長短縮・年齢・性別・斤量・持ち時計・ファイナルの出走回数）
    Theory(NO_GAP, "1〜2枠", lambda t: t["frame_no"] <= 2),
    Theory(NO_GAP, "7〜8枠", lambda t: t["frame_no"] >= 7),
    Theory(NO_GAP, "1〜2枠で前", lambda t: (t["frame_no"] <= 2) & _front_wide(t)),
    Theory(NO_GAP, "7〜8枠で前", lambda t: (t["frame_no"] >= 7) & _front_wide(t)),
    Theory(NO_GAP, "馬場 重・不良", _heavy),
    Theory(NO_GAP, "重・不良で前", lambda t: _heavy(t) & _front(t)),
    Theory(NO_GAP, "良で後ろ", lambda t: (t["condition"] == "良") & _back(t)),
    Theory(NO_GAP, "距離延長", lambda t: t["distance_m"] > t["prev_run_distance_m"]),
    Theory(NO_GAP, "距離短縮", lambda t: t["distance_m"] < t["prev_run_distance_m"]),
    Theory(NO_GAP, "1600mの日", lambda t: t["distance_m"] == 1600),
    Theory(NO_GAP, "3〜4歳", lambda t: t["age"] <= 4),
    Theory(NO_GAP, "8歳以上", lambda t: t["age"] >= 8),
    Theory(NO_GAP, "牝馬", lambda t: t["sex"] == "牝"),
    Theory(NO_GAP, "斤量が前走より1kg以上減", lambda t: t["carried"] - t["prev_run_carried"] <= -1),
    Theory(NO_GAP, "斤量52kg以下", lambda t: t["carried"] <= 52),
    Theory(NO_GAP, "持ち時計1位", lambda t: t["best_time_unit_rank"] == 1),
    Theory(NO_GAP, "ファイナル5回以上", lambda t: t["final_runs_before"] >= 5),
    Theory(NO_GAP, "ファイナル3着以内率40%以上（3回以上）", lambda t: (t["final_runs_before"] >= 3) & (_final_place_rate(t) >= 0.4)),
    Theory(NO_GAP, "ファイナル3回以上で3着以内なし", lambda t: (t["final_runs_before"] >= 3) & (t["final_places_before"] == 0)),
    Theory(NO_GAP, "ファイナル勝ちあり", lambda t: t["final_wins_before"] >= 1),
    # そのほかに確かめた材料
    Theory(OTHER, "近5走の上がり順位平均4位以内", lambda t: t["last3f_rank_recent5"] <= 4),
    Theory(OTHER, "前走上がり1〜2位", lambda t: t["prev_run_last3f_rank"] <= 2),
    Theory(OTHER, "前走上がり1〜2位で4着以下", lambda t: (t["prev_run_last3f_rank"] <= 2) & (t["prev_finish"] >= 4)),
    Theory(OTHER, "近3走より今回の人気が3以上下", lambda t: t["popularity"] - t["popularity_recent3"] >= 3),
    Theory(OTHER, "近3走より今回の人気が3以上上", lambda t: t["popularity_recent3"] - t["popularity"] >= 3),
    Theory(OTHER, "クラス下がり", lambda t: t["prev_run_class_order"] > t["class_order"]),
    Theory(OTHER, "クラス上がり", lambda t: t["prev_run_class_order"] < t["class_order"]),
    Theory(OTHER, "同距離で3着以内2回以上", lambda t: t["distance_places_before"] >= 2),
    Theory(OTHER, "同距離5走以上で3着以内なし", lambda t: (t["distance_runs_before"] >= 5) & (t["distance_places_before"] == 0)),
    Theory(OTHER, "間隔7日以内", lambda t: t["interval_days"] <= 7),
    Theory(OTHER, "間隔21〜59日", lambda t: t["interval_days"].between(21, 59)),
    Theory(OTHER, "間隔60日以上", lambda t: t["interval_days"] >= 60),
    Theory(OTHER, "その日 前有利で自分は前", lambda t: (t["day_corner4_rel"] <= _DAY_FRONT) & _front_wide(t)),
    Theory(OTHER, "その日 前有利で自分は後ろ", lambda t: (t["day_corner4_rel"] <= _DAY_FRONT) & _back(t)),
    Theory(OTHER, "その日 差しも届くで自分は後ろ", lambda t: (t["day_corner4_rel"] >= _DAY_BACK) & _back(t)),
    Theory(OTHER, "その日 外枠有利で7〜8枠", lambda t: (t["day_frame"] >= _DAY_OUTSIDE) & (t["frame_no"] >= 7)),
    Theory(OTHER, "その日 内枠有利で1〜2枠", lambda t: (t["day_frame"] <= _DAY_INSIDE) & (t["frame_no"] <= 2)),
    Theory(OTHER, "馬体重10kg以上増", lambda t: t["weight_change"] >= 10),
    Theory(OTHER, "馬体重10kg以上減", lambda t: t["weight_change"] <= -10),
)
