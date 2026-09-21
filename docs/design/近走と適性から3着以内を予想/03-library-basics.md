# 03 LightGBM と CatBoost（と pandas）の使い方

**この文書の目的:** 設計を読む前に、LightGBM と CatBoost（と、表を扱う pandas）で何ができるかを知っておく。この文書は決めごとではなく、道具の説明である。

**結論: LightGBM と CatBoost は、どちらも「モデルを作る → `fit()` で学習する → `predict_proba()` で予測する」の3つの手順で使える。** この予想では、そのうえで「検証データを使って木の数を決める（早期終了）」「カテゴリ特徴量を指定する」「学習したモデルを保存して、レース当日に読み込む」の機能を使う。

- この文書は、道具としての使い方の説明である。この予想での使い方（ハイパーパラメータの値など）は [12-lightgbm.md](12-lightgbm.md)・[13-catboost.md](13-catboost.md) を参照。
- 用語の意味（特徴量・目的変数・予測確率など）は [02-glossary.md](02-glossary.md) を参照。
- コードは、lightgbm 4.7.0・catboost 1.2.10・pandas 3.0.6 で、乱数で作った架空の馬のデータを使って動くことを確かめた（2026-09-21）。出力の数字も、その架空のデータのものである。

## 1. 準備

プログラムを作るときに、keiba-yosou の依存に次の4つを足す（まだ足していない）。

| パッケージ | 何に使うか |
|---|---|
| `lightgbm` | LightGBM 本体 |
| `catboost` | CatBoost 本体 |
| `scikit-learn` | LightGBM の `LGBMClassifier` を使うのに要る。入っていないと、モデルを作るところでエラーになる（確かめたときに実際になった） |
| `pandas` | 学習データを表（`DataFrame`）で扱う。使い方は下の「2. pandas の使い方」 |

## 2. pandas の使い方

pandas は、Python で表（Excel のような、行と列のあるデータ）を扱うライブラリである。この予想では、学習データと予測用データを pandas の表で持ち、そのまま LightGBM と CatBoost に渡す。2つのモデルは、pandas の表を受け取ると、列の名前と列の型を見て、1列を1つの特徴量として扱う。

| 言葉 | 意味 | この予想では |
|---|---|---|
| `DataFrame` | pandas の表。行と列を持つ | 学習データ（下の 4.・5. のコードの `X_train`） |
| 列 | 表の縦の並び。名前が付いている | 1列 = 1つの特徴量（例: 「斤量」） |
| 行 | 表の横の並び | 1行 = 1頭 |
| 列の型（dtype） | 列に入っている値の種類。1つの列の中は、全部同じ型になる | 数値（`float64`）、文字列（`str`）、カテゴリ型（`category`） |
| `NaN` | 欠損値の印 | 前走が無い馬の「前走の着順」 |

### 表を作って見る

```python
import pandas as pd

# 表を作る。{"列の名前": [1行目の値, 2行目の値, 3行目の値], ...} の形で書く
X = pd.DataFrame({
    "斤量":       [55.0, 57.0, 56.0],
    "前走の着順": [2, 8, None],           # None と書いた所は、欠損値（NaN）になる
    "競馬場":     ["東京", "中山", "東京"],
    "騎手":       ["騎手A", "騎手B", None],
})
print(X)
```

`print(X)` の出力（pandas 3.0.6 で確かめた）:

```text
     斤量  前走の着順 競馬場   騎手
0  55.0    2.0  東京  騎手A
1  57.0    8.0  中山  騎手B
2  56.0    NaN  東京  NaN
```

- 左端の 0・1・2 は、pandas が自動で付ける行の番号である。
- 「前走の着順」の 2 が 2.0 と小数で出るのは、NaN が小数の仲間だからである。欠損値が1つでもあると、その列は全部小数の型になる。

### この予想で使う操作

上の表 `X` で試した結果を並べる。

| やりたいこと | 書き方 | 結果 |
|---|---|---|
| 1列を取り出す | `X["斤量"]` | 55.0, 57.0, 56.0 |
| 列の型を見る | `X.dtypes` | 斤量 `float64`、前走の着順 `float64`、競馬場 `str`、騎手 `str` |
| 列を計算して足す | `X["斤量の差"] = X["斤量"] - X["斤量"].mean()` | 「斤量の差」の列ができ、−1.0, 1.0, 0.0 が入る（斤量の平均 56.0 との差） |
| 欠損値を埋める | `X["騎手"].fillna("なし")` | 騎手A, 騎手B, なし |
| 列の型を変える | `X["競馬場"].astype("category")` | 文字列 → カテゴリ型。下の「4. LightGBM の使い方」の変換前・変換後の表を参照 |
| 元DB から表で受け取る | `con.sql("select ...").df()` | DuckDB（元DB）の SQL の結果が、そのまま `DataFrame` になる。`con` は DuckDB への接続 |

