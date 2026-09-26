# 14 ハイパーパラメータを外から指定する

**この文書で決めること:** 木の数などのハイパーパラメータを、プログラムを書き換えずに外から指定する方法。

**結論: 設定ファイル（TOML 形式）の形も、指定のしかたの決まりも、手本とまったく同じである。この予想で違うのは、初期値のファイルの置き場所と、1つの設定ファイルで8種類のモデルを学習すること、予想ごとに目的関数が違うことである。予想ごとに設定を変える仕組みは作っていない（8種類のモデルで同じ設定を使う）。年ごとの確かめ（`backtest`）は、速さのために学習率を上げた設定ファイル（`setting/backtest_settings.toml`）を既定で使う。**

- 設定ファイルの中身の例と、表（`[ ]` の部分）の説明は [手本の 14 の「設定ファイルの形」](../近走と適性から3着以内を予想/14-hyperparameter-settings.md#設定ファイルの形) を参照。
- `--config` での指定、書き間違いをエラーにする、目的関数は変えられない、使った設定をモデルと一緒に保存する、の決まりは [手本の 14 の「決まり」](../近走と適性から3着以内を予想/14-hyperparameter-settings.md#決まり) を参照。
- 用語の意味は [02-glossary.md](02-glossary.md) を参照。

## この予想で違う点

| 項目 | 手本 | この予想 |
|---|---|---|
| 初期値の設定ファイルの置き場所 | `src/yosou/form_aptitude_top3/setting/default_settings.toml` | `src/yosou/race_development/setting/default_settings.toml` |
| 1つの設定ファイルで学習するモデル | 3つの時点 × 2つのライブラリ | 8種類 × 3つの時点 × 2つのライブラリ。どの予想も同じ `[lightgbm.params]`・`[catboost.params]` を使う。年ごとの確かめ（`backtest`）も、同じ設定ファイルを `--config` で受け取る |
| 目的関数（設定ファイルでは変えられない） | `binary` / `Logloss` | 予想ごとに決まっている（[12-lightgbm.md](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md](13-catboost.md#2-ハイパーパラメータの初期値)）。多クラスの `num_class` と、分位点の `alpha`（0.1・0.5・0.9）も書かない |
| 分位点回帰のモデルに渡す引数 | ― | `[lightgbm.params]`・`[catboost.params]` を、`LGBMRegressor`・`CatBoostRegressor` にもそのまま渡す。分類と回帰で同じ名前の引数（`learning_rate`・`n_estimators`・`depth` など）だけを初期値にしてあるので、そのまま渡せる |
| 設定ファイルを読むクラス | 共通の `src/yosou/shared/setting/` | 同じ |

**年ごとの確かめの設定。** 年ごとの確かめでは、1年につき 18 のモデルを、7〜9年ぶん学習し直す。初期値のままだと1日近くかかるので、`backtest` は `--config` を省略すると `src/yosou/race_development/setting/backtest_settings.toml` を使う。書いてあるのは、初期値から置き換える項目だけである。

| 項目 | 初期値 | 年ごとの確かめの既定 |
|---|---|---|
| `learning_rate`（LightGBM・CatBoost） | 0.05 | 0.1 |
| 木の数の上限（`n_estimators`・`iterations`） | 2000 | 1000 |
| 早期終了（`early_stopping_rounds`） | 100 | 50 |

使った設定は、年ごとの確かめの結果の表（「確かめの条件」）に書く。学習（`train`）は初期値を使うので、予測に使うモデルと、年ごとの確かめのモデルは、設定が少し違う。

**予想ごとに設定を変えたくなったとき。** 設定ファイルに予想ごとの表（`[pace.lightgbm.params]` のようなもの）は作っていない。予想ごとに設定が違うことが当たり前になったら、そのとき足す。

**設定ファイルに書かないもの。** 次の値は、モデルのハイパーパラメータではなく、特徴量や目的変数の作り方の値なので、それぞれのクラスの定数にする。変えたら、学習データを作り直す。

| 値 | 初期値 | 置き場所 |
|---|---|---|
| 先頭率・先団率の平滑化の α | 3 | `SmoothedRate`（[09-features.md の K](09-features.md#k-序盤の位置取りの履歴15個)） |
| 日数の重みの半減期 | 180日 | `EarlyRunSummary` |
| 前半タイムの基準の件数の下限・標準偏差の下限 | 30 レース・0.1秒 | `PaceBaseline`（[10-target.md の 5.](10-target.md#5-前半タイムの基準の作り方)） |
| ペースの区分の線引き | z = ±0.5 | `RaceLabeler` |
| 温度の候補 | 0.50〜2.00 の 0.01 刻み | `TemperatureFitter` |
| 2着・3着の割り当てのならしの指数 λ の候補 | 0.50〜1.00 の 0.05 刻み | `OrderLambdaFitter`（[10-target.md の 10.](10-target.md#10-着順の目的変数と確率の出し方)） |
| 後半タイムの基準の件数の下限・標準偏差の下限 | 30 レース・0.1秒（前半と同じ） | `PaceBaseline` |
| 期待値で買う線 | 1.0 | `ExpectedValueTicketRule`（[16-evaluation.md の 8.](16-evaluation.md#8-券種ごとの買い方)）。設定ファイルには書かない。変えるときは、変えたことを結果に書く |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-26 |
| 更新 | 2026-09-26 8種類のモデルと、後半・着順・買い方の定数を足した |
| 更新 | 2026-09-26 年ごとの確かめの設定を足し、作っていない `--kind` の記述を消した |
| 確かめた版 | 設定ファイルの形は手本と同じ（Python 3.12、lightgbm 4.7.0、catboost 1.2.10）。手本の初期値の引数をそのまま `LGBMRegressor(objective="quantile")`・`CatBoostRegressor(loss_function="MultiQuantile:…")` に渡し、早期終了付きで学習できることを、架空のデータで確かめた（2026-09-26。lightgbm 4.7.0、catboost 1.2.10） |
