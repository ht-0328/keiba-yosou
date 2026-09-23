"""人気馬の「普段より危ない」の判定（既存モデルの修正計画の 1「人気馬の4着以下」）。

1番人気より4・5番人気のほうが普通に負けやすいので、「4着以下になる確率」の高さで危険と決めると、人気の低い馬ばかりが
危険になる。ここでは「危険度 = 4着以下になる確率 − オッズから見た4着以下の確率」（同じオッズの馬より、どれだけ
負けやすいか）で判定し、線は人気帯ごとに検証期間で決める。

| クラス | 仕事 |
|---|---|
| ``DangerThreshold`` | 人気帯ごとの危険度の線を、検証期間の結果で決める |
| ``DangerJudge`` | 予測の結果に、オッズから見た4着以下の確率・危険度・危険かを足す |
"""

from .danger_judge import BASE_OUT, DANGER, IS_DANGER, DangerJudge
from .danger_threshold import CANDIDATES, DangerThreshold

__all__ = ["DangerThreshold", "DangerJudge", "CANDIDATES", "BASE_OUT", "DANGER", "IS_DANGER"]
