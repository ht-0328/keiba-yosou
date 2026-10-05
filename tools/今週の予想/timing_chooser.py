"""1レースを、どの時点（木曜・前日・当日）のモデルで予想するかを決める。"""

from __future__ import annotations

import duckdb

from 共通.race_signals import RaceSignalReader, RaceSignals

from yosou.shared.feature import PredictionTiming

from 今週の予想.timing_choice import TimingChoice


class TimingChooser:
    """DB に入っている情報から、いちばん新しい時点のモデルを選ぶ（設計書「近走と適性から3着以内を予想」07）。

    - 当日: 締め切り前の単勝オッズがあり、馬場状態と馬体重が発表されている。
    - 前日: 締め切り前の単勝オッズがあり、馬番が決まっている（出馬表）。
    - 木曜: それより前（オッズが無い・出走馬名表の段階）。
    オッズは jvdata-store の ``jvstore realtime --date <開催日>`` で取り込む。
    DB の読み方は ``共通.race_signals``（事実表を作らないので、取得中の DB を長く塞がない）。
    """

    def choose(self, con: duckdb.DuckDBPyConnection, race_id: str) -> TimingChoice:
        """DB を読んで選ぶ。レースが無ければ ``LookupError``。"""
        return self.choose_from(RaceSignalReader(con).read_race(race_id))

    def choose_from(self, signals: RaceSignals) -> TimingChoice:
        """読んである材料の有無（``RaceSignals``）から選ぶ。道具「取得と予想の状況」が、開催日ぶんまとめて読んだ材料に使う。"""
        if not signals.has_odds:
            return TimingChoice(PredictionTiming.THURSDAY, "締め切り前のオッズがまだ DB に無いので、木曜（オッズを使わない）のモデル")
        if signals.is_weighed and signals.going_announced:
            return TimingChoice(PredictionTiming.RACE_DAY, "馬体重と馬場状態が発表され、オッズもあるので、当日のモデル")
        if signals.is_numbered:
            return TimingChoice(PredictionTiming.DAY_BEFORE, "出馬表（馬番）とオッズがあるので、前日のモデル（馬体重はまだ使わない）")
        return TimingChoice(PredictionTiming.THURSDAY, "馬番がまだ決まっていないので、木曜のモデル")
