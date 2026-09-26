"""特徴量を作る元の記録の入れ物。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import pandas as pd

from .history import WorkoutCoverage


@dataclass(frozen=True)
class EntryRecords:
    """特徴量を作る元の記録。どれも pandas の表で、リポジトリが元DB から読んだもの。

    - ``entries``: 1行 = 1頭の出走。事実表の列と、その出走の出走別着度数（``ck_`` で始まる列）。
    - ``past_runs``: ``entries`` の馬が中央で出走した過去のレース（1行 = 1走）。
    - ``workouts``: ``entries`` の馬の、開催日の前 14日以内の調教（坂路とウッド）。
    - ``workout_coverage``: 調教の記録が DB にある期間（コースごとの最初の日）。
    - ``jockey_days``・``trainer_days``: 騎手・調教師ごと、開催日ごとの出走数と3着以内の数。
    - ``sire_days``・``damsire_days``: 父・母父ごと、開催日ごと、芝ダごとの、産駒の出走数と3着以内の数。
    - ``race_history``: 対象の出走のレースと、その前の3年の平地のレース（1行 = 1レース。最初のコーナー・先頭の馬番・
      前3ハロン・後3ハロンなど）。展開から着順を予想する予想だけが読む。ほかの予想では空の表。
    """

    entries: pd.DataFrame
    past_runs: pd.DataFrame
    workouts: pd.DataFrame
    workout_coverage: WorkoutCoverage
    jockey_days: pd.DataFrame
    trainer_days: pd.DataFrame
    sire_days: pd.DataFrame
    damsire_days: pd.DataFrame
    race_history: pd.DataFrame = field(default_factory=pd.DataFrame)

    def with_entries(self, entries: pd.DataFrame) -> EntryRecords:
        """出走の行だけを差し替えた記録。入れる行を選んだあとや、速報を反映したあとに使う。"""
        return replace(self, entries=entries)
