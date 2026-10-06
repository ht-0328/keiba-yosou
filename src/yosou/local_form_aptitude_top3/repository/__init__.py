"""地方の元DB の表の決めごと。SQL そのものは ``yosou.shared.repository`` にあり、ここには欄の決めごとだけを置く。

| 名前 | 仕事 |
|---|---|
| ``LOCAL_CAREER_LAYOUT`` | 出走別着度数地方（``nd``）の欄の決めごと（通算は総合着回数、競馬場別は地方 14場のダートと盛岡の芝、距離帯は 1000以下〜2201以上） |
"""

from .local_career_layout import LOCAL_CAREER_LAYOUT

__all__ = ["LOCAL_CAREER_LAYOUT"]
