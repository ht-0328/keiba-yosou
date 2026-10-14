"""この予想が使う特徴量の一覧（設計書 09）。

手本（近走と適性から3着以内を予想）の材料と同じ構成に、K（重賞の傾向）の51個を足す（設計書 15 の 10）。

- 馬の力の材料（木曜・前日）: M（202個）・O（対戦レーティング。7個）と J（市場の評価。前日から）に K を足す（``ABILITY_CATALOG``）。
- 当日の材料: 手本の当日と同じ A〜L（79個）・N（券種ごとの支持。6個）・M のうち名前の重ならない 200個に、K を足す
  （``RACE_DAY_CATALOG``。336個）。

K の作り方は ``stakes_tendency_features.py``、切り口と成績の名前は ``tendency_cut.py``。
"""

from __future__ import annotations

from yosou.shared.feature import (
    ABILITY_FEATURES,
    BASE_FEATURES,
    HEAD_TO_HEAD_FEATURES,
    MARKET_FEATURES,
    PEOPLE_MARKET_FEATURES,
    POOL_SUPPORT_FEATURES,
    Feature,
    FeatureCatalog,
    FeatureKind,
)

from .tendency_cut import CUTS, RACE_LEVEL_NAMES, STATS

_N = FeatureKind.NUMERIC

#: K. 重賞の傾向（51個）。レース単位の3個（過去の開催の数、1番人気と1〜3番人気の複勝率）と、
#: 12個の切り口 × 4つの成績（「過去の開催で自分と同じ条件だった馬」の 出走数・複勝率・単勝回収率・複勝回収率）。
#: どれも、そのレースより前の開催だけから数えたそのレースの数字そのもの（設計書 09 の K）。
#: 枠・単勝オッズ・人気の切り口（12個）だけ、自分の帯が決まる前日から。
K_FEATURES: tuple[Feature, ...] = (
    *(Feature(name, "K", _N) for name in RACE_LEVEL_NAMES),
    *(Feature(cut.feature_name(stat), "K", _N, cut.known_from) for cut in CUTS for stat in STATS),
)

#: 手本の当日の材料のうち、M を除いた部分（A〜I・J・L の 79個と N の6個）。
_FORM_RACE_DAY_FEATURES: tuple[Feature, ...] = BASE_FEATURES + MARKET_FEATURES + PEOPLE_MARKET_FEATURES + POOL_SUPPORT_FEATURES

#: 当日のモデルが足す M（手本と同じく、A〜L・N と同じ名前の2つ（前走からの日数・芝ダ替わり）を除いた 200個）。
RACE_DAY_ABILITY_FEATURES: tuple[Feature, ...] = tuple(
    feature for feature in ABILITY_FEATURES
    if feature.name not in {feature.name for feature in _FORM_RACE_DAY_FEATURES}
)

#: 馬の力の材料の一覧（木曜・前日のモデル。手本と同じ M・O・J に K を足したもの。木曜は 199 + 39 = 238個、前日は 210 + 51 = 261個）。
ABILITY_CATALOG = FeatureCatalog(ABILITY_FEATURES + HEAD_TO_HEAD_FEATURES + MARKET_FEATURES + K_FEATURES)

#: 当日のモデルの一覧（手本の当日の 285個に K の51個を足した 336個）。
RACE_DAY_CATALOG = FeatureCatalog(_FORM_RACE_DAY_FEATURES + RACE_DAY_ABILITY_FEATURES + K_FEATURES)
