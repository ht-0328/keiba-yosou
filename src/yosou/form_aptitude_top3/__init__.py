"""近走と適性から3着以内を予想する（設計書 ``docs/design/近走と適性から3着以内を予想/``）。

レースに出る1頭ずつについて「3着以内に入る確率」を、LightGBM と CatBoost の予測確率の平均で出す。
木曜・前日・当日の3つの時点ごとに、その時点で分かる特徴量だけで学習した別のモデルを使う。

| フォルダ | 中身 |
|---|---|
| ``command/`` | コマンド（train・predict）の引数と、結果の表 |
| ``workflow/`` | 学習の流れ・予測の流れ（ほかを順に呼ぶだけ） |
| ``evaluation/`` | 当たり具合を測る |
| ``ml_model/`` | 機械学習のモデル（LightGBM・CatBoost・エンコーダー・平均） |
| ``dataset/`` | 学習データ・予測用データを作る（記録を集める・行を選ぶ・目的変数・期間で分ける） |
| ``feature/`` | 特徴量 68個を作る（一覧・時点・まとまり A〜I） |
| ``repository/`` | データの読み書き。1 SQL につき 1 リポジトリ。学習済みモデルのファイルも |
| ``setting/`` | ハイパーパラメータの設定ファイル |

決まり: 1ファイルに1クラス。1クラスに1つの仕事。SQL は ``repository/`` だけ。
参照の向きは上から下へ一方向（``command`` → ``workflow`` → ``evaluation`` → ``ml_model`` → ``dataset`` → ``feature``。
``dataset`` と ``workflow`` は ``repository`` を、``ml_model`` と ``repository`` は ``setting`` を使う）。
"""
