"""予測に要る情報が DB にあるかを確かめる。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

#: 1頭ごとの予想で、その時点で使うのに DB にまだ無いと予測できない特徴量と、取り込み方の案内。
HORSE_GUIDANCE: dict[str, str] = {
    "馬番": "馬番がまだ決まっていません（出走馬名表の段階）。"
            "jvstore sync で出馬表を取り込むか、時点を木曜にしてください。",
    "馬場状態": "馬場状態がまだ DB にありません。jvstore realtime（開催日）で速報を取り込んでください。",
    "馬体重": "馬体重がまだ DB にありません。"
              "馬体重の発表のあとに jvstore realtime（開催日）で速報を取り込んでください。",
    "単勝オッズ": "単勝オッズがまだ DB にありません。--odds 馬番:オッズ で渡すか、"
                  "jvstore realtime（開催日）で締め切り前のオッズを取り込んでください。",
}


class RequiredInfoCheck:
    """その時点で使う特徴量のうち、DB に無いと予測できないもの（馬番・馬場状態・馬体重・単勝オッズなど）が、
    全部の行で欠けていないかを確かめる。

    欠けたまま予測すると、学習のときと違う様子のデータをモデルに渡すことになる（設計書 07）。
    ``guidance`` は「特徴量の名前 → 欠けていたときの案内」。省略すると1頭ごとの予想の4つ。レース単位の予想は、
    レース単位の特徴量の名前（1番人気のオッズ など）で渡す（荒れ具合の設計書 06 の図2）。
    その予想に無い名前の列は、確認を素通りする。
    """

    def __init__(self, guidance: Mapping[str, str] | None = None) -> None:
        self._guidance = dict(HORSE_GUIDANCE if guidance is None else guidance)

    def check(self, features: pd.DataFrame) -> None:
        """欠けていれば、取り込み方の案内を付けて ``ValueError``。"""
        missing = [column for column in self._guidance if self._is_missing(features, column)]
        if missing:
            raise ValueError(self._guidance[missing[0]])

    def _is_missing(self, features: pd.DataFrame, column: str) -> bool:
        """その時点で使う列なのに、全部の行で欠損値か。"""
        return column in features.columns and bool(features[column].isna().all())
