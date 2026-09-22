"""3つの予想（``form_aptitude_top3``・``favorites_out_of_top3``・``longshots_in_top3``）から使う共通の部品。

同じ仕事のクラスを予想ごとに複製しないために、ここに置く。予想ごとに違うところは、インターフェース
（``SampleSelector``・``TargetLabeler``・``FeatureGroup``）を守るクラスと、特徴量の一覧（``FeatureCatalog``）と、
ハイパーパラメータの初期値のファイルにして、予想のパッケージから渡す。

| フォルダ | 中身 |
|---|---|
| ``command/`` | コマンドの部品のうち、予想に依らないもの（共通の引数・結果の表） |
| ``workflow/`` | 学習の流れ（``TrainingWorkflow``）。予測の流れは予想ごとなので入れない |
| ``evaluation/`` | 当たり具合を測る。学習の結果の入れ物 |
| ``ml_model/`` | 機械学習のモデル（LightGBM・CatBoost・エンコーダー・平均） |
| ``dataset/`` | 学習データ・予測用データを作る（記録を集める・期間で分ける・予測のときの人気を決める・3着以内の目的変数） |
| ``feature/`` | 特徴量を作る（まとまり A〜J と、過去の記録から数える部品） |
| ``repository/`` | データの読み書き。1 SQL につき 1 リポジトリ。学習済みモデルのファイルも |
| ``setting/`` | ハイパーパラメータの設定ファイルを読む（初期値のファイルは予想ごと） |
| ``tests/`` | 共通の部品のテストと、テスト用の合成DB（``synthetic_season/``） |

決まり: **``shared`` から予想のパッケージ（``form_aptitude_top3`` など）を参照しない。**
参照の向きは上から下へ一方向（``command`` → ``workflow`` → ``evaluation`` → ``ml_model`` → ``dataset`` → ``feature``。
``dataset`` は ``repository`` を、``ml_model`` と ``repository`` は ``setting`` を使う）。
"""
