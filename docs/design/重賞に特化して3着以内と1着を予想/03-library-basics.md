# 03 LightGBM と CatBoost（と pandas）の使い方

**この文書の目的:** 設計を読む前に、LightGBM と CatBoost（と、表を扱う pandas）で何ができるかを知っておく。

**この文書で示すこと: 使う道具は手本の予想と同じである。道具の説明は [手本の 03](../近走と適性から3着以内を予想/03-library-basics.md) を参照する。この予想で増えるのは「行に重みを付けて学ぶ」書き方だけで、その例をこの文書に置く。**

同じ説明を2つのフォルダに写すと、片方だけ直したときに食い違う。そのため、手本と同じところは入口だけを持つ。

## 手本の 03 のどこに何が書いてあるか

| 知りたいこと | 手本の節 |
|---|---|
| 入れるパッケージ（`lightgbm`・`catboost`・`scikit-learn`・`pandas`） | [1. 準備](../近走と適性から3着以内を予想/03-library-basics.md#1-準備) |
| 表（`DataFrame`）の作り方、列の型、欠損値、この予想で使う操作 | [2. pandas の使い方](../近走と適性から3着以内を予想/03-library-basics.md#2-pandas-の使い方) |
| 2つのモデルに共通の流れ（モデルを作る → `fit()` → `predict_proba()`） | [3. 2つに共通する使い方](../近走と適性から3着以内を予想/03-library-basics.md#3-2つに共通する使い方) |
| LightGBM のコード例と機能（カテゴリ型・早期終了・保存） | [4. LightGBM の使い方](../近走と適性から3着以内を予想/03-library-basics.md#4-lightgbm-の使い方) |
| CatBoost のコード例と機能（`cat_features`・早期終了・保存） | [5. CatBoost の使い方](../近走と適性から3着以内を予想/03-library-basics.md#5-catboost-の使い方) |
| 2つの予測確率の平均のしかた（重みを付けない単純な平均） | [6. 2つの予測確率を合わせる](../近走と適性から3着以内を予想/03-library-basics.md#6-2つの予測確率を合わせる) |

## 行に重みを付けて学ぶ

**重賞の行を重く見るために、行ごとの重み（サンプルの重み）を `fit()` に渡す。** 重み 5 の行は、同じ行が5つあるのと同じように誤差に数えられる。学習データにも検証データにも、同じ決まりで重みを付ける（検証データの当たり具合で早期終了するので、検証データも重賞の行を重く見る）。

| ライブラリ | 学習データの重み | 検証データの重み |
|---|---|---|
| LightGBM | `fit(sample_weight=重み)` | `fit(eval_sample_weight=[重み])`（検証データごとのリストで渡す） |
| CatBoost | `Pool(weight=重み)` | 検証データの `Pool(weight=重み)` を `eval_set` に渡す |

重みは、目的変数の 1 と 0 ではなく、**レースの種類（重賞か）**で付ける。そのため、重賞の行の中の 1 と 0 の割合は変わらず、確率の大きさはずれない（[10-target.md](10-target.md#1-と-0-の数の偏り)）。

次のコードは、乱数の架空データで動かして確かめた版である（lightgbm 4.7.0・catboost 1.2.10・pandas 3.0.6）。前日・当日のモデルは、手本と同じく、オッズから作った基準（ロジット）を出発点にするので、その渡し方（`init_score`・`baseline`）も一緒に書いた。

```python
import catboost
import lightgbm
import numpy as np
import pandas as pd

rng = np.random.default_rng(0)
n = 2000  # 例なので 2000行。本番の学習データは約70万行
X = pd.DataFrame({
    "距離": rng.choice([1200, 1600, 2000], n),
    "斤量": rng.normal(56, 1.5, n).round(1),
    "競馬場": pd.Categorical(rng.choice(["東京", "中山", "京都"], n)),
})
y = pd.Series(rng.integers(0, 2, n))                 # 目的変数（3着以内なら 1）
is_graded = pd.Series(rng.random(n) < 0.05)          # 重賞の行（全体の 5% ほど）
base = pd.Series(np.log(0.2 / 0.8), index=X.index)   # 出発点（オッズから作った基準のロジット）

# 重み: 重賞の行は 5、ほかは 1（目的変数の 1 と 0 ではなく、レースの種類で付ける）
weight = np.where(is_graded, 5.0, 1.0)

train, valid = X.index < 1600, X.index >= 1600       # 例なので行の番号で分ける。本番は時期で分ける

# LightGBM: 学習データは sample_weight、検証データは eval_sample_weight（リストで渡す）
lgbm = lightgbm.LGBMClassifier(objective="binary", n_estimators=200, learning_rate=0.05, verbose=-1)
lgbm.fit(
    X[train], y[train], sample_weight=weight[train], init_score=base[train].to_numpy(),
    eval_X=X[valid], eval_y=y[valid], eval_sample_weight=[weight[valid]],
    eval_init_score=[base[valid].to_numpy()],
    callbacks=[lightgbm.early_stopping(20, verbose=False)],
)
raw = lgbm.predict(X[valid], raw_score=True) + base[valid].to_numpy()
p_lgbm = 1 / (1 + np.exp(-raw))                       # 基準を足して確率に戻す

# CatBoost: 学習データと検証データの Pool に weight を付ける。カテゴリ特徴量は文字列のまま
Xc = X.assign(競馬場=X["競馬場"].astype(str))
pool_train = catboost.Pool(Xc[train], y[train], cat_features=["競馬場"],
                           weight=weight[train], baseline=base[train].to_numpy())
pool_valid = catboost.Pool(Xc[valid], y[valid], cat_features=["競馬場"],
                           weight=weight[valid], baseline=base[valid].to_numpy())
cb = catboost.CatBoostClassifier(loss_function="Logloss", iterations=200, verbose=0, allow_writing_files=False)
cb.fit(pool_train, eval_set=pool_valid, early_stopping_rounds=20)
raw_cb = cb.predict(catboost.Pool(Xc[valid], cat_features=["競馬場"]), prediction_type="RawFormulaVal")
p_cb = 1 / (1 + np.exp(-(raw_cb + base[valid].to_numpy())))
```

- **予測には重みを渡さない。** 重みは学習のときに「どの行の誤差を重く見るか」を決めるだけで、`predict_proba()` や `predict()` の引数には無い。
- lightgbm 4.7.0 では、検証データを `eval_X=`・`eval_y=` で渡す（手本の 03 と同じ。`eval_set=` は非推奨）。重みと基準は、検証データごとのリスト（`eval_sample_weight=[…]`・`eval_init_score=[…]`）で渡す。この形で警告が出ないことを確かめた。
- 2つのモデルの確率の平均（`(p_lgbm + p_cb) / 2`）は手本と同じで、重みは関係しない。

## この予想で使う機能と、書いてある文書

| この予想でやること | 使う機能 | この予想での使い方 |
|---|---|---|
| 全レースで学び、重賞の行を重く見る | `sample_weight`・`eval_sample_weight`（LightGBM）、`Pool` の `weight`（CatBoost） | [12-lightgbm.md の 1](12-lightgbm.md#1-学習データの渡し方)・[13-catboost.md の 1](13-catboost.md#1-学習データの渡し方) |
| オッズから作った基準を出発点にする（前日・当日） | `init_score`（LightGBM）、`Pool` の `baseline`（CatBoost） | 手本と同じ（[手本の 12](../近走と適性から3着以内を予想/12-lightgbm.md)・[手本の 13](../近走と適性から3着以内を予想/13-catboost.md)） |
| 学習しすぎを防ぐ | 検証データと早期終了（重み付きのログ損失で見る） | [12-lightgbm.md の 2](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md の 2](13-catboost.md#2-ハイパーパラメータの初期値) |
| 騎手・父・格などを扱う | カテゴリ特徴量の指定 | [12-lightgbm.md の 1](12-lightgbm.md#1-学習データの渡し方)・[13-catboost.md の 1](13-catboost.md#1-学習データの渡し方) |
| 学習したモデルを、レース当日まで取っておく | 保存と読み込み | [12-lightgbm.md の 6](12-lightgbm.md#6-保存)・[13-catboost.md の 6](13-catboost.md#6-保存) |
| 重賞の3着以内・1着の確率を出す | `predict_proba()` の2列目（基準を使うモデルは生の値に基準を足す） | [05-sequence.md の図2](05-sequence.md#図2-予測) |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-11-14 |
| 確かめた版 | Python 3.14、lightgbm 4.7.0、catboost 1.2.10、pandas 3.0.6（重みの例をスクラッチの架空データで動かした） |
