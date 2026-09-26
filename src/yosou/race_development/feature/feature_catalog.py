"""この予想が使う特徴量の一覧（設計書 09 の表の写し）。

1頭ごとの特徴量は、共通の 71個（A〜I）に K・L・M・N・O を足した 111個を、1回で作る（``HORSE_CATALOG``）。
予想ごとに、そのうちの列と、前の組の予想の結果（S・T）を選んで使う。1レースごとの特徴量も同じく、R・P・Q・U の 34個を
1回で作り（``RACE_CATALOG``）、予想ごとに選ぶ。

| 一覧 | 予想 | 数（当日） |
|---|---|---|
| ``EARLY_HORSE_CATALOG`` | ① 先頭・② 序盤の位置 | 98（A〜I・K・L・M） |
| ``EARLY_RACE_CATALOG`` | ③ 前半のペース | 27（R・P・Q） |
| ``LATE_HORSE_CATALOG`` | ④ 4コーナーの位置・⑤ 上がりの速さ | 120（①② の全部・N・O・S） |
| ``LATE_RACE_CATALOG`` | ⑥ 後半のペース | 40（③ の全部・U・1レースごとの S） |
| ``FINISH_CATALOG`` | ⑦ 着順 | 127（④⑤ の全部・T） |
| ``FINISH_PLAIN_CATALOG`` | ⑦ の比べる基準（前半・後半の予想を入れない） | 111（⑦ から S・T を除く） |
"""

from __future__ import annotations

from yosou.shared.feature import (
    BASE_FEATURES,
    FIELD_SIZE,
    GOING,
    HANDICAP,
    SPECIAL_RACE,
    Feature,
    FeatureCatalog,
    FeatureKind,
    PredictionTiming,
)

_N = FeatureKind.NUMERIC
_C = FeatureKind.CATEGORICAL
#: 前日から分かる（馬番・馬場状態）。
_DAY_BEFORE = PredictionTiming.DAY_BEFORE

