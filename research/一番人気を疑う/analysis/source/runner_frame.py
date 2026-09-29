"""読んだ表を、この研究の共通の形（1行 = 1頭）にそろえる。"""

from __future__ import annotations

import pandas as pd

#: どの表からも必ずそろえる列。
KEY_COLUMNS: tuple[str, ...] = ("レースID", "開催日", "馬番", "確定の単勝人気", "3着以内")
#: 学習データでの出走がこれより少ないカテゴリの値は「その他」にまとめる（今の予想の min_category_count と同じ）。
MIN_CATEGORY_COUNT = 2000
OTHER = "その他"


class RunnerFrame:
    """列の型をそろえる。レースIDは文字列、開催日は日付、文字の材料はカテゴリの型にする。

    LightGBM は文字列を扱えないので、文字の材料はカテゴリの型に変える。出走の少ない値は、その値を覚えるだけに
    なるので「その他」にまとめる。
    """

    def shape(self, frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
        missing = [column for column in KEY_COLUMNS if column not in frame.columns]
        if missing:
            raise ValueError(f"表に無い列があります: {'・'.join(missing)}")
        frame = frame[frame["3着以内"].notna()].reset_index(drop=True)
        frame["レースID"] = frame["レースID"].astype(str)
        frame["開催日"] = pd.to_datetime(frame["開催日"]).dt.date
        for column in features:
            if not pd.api.types.is_numeric_dtype(frame[column]):
                frame[column] = self._category(frame[column])
        return frame

    @staticmethod
    def _category(values: pd.Series) -> pd.Series:
        text = values.astype(str)
        counts = text.map(text.value_counts())
        return text.where(counts >= MIN_CATEGORY_COUNT, OTHER).astype("category")
