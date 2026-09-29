# 14 ハイパーパラメータを外から指定する

**この文書で決めること:** 木の数などのハイパーパラメータを、プログラムを書き換えずに外から指定する方法。

**結論: 設定ファイル（TOML 形式）の形も、指定のしかたの決まりも、手本とまったく同じである。この予想で違うのは、初期値のファイルの置き場所と、初期値の中身（[12-lightgbm.md](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md](13-catboost.md#2-ハイパーパラメータの初期値) の値）だけである。**

- 設定ファイルの中身の例と、表（`[ ]` の部分）の説明は [手本の 14 の「設定ファイルの形」](../近走と適性から3着以内を予想/14-hyperparameter-settings.md#設定ファイルの形) を参照。
- `--config` での指定、書き間違いをエラーにする、目的関数は変えられない、使った設定をモデルと一緒に保存する、の決まりは [手本の 14 の「決まり」](../近走と適性から3着以内を予想/14-hyperparameter-settings.md#決まり) を参照。
- 用語の意味は [02-glossary.md](02-glossary.md) を参照。

## この予想で違う点

| 項目 | 手本 | この予想 |
|---|---|---|
| 初期値の設定ファイルの置き場所 | `src/yosou/form_aptitude_top3/setting/default_settings.toml` | `src/yosou/stakes_tendency_top3/setting/default_settings.toml` |
| 初期値の中身 | 手本の 12・13 の表 | この予想の 12・13 の表（`learning_rate` 0.03、`n_estimators`・`iterations` 3000、`num_leaves` 15、`min_child_samples` 50、`depth` 5、`l2_leaf_reg` 5、`min_category_count` 300。ほかは手本と同じ） |
| 同じ設定で学習するモデルの数 | 3つの時点（木曜・前日・当日） | 手本と同じ3つの時点（[07-prediction-timing.md](07-prediction-timing.md)） |
| 設定ファイルを読むクラス | 共通の `src/yosou/shared/setting/` | 同じ（[04-classes.md の 1](04-classes.md#1-共通の部品とこの予想だけの部品の分け方)） |

項目の名前は手本と同じで、書き方の決まりは共通の部品（ファイルを読む・名前を確かめる・初期値に重ねる）が1か所で守る。初期値のファイルだけがこの予想のもので、値を見直すときはこのファイルを書き換える（見直しの手順は [16-evaluation.md の 5](16-evaluation.md#5-ハイパーパラメータの調整のやり方)）。

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-29 |
| 確かめた版 | 手本と同じ（Python 3.12、lightgbm 4.7.0、catboost 1.2.10）。設定ファイルの形を変えていないので、確かめ直していない |
