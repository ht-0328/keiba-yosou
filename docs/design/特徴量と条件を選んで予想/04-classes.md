# 04 クラスとパッケージの設計

**この文書で決めること:** この予想のクラスが何をするか。共通の部品（`src/yosou/shared/`）の何を使い、何をこの予想だけで作るか。それらをどのフォルダ（パッケージ）・ファイルに置くか。

**結論: 出走の記録を読む・人気とオッズを決める・LightGBM と CatBoost で学習して平均する、は共通の部品をそのまま使う。この予想だけに作るのは、設定を読むクラス、特徴量を登録して選んだものだけを計算するクラス、人気範囲と条件で絞る部品、券種オッズを読む部品、保存の部品、回収率の評価である。流れは、手本と同じく流れを進めるクラス（`TrainingWorkflow`・`PredictionWorkflow`・`TestEvaluationWorkflow`）が進める。**

- 用語の意味（public メソッド・オーケストレーション・インターフェース・リポジトリ）は [手本の 02 の「機械学習の用語」](../近走と適性から3着以内を予想/02-glossary.md#機械学習の用語) を参照。
- 分け方の決まり（1ファイル1クラス、1クラス1つの仕事、1 SQL につき1つのリポジトリ、入れ子は1段まで）は [手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) を参照。この予想も、この決まりに従う（下の「4. 手本の決まりと違うところ」）。
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
| ハイパーパラメータ | `HyperparameterSettings`・`SettingsNameCheck`・`SettingsOverlay` | YAML の値を当てはめる `HyperparameterReader` と、この予想の初期値のファイル（`setting/default_settings.toml`） |
| 保存 | `ModelRepository` | 設定と特徴量の形を一緒に保存する `ModelStore` |
| 評価 | ― | `evaluation/`（当たり具合と回収率） |
| 複勝の払戻の見積もり | `PlacePriceEstimator` | ― |

## 2. パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。パッケージ名は `custom_binary`（利用者が組み立てる二値分類）とした。フォルダの分け方は、手本（`form_aptitude_top3`）の `command/`・`workflow/`・`dataset/`・`feature/`・`setting/` にそろえ、この予想にある仕事（評価・追加の元データ・保存）のフォルダを足した。

```text
src/yosou/custom_binary/
├── __main__.py               コマンドの入口（command/ を呼ぶだけ）
├── command/                  サブコマンド（features・train・predict・evaluate）の引数と、結果の表
├── workflow/                 学習・予測・テスト期間の評価の流れ（ほかを順に呼ぶだけ）
├── setting/                  設定ファイル（YAML）を読む。人気範囲・条件。ハイパーパラメータの初期値のファイル
├── dataset/                  学習データ・予測用データを作る（全頭で計算してから絞る）。オッズの基準
├── evaluation/               当たり具合と回収率。予測の期待値
├── store/                    学習したモデルを、設定と一緒に保存・読込する。その置き場所
├── feature/                  特徴量の決まり・登録・計算
├── extra_data/               追加の元データ（券種オッズ）を読んで出走の行に足す
├── repository/               券種オッズの SQL（1 SQL につき1つのリポジトリ）
└── tests/                    テスト。合成DB だけを使う（keiba-yosou の決まり）
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く（手本と同じ）。ファイルの名前は、クラスの名前を小文字と `_` にしたもの（`TrainingWorkflow` → `training_workflow.py`）。学習したモデルは、Git の対象外の `reports/特徴量と条件を選んで予想/<設定の name>/` に、設定ごとに保存する（[12-lightgbm.md](12-lightgbm.md#6-保存)）。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `custom_binary` → `shared`。`shared` から参照しない。ほかの予想のパッケージ（`form_aptitude_top3` など）も参照しない | 参照が循環すると、1つを直すと全部に響く。ほかの予想の都合が入り込まない |
| パッケージの中も一方向にする: `command` → `workflow` → `store`・`evaluation` → `dataset` → `setting` → `feature` → `extra_data` → `repository` | 同上 |
| 流れのクラス（`workflow/`）は、ほかのクラスを呼んで受け渡すだけにする。結果を表にするのは `command/` | 流れを変えるときと、中身や見せ方を変えるときで、直すクラスが分かれる |
| 特徴量は `feature/` の登録（`registrations.py`）だけで増やせるようにする。学習・コマンドに特徴量ごとの分岐を書かない | 特徴量を足すたびに、学習やコマンドを直さずに済む（[09-features.md](09-features.md#特徴量を足す仕組み)） |
| 券種オッズの SQL は `repository/` に置き、`src/` から `research/` を import しない | 研究のコードは試しのもので、予想のパッケージが依存すると研究を直せなくなる |
| 保存物にクラスの置き場所を埋め込まない（設定は JSON、モデルは共通の `ModelRepository` が書く） | クラスを別のフォルダに動かしても、前に保存したモデルを読める |

## 3. この予想だけのクラスの一覧

### command/ — コマンド

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `CommandLine` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す | `run(引数)` | 下の4つのコマンド |
| `FeaturesCommand` | `features`: 選べる特徴量の一覧 | `run(引数)` | `DefaultRegistry` |
| `TrainCommand` | `train`: 設定の YAML で学習して保存し、検証期間の成績を出す | `run(引数)` | `TrainingWorkflow`、`TrainingTables` |
| `PredictCommand` | `predict`: 保存したモデルで1レースを予想する | `run(引数)` | `LoadedModel`、`PredictionWorkflow`、`PredictionTable` |
| `EvaluateCommand` | `evaluate`: 未学習のテスト期間で評価する | `run(引数)` | `TestEvaluationWorkflow` |
| `CommonOptions` | サブコマンドに共通の引数（`--format`・`--out`・`--db`・`--models`） | `add_output(…)`、`add_db(…)`、`add_models(…)` | ― |
| `TrainingTables` | 学習の結果（設定の要約・検証期間の成績と回収率）を表にする | `tables()` | ― |
| `PredictionTable` | 予測の結果を表にする。道具 `tools/当日の予想/` も使う | `table(予測の結果)` | ― |

### workflow/ — 流れを進める

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `TrainingWorkflow` | 学習の流れ。設定を読む → 学習データを作る → 元DB を閉じる → 学ぶ → 検証期間で評価する → 保存する。モデルの置き場所は、作るときに受け取れる（省略すると `reports/特徴量と条件を選んで予想/`） | `run(設定ファイルのパス)`、`fit_and_save(学習データ, 設定, 保存先)` | `ModelSettings`、`ModelStore`、`CustomDataset`、`EnsembleFitter`、`ModelReport`、`PlacePriceFit` |
| `PredictionWorkflow` | 予測の流れ。人気とオッズを決める → 予測用データを作る → 2つのモデルの確率の平均と期待値を出す → 確率の高い順に並べる。開いた元DB を受け取り、何レースも続けて使い回せる | `run(レースID, 読んだモデル, 人気, オッズ)` | 共通の `OddsResolver`・`PopularityApplier`、`CustomDataset`、`PredictionValues` |
| `TestEvaluationWorkflow` | テスト期間の評価の流れ。保存したモデルで学習データを作り直し、テスト期間の当たり具合と回収率を出して `test_evaluation.json` に書く | `run(モデルのフォルダ)` | `ModelStore`、`CustomDataset`、`ModelReport` |
| `EnsembleFitter` | 学習期間で2つのモデルを学び、検証期間で早期終了を決める。学ぶ前に、データが空・正解が1クラス・特徴量が設定と違うときは止める。保存はしない（研究の探索でも使う） | `fit(学習データ, 設定)` | 共通の `LightGbmModel`・`CatBoostModel`・`EnsembleModel` |
| `LoadedModel` | 予想に使う、保存したモデル一式（設定・2つのモデルの平均・複勝の想定払戻倍率） | `load(モデルのフォルダ, 登録)` | `ModelStore` |
| `TrainedModel` | 学習の流れの結果（設定・保存先・検証期間の成績） | ―（値） | ― |

### setting/ — 設定

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `ModelSettings` | 1つのモデルの設定（名前・選んだ特徴量・目的・時点・人気範囲・期間・ハイパーパラメータ・条件・オッズの基準）を持つ値。YAML と保存した設定から作る | `load(YAML のパス, 登録)`、`from_values(値, 特徴量, 登録)`、`from_saved(保存した値, 登録)`、`as_dict()` | `FeatureRegistry`、下のクラス |
| `UniqueKeyLoader` | 同じキーと、文字列でないキーをエラーにする YAML の読み込み | ―（PyYAML から使う） | ― |
| `YamlMapping` | YAML の1つの組が、知っているキーだけでできているかを確かめる | `check(値, 書けるキー, 場所)` | ― |
| `PopularityRange` | 人気範囲（最小・最大。片方だけでもよい） | `bounded`、`as_dict()` | ― |
| `TrainingPeriodReader` | `training`（学習・検証・テストの期間の区切り）を読む | `read(値)` | 共通の `TrainingPeriod` |
| `HyperparameterReader` | `lightgbm`・`catboost` を、この予想の初期値のファイルに上書きして読む。名前・型・範囲を確かめる | `read(値)` | 共通の `HyperparameterSettings`・`SettingsNameCheck`・`SettingsOverlay` |
| `RowCondition` | 条件1つ。数値は min〜max、カテゴリは値のリスト。欠損値は当てはまらないとする | `parse(名前, 値, 型)`、`mask(列)`、`label()` | ― |
| `RowConditions` | 条件の組。すべてに当てはまる馬だけを残す | `parse(値, 登録, 時点)`、`mask(特徴量の表)`、`names` | `RowCondition` |

初期値のファイル `setting/default_settings.toml` の値は、手本の初期値と同じである（[14-hyperparameter-settings.md](14-hyperparameter-settings.md#この予想で違う点)）。

### dataset/ — 学習データ・予測用データ

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `CustomDataset` | 学習データ・予測用データを作る。全頭で特徴量を作ってから、人気範囲と条件で絞る | `training()`、`prediction(レースID, 人気, オッズ)` | 共通のローダー、`ExtraDataLoader`、`SelectedFeatureBuilder`、下のクラス |
| `TrainingDataSelector` | 全頭の特徴量の表から、人気範囲と条件に当てはまる馬の学習データを作る（研究で何通りも絞るときにも使う） | `select(出走の行, 特徴量の表, 設定, 特徴量の一覧)` | `PopularityFilter`、`RowConditions`、`BinaryTargetLabeler`、`OddsBaseline` |
| `PopularityFilter` | 人気範囲に入る馬を選ぶ。範囲があるのに人気が不明なら止める | `mask(出走の行, 人気範囲)` | ― |
| `BinaryTargetLabeler` | 目的変数（馬券内・馬券外・勝利）を付ける | `labels(出走の行, 目的)` | ― |
| `AnnouncementCheck` | 予測の前に、選んだ特徴量に要る今回の情報（券種オッズ・単勝オッズ・馬番・馬体重・馬場状態など）がそろっているかを確かめる | `check(出走の行)` | ― |
| `OddsBaseline` | 目的ごとのオッズの基準（勝利は勝率、馬券内は3着以内率、馬券外はその裏返し）のロジット | `build(出走の行)` | 共通の `MarketPlaces`・`Top3Baseline` |

### evaluation/ — 当たり具合と回収率

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `ModelReport` | 1つの期間での当たり具合と回収率をまとめて出す（[16-evaluation.md](16-evaluation.md)） | `of(モデル, データ, 目的, 学習データ)` | `ProbabilityScores`、`Paybacks`、`PlacePriceFit` |
| `ProbabilityScores` | 当たり具合（件数・正例率・ログ損失・Brier・AUC）を、モデルごとと人気ごとに出す | `evaluate(モデル, データ)`、`scores(正解, 確率)` | ― |
| `Paybacks` | 対象の全頭・各レースの確率1位・期待値の線ごとに買った回収率 | `of(データ, 確率, 目的, 想定払戻倍率)` | `BetResult`、`ExpectedValue` |
| `BetResult` | 選んだ馬を単勝・複勝1点100円ずつ買った結果 | `of(データ, 買う馬, 買い方の名前)` | `BootstrapLowerBound` |
| `BootstrapLowerBound` | 回収率の下限（開催日を丸ごと取り直したときの90%の幅の下側） | `of(開催日, 払戻)` | ― |
| `ExpectedValue` | 学習・評価のデータの期待値 | `of(データ, 確率, 目的, 想定払戻倍率)` | `PlaceProbability` |
| `PlaceProbability` | 3着以内の確率。全頭がそろったレースだけ、合計を3（7頭以下は2）にそろえ直す | `of(データ, 確率, 目的)` | ― |
| `PredictionValues` | 予測した1レースの期待値とその材料（その時点のオッズで、`ExpectedValue` と同じ計算） | `of(確率, 目的, オッズ, 想定払戻倍率)` | ― |
| `PlacePriceFit` | 複勝の想定払戻倍率を、学習期間の払戻から求める | `fit(学習データ)` | 共通の `PlacePriceEstimator` |

### store/ — 保存

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `ModelStore` | 学習した2つのモデルと、設定・特徴量の形・コードの版・保存形式の版を保存する。読み込むときは、特徴量の形が今のコードと同じかを確かめる。テスト期間の成績も書く | `save(…)`、`load(登録)`、`place_price()`、`save_test_evaluation(成績)` | 共通の `ModelRepository`、`CodeVersion` |
| `CodeVersion` | 学習したときのコードの版（Git のコミットと、Python ソースのハッシュ） | `current()` | ― |

置き場所（`reports/特徴量と条件を選んで予想/`）は `store/model_location.py` の `MODELS_ROOT` に1か所だけ書く。

### feature/ — 特徴量

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `FeatureDefinition`（インターフェース） | 特徴量1個の決まり。名前・説明・型・利用可能な時点・依存項目・（省略できる）追加の元データと、1列を返す `compute` | `compute(記録, 依存項目の列)` | ― |
| `FeatureRegistry` | 登録された特徴量の一覧。名前の重複・未登録の依存先・循環・時点に合わない特徴量を検出し、依存の順に並べる | `order(選んだ特徴量, 時点)`、`read_selection(特徴量テキスト, 時点)`、`catalog(選んだ特徴量)`、`schema(選んだ特徴量)` | ― |
| `SelectedFeatureBuilder` | 選んだ特徴量と条件の列を、依存の順に1回ずつ計算する。共通のまとまりは1回の計算の中で使い回す | `build(記録)`、`sources` | `FeatureRegistry`、各 `FeatureDefinition` |
| `GroupColumn` | 共通のまとまり（A〜K）の1列を、1個ずつ選べる形にする | `compute(…)` | 共通の `FeatureGroup` |
| `BuiltinFeatures` | 共通の特徴量（78個）を、1個ずつの `GroupColumn` にして並べる | `all()` | `GroupColumn` |
| `PoolProbability` | 券種オッズから見た確率（6個） | `compute(…)` | ― |
| `PoolGap` | 券種オッズから見た確率と、単勝オッズから見た確率の対数の差（6個） | `compute(…)` | 共通の `MarketPlaces` |
| `PoolFeatureList` | 券種オッズの特徴量（12個）を並べる | `all()` | `PoolProbability`、`PoolGap` |
| `DefaultRegistry` | 選べる特徴量の一覧を作る（共通の 78個 + `registrations.py` の `ADDITIONAL_FEATURES`（券種オッズの 12個 + 利用者が足したもの）） | `build()` | `BuiltinFeatures`、`FeatureRegistry` |

新しい特徴量を足す場所は `registrations.py` の `ADDITIONAL_FEATURES`（値の一覧だけを置くファイル）である（[09-features.md](09-features.md#特徴量を足す仕組み)）。

### extra_data/・repository/ — 追加の元データ

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `ExtraDataLoader` | 選んだ特徴量が使う追加の元データを読み、レースID・馬番で出走の行に列を足す。行の並びは変えない | `attach(出走の行, 対象のレース, 元データの名前)` | 各元データのクラス |
| `PoolProbabilitySource` | 追加の元データ「券種オッズ」。6つの券種の確率を1つの表にする | `read(接続, 対象のレース)` | 下の2つのリポジトリ |
| `RaceRelation` | 予想する1レースだけを対象にする関係（SQL）。レースIDは数字だけを受け付ける | `of(レースID)` | ― |
| `FirstHorsePoolRepository` | 馬単・3連単から「1着になる確率」を読む SQL | `read(券種, 対象のレース)` | `PoolOddsRowsSql` |
| `AllHorsesPoolRepository` | 馬連・ワイド・3連複・複勝から「組に入る確率」を読む SQL | `read(券種, 対象のレース)` | `PoolOddsRowsSql` |
| `PoolOddsRowsSql` | 上の2つのリポジトリに共通の、SQL の前半（`WITH` の中身。確定か最新の断面の、買い目ごとの 1/オッズ）を作る。SQL を流すのは各リポジトリ | `with_clause(券種, 対象のレース)` | ― |
| `PoolSpec` | どの表のどの列をどう足すかの決まり（6券種ぶんの値 `POOLS`） | ―（値） | ― |

## 4. 手本の決まりと違うところ

**直した（2026-09-30）。** 今のコードは、計画書に沿って先に作り、あとからこの設計書を書いたため、はじめは手本の決まりと違うところが残っていた。挙動を変えずに、次のとおり直した。保存済みのモデルは、そのまま読める（保存物にクラスの置き場所を埋め込んでいないため）。

| 違っていたところ | 手本の決まり | 直したこと |
|---|---|---|
| 流れを進めるのが `workflow.py` の関数（`train`・`predict`・`test_evaluation`・`fit`・`report`） | 流れを進めるクラスを置き、受け渡すだけにする | `workflow/` に `TrainingWorkflow`・`PredictionWorkflow`・`TestEvaluationWorkflow` を置いた。学ぶ部分は `EnsembleFitter`、評価をまとめる部分は `ModelReport`、結果の表は `command/` に分けた |
| `settings.py` に3つのクラス、`dataset.py`・`evaluation.py`・`model_store.py` に関数が並ぶ | 1ファイル1クラス | クラスごとにファイルを分けた（関数はクラスにした。例: `select_training_data()` → `TrainingDataSelector`、`paybacks()` → `Paybacks`） |
| 直下にファイルが並ぶ | 仕事の領域でフォルダを分ける | 手本と同じ `command/`・`workflow/`・`dataset/`・`setting/` に分け、`evaluation/`・`store/` を足した |
| 初期値のハイパーパラメータを `form_aptitude_top3` の設定ファイルから読む | 予想のパッケージどうしで import しない | 初期値の設定ファイルを `custom_binary/setting/` に持った（値は同じ） |
| `feature/`・`extra_data/`・`repository/` に関数だけのファイルが5つある（`default_registry()`・`builtin_features()`・`pool_features()`・`race_relation()`・`pool_odds_rows()`） | 1ファイル1クラス | それぞれクラスにした（`DefaultRegistry`・`BuiltinFeatures`・`PoolFeatureList`・`RaceRelation`・`PoolOddsRowsSql`）。特徴量を足す場所（`registrations.py` の `ADDITIONAL_FEATURES`）は変えていない |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-26 |
| 更新日 | 2026-09-30（手本の決まりに合わせてフォルダとクラスを分けたので、パッケージ構成とクラスの一覧を今のコードに合わせた） |
