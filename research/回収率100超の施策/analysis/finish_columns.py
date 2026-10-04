"""勝ち切る材料（まとまり Q）の列の名前と特徴量の一覧（予想のパッケージに移したものを、研究の名前で引く）。"""

from __future__ import annotations

from yosou.shared.feature import FINISH_POWER_FEATURES, FINISH_POWER_NAMES
from yosou.shared.repository import HORSE_FINISH_NAMES, PEOPLE_FINISH_NAMES

#: 馬の近10走から作る列（``HorseFinishRepository``）と、騎手・調教師の近1年から作る列（``PeopleFinishRepository``）。
HORSE_NAMES: tuple[str, ...] = HORSE_FINISH_NAMES
PEOPLE_NAMES: tuple[str, ...] = PEOPLE_FINISH_NAMES
FINISH_NAMES: tuple[str, ...] = FINISH_POWER_NAMES
#: 特徴量の一覧（どれも数値。過去の記録だけから作るので木曜から分かる。まとまりの記号は Q）。
FINISH_FEATURES = FINISH_POWER_FEATURES
