# 04 クラスとパッケージの設計

**この文書で決めること:** この予想のクラスが何をするか。共通の部品（`src/yosou/shared/`）の何を使い、何をこの予想だけで作るか。それらをどのフォルダ（パッケージ）・ファイルに置くか。

**結論: 出走の記録を読む・人気とオッズを決める・LightGBM と CatBoost で学習して平均する、は共通の部品をそのまま使う。この予想だけに作るのは、設定を読むクラス、特徴量を登録して選んだものだけを計算するクラス、人気範囲と条件で絞る部品、券種オッズを読む部品、保存の部品、回収率の評価である。流れは `workflow.py` の関数（`train`・`predict`・`test_evaluation`）が進める。**

- 用語の意味（public メソッド・オーケストレーション・インターフェース・リポジトリ）は [手本の 02 の「機械学習の用語」](../近走と適性から3着以内を予想/02-glossary.md#機械学習の用語) を参照。
- 分け方の決まり（1ファイル1クラス、1クラス1つの仕事、1 SQL につき1つのリポジトリ）は [手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) を参照。**今のコードには、この決まりと違うところがある**（下の「4. 手本の決まりと違うところ」）。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。

## 1. 共通の部品と、この予想だけの部品の分け方

**共通の部品には手を入れず、そのまま使う。** ほかの予想モデルに影響を出さないためである（[15-decisions.md](15-decisions.md#2-既存の予想モデルを変えずに作るか)）。

| 仕事 | 使う共通の部品（`src/yosou/shared/`） | この予想で足したもの |
|---|---|---|
| 出走の記録を読む | `HistoryRecordsLoader`（学習）・`RaceRecordsLoader`（予測）・`FlatRunnerFilter` | 券種オッズを出走の行に足す `ExtraDataLoader` |
| 人気とオッズを決める（予測） | `PopularityApplier`・`OddsResolver`・`AnnouncedOddsRepository` | ― |
| 特徴量を作る | まとまり A〜K の `FeatureGroup` と `FieldComparisonFeatures` | 1個ずつ選べる形にする `GroupColumn`、登録と計算順の `FeatureRegistry`・`SelectedFeatureBuilder`、券種オッズの特徴量 |
| 学習データの入れ物 | `TrainingData`・`PredictionData` | ― |
| オッズの基準 | `Top3Baseline`・`MarketPlaces`・`BaselineLogit` | 目的ごとに基準を選ぶ `OddsBaseline` |
| 学習・予測 | `LightGbmModel`・`CatBoostModel`・`EnsembleModel` | ― |
| ハイパーパラメータ | `HyperparameterSettings`・`SettingsNameCheck`・`SettingsOverlay` | YAML の値を当てはめる `settings.py` |
| 保存 | `ModelRepository` | 設定と特徴量の形を一緒に保存する `ModelStore` |
| 評価 | ― | `evaluation.py`（当たり具合と回収率） |
| 複勝の払戻の見積もり | `PlacePriceEstimator` | ― |

## 2. パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。パッケージ名は `custom_binary`（利用者が組み立てる二値分類）とした。

```text
src/yosou/custom_binary/
├── __main__.py               コマンドの入口（command.py を呼ぶだけ）
├── command.py                サブコマンド（features・train・predict・evaluate）の引数
├── workflow.py               学習・予測・テスト評価の流れ（関数）
├── settings.py               設定ファイル（YAML）を読む
├── row_condition.py          条件1つ（1つの特徴量の値の範囲）
├── row_conditions.py         条件の組（すべてに当てはまる馬を残す）
├── odds_baseline.py          目的ごとのオッズの基準
├── dataset.py                学習データ・予測用データを作る（全頭で計算してから絞る）
├── evaluation.py             当たり具合と回収率
├── model_store.py            学習したモデルを、設定と一緒に保存・読込する
├── feature/                  特徴量の決まり・登録・計算
├── extra_data/               追加の元データ（券種オッズ）を読んで出走の行に足す
├── repository/               券種オッズの SQL（1 SQL につき1つのリポジトリ）
└── tests/                    テスト。合成DB だけを使う（keiba-yosou の決まり）
```

学習したモデルは、Git の対象外の `reports/custom_binary/<設定の name>/` に、設定ごとに保存する（[12-lightgbm.md](12-lightgbm.md#6-保存)）。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `custom_binary` → `shared`。`shared` から参照しない | 参照が循環すると、1つを直すと全部に響く |
| 特徴量は `feature/` の登録（`registrations.py`）だけで増やせるようにする。学習・コマンドに特徴量ごとの分岐を書かない | 特徴量を足すたびに、学習やコマンドを直さずに済む（[09-features.md](09-features.md#特徴量を足す仕組み)） |
| 券種オッズの SQL は `repository/` に置き、`src/` から `research/` を import しない | 研究のコードは試しのもので、予想のパッケージが依存すると研究を直せなくなる |

## 3. この予想だけのクラスの一覧

### 設定 — `settings.py`・`row_condition.py`・`row_conditions.py`

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `ModelSettings` | 1つのモデルの設定（名前・選んだ特徴量・目的・時点・人気範囲・期間・ハイパーパラメータ・条件・オッズの基準）を持つ値。YAML と保存した設定から作る | `load(YAML のパス, 登録)`、`from_values(値, 特徴量, 登録)`、`from_saved(保存した値, 登録)`、`as_dict()` | `FeatureRegistry`、`RowConditions`、共通の `HyperparameterSettings` |
| `UniqueKeyLoader` | 同じキーと、文字列でないキーをエラーにする YAML の読み込み | ―（PyYAML から使う） | ― |
| `PopularityRange` | 人気範囲（最小・最大。片方だけでもよい） | `bounded`、`as_dict()` | ― |
| `RowCondition` | 条件1つ。数値は min〜max、カテゴリは値のリスト。欠損値は当てはまらないとする | `parse(名前, 値, 型)`、`mask(列)`、`label()` | ― |
| `RowConditions` | 条件の組。すべてに当てはまる馬だけを残す | `parse(値, 登録, 時点)`、`mask(特徴量の表)`、`names` | `RowCondition` |

### 特徴量 — `feature/`

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `FeatureDefinition`（インターフェース） | 特徴量1個の決まり。名前・説明・型・利用可能な時点・依存項目・（省略できる）追加の元データと、1列を返す `compute` | `compute(記録, 依存項目の列)` | ― |
| `FeatureRegistry` | 登録された特徴量の一覧。名前の重複・未登録の依存先・循環・時点に合わない特徴量を検出し、依存の順に並べる | `order(選んだ特徴量, 時点)`、`read_selection(特徴量テキスト, 時点)`、`catalog(選んだ特徴量)`、`schema(選んだ特徴量)` | ― |
| `SelectedFeatureBuilder` | 選んだ特徴量と条件の列を、依存の順に1回ずつ計算する。共通のまとまりは1回の計算の中で使い回す | `build(記録)`、`sources` | `FeatureRegistry`、各 `FeatureDefinition` |
| `GroupColumn` | 共通のまとまり（A〜K）の1列を、1個ずつ選べる形にする | `compute(…)` | 共通の `FeatureGroup` |
| `PoolProbability` | 券種オッズから見た確率（6個） | `compute(…)` | ― |
| `PoolGap` | 券種オッズから見た確率と、単勝オッズから見た確率の対数の差（6個） | `compute(…)` | 共通の `MarketPlaces` |
| `registrations.py` の `default_registry()` | 選べる特徴量の一覧を作る（共通の 78個 + 券種オッズの 12個 + 利用者が足したもの） | `default_registry()` | 上のクラス |

### 追加の元データ — `extra_data/`・`repository/`

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `ExtraDataLoader` | 選んだ特徴量が使う追加の元データを読み、レースID・馬番で出走の行に列を足す。行の並びは変えない | `attach(出走の行, 対象のレース, 元データの名前)` | 各元データのクラス |
| `PoolProbabilitySource` | 追加の元データ「券種オッズ」。6つの券種の確率を1つの表にする | `read(接続, 対象のレース)` | 下の2つのリポジトリ |
| `FirstHorsePoolRepository` | 馬単・3連単から「1着になる確率」を読む SQL | `read(券種, 対象のレース)` | ― |
| `AllHorsesPoolRepository` | 馬連・ワイド・3連複・複勝から「組に入る確率」を読む SQL | `read(券種, 対象のレース)` | ― |
| `PoolSpec` | どの表のどの列をどう足すかの決まり（6券種ぶんの値 `POOLS`） | ―（値） | ― |

### データ・保存・評価・流れ

| 名前 | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `CustomDataset` | 学習データ・予測用データを作る。全頭で特徴量を作ってから、人気範囲と条件で絞る。予測では、選んだ特徴量に要る情報がそろっているかを確かめる | `training()`、`prediction(レースID, 人気, オッズ)` | 共通のローダー、`ExtraDataLoader`、`SelectedFeatureBuilder`、`OddsBaseline` |
| `dataset.py` の `select_training_data()` | 全頭の特徴量の表から、人気範囲と条件に当てはまる馬の学習データを作る（研究で何通りも絞るときにも使う） | ―（関数） | `RowConditions` |
| `OddsBaseline` | 目的ごとのオッズの基準（勝利は勝率、馬券内は3着以内率、馬券外はその裏返し）のロジット | `build(出走の行)` | 共通の `MarketPlaces`・`Top3Baseline` |
| `ModelStore` | 学習した2つのモデルと、設定・特徴量の形・コードの版・保存形式の版を保存する。読み込むときは、特徴量の形が今のコードと同じかを確かめる | `save(…)`、`load(登録)` | 共通の `ModelRepository` |
| `evaluation.py` | 当たり具合（件数・正例率・ログ損失・Brier・AUC・人気別）と回収率（[16-evaluation.md](16-evaluation.md)） | `evaluate(…)`、`paybacks(…)` | 共通の `PlacePriceEstimator` |
| `workflow.py` | 流れを進める関数。`fit` は学習だけ、`train` は読む → 学習 → 保存、`predict` は1レースの予測、`test_evaluation` はテスト期間の評価 | `train(…)`、`predict(…)`、`test_evaluation(…)`、`fit(…)`、`report(…)` | 上のすべて |
| `CommandLine` | 入口。サブコマンドの引数を読み、`workflow.py` を呼び、結果の表を出す | `run(引数)` | `workflow.py` |

## 4. 手本の決まりと違うところ

**今のコードは、計画書に沿って先に作り、あとからこの設計書を書いた。** そのため、手本の決まりと違うところが残っている。動きには影響しないが、直すなら次のとおりである。

| 違うところ | 手本の決まり | 直すなら |
|---|---|---|
| 流れを進めるのが `workflow.py` の関数 | 流れを進めるクラス（`TrainingWorkflow`・`PredictionWorkflow`）を置き、受け渡すだけにする | `TrainingWorkflow`・`PredictionWorkflow`・`TestEvaluationWorkflow` のクラスにする |
| `settings.py` に3つのクラス、`dataset.py`・`evaluation.py` に関数が並ぶ | 1ファイル1クラス | クラスごとにファイルを分ける（`RowCondition` のように） |
| 直下にファイルが並ぶ | 仕事の領域（`dataset/`・`setting/`・`workflow/`・`command/`）でフォルダを分ける | 手本と同じフォルダに分ける |
| 初期値のハイパーパラメータを `form_aptitude_top3` の設定ファイルから読む | 予想のパッケージどうしで import しない | 初期値の設定ファイルを `custom_binary` に持つ（[14-hyperparameter-settings.md](14-hyperparameter-settings.md#この予想で違う点)） |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-26 |
