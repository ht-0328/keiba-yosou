"""近走と適性から3着以内を予想する（設計書 ``docs/design/近走と適性から3着以内を予想/``）。

レースに出る1頭ずつについて「3着以内に入る確率」を、LightGBM と CatBoost の予測確率の平均で出す。
木曜・前日・当日の3つの時点ごとに、その時点で分かる特徴量だけで学習した別のモデルを使う
（木曜・前日は馬の力の材料、当日は今の材料に券種ごとのオッズから見た支持を足したもの。設計書 07）。

データを読む・特徴量を作る・学習する・予測するクラスは、ほかの予想と共通で ``yosou.shared``（設計書 04）。
この予想の予測は、道具「今週の予想」と予想「近走と適性からWIN5の買い目を決める」も同じ部品で出すので、特徴量の一覧
（``shared/feature/form_aptitude_catalog.py``）・``DatasetBuilder`` の組み立て（``shared/dataset/form_aptitude_assembly.py``）・
時点の並び（``shared/workflow/form_aptitude_timings.py``）・予測の流れの組み立て（``FormAptitudePrediction``）も ``yosou.shared`` にある。
予測用データに足す材料（P・S・T・U・V）を作る部品は ``yosou.form_aptitude_materials``。ここには、コマンドと初期値のファイルだけを置く。

| フォルダ | 中身 |
|---|---|
| ``command/`` | コマンド（train・predict）の引数。入口 |
| ``setting/`` | ハイパーパラメータの初期値のファイル |
| ``tests/`` | この予想の組み立てのテスト（共通の部品のテストは ``yosou.shared.tests``） |

決まり: 1ファイルに1クラス。1クラスに1つの仕事。SQL は ``yosou.shared.repository`` だけ。
参照の向きは一方向（``command`` → ``setting``）。``yosou.shared``・``yosou.form_aptitude_materials`` は参照してよいが、そちらからここを参照しない。
"""
