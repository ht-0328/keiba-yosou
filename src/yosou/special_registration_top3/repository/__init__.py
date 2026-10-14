"""この予想だけのデータの読み書き（1 SQL につき 1 リポジトリ）。元DB は読むだけ。

共通のリポジトリ（事実表・出走の行・過去走・馬の力の材料・対戦レーティング・モデル など）は ``yosou.shared.repository``。

| リポジトリ | 読む・書くもの |
|---|---|
| ``RegistrationEntryTableRepository`` | 予測する1レースの登録馬に、事実表と同じ列と材料の締めの日を付けた一時表を作る（登録馬の行は ``tools/共通/registration.py``） |
| ``RegistrationRaceRepository`` | 開催日・競馬場・レース番号から、特別登録のレースの rid を引く |
| ``RegistrationListRepository`` | 期間の、特別登録のある平地のレースの一覧 |
| ``RegistrationEntryInfoRepository`` | 1レースの登録馬の、表に出す情報（調教師・負担重量・交流区分） |
"""

from .registration_entry_info_repository import CARRIED, EXCHANGE, TRAINER, RegistrationEntryInfoRepository
from .registration_entry_table_repository import TABLE, RegistrationEntryTableRepository
from .registration_list_repository import RegistrationListRepository
from .registration_race_repository import RegistrationRaceRepository

__all__ = [
    "RegistrationEntryTableRepository", "RegistrationRaceRepository", "RegistrationListRepository",
    "RegistrationEntryInfoRepository", "TABLE", "TRAINER", "CARRIED", "EXCHANGE",
]
