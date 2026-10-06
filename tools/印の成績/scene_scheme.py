"""場面の帯の区分（中央と地方で違うところ）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SceneScheme:
    """場面の表（表10）の、クラスと競馬場の帯の区分。中央と地方で、クラスの並び順の境目と、競馬場の分け方が違う。

    - ``class_bands``: クラスの帯の名前（低い順）。``class_edges`` はその境目（事実表の ``class_order``。「その値未満」が前の帯）。
    - ``venue_bands``: 競馬場の2つの帯の名前（``main_venues`` に入る競馬場, それ以外）。
    """

    name: str
    class_bands: tuple[str, ...]
    class_edges: tuple[int, ...]
    venue_bands: tuple[str, str]
    main_venues: frozenset[str]


#: 中央。クラスの並び順は 新馬 0・未出走 1・未勝利 2 / 1勝 3 / 2勝 4・3勝 5 / オープン 6・L 7 / 重賞 8〜。
#: 競馬場は主場（東京・中山・京都・阪神）とローカル（研究「既存モデルの改善」の条件で分ける実験と同じ）。
JRA_SCENE_SCHEME = SceneScheme(
    name="中央", class_bands=("新馬・未勝利", "1勝クラス", "2勝・3勝クラス", "オープン・L", "重賞"), class_edges=(3, 4, 6, 8),
    venue_bands=("主場", "ローカル"), main_venues=frozenset({"東京", "中山", "京都", "阪神"}),
)
#: 地方。クラスの並び順は 新馬 0・未勝利 1・年齢の条件戦 2 / C 3〜6 / B 7〜10 / A 11〜14・オープン 15 / 準重賞 16・重賞 17〜
#: （``tools/共通/local_codes.py`` の ``LOCAL_CLASS_ORDER``）。競馬場は南関東（浦和・船橋・大井・川崎）とそれ以外。
LOCAL_SCENE_SCHEME = SceneScheme(
    name="地方", class_bands=("新馬・未勝利・年齢の条件戦", "C", "B", "A・オープン", "重賞"), class_edges=(3, 7, 11, 16),
    venue_bands=("南関東", "それ以外"), main_venues=frozenset({"浦和", "船橋", "大井", "川崎"}),
)
#: 名前 → 区分（``mark_stats.py --scene``）。
SCENE_SCHEMES: dict[str, SceneScheme] = {scheme.name: scheme for scheme in (JRA_SCENE_SCHEME, LOCAL_SCENE_SCHEME)}
