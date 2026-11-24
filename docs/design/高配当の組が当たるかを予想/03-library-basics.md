# 03 LightGBM と CatBoost（と pandas）の使い方

**この文書の目的:** 設計を読む前に、LightGBM と CatBoost（と、表を扱う pandas）で何ができるかを知っておく。

**この文書で示すこと: 使う道具は手本の予想と同じである。道具の説明は書かず、[手本の 03](../近走と適性から3着以内を予想/03-library-basics.md) を参照する。この予想で手本と違うのは、出発点（基準）と行の重みを `fit()` に渡すことと、カテゴリ特徴量が無いことの3つである。**

同じ説明を2つのフォルダに写すと、片方だけ直したときに食い違う。そのため、この文書は入口だけを持つ。

## 手本の 03 のどこに何が書いてあるか

| 知りたいこと | 手本の節 |
|---|---|
| 入れるパッケージ（`lightgbm`・`catboost`・`scikit-learn`・`pandas`） | [1. 準備](../近走と適性から3着以内を予想/03-library-basics.md#1-準備) |
| 表（`DataFrame`）の作り方、列の型、欠損値 | [2. pandas の使い方](../近走と適性から3着以内を予想/03-library-basics.md#2-pandas-の使い方) |
| 2つのモデルに共通の流れ（モデルを作る → `fit()` → `predict_proba()`） | [3. 2つに共通する使い方](../近走と適性から3着以内を予想/03-library-basics.md#3-2つに共通する使い方) |
| LightGBM のコード例と機能 | [4. LightGBM の使い方](../近走と適性から3着以内を予想/03-library-basics.md#4-lightgbm-の使い方) |
| CatBoost のコード例と機能 | [5. CatBoost の使い方](../近走と適性から3着以内を予想/03-library-basics.md#5-catboost-の使い方) |
| 2つの予測確率の平均のしかた（重みを付けない単純な平均） | [6. 2つの予測確率を合わせる](../近走と適性から3着以内を予想/03-library-basics.md#6-2つの予測確率を合わせる) |

## この予想で違う点

| 違う点 | 何をするか | 使い方が書いてある所 |
|---|---|---|
| 出発点（基準）を渡す | 市場の確率のロジットを、LightGBM は `init_score`、CatBoost は `Pool` の `baseline` として渡す。モデルは、出発点からの上げ下げだけを学ぶ。予測では、木の出した値に出発点を足して確率に戻す | [重賞の予想の 03 の「行に重みを付けて学ぶ」](../重賞に特化して3着以内と1着を予想/03-library-basics.md#行に重みを付けて学ぶ)（基準と重みを両方渡すコード例。乱数の架空データで動かして確かめた版） |
| 行の重みを渡す | 間引いた外れの組に付けた重みを、LightGBM は `sample_weight`（検証データは `eval_sample_weight`）、CatBoost は `Pool` の `weight` として渡す | 同じ節 |
| カテゴリ特徴量が無い | 特徴量は全部が数値なので、カテゴリ型への変換（LightGBM）と `cat_features`（CatBoost）は使わない | ―（使わない機能） |

新しいライブラリは使わない。この文書にコード例は足していない。出発点と重みを両方渡して学習・予測できることは、この予想の初期値の設定で、乱数の架空データで確かめた（[14-hyperparameter-settings.md](14-hyperparameter-settings.md#設定ファイルの形)）。出発点と重みを実際に渡すのは共有の `LightGbmModel`・`CatBoostModel` で、この予想はそれを呼ぶだけである（[12-lightgbm.md](12-lightgbm.md#1-学習データの渡し方)・[13-catboost.md](13-catboost.md#1-学習データの渡し方)）。

## この予想で使う機能と、書いてある文書

| この予想でやること | 使う機能 | この予想での使い方 |
|---|---|---|
| 過去のレースの組で学習する | `fit()` | [05-sequence.md](05-sequence.md#図2-学習)、[12-lightgbm.md](12-lightgbm.md)・[13-catboost.md](13-catboost.md) |
| 市場の確率を出発点にする | `init_score`（LightGBM）、`Pool` の `baseline`（CatBoost） | [10-target.md](10-target.md#出発点基準) |
| 間引いた外れの組を、元の数のぶん重く見る | `sample_weight`・`eval_sample_weight`（LightGBM）、`Pool` の `weight`（CatBoost） | [08-training-data.md](08-training-data.md#4-外れの組の間引きと行の重み) |
| 学習しすぎを防ぐ | 検証データと早期終了 | [12-lightgbm.md](12-lightgbm.md#2-ハイパーパラメータの初期値)・[13-catboost.md](13-catboost.md#2-ハイパーパラメータの初期値) |
| 学習したモデルを、レース当日まで取っておく | 保存と読み込み | [12-lightgbm.md](12-lightgbm.md#6-保存)・[13-catboost.md](13-catboost.md#6-保存) |
| 今日のレースの組の確率を出す | `predict_proba()` の2列目に当たる値（出発点を足して確率に戻したもの） | [05-sequence.md](05-sequence.md#図4-1レースの予測と買い目) |
| 2つのモデルの確率を合わせる | 単純な平均 | [15-decisions.md の 12](15-decisions.md#12-2つのモデルの確率の合わせ方) |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-11-24 |
| 確かめた版 | lightgbm 4.7.0、catboost 1.2.10、pandas 3.0.6（手本・重賞の予想と同じ） |
