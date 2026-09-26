# 03 LightGBM と CatBoost（と pandas）の使い方

**この文書の目的:** 設計を読む前に、LightGBM と CatBoost（と、表を扱う pandas）で何ができるかを知っておく。

**この文書で示すこと: 使う道具は手本の予想と同じ（LightGBM・CatBoost・pandas・scikit-learn）である。道具の基本の説明は書かず、[手本の 03](../近走と適性から3着以内を予想/03-library-basics.md) を参照する。この予想で足すのは、①二値分類の確率をレースの中で合計 1 にそろえる計算（先頭の馬と、1着の馬）、②多クラス分類（3クラス）、③分位点回帰（前半タイムと後半タイム）、④回帰（4コーナーの位置と上がりの速さ）、⑤1着の確率から 2着・3着と買い目ごとの確率を出す計算（Harville の式）、の5つである。**

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

着順の予想⑦の「1着になる確率」も、この節とまったく同じ計算でレースの中で合計 1 にそろえる（目的変数が「先頭」ではなく「1着」になるだけ）。

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

後半のペースの予想⑥（後半タイムの基準との差）も、この節とまったく同じ計算で当てる。

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

## 4. 4コーナーの位置と上がりの速さの回帰

**何をするか。** 予想④（4コーナーの位置）と⑤（上がりの速さ）は、0〜1 の値を1頭ずつ当てる。区分に分けず、値そのものを当てる回帰にする。後の組（着順⑦）の特徴量に入れるとき、区分より細かい差が残るためである（[15-decisions.md の 17](15-decisions.md#17-後半で何を当てるか)）。

```python
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor

# X_train: 1行 = 1頭の特徴量、y_train: 4コーナーの位置（0〜1）。X_new: 予測したい馬
lgb = LGBMRegressor(objective="regression", learning_rate=0.05, n_estimators=200, verbose=-1)   # 二乗誤差
lgb.fit(X_train, y_train)
cb = CatBoostRegressor(loss_function="RMSE", learning_rate=0.05, iterations=300, verbose=0, allow_writing_files=False)
cb.fit(X_train, y_train)
position = (lgb.predict(X_new) + cb.predict(X_new)) / 2                # 2つの平均。1頭ずつの 4コーナーの位置の予測
```

| 何を確かめたか | 結果 |
|---|---|
| 架空のデータ（2000行、0〜1 の値）で、学習に使っていない 500行の MAE | モデル 0.082、学習データの平均を出すだけ 0.135 |
| 予測の値が 0〜1 に収まるか | 収まるとは限らない（回帰は範囲を知らない）。後の組の特徴量に入れるだけなので、切り詰めない |

- 分位点回帰（3.）と違い、真ん中の値だけを出す。④⑤は、着順の特徴量として使うのが目的で、幅は使わないためである。
- 二値分類・多クラス分類と違い `predict_proba()` ではなく `predict()` を呼ぶ。`ProbabilityModel` の決まり（`predict_proba`）を守れないので、回帰のモデルのクラスを別に置く（[04-classes.md の「ml_model/」](04-classes.md#ml_model--レースの中でそろえるモデル分位点回帰回帰2着3着の割り当て)）。

## 5. 1着の確率から、2着・3着と買い目ごとの確率を出す

**何をするか。** 予想⑦は、各馬が1着になる確率（レースの中で合計 1）を出す。2着・3着の確率は、Harville の式で割り当てる。「1着の馬を除いた残りの馬の中で、1着の確率の割合で 2着が決まる。1・2着の馬を除いた残りで、同じように 3着が決まる」と考える。1着の確率を λ 乗してから割り当てると（ならしの指数。[02-glossary.md](02-glossary.md)）、2着・3着の確率が人気のない馬にも配られる。λ = 1 なら Harville の式のままである。

次のコードで、架空の6頭立てのレースで動くことを確かめた（2026-09-26。numpy と pandas だけを使う）。

```python
import itertools
import numpy as np
import pandas as pd

def order_probabilities(win_prob, lam):
    """1着の確率から、1着・2着・3着の並び（3連単）ごとの確率を出す（Harville の式に、ならしの指数 lam を付けたもの）。"""
    p = np.asarray(win_prob, dtype=float)
    q = p ** lam                                    # 2着・3着を割り当てるときの重み
    rows = []
    for i, j, k in itertools.permutations(range(len(p)), 3):
        p_ij = q[j] / (q.sum() - q[i])              # i が1着のとき、j が2着の確率
        p_ijk = q[k] / (q.sum() - q[i] - q[j])      # i・j が1・2着のとき、k が3着の確率
        rows.append((i, j, k, p[i] * p_ij * p_ijk))
    return pd.DataFrame(rows, columns=["1着", "2着", "3着", "確率"])

win = np.array([0.40, 0.25, 0.15, 0.10, 0.06, 0.04])   # 架空の6頭立ての1着の確率（合計 1）
trifecta = order_probabilities(win, lam=0.8)              # 3連単の 6 × 5 × 4 = 120 通りの確率
```

3連単の表から、ほかの券種の確率は足し算で出せる。

| 券種 | 当たる確率の出し方（3連単の表の、どの行の確率を足すか） |
|---|---|
| 単勝（i） | 1着が i の行（= 1着の確率そのもの） |
| 複勝（i） | 1〜3着のどれかが i の行。7頭立て以下は、1・2着のどちらかが i の行 |
| ワイド（i-j） | 1〜3着に i と j の両方がいる行 |
| 馬連（i-j） | 1・2着が i と j（順番は問わない）の行 |
| 馬単（i→j） | 1着が i、2着が j の行 |
| 3連複（i-j-k） | 1〜3着が i・j・k（順番は問わない）の行 |
| 3連単（i→j→k） | その1行 |

| 何を確かめたか | 結果 |
|---|---|
| 3連単の確率の合計 | λ = 1.0 でも 0.8 でも 1 |
| 各馬の3着以内の確率の合計 | 3（3頭が3着以内に入るので） |
| λ を 1.0 から 0.8 に下げたときの、1着の確率 0.40 の馬の 3着以内の確率 | 0.873 → 0.834（強い馬の 2着・3着の確率が下がり、弱い馬に配られる） |

- 18頭立てでも 3連単は 4,896 通りで、1レースずつ計算しても数ミリ秒で終わる。
- λ は、学習に使っていないデータ（検証データの後半）で、実際に 2着・3着だった馬に付けた確率がいちばん高くなる値を選ぶ（[10-target.md の 10.](10-target.md#10-着順の目的変数と確率の出し方)）。
- 確かめたスクリプトは JV-Data を使っていない。出力の数字も、架空のデータのものである。

## 6. この予想で使う機能と、書いてある文書

| この予想でやること | 使う機能 | この予想での使い方 |
|---|---|---|
| 過去のレースで学習する（7つの予想） | `fit()` | [05-sequence.md](05-sequence.md#図1-学習)、[12-lightgbm.md](12-lightgbm.md#4-学習のやりとりシーケンス図)・[13-catboost.md](13-catboost.md#4-学習のやりとりシーケンス図) |
| 学習しすぎを防ぐ | 検証データと早期終了 | [12-lightgbm.md](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md](13-catboost.md#2-ハイパーパラメータの初期値) |
| 先頭と1着の確率をレースの中で合計 1 にする | raw スコア・ソフトマックス・温度 | 上の 2.、[05-sequence.md](05-sequence.md#図3-先頭の確率をレースの中でそろえる) |
| 序盤の位置・ペースの区分の確率を出す | 多クラス分類（3クラス） | [12-lightgbm.md](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md](13-catboost.md#2-ハイパーパラメータの初期値) |
| 4コーナーの位置と上がりの速さを出す | 回帰（二乗誤差） | 上の 4.、[12-lightgbm.md](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md](13-catboost.md#2-ハイパーパラメータの初期値) |
| 2着・3着と買い目ごとの確率を出す | numpy（ライブラリの機能ではない） | 上の 5.、[10-target.md の 10.](10-target.md#10-着順の目的変数と確率の出し方) |
| 前半タイム・後半タイムの秒数と幅を出す | 分位点回帰 | 上の 3.、[12-lightgbm.md](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md](13-catboost.md#2-ハイパーパラメータの初期値) |
| 競馬場・騎手などを扱う | カテゴリ特徴量の指定 | [12-lightgbm.md](12-lightgbm.md#1-学習データの渡し方)・[13-catboost.md](13-catboost.md#1-学習データの渡し方) |
| 学習したモデルを、レース当日まで取っておく | 保存と読み込み | [12-lightgbm.md](12-lightgbm.md#6-保存)・[13-catboost.md](13-catboost.md#6-保存) |
| 当たり具合を測る | scikit-learn の `log_loss`・`accuracy_score`・`f1_score(average="macro")`・`mean_absolute_error`・`mean_pinball_loss` | [16-evaluation.md](16-evaluation.md#2-評価指標) |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-26 |
| 更新 | 2026-09-26 4.（回帰）と 5.（2着・3着の確率）を足した |
| 確かめた版 | lightgbm 4.7.0、catboost 1.2.10、scikit-learn 1.9.1、pandas 3.0.6 |
| 例の値 | すべて乱数で作った架空のデータのもの。JV-Data の値は使っていない |