## 3. 2つに共通する使い方

LightGBM も CatBoost も、scikit-learn と同じ形のメソッドを持っている。そのため、使い方の流れは同じである。

| 手順 | コード | 何が起きるか |
|---|---|---|
| 1. モデルを作る | `model = LGBMClassifier(...)`<br>`model = CatBoostClassifier(...)` | 設定（ハイパーパラメータ）を決めるだけ。まだ何も学んでいない |
| 2. 学習する | `model.fit(X, y)` | `X` は特徴量の表（1行 = 1頭）、`y` は目的変数（3着以内なら 1）。決定木を1本ずつ足していく |
| 3. 予測する | `model.predict_proba(X_new)` | 予測したい馬の特徴量の表を渡すと、1頭ずつ「0 になる確率」と「1 になる確率」の2列が返る |

`predict_proba()` の戻り値は、次のような2列の表である（架空の3頭）。

```text
[[0.851 0.149]    ← 1頭目: 3着以内に入らない確率 0.851、入る確率 0.149
 [0.731 0.269]    ← 2頭目: 入る確率 0.269
 [0.825 0.175]]   ← 3頭目: 入る確率 0.175
```

2列目（`[:, 1]`）が、この予想で使う「3着以内に入る確率」である。

**`predict()` は使わない。** `predict()` は、確率が 0.5 以上なら 1、それ未満なら 0 を返す。3着以内に入る確率は、ほとんどの馬で 0.5 より小さい。そのため、上の3頭はどれも 0 になり、馬どうしの差が分からなくなる。

## 4. LightGBM の使い方

```python
import pandas as pd
import lightgbm as lgb

# 学習データ: 1行 = 1頭。X_train が特徴量、y_train が目的変数（3着以内なら 1）
X_train = pd.DataFrame({
    "斤量":       [55.0, 57.0, 56.0],
    "前走の着順": [2, 8, None],           # 前走が無い馬は、欠損値のまま
    "競馬場":     ["東京", "中山", "東京"],
    "騎手":       ["騎手A", "騎手B", None],
})
y_train = [1, 0, 1]
# 実際には何万行もある。検証データ X_valid・y_valid と、予測したい馬 X_new も同じ列の表

# LightGBM は文字列を扱えないので、文字列の列（この例では競馬場と騎手）をカテゴリ型にする
for col in ["競馬場", "騎手"]:
    X_train[col] = X_train[col].astype("category")

# 1. モデルを作る
model = lgb.LGBMClassifier(objective="binary", learning_rate=0.05, n_estimators=2000)

# 2. 学習する。検証データの当たり具合が、木を 100 本足しても良くならなければ止める
model.fit(
    X_train, y_train,
    eval_X=X_valid, eval_y=y_valid,
    callbacks=[lgb.early_stopping(100)],
)

# 3. 予測する
p = model.predict_proba(X_new)[:, 1]    # 1頭ずつの「3着以内に入る確率」
```

**文字列の列は、カテゴリ型にする。**（LightGBM は文字列を扱えないため）

| | 変換前 | 変換後 |
|---|---|---|
| 型 | `str`（文字列） | `category`（enum のようなもの） |
| 値 | `"東京"`, `"中山"`, `"東京"`, `"阪神"` | 一覧 `["中山", "東京", "阪神"]` と、番号 `[1, 0, 1, 2]` |

| 機能 | 書き方 |
|---|---|
| カテゴリ特徴量 | 列を `category` 型にする |
| 欠損値 | NaN のまま渡す |
| 検証データと早期終了 | `fit()` に `eval_X=`・`eval_y=`・`callbacks=[lgb.early_stopping(100)]` |
| 特徴量の重要度 | `model.feature_importances_` |
| 保存・読み込み | `joblib.dump(model, "ファイル名")`・`joblib.load("ファイル名")` |

## 5. CatBoost の使い方

