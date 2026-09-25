"""1つのグループの馬を覚え、そのグループへの近さの点数を出す。"""

from __future__ import annotations

import numpy as np
from sklearn.neighbors import NearestNeighbors

#: 近さを測るのに要る、グループのいちばん少ない頭数（自分を除いて1頭は比べる相手が要る）。
MIN_GROUP_ROWS = 2


class GroupSimilarity:
    """1つのグループ（勝利・馬券内・馬券外のどれか）の近さのモデル（設計書 12・13）。k近傍法。

    モデルが覚えるのは、そのグループの馬だけである。対象の馬の「近さ」は、そのグループで似ている k頭との
    平均の距離で測る。距離のままでは、頭数の多いグループほど似た馬が見つかりやすく、近く出てしまう。
    そこで、同じ単位の1番人気全員（3つのグループを合わせた学習データ）についても同じ距離を出しておき、
    対象の馬の距離がその中のどこに来るかを点数（0〜100）にする。点数 70 なら「この単位の1番人気の 70% より、
    このグループに近い」。3つのグループを同じ顔ぶれと比べるので、点数どうしを比べられる。
    学習データの馬がそのグループの馬なら、自分自身は似ている馬から除いて距離を出す。
    """

    def __init__(self, k: int) -> None:
        self._requested_k = k
        self._k = k
        self._neighbors = NearestNeighbors()
        self._reference = np.empty(0)

    def fit(self, matrix: np.ndarray, is_member: np.ndarray) -> GroupSimilarity:
        """``matrix`` は単位の1番人気全員の行列、``is_member`` はそのうちこのグループの馬か（行ごとの真偽）。

        グループの馬が少なすぎれば ``ValueError``。
        """
        members = matrix[is_member]
        if len(members) < MIN_GROUP_ROWS:
            raise ValueError(f"近さを測るには、グループに {MIN_GROUP_ROWS}頭以上が要ります（{len(members)}頭）")
        self._k = min(self._requested_k, len(members) - 1)
        self._neighbors = NearestNeighbors(n_neighbors=self._k + 1).fit(members)
        distances, _ = self._neighbors.kneighbors(matrix)
        # グループの馬は、いちばん近いのが自分自身（距離 0）なので、2番目から k頭を使う
        own = distances[:, 1:].mean(axis=1)
        other = distances[:, :self._k].mean(axis=1)
        self._reference = np.sort(np.where(is_member, own, other))
        return self

    @property
    def k(self) -> int:
        """実際に使う k（グループの頭数 − 1 を超えない）。"""
        return self._k

    def distances(self, matrix: np.ndarray) -> np.ndarray:
        """対象の馬ごとの、そのグループで似ている k頭との平均の距離。"""
        distances, _ = self._neighbors.kneighbors(matrix, n_neighbors=self._k)
        return distances.mean(axis=1)

    def scores(self, matrix: np.ndarray) -> np.ndarray:
        """対象の馬ごとの近さの点数（0〜100）。単位の1番人気のうち、対象の馬と同じか、より遠い馬の割合。"""
        nearer = np.searchsorted(self._reference, self.distances(matrix), side="left")
        return 100.0 * (len(self._reference) - nearer) / len(self._reference)
