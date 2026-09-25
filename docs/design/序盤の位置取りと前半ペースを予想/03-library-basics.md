# 03 LightGBM と CatBoost（と pandas）の使い方

**この文書の目的:** 設計を読む前に、LightGBM と CatBoost（と、表を扱う pandas）で何ができるかを知っておく。

**この文書で示すこと: 使う道具は手本の予想と同じ（LightGBM・CatBoost・pandas・scikit-learn）である。道具の基本の説明は書かず、[手本の 03](../近走と適性から3着以内を予想/03-library-basics.md) を参照する。この予想で足すのは、①二値分類の確率をレースの中で合計 1 にそろえる計算、②多クラス分類（3クラス）、③分位点回帰、の3つである。**

同じ説明を2つのフォルダに写すと、片方だけ直したときに食い違う。そのため、この文書は入口と、この予想で足す点だけを持つ。

## 1. 手本の 03 のどこに何が書いてあるか

| 知りたいこと | 手本の節 |
|---|---|
| 入れるパッケージ（`lightgbm`・`catboost`・`scikit-learn`・`pandas`） | [1. 準備](../近走と適性から3着以内を予想/03-library-basics.md#1-準備) |
| 表（`DataFrame`）の作り方、列の型、欠損値 | [2. pandas の使い方](../近走と適性から3着以内を予想/03-library-basics.md#2-pandas-の使い方) |
| 2つのモデルに共通の流れ（モデルを作る → `fit()` → `predict_proba()`） | [3. 2つに共通する使い方](../近走と適性から3着以内を予想/03-library-basics.md#3-2つに共通する使い方) |
| LightGBM のコード例と機能（カテゴリ型・早期終了・保存） | [4. LightGBM の使い方](../近走と適性から3着以内を予想/03-library-basics.md#4-lightgbm-の使い方) |
| CatBoost のコード例と機能（`cat_features`・早期終了・保存） | [5. CatBoost の使い方](../近走と適性から3着以内を予想/03-library-basics.md#5-catboost-の使い方) |
| 多クラス分類（`multiclass`・`MultiClass`、`predict_proba()` が列を3つ以上返す、2つの表の平均） | [荒れ具合の 03 の「この予想で違う点」](../レースの荒れ具合を4段階で予想/03-library-basics.md#この予想で違う点)。この予想では 4クラスではなく 3クラス（`num_class=3`）で使う |

この予想で足す pandas の操作は、`groupby("レースID")` で、レースごとに最大・合計を出して各行に戻す `transform()` である。下の 2. で使う。

## 2. 先頭の確率をレースの中で合計 1 にそろえる

**何をするか。** 予想①は、1頭ずつ「先頭になるか（1 か 0）」を二値分類で学習する。二値分類の確率は1頭ずつ別に出るので、1レースで足しても 1 にならない。先頭になる馬は1レースに1頭なので、レースの中で合計 1 になるように直す。

**どう直すか。** 確率を raw スコア（`log(p / (1 − p))`）に戻し、温度で割ってから、レースごとにソフトマックスで合計 1 の確率にする。温度は、学習に使わなかったデータ（検証データの後半。[16-evaluation.md](16-evaluation.md#1-期間の分け方)）で、レースごとのログ損失がいちばん小さくなる値を 0.50〜2.00 の 0.01 刻みから選ぶ。

次のコードで、乱数で作った架空のレースのデータを使って動くことを確かめた（2026-09-26。lightgbm 4.7.0、catboost 1.2.10、scikit-learn 1.9.1、pandas 3.0.6）。

```python
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier

def softmax_in_race(raw, race_ids, temperature):
    """raw スコアを温度で割り、レースごとに合計 1 の確率に直す。"""
    s = pd.Series(raw / temperature)
    s = s - s.groupby(race_ids).transform("max")        # 大きな数の exp であふれないよう、レースの最大を引く
    e = np.exp(s)
    return (e / e.groupby(race_ids).transform("sum")).to_numpy()

def race_log_loss(prob, is_leader):
    """実際に先頭になった馬に付けた確率の −log を、レースで平均する。"""
    return float(-np.log(prob[is_leader == 1]).mean())

# X_train・y_train: 学習データ（1行 = 1頭、y は先頭なら 1）。X_calib・y_calib・race_calib: 温度を決める用のデータとそのレースID
model = LGBMClassifier(objective="binary", learning_rate=0.05, n_estimators=200, verbose=-1)
model.fit(X_train, y_train)
p = model.predict_proba(X_calib)[:, 1]                  # 1頭ずつの「先頭になる確率」。レースの合計は 1 にならない
raw = np.log(p / (1 - p))                               # raw スコアに戻す（predict_proba(X, raw_score=True) と同じ値）

temperatures = np.round(np.arange(0.50, 2.001, 0.01), 2)  # 0.50〜2.00 の 0.01 刻み
losses = [race_log_loss(softmax_in_race(raw, race_calib, t), y_calib) for t in temperatures]
best = temperatures[int(np.argmin(losses))]
prob = softmax_in_race(raw, race_calib, best)           # レースの合計が 1 の「先頭になる確率」
```

| 何を確かめたか | 結果 |
|---|---|
| `log(p / (1 − p))` と、LightGBM の `predict_proba(X, raw_score=True)` が同じ値か | 同じ（CatBoost の `predict(X, prediction_type="RawFormulaVal")` とも同じ） |
| 直した確率の、レースごとの合計 | どのレースも 1 |
| レースごとのログ損失 | 12頭立ての架空のデータで、全馬に同じ確率（1/12）を付けたときより小さくなった。確率を単純に合計で割っただけのときより、温度を選んだほうが小さくなった |

- raw スコアに戻すのは、2つのライブラリで同じ計算にするためである。`predict_proba()` の値から戻せるので、手本の `LightGbmModel`・`CatBoostModel` を書き換えずに使える。
- 温度を決めるデータは、木の数を決める（早期終了）データと分ける。同じデータで両方を決めると、確率が実際より当たって見える（[16-evaluation.md](16-evaluation.md#1-期間の分け方)）。
- LightGBM と CatBoost は、それぞれ自分の温度でそろえてから平均する。合計 1 の確率どうしの平均なので、平均も合計 1 になる。

**比べる候補: CatBoost の `QuerySoftMax`。** CatBoost には、はじめから「1レースを1グループとして、グループの中で合計 1 になる確率」を学習する目的関数（`CatBoostRanker(loss_function="QuerySoftMax")` に、`Pool(X, y, group_id=レースID)` を渡す）がある。架空のデータで動くことを確かめた。LightGBM には同じものが無く、2つのライブラリでやり方がそろわないので、最初の作り方にはしない（[15-decisions.md](15-decisions.md#1-先頭の確率の作り方)）。

## 3. 前半タイムの分位点回帰

**何をするか。** 予想③の前半タイムは、「基準との差（秒）」の 10%・50%・90% の分位点を当てる。50% の値を予測の秒数にし、10% から 90% までを 80% の予測区間にする。

```python
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor

# X_race_train: 1行 = 1レースの特徴量、y_diff_train: 前半タイムの基準との差（秒）。X_race_new: 予測したいレース
quantiles = {}
for alpha in (0.1, 0.5, 0.9):                           # LightGBM は分位点ごとに1つのモデル（3つ）
    m = LGBMRegressor(objective="quantile", alpha=alpha, learning_rate=0.05, n_estimators=200, verbose=-1)
    m.fit(X_race_train, y_diff_train)
    quantiles[alpha] = m.predict(X_race_new)
lgb_q = np.column_stack([quantiles[0.1], quantiles[0.5], quantiles[0.9]])   # 行数 × 3

cb = CatBoostRegressor(loss_function="MultiQuantile:alpha=0.1,0.5,0.9",       # CatBoost は1つのモデルで3つを出す
                       learning_rate=0.05, iterations=500, verbose=0, allow_writing_files=False)
cb.fit(X_race_train, y_diff_train)
cb_q = cb.predict(X_race_new)                           # 行数 × 3

mean_q = np.sort((lgb_q + cb_q) / 2, axis=1)            # 2つを平均し、小さい順に並べ直す（10% の値が 90% の値を超えないように）
```

`mean_q` は、次のような3列の表である（架空の3レース。単位は秒で、マイナスは基準より速い）。

```text
[[-2.05 -1.48 -1.31]    ← 10% の値 −2.05、真ん中 −1.48、90% の値 −1.31
 [-2.35 -1.53 -1.20]
 [-2.06 -1.46 -1.25]]
```

| 手本（二値分類） | 前半タイム（分位点回帰） |
|---|---|
| `LGBMClassifier(objective="binary")` / `CatBoostClassifier(loss_function="Logloss")` | `LGBMRegressor(objective="quantile", alpha=…)` を3つ / `CatBoostRegressor(loss_function="MultiQuantile:alpha=0.1,0.5,0.9")` を1つ |
| `predict_proba()` の2列目を使う | `predict()` が秒を返す。LightGBM は3つのモデルの値を横に並べ、CatBoost は1つのモデルが3列を返す |
| 2つの確率の平均 | 2つの表（行数 × 3）の平均。平均したあと、行ごとに小さい順に並べ直す |

- 動かして分かったこと: 架空のデータでは、80% の予測区間に実際の値が入った割合（包含率）は 64% で、80% に届かなかった。分位点回帰の区間は、学習データに合わせすぎて狭くなりやすい。本番のデータでも包含率を測り、足りなければ直し方を決める（[16-evaluation.md](16-evaluation.md#2-評価指標)）。
- 平均絶対誤差（MAE）は、基準だけを出す（差 0 と予測する）ときより小さくなった。
- 確かめたスクリプトは JV-Data を使っていない。出力の数字も、乱数のデータのものである。

## 4. この予想で使う機能と、書いてある文書

| この予想でやること | 使う機能 | この予想での使い方 |
|---|---|---|
| 過去のレースで学習する（3つの予想） | `fit()` | [05-sequence.md](05-sequence.md#図1-学習)、[12-lightgbm.md](12-lightgbm.md#4-学習のやりとりシーケンス図)・[13-catboost.md](13-catboost.md#4-学習のやりとりシーケンス図) |
| 学習しすぎを防ぐ | 検証データと早期終了 | [12-lightgbm.md](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md](13-catboost.md#2-ハイパーパラメータの初期値) |
| 先頭の確率をレースの中で合計 1 にする | raw スコア・ソフトマックス・温度 | 上の 2.、[05-sequence.md](05-sequence.md#図3-先頭の確率をレースの中でそろえる) |
| 序盤の位置・ペースの区分の確率を出す | 多クラス分類（3クラス） | [12-lightgbm.md](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md](13-catboost.md#2-ハイパーパラメータの初期値) |
| 前半タイムの秒数と幅を出す | 分位点回帰 | 上の 3.、[12-lightgbm.md](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md](13-catboost.md#2-ハイパーパラメータの初期値) |
| 競馬場・騎手などを扱う | カテゴリ特徴量の指定 | [12-lightgbm.md](12-lightgbm.md#1-学習データの渡し方)・[13-catboost.md](13-catboost.md#1-学習データの渡し方) |
| 学習したモデルを、レース当日まで取っておく | 保存と読み込み | [12-lightgbm.md](12-lightgbm.md#6-保存)・[13-catboost.md](13-catboost.md#6-保存) |
| 当たり具合を測る | scikit-learn の `log_loss`・`accuracy_score`・`f1_score(average="macro")`・`mean_absolute_error`・`mean_pinball_loss` | [16-evaluation.md](16-evaluation.md#2-評価指標) |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-26 |
| 確かめた版 | lightgbm 4.7.0、catboost 1.2.10、scikit-learn 1.9.1、pandas 3.0.6 |
| 例の値 | すべて乱数で作った架空のデータのもの。JV-Data の値は使っていない |