```python
import pandas as pd
from catboost import CatBoostClassifier

# 学習データは LightGBM と同じ形。ただし、カテゴリ特徴量は文字列のままにする
X_train = pd.DataFrame({
    "斤量":       [55.0, 57.0, 56.0],
    "前走の着順": [2, 8, None],           # 数値の欠損値は、そのままでよい
    "競馬場":     ["東京", "中山", "東京"],
    "騎手":       ["騎手A", "騎手B", None],
})
y_train = [1, 0, 1]

# カテゴリ特徴量の欠損値は、文字列にしておく（NaN のままだとエラーになる）
X_train["騎手"] = X_train["騎手"].fillna("なし")

# 1. モデルを作る。verbose=0 は途中経過を表示しない、allow_writing_files=False は作業用のフォルダを作らない
model = CatBoostClassifier(
    loss_function="Logloss", learning_rate=0.05, iterations=2000,
    verbose=0, allow_writing_files=False,
)

# 2. 学習する。カテゴリ特徴量の列名を cat_features に並べる
model.fit(
    X_train, y_train,
    cat_features=["競馬場", "騎手"],
    eval_set=(X_valid, y_valid),
    early_stopping_rounds=100,
)

# 3. 予測する
p = model.predict_proba(X_new)[:, 1]    # 1頭ずつの「3着以内に入る確率」
```

**文字列の列は、文字列のまま渡す。欠損値だけ、文字列「なし」にする。**（CatBoost は文字列を扱えるが、カテゴリの列の NaN は扱えないため）

| | 変換前 | 変換後 |
|---|---|---|
| 型 | `str`（文字列） | `str`（文字列）のまま |
| 値 | `"騎手A"`, `"騎手B"`, `NaN` | `"騎手A"`, `"騎手B"`, `"なし"` |

| 機能 | 書き方 |
|---|---|
| カテゴリ特徴量 | 文字列のまま、`fit()` の `cat_features=` に列名を書く（書き忘れるとエラー） |
| 欠損値 | 数値は NaN のまま。カテゴリは `fillna("なし")` |
| 検証データと早期終了 | `fit()` に `eval_set=(X_valid, y_valid)`・`early_stopping_rounds=100` |
| 特徴量の重要度 | `model.get_feature_importance()` |
| 保存・読み込み | `model.save_model("ファイル名.cbm")`・`CatBoostClassifier().load_model("ファイル名.cbm")` |

## 6. 2つの予測確率を合わせる

2つのモデルは、同じ馬に少し違う確率を出す。この予想では、2つを平均して1つの確率にする（アンサンブル）。

| 架空の馬 | LightGBM | CatBoost | 平均 |
|---|---|---|---|
| 1頭目 | 0.149 | 0.128 | 0.138 |
| 2頭目 | 0.269 | 0.331 | 0.300 |
| 3頭目 | 0.175 | 0.170 | 0.173 |

平均のしかた（単純な平均にするか、重みを付けるか）は、次の設計書で決める。

## 7. この予想で使う機能と、書いてある文書

| この予想でやること | 使う機能 | この予想での使い方 |
|---|---|---|
| 過去のレースで学習する | `fit()` | [05-sequence.md](05-sequence.md) の図1、[12-lightgbm.md](12-lightgbm.md)・[13-catboost.md](13-catboost.md) の「4. 学習のやりとり」 |
| 学習しすぎを防ぐ | 検証データと早期終了 | [12-lightgbm.md](12-lightgbm.md)・[13-catboost.md](13-catboost.md) の「2. ハイパーパラメータの初期値」 |
| 騎手・父などを扱う | カテゴリ特徴量の指定 | [12-lightgbm.md](12-lightgbm.md)・[13-catboost.md](13-catboost.md) の「1. 学習データの渡し方」 |
| 学習したモデルを、レース当日まで取っておく | 保存と読み込み | [12-lightgbm.md](12-lightgbm.md)・[13-catboost.md](13-catboost.md) の「6. 保存」 |
| 今日のレースの確率を出す | `predict_proba()` の2列目 | [05-sequence.md](05-sequence.md) の図2、[12-lightgbm.md](12-lightgbm.md)・[13-catboost.md](13-catboost.md) の「5. 予測のやりとり」 |
| モデルが何を重く見ているかを確かめる | 特徴量の重要度 | 確かめ方は、評価指標と一緒に次の設計書で決める |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-21 |
| 確かめた版 | lightgbm 4.7.0、catboost 1.2.10、pandas 3.0.6 |
| 例の値 | すべて乱数で作った架空のデータのもの。JV-Data の値は使っていない |
