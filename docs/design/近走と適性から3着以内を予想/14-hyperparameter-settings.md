# 14 ハイパーパラメータを外から指定する

**この文書で決めること:** 木の数などのハイパーパラメータを、プログラムを書き換えずに外から指定する方法。

**結論: ハイパーパラメータは設定ファイル（TOML 形式）に書き、学習を始めるときにそのファイルを指定する。ファイルに書かなかった項目は、[12-lightgbm.md](12-lightgbm.md)・[13-catboost.md](13-catboost.md) の「2. ハイパーパラメータの初期値」を使う。**

- 用語の意味は [02-glossary.md](02-glossary.md) を参照。
- TOML は、`pyproject.toml` と同じ書き方の設定ファイルである。Python に読み込む機能（`tomllib`）が最初から入っていて、`#` でコメントも書ける。

## 設定ファイルの形

中身は初期値のままの例。変えたい項目だけを書き換える。

```toml
# 予想モデルのハイパーパラメータ。書かなかった項目は、設計書 12・13 の初期値を使う。

[lightgbm]
early_stopping_rounds = 100   # 検証データで、木を何本足しても良くならなければ止めるか
min_category_count = 2000     # 学習データでの出走がこれより少ないカテゴリの値は「その他」にまとめる

[lightgbm.params]             # LGBMClassifier の引数。書いたものがそのまま渡る
learning_rate = 0.05
n_estimators = 2000           # 木の数の上限
num_leaves = 31
min_child_samples = 100
subsample = 0.8
subsample_freq = 1
colsample_bytree = 0.8
random_state = 42

[catboost]
early_stopping_rounds = 100

[catboost.params]             # CatBoostClassifier の引数。書いたものがそのまま渡る
learning_rate = 0.05
iterations = 2000             # 木の数の上限
depth = 6
l2_leaf_reg = 3
random_seed = 42
```

| 表（`[ ]` の部分） | 書くもの |
|---|---|
| `[lightgbm]`・`[catboost]` | モデルの引数ではない設定（早期終了の本数、LightGBM の「その他」にまとめる出走数） |
| `[lightgbm.params]`・`[catboost.params]` | `LGBMClassifier`・`CatBoostClassifier` の引数。名前は 12・13 の表と同じ |

この例のファイルを読み込み、そのまま2つのモデルに渡して学習できることを確かめた（Python 3.12、lightgbm 4.7.0、catboost 1.2.10）。

## 決まり

| 決まり | 理由 |
|---|---|
| 学習のコマンドに `--config 設定ファイルのパス` を付けて指定する。付けなければ、初期値の設定ファイルを使う | 設定を変えて試すたびに、プログラムを書き換えずに済む |
| 12・13 の表に無い名前が書かれていたら、エラーにして止める | 書き間違えた項目が、黙って無視されるのを防ぐ |
| 目的関数（`objective`・`loss_function`）は、設定ファイルでは変えられない | 変えると、`predict_proba()` が「3着以内に入る確率」を返さなくなる |
| 3つの時点のモデルは、同じ設定で学習する | 時点ごとに変える必要が出たら、そのとき足す |
| 学習したモデルと一緒に、使った設定を保存する | あとで、どの設定で学習したモデルかが分かるようにする |

初期値の設定ファイルは `src/yosou/form_aptitude_top3/setting/default_settings.toml` に置く。設定ファイルを読む入口は `HyperparameterSettings` で、ファイルを読む（`SettingsFile`）・名前を確かめる（`SettingsNameCheck`）・初期値に重ねる（`SettingsOverlay`）を順に呼ぶ（[04-classes.md](04-classes.md)）。

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-21 |
| 確かめた版 | Python 3.12、lightgbm 4.7.0、catboost 1.2.10 |
