"""特徴量を作る元の記録の入れ物。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import pandas as pd

from .ability import AbilitySources
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
    - ``stakes_tendency``: 対象のうち重賞のレースごとの傾向（それより前の開催の数え上げと基準。1行 = 1レース）。
      重賞の傾向と近走から3着以内を予想する予想だけが読む。ほかの予想では空の表。
    - ``market_runs``: 対象の開催日の前 365日の、平地の全出走（1行 = 1頭。単勝オッズ・着順・騎手・調教師・父・母父）。
      騎手・調教師・血統の市場に対する成績（まとまり L）を数える予想（全頭の3着以内・穴馬・人気馬）だけが読む。
      ほかの予想では空の表。
    - ``ability_sources``: 馬の力の材料（まとまり M）の元の記録（過去の全出走・スピード指数・調教のまとめ・セリの取引）。
      近走と適性の予想の木曜（と前日）のモデルだけが読む。ほかの予想では None。
    - ``pool_probabilities``: 対象のレースの、券種ごとのオッズから見た馬ごとの確率（1行 = 1頭。race_id・horse_no と
      ``POOLS`` の列）。券種ごとのオッズから見た支持（まとまり N）を使う近走と適性の予想の当日版だけが読む。ほかの予想では空の表。
    - ``head_to_head_runs``: 過去の平地の全出走と対象の出走（1行 = 1頭の出走。race_id・race_date・horse_id・finish・is_target）。
      対戦レーティング（まとまり O）を使う予想だけが読む。ほかの予想では空の表。
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
    stakes_tendency: pd.DataFrame = field(default_factory=pd.DataFrame)
    market_runs: pd.DataFrame = field(default_factory=pd.DataFrame)
    ability_sources: AbilitySources | None = None
    pool_probabilities: pd.DataFrame = field(default_factory=pd.DataFrame)
    head_to_head_runs: pd.DataFrame = field(default_factory=pd.DataFrame)

    def with_entries(self, entries: pd.DataFrame) -> EntryRecords:
        """出走の行だけを差し替えた記録。入れる行を選んだあとや、速報を反映したあとに使う。"""
        return replace(self, entries=entries)
