"""対戦レーティング（まとまり O）の表を作る。"""

from __future__ import annotations

import pandas as pd

from .head_to_head_columns import HEAD_TO_HEAD_NAMES, KEY, LAST_CHANGE, RATING, RECENT_CHANGE, RUN_COUNT
from .rating_change_columns import RatingChangeColumns
from .rating_field_columns import RatingFieldColumns
from .rating_history_builder import RatingHistoryBuilder

#: 出走ごとの履歴から、出走の行に付ける列。
_PER_RUN_COLUMNS = [RATING, RUN_COUNT, LAST_CHANGE, RECENT_CHANGE]


class RatingTableBuilder:
    """全出走（``runs``）からレーティングの履歴を作り、対象の出走の行（``entries``）に付けて、まとまり O の7列にする。部品を順に呼ぶだけ。

    レース内の順位・偏差・平均との差は、``entries`` に入っている馬どうしで比べる（学習は出走した馬、予測は取消・除外になっていない馬）。
    ``entries`` は ``race_id``・``horse_id`` を持つ行。``runs`` に無い出走（記録が無い）は全部欠損値。``runs`` が空なら全部欠損値。
    列は ``HEAD_TO_HEAD_NAMES`` の順。行の並びと index は ``entries`` と同じ。
    """

    def build(self, entries: pd.DataFrame, runs: pd.DataFrame) -> pd.DataFrame:
        if runs.empty:
            return pd.DataFrame(float("nan"), index=entries.index, columns=list(HEAD_TO_HEAD_NAMES))
        per_run = self._per_run(runs)
        keys = pd.DataFrame({column: entries[column].astype(str).to_numpy() for column in KEY})
        aligned = keys.merge(per_run, on=KEY, how="left").set_axis(entries.index)
        field = RatingFieldColumns().build(entries["race_id"], aligned[RATING])
        return pd.concat([aligned[_PER_RUN_COLUMNS], field], axis=1)[list(HEAD_TO_HEAD_NAMES)].astype("float64")

    def _per_run(self, runs: pd.DataFrame) -> pd.DataFrame:
        """出走ごとの、レーティング・対戦数・前走と近5走の変化（鍵は文字列にそろえる）。"""
        history = RatingHistoryBuilder().build(runs)
        changes = RatingChangeColumns().build(history)
        table = pd.concat([history, changes], axis=1)
        table = table.assign(**{column: table[column].astype(str) for column in KEY})
        return table.drop_duplicates(KEY)[[*KEY, *_PER_RUN_COLUMNS]]
