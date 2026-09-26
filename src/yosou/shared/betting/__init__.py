"""馬券の券種。予想に依らない、券種ごとの決まりごと（元DB の表の名前・組の形・順番を問うか）。

| クラス | 仕事 |
|---|---|
| ``TicketType`` | 7つの券種（単勝・複勝・馬連・馬単・ワイド・3連複・3連単）を表す値。表の名前や組の形は ``spec`` |
| ``TicketTypeSpec`` | 券種ごとの決まりごと（払戻・オッズの表、馬番か組番の列、馬の数、着順を区別するか、オッズが幅で出るか） |

``TICKET_TYPE_CHOICES`` は券種の書き方の案内（コマンドの説明と、誤りの文面に使う）。
買い目の作り方と精算は、予想ごとに決まりが違うので、予想のパッケージの側に置く。
"""

from .ticket_type import TICKET_TYPE_CHOICES, TicketType
from .ticket_type_spec import TicketTypeSpec

__all__ = ["TicketType", "TicketTypeSpec", "TICKET_TYPE_CHOICES"]
