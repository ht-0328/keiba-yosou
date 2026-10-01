"""方針のうち、名前で選ぶ項目に書ける値（設計書 12・14）。設定ファイルに書けるのは、ここにある値だけ。"""

#: ``[unit]`` の ``split``: 単位の分け方。
SPLIT_BY_COURSE = "芝ダートと距離"
SPLIT_NONE = "なし"
UNIT_SPLITS: tuple[str, ...] = (SPLIT_BY_COURSE, SPLIT_NONE)

#: ``[features]`` の ``scaling``: 数の列のそろえ方。
SCALING_STANDARD = "標準化"
SCALING_RANK = "順位"
SCALINGS: tuple[str, ...] = (SCALING_STANDARD, SCALING_RANK)

#: ``[features]`` の ``categorical``: カテゴリの列の直し方。
ENCODING_ONE_HOT = "one-hot"
ENCODING_OUT_RATE = "馬券外率"
CATEGORICAL_ENCODINGS: tuple[str, ...] = (ENCODING_ONE_HOT, ENCODING_OUT_RATE)

#: ``[features.column_weighting]`` の ``method``: 列ごとの重みの決め方。
WEIGHTING_NONE = "なし"
WEIGHTING_AUC = "馬券外とのAUC"
COLUMN_WEIGHTINGS: tuple[str, ...] = (WEIGHTING_NONE, WEIGHTING_AUC)
