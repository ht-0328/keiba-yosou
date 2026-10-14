"""オッズを使わない予想のための、予測に使うオッズを決めない部品。"""

from __future__ import annotations

from yosou.shared.dataset import OddsInput


class NoOddsResolver:
    """``PredictionWorkflow`` の「予測に使うオッズを決める」段の代わり。いつも None（オッズ無し）を返す。

    特別登録の時点にはオッズが無く、この予想はオッズを特徴量にも基準にも使わない（設計書 07）。
    """

    def resolve(self, race_id: str, given: OddsInput | None) -> None:
        return None
