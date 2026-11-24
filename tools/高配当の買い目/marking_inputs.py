"""印を付けるのに元DB から読んだもの。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class MarkingInputs:
    #: 出走の結果（``RaceResults.read``。着順・確定の単勝と複勝のオッズ・人気・払戻・頭数・所属・中央の出走数）。
    #: 印を付けるレースと、危険な人気馬の線・単勝の期待値を出すレースの全部。
    results: pd.DataFrame
    #: 馬ごとの「3連単から見た勝率」（``PoolWinReader.read``。印を付けるレースだけ）。
    pools: pd.DataFrame
    #: 前日夜と当日朝の単勝オッズ（``OddsSnapshotRepository.read``。印を付けるレースだけ。時系列オッズのあるレースだけ行がある）。
    movements: pd.DataFrame
