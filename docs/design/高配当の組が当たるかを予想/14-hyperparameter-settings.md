# 14 ハイパーパラメータを外から指定する

**この文書で決めること:** 木の数などのハイパーパラメータを、プログラムを書き換えずに外から指定する方法。

**結論: 設定ファイル（TOML 形式）の形と、指定のしかたの決まりは、手本と同じである。初期値のファイルだけは、この予想のもの（`src/yosou/high_payout_combos/setting/default_settings.toml`）を持つ。初期値が手本と違うためである。**

- 表（`[ ]` の部分）の説明は [手本の 14 の「設定ファイルの形」](../近走と適性から3着以内を予想/14-hyperparameter-settings.md#設定ファイルの形) を参照。
- `--config` での指定、書き間違いをエラーにする、目的関数は変えられない、使った設定をモデルと一緒に保存する、の決まりは [手本の 14 の「決まり」](../近走と適性から3着以内を予想/14-hyperparameter-settings.md#決まり) を参照。
- 用語の意味は [02-glossary.md](02-glossary.md) を参照。

## 設定ファイルの形

中身は、この予想の初期値のままの例。変えたい項目だけを書いたファイルを作り、`--config` で渡す。

```toml
# 予想「高配当の組が当たるかを予想」のハイパーパラメータ。書かなかった項目は、設計書 12・13 の初期値を使う。

[lightgbm]
early_stopping_rounds = 100   # 検証データで、木を何本足しても良くならなければ止めるか
min_category_count = 2000     # カテゴリ特徴量が無いので、この予想では何も変えない（共有の設定の形に合わせて置く）

[lightgbm.params]             # LGBMClassifier の引数。書いたものがそのまま渡る
learning_rate = 0.03
n_estimators = 3000           # 木の数の上限
num_leaves = 31
min_child_samples = 300
colsample_bytree = 0.5
subsample = 0.7
subsample_freq = 1
reg_lambda = 20
max_bin = 127
random_state = 0
n_jobs = 3                    # 使うスレッドの数（結果ではなく、速さと PC の空きのための設定）

[catboost]
early_stopping_rounds = 100

[catboost.params]             # CatBoostClassifier の引数。書いたものがそのまま渡る
learning_rate = 0.05
iterations = 3000             # 木の数の上限
depth = 6
l2_leaf_reg = 10
rsm = 0.5
border_count = 128
bootstrap_type = "Bernoulli"
subsample = 0.7
random_seed = 0
thread_count = 3              # 使うスレッドの数
```

値の意味と理由は [12-lightgbm.md の 2](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md の 2](13-catboost.md#2-ハイパーパラメータの初期値) を参照。

## この予想で違う点

| 項目 | 手本 | この予想 |
|---|---|---|
| 初期値の設定ファイル | `src/yosou/form_aptitude_top3/setting/default_settings.toml` | `src/yosou/high_payout_combos/setting/default_settings.toml`（値が手本と違う） |
| 設定を渡すコマンド | `train` | `train`（本番のモデル）と `walk`（年ごとの確かめ） |
| モデルごとの設定 | 3つの時点のモデルを同じ設定で学ぶ | 5つの券種のモデルを同じ設定で学ぶ。券種ごとに変える必要が出たら、そのとき足す |
| 学習したモデルと使った設定の置き場所 | `reports/近走と適性から3着以内を予想/models/` | `reports/高配当の組が当たるかを予想/models/<券種の英名>/race_day/`（[12-lightgbm.md の 6](12-lightgbm.md#6-保存)） |
| 設定ファイルに書かないもの | ― | オッズの帯・期待値の線・外れの組を残す割合。予想の決まりなので、コードの定数に置く（[04-classes.md](04-classes.md#2-この予想だけのクラス)） |

設定ファイルを読む入口は、共有の `HyperparameterSettings`（`src/yosou/shared/setting/`）である。

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-11-24 |
| 確かめた版 | Python 3.14.7、lightgbm 4.7.0、catboost 1.2.10、pandas 3.0.6。上の例を読み込み、出発点と行の重みを付けた乱数の架空データで、そのまま2つのモデルに渡して学習・予測できることを確かめた |
