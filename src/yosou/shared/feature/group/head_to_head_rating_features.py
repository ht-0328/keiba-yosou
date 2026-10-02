"""O. 対戦レーティング（7個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_records import EntryRecords
from ..head_to_head import RatingTableBuilder


class HeadToHeadRatingFeatures:
    """O. 対戦レーティング（名前は ``HEAD_TO_HEAD_NAMES``）。``FeatureGroup`` を守る。

    同じレースを走った馬どうしの着順の勝ち負けから、Elo のレーティングを開催日の順に更新して作る。着順の良い馬・着差の
    大きい馬を直接見るのではなく、「誰に勝って誰に負けたか」を見るので、強い相手に負けた馬と弱い相手に勝った馬を見分けられる。
    レーティングの値・レース内の順位と偏差・レースの平均との差・前走と近5走の変化・対戦数の7個。過去のレースの結果だけから
    作るので、木曜から分かる。元の記録は ``records.head_to_head_runs``（``HeadToHeadRunRepository`` が読む）。
    読んでいなければ（空の表）全部欠損値。作り方は ``feature/head_to_head/`` の部品。
    """

    def build(self, records: EntryRecords) -> pd.DataFrame:
        return RatingTableBuilder().build(records.entries, records.head_to_head_runs)
