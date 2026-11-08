"""今のモデル（予想「近走と適性から3着以内を予想」）の予測用データに足す材料（P・S・T・U・V）を作る部品。

今のモデルの予測の流れ（``yosou.shared.workflow`` の ``FormAptitudePrediction``）は ``shared`` にあるが、材料を作る部品は
予想「展開から着順を予想」（``yosou.race_development``）の保存したモデルと、材料のパッケージ（``ability_score``・``development_score``・
``track_bias``・``weight_table``）を使うので、``shared`` には置けない（``shared`` から予想のパッケージを参照しない決まり）。
そこで、``shared`` の決まり（``FormAptitudeMaterials``）を守るクラスをここに置き、今のモデルのパッケージ・道具・
予想「近走と適性からWIN5の買い目を決める」が ``FormAptitudePrediction`` に渡す（設計書「近走と適性からWIN5の買い目を決める」04 の 1）。

| クラス | 仕事 |
|---|---|
| ``MaterialAttachers`` | 予測用データに材料（P・S・T・U・V）を足す関数を作る。S と U の部品は作るのに時間がかかるので、1回の予測で1つだけ作り、3着以内と1着のモデルで使い回す |

使い方: ``FormAptitudePrediction(models, lambda con: MaterialAttachers(con, development_root))``。
参照の向きは一方向: ここ → 材料のパッケージ・``yosou.race_development``・``yosou.shared``。予想のパッケージ（``form_aptitude_top3`` など）は参照しない。
"""

from .material_attachers import MaterialAttachers

__all__ = ["MaterialAttachers"]
