# 03 LightGBM と CatBoost（と pandas）の使い方

**この文書の目的:** 設計を読む前に、LightGBM と CatBoost（と、表を扱う pandas）で何ができるかを知っておく。

**この文書で示すこと: 使う道具は手本の予想と同じ（LightGBM・CatBoost・pandas・scikit-learn）である。道具の説明は書かず、[手本の 03](../近走と適性から3着以内を予想/03-library-basics.md) を参照する。この予想で違うのは、二値分類ではなく多クラス分類（4クラス）で使う点で、`predict_proba()` が2列ではなく4列を返し、平均の取り方が変わる。**

同じ説明を2つのフォルダに写すと、片方だけ直したときに食い違う。そのため、この文書は入口と、多クラス分類で違う点だけを持つ。

## 手本の 03 のどこに何が書いてあるか

| 知りたいこと | 手本の節 |
|---|---|
| 入れるパッケージ（`lightgbm`・`catboost`・`scikit-learn`・`pandas`） | [1. 準備](../近走と適性から3着以内を予想/03-library-basics.md#1-準備) |
| 表（`DataFrame`）の作り方、列の型、欠損値、この予想で使う操作 | [2. pandas の使い方](../近走と適性から3着以内を予想/03-library-basics.md#2-pandas-の使い方) |
| 2つのモデルに共通の流れ（モデルを作る → `fit()` → `predict_proba()`）と、`predict()` を使わない理由 | [3. 2つに共通する使い方](../近走と適性から3着以内を予想/03-library-basics.md#3-2つに共通する使い方) |
| LightGBM のコード例と機能（カテゴリ型・早期終了・保存） | [4. LightGBM の使い方](../近走と適性から3着以内を予想/03-library-basics.md#4-lightgbm-の使い方) |
| CatBoost のコード例と機能（`cat_features`・早期終了・保存） | [5. CatBoost の使い方](../近走と適性から3着以内を予想/03-library-basics.md#5-catboost-の使い方) |

この予想で足す pandas の操作は、1頭ごとの表をレース単位に集約するもの（`X.groupby("レースID")["単勝オッズ"].min()` のように、レースIDごとにまとめて最小・最大・数・平均を出す）である。集約するクラスは [04-classes.md](04-classes.md#3-この予想だけのクラスの一覧) を参照。

## この予想で違う点

**多クラス分類（4クラス）で使う。** 次のコードで、乱数で作った架空のレースのデータを使って動くことを確かめた（2026-09-23。lightgbm 4.7.0、catboost 1.2.10、scikit-learn 1.9.1、pandas 3.0.6）。

```python
import numpy as np
import pandas as pd
import lightgbm
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier

# 学習データ: 1行 = 1レース。X_train が特徴量、y_train が荒れ具合（0 = 固い、1 = 中荒れ、2 = 大荒れ、3 = 超荒れ）
X_train = pd.DataFrame({
    "1番人気のオッズ":  [3.4, 1.6, 5.1],
    "10倍未満の頭数":   [4, 3, 6],
    "出走頭数":         [16, 8, 18],
    "芝ダ":             ["芝", "ダート", "芝"],
})
y_train = [2, 0, 3]
# 実際には何万行もある。検証データ X_valid・y_valid と、予測したいレース X_new も同じ列の表

# LightGBM: 目的関数を multiclass にし、クラスの数を num_class で渡す。文字列の列はカテゴリ型にする（手本と同じ）
X_lgb = X_train.copy()
X_lgb["芝ダ"] = X_lgb["芝ダ"].astype("category")
lgb = LGBMClassifier(objective="multiclass", num_class=4, learning_rate=0.05, n_estimators=2000)
lgb.fit(X_lgb, y_train, eval_X=X_valid_lgb, eval_y=y_valid, callbacks=[lightgbm.early_stopping(100)])
p_lgb = lgb.predict_proba(X_new_lgb)     # 行数 × 4 の表

# CatBoost: 目的関数を MultiClass にする。クラスの数は y から決まる。カテゴリ特徴量は文字列のまま cat_features に書く（手本と同じ）
cb = CatBoostClassifier(loss_function="MultiClass", learning_rate=0.05, iterations=2000, verbose=0, allow_writing_files=False)
cb.fit(X_train, y_train, cat_features=["芝ダ"], eval_set=(X_valid, y_valid), early_stopping_rounds=100)
p_cb = cb.predict_proba(X_new)           # 行数 × 4 の表

# 2つを平均する。np.stack で「2 × 行数 × 4」に重ねてから、最初の軸で平均すると「行数 × 4」に戻る
p_mean = np.stack([p_lgb, p_cb], axis=0).mean(axis=0)
top = p_mean.argmax(axis=1)              # いちばん高いクラス（0〜3）
p_upset = p_mean[:, 1:].sum(axis=1)      # 中荒れ以上の確率（固い以外の合計）
```

`predict_proba()` の戻り値は、次のような4列の表である（架空の3レース）。

```text
[[0.482 0.271 0.188 0.059]    ← 1レース目: 固い 0.482、中荒れ 0.271、大荒れ 0.188、超荒れ 0.059（合計 1）
 [0.905 0.071 0.019 0.005]    ← 2レース目: ほぼ固い
 [0.104 0.322 0.351 0.223]]   ← 3レース目: 大荒れがいちばん高い
```

| 手本（二値分類） | この予想（多クラス分類） |
|---|---|
| `objective="binary"` / `loss_function="Logloss"` | `objective="multiclass", num_class=4` / `loss_function="MultiClass"` |
| `predict_proba()` は2列（0 になる確率、1 になる確率） | 4列（固い・中荒れ・大荒れ・超荒れの確率）。列の順は `classes_`（`[0 1 2 3]`）と同じで、2つのモデルで一致することを確かめた |
| 2列目 `[:, 1]` を使う | 4列をそのまま使う。いちばん高いクラスは `argmax(axis=1)`、中荒れ以上の確率は `[:, 1:].sum(axis=1)` |
| 2つの確率（1列）の平均 | 2つの表（行数 × 4）の平均。`np.vstack` だと縦につないで「2 × 行数 行」になるので、`np.stack(…, axis=0).mean(axis=0)` にする |
| 目的変数は 1/0 | 目的変数は 0〜3 の整数。欠損値の行（発売の無い券種）は、学習の前に除く |

- 動かして分かったこと: 2つのライブラリとも、`predict_proba()` の各行の合計は 1 になり、`classes_` は `[0 1 2 3]` で一致した。`np.vstack` で平均しようとすると形が崩れる（共通の `EnsembleModel` を直す理由。[04-classes.md](04-classes.md#2-共通の部品に足すもの変えるもの)）。
- 確かめたスクリプトは JV-Data を使っていない。出力の数字も、乱数のデータのものである。

## この予想で使う機能と、書いてある文書

| この予想でやること | 使う機能 | この予想での使い方 |
|---|---|---|
| 過去のレースで学習する（券種ごと） | `fit()` | [05-sequence.md](05-sequence.md#図1-学習)、[12-lightgbm.md](12-lightgbm.md#4-学習のやりとりシーケンス図)・[13-catboost.md](13-catboost.md#4-学習のやりとりシーケンス図) |
| 学習しすぎを防ぐ | 検証データと早期終了 | [12-lightgbm.md](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md](13-catboost.md#2-ハイパーパラメータの初期値) |
| 競馬場・芝ダなどを扱う | カテゴリ特徴量の指定 | [12-lightgbm.md](12-lightgbm.md#1-学習データの渡し方)・[13-catboost.md](13-catboost.md#1-学習データの渡し方) |
| 学習したモデルを、レース当日まで取っておく | 保存と読み込み | [12-lightgbm.md](12-lightgbm.md#6-保存)・[13-catboost.md](13-catboost.md#6-保存) |
| 今日のレースの荒れ具合の確率を出す | `predict_proba()` の4列と、2つの表の平均 | [05-sequence.md](05-sequence.md#図2-予測)、[12-lightgbm.md](12-lightgbm.md#5-予測のやりとりシーケンス図)・[13-catboost.md](13-catboost.md#5-予測のやりとりシーケンス図) |
| 4クラスの当たり具合を測る | scikit-learn の `accuracy_score`・`f1_score(average="macro")`・`confusion_matrix`・`log_loss`・`roc_auc_score` | [16-evaluation.md](16-evaluation.md#2-評価指標) |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-23 |
| 確かめた版 | lightgbm 4.7.0、catboost 1.2.10、scikit-learn 1.9.1、pandas 3.0.6 |
| 例の値 | すべて乱数で作った架空のデータのもの。JV-Data の値は使っていない |