#: K. 序盤の位置取りの履歴（15個）。
K_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "K", _N) for name in (
    "前走の序盤の位置", "近5走の序盤の位置の平均", "近5走の序盤の位置の最小", "近5走の序盤の位置のばらつき",
    "近5走の序盤の記録の数", "近5走の先頭の数", "近5走の先団の数", "先頭率", "先団率",
    "日数で重みを付けた序盤の位置の平均", "同じ芝ダでの序盤の位置の平均", "前走の序盤から4コーナーへの位置の変化",
    "前走からの距離の差", "騎手の先頭率", "騎手の先団率",
))
#: L. 同じレースの馬との比較（序盤）（9個）。内・外と相対馬番は、馬番の決まる前日から。
L_FEATURES: tuple[Feature, ...] = (
    Feature("ほかの馬の先頭率の合計", "L", _N),
    Feature("ほかの馬の先団率の合計", "L", _N),
    Feature("自分より内の馬の先頭率の合計", "L", _N, _DAY_BEFORE),
    Feature("自分より外の馬の先頭率の合計", "L", _N, _DAY_BEFORE),
    Feature("先頭率のレース内順位", "L", _N),
    Feature("近5走の序盤の位置の平均のレース内順位", "L", _N),
    Feature("先頭率がいちばん高い相手との差", "L", _N),
    Feature("序盤の記録が無い馬の数", "L", _N),
    Feature("相対馬番", "L", _N, _DAY_BEFORE),
)
#: M. コースの形（3個）。
M_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "M", _N) for name in (
    "最初のコーナーの番号", "記録されるコーナーの数", "このコースで先頭になった馬の馬番の位置の平均",
))
#: N. 末脚の履歴（10個）。
N_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "N", _N) for name in (
    "前走の上がりの速さ", "近5走の上がりの速さの平均", "近5走の上がりの速さの最小", "近5走の上がりの速さのばらつき",
    "近5走で上がりが1位だった数", "日数で重みを付けた上がりの速さの平均", "同じ芝ダでの上がりの速さの平均",
    "近5走の 4コーナーからゴールまでの位置の変化の平均", "近5走の序盤から 4コーナーまでの位置の変化の平均",
    "近5走の上がりとレースの後半タイムとの差の平均",
))
#: O. 同じレースの馬との比較（末脚）（3個）。
O_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "O", _N) for name in (
    "近5走の上がりの速さの平均のレース内順位", "ほかの馬の近5走の上がりの速さの平均の最小", "末脚がいちばんある相手との差",
))
#: S. 前半の予想の結果（1頭ごと 9個）。どの時点でも、同じ時点の前半のモデルの予測を入れる。
S_HORSE_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "S", _N) for name in (
    "先頭の確率", "先団の確率", "中団の確率", "後方の確率", "先頭の確率のレース内順位", "先団の確率のレース内順位",
    "ハイペースの確率", "スローペースの確率", "前半タイムの基準との差の予測",
))
#: S. 前半の予想の結果（1レースごと 6個）。
S_RACE_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "S", _N) for name in (
    "ハイペースの確率", "スローペースの確率", "前半タイムの基準との差の予測", "前半タイムの予測の幅",
    "先頭の確率の1位", "先団の確率の合計",
))
#: T. 後半の予想の結果（7個）。
T_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "T", _N) for name in (
    "4コーナーの位置の予測", "上がりの速さの予測", "4コーナーの位置の予測のレース内順位", "上がりの速さの予測のレース内順位",
    "位置と上がりの予測の和", "位置と上がりの予測の和のレース内順位", "後半タイムの基準との差の予測",
))
#: R. レースの条件（11個。荒れ具合の予想の A と同じ。共通の ``RaceConditionSummary`` が作る）。
R_FEATURES: tuple[Feature, ...] = (
    Feature("競馬場", "R", _C),
    Feature("芝ダ", "R", _C),
    Feature("コース", "R", _C),
    Feature("距離", "R", _N),
    Feature(GOING, "R", _C, _DAY_BEFORE),
    Feature("クラス", "R", _N),
    Feature(FIELD_SIZE, "R", _N),
    Feature("開催月", "R", _N),
    Feature("牡馬と牝馬が一緒に走るか", "R", _C),
    Feature(SPECIAL_RACE, "R", _C),
    Feature(HANDICAP, "R", _C),
)
#: P. ペースの材料（10個）。先頭率の1位の馬の相対馬番は、馬番の決まる前日から。
P_FEATURES: tuple[Feature, ...] = (
    *(Feature(name, "P", _N) for name in (
        "先頭率の合計", "先頭率の1位", "先頭率の2位", "先頭率の1位と2位の差", "先団率が 0.5 以上の馬の数",
        "先団率の合計", "前にいる3頭の序盤の位置の平均", "序盤の記録が無い馬の割合", "逃げそうな馬の数",
    )),
    Feature("先頭率の1位の馬の相対馬番", "P", _N, _DAY_BEFORE),
)
#: Q. 前半タイムの基準とコース（6個）。
Q_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "Q", _N) for name in (
    "測る区間", "前半タイムの基準", "基準の標準偏差", "基準の件数", "最初のコーナーの番号",
    "このコースで先頭になった馬の馬番の位置の平均",
))
#: U. 後半の材料（7個）。
U_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "U", _N) for name in (
    "後半タイムの基準", "後半タイムの基準の標準偏差", "後半タイムの基準の件数", "近5走の上がりの速さの平均の最小",
    "近5走の上がりの速さの平均が 0.3 以下の馬の数", "近5走の上がりとレースの後半タイムとの差の平均の、レースの平均",
    "上がりの記録が無い馬の割合",
))

#: 1頭ごとに1回で作る特徴量（111個）。
HORSE_CATALOG = FeatureCatalog(BASE_FEATURES + K_FEATURES + L_FEATURES + M_FEATURES + N_FEATURES + O_FEATURES)
#: 1レースごとに1回で作る特徴量（34個）。
RACE_CATALOG = FeatureCatalog(R_FEATURES + P_FEATURES + Q_FEATURES + U_FEATURES)
#: 予想ごとの一覧。
EARLY_HORSE_CATALOG = FeatureCatalog(BASE_FEATURES + K_FEATURES + L_FEATURES + M_FEATURES)
EARLY_RACE_CATALOG = FeatureCatalog(R_FEATURES + P_FEATURES + Q_FEATURES)
LATE_HORSE_CATALOG = FeatureCatalog(HORSE_CATALOG.features + S_HORSE_FEATURES)
LATE_RACE_CATALOG = FeatureCatalog(RACE_CATALOG.features + S_RACE_FEATURES)
FINISH_CATALOG = FeatureCatalog(LATE_HORSE_CATALOG.features + T_FEATURES)
FINISH_PLAIN_CATALOG = HORSE_CATALOG
