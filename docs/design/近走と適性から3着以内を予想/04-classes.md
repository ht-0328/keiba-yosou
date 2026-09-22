# 04 クラスとパッケージの設計

**この文書で決めること:** データを読む・特徴量を作る・学習する・予測するを、どのクラスにやらせるか。それらのクラスを順に呼んで流れを進める（オーケストレーションする）のは、どのクラスか。クラスを、どのフォルダ（パッケージ）・ファイルに置くか。

**結論: 学習の流れは `TrainingWorkflow`、予測の流れは `PredictionWorkflow` が進める。** この2つは、ほかのクラスを順に呼んでデータを受け渡すだけで、自分では計算しない。仕事は1つのクラスに1つずつ分け、1つのファイルに1つのクラスを置く。元DB を読む SQL は、1つの SQL につき1つのリポジトリにして、`repository/` にまとめる。

- 用語の意味（public メソッド・オーケストレーション・インターフェース・リポジトリ・エンコーダー）は [02-glossary.md](02-glossary.md) を参照。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。

## 分け方の決まり

| 決まり | 理由 |
|---|---|
| 1つのファイルに、1つのクラスを置く | ファイルの名前を見れば、中のクラスが分かる。開いたファイルに、関係の無いクラスが混ざらない |
| 1つのクラスに、1つの仕事だけをやらせる | 「〜と〜と〜をするクラス」は、読んでもすぐに分からず、直すときに関係の無いところまで壊しやすい |
| 1つの SQL につき、1つのリポジトリにする。リポジトリは `repository/` にまとめる | SQL を読みたいとき、開くファイルが1つで済む。元DB の表や列が変わったとき、直す場所が `repository/` の中に収まる |
| リポジトリを順に呼んで結果を集める仕事は、リポジトリとは別のクラスにする（`EntryRecordsLoader` など） | 「SQL を1本流す」と「何本かの結果を集める」は、別の仕事だからである |
| if 文・for 文の入れ子は、基本は作らない。あっても1段まで | 入れ子が深いと、どの条件のときにどこを通るかを追いにくい。中身を名前の付いたメソッドに出す |
| Workflow の2つは、ほかのクラスを呼んで受け渡すだけにする。計算・判断・SQL は書かない | 流れを変えるときと、中身を変えるときで、直すクラスが分かれる |
| LightGBM と CatBoost は、同じ `ProbabilityModel` の決まりを守る | Workflow と `EnsembleModel` が、モデルの違いを知らずに済む。モデルごとの違いは、それぞれのクラスとエンコーダーの中に閉じる |
| 学習データと予測用データは、同じ `DatasetBuilder` と `FeatureBuilder` で作る | 学習と予測で、特徴量の中身がずれないようにする（[11-leak-prevention.md](11-leak-prevention.md) の 4） |
| フォルダの名前は、中に何があるかが名前だけで分かるようにする。機械学習のモデルを置くフォルダは `ml_model` とし、`model` としない | `model` は、データの形を表す「データモデル」と読める |
| `Manager`・`Processor` のような、何でも入る名前を付けない | 名前から仕事が分かり、関係の無い仕事が足されにくい |

## パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。この予想のパッケージ名は、予想のやり方が分かる `form_aptitude_top3`（form = 近走、aptitude = 適性、top3 = 3着以内）とする。

**下の一覧のクラスのうち、予想で変わらないものは `src/yosou/shared/` に置き、ほかの予想（[人気馬が4着以下になるかを予想](../人気馬が4着以下になるかを予想/04-classes.md#1-共通の部品とこの予想だけの部品の分け方)）と共通で使う。** この予想のパッケージには、この予想だけの決めごと（入れる行の選び方・目的変数・特徴量の一覧・初期値の設定ファイル）と、それらを渡して共通の部品を組み立てるところ（`command/`・`workflow/`・`dataset/dataset_assembly.py`）だけが残る。

```text
src/yosou/shared/               両方の予想から使う部品
├── command/                    コマンドの部品のうち、予想に依らないもの（共通の引数・結果の表）
├── evaluation/                 当たり具合を測る。学習の結果の入れ物（TrainingReport）
├── ml_model/                   機械学習のモデル（LightGBM・CatBoost・エンコーダー・平均）
├── dataset/                    学習データ・予測用データを作る（入れる行と目的変数はインターフェースで受け取る）
├── feature/                    特徴量を作る（まとまり A〜I と、過去の記録から数える部品）
│   ├── group/                  まとまり A〜I ごとに1クラス
│   └── history/                過去の記録から数える部品
├── repository/                 データの読み書き。1 SQL につき 1 リポジトリ
├── setting/                    ハイパーパラメータの設定ファイルを読む（初期値のファイルは予想ごと）
├── workflow/                   学習の流れ（TrainingWorkflow）
└── tests/                      共通の部品のテストと、テスト用の合成DB（synthetic_season/）

src/yosou/form_aptitude_top3/   近走と適性から3着以内を予想する
├── __main__.py                 コマンドの入口（command/ を呼ぶだけ）
├── command/                    コマンド（train・predict）の引数。入口
├── workflow/                   予測の流れ（ほかを順に呼ぶだけ）と、予測を出す時点
├── dataset/                    入れる行の選び方・目的変数（3着以内）・予測に使うオッズの決め方と、DatasetBuilder の組み立て
├── feature/                    まとまり J（市場の評価）を作る。この予想の特徴量 74個の一覧（CATALOG）
├── setting/                    ハイパーパラメータの初期値のファイル
└── tests/                      この予想の組み立てのテスト。合成DB だけを使う（keiba-yosou の決まり）
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く。ファイルの名前は、クラスの名前を小文字と `_` にしたもの（`TrainingWorkflow` → `training_workflow.py`）。学習したモデルは、Git の対象外の `reports/form_aptitude_top3/models/` に、時点ごとに保存する。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `form_aptitude_top3` → `shared`。**`shared` から予想のパッケージを参照しない** | 片方の予想の都合が、もう片方に入り込まない |
| `shared` の中も一方向にする: `command` → `workflow` → `evaluation` → `ml_model` → `dataset` → `feature`。`dataset` は `repository` を、`ml_model` と `repository` は `setting` を使う | 参照が循環すると、1つを直すと全部に響く |
| 予想のパッケージの中も一方向にする: `command` → `workflow` → `dataset` → `feature` | 同上 |
| 予想ごとの違いは、`shared` のインターフェース（`SampleSelector`・`TargetLabeler`・`FeatureGroup`）を守るクラスと、特徴量の一覧（`FeatureCatalog`）と、初期値のファイルにして渡す | 共通のクラスの中に「どの予想か」の if 文が増えない |
| 各フォルダの `__init__.py` で外に出すのは、ほかのフォルダから使うクラスだけにする | 外に見せるものが少ないほど、中を変えても外に響かない |
| この構成は、作りながら動かしてよい | 作る前に決めた構成は、少ない情報で決めたものだからである |

事実表を作る SQL は `tools/共通/facts.py` のものを使い、同じ SQL を2か所に書かない（`FactTableRepository`・`RaceEntryTableRepository`）。そのために、`pyproject.toml` に `src` をパッケージとして入れる設定と、`tools/共通` を読める設定を入れてある。

## クラスの一覧

各見出しに、そのフォルダが `src/yosou/shared/` と `src/yosou/form_aptitude_top3/` のどちらにあるかを書く。

### workflow/ — 流れを進める（学習は `shared`、予測はこの予想のパッケージ）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `TrainingWorkflow` | 学習の流れを進める。設定を読み、渡された期間（`TrainingPeriod`）で学習データを作り、期間で分け、渡された時点（この予想は3つ全部）ごとに2つのモデルを学習して保存し、検証データで当たり具合を確かめる。**中身が2つ目の予想と同じなので `shared/workflow/` にある。** 学習する時点の並びとハイパーパラメータの初期値のファイルは、作られるときに受け取る。元DB が要るのは学習データを読む段だけなので、読む段と学習する段を分けて呼べる | `run(設定ファイルのパス)`、`read_training_data()`、`train(学習データ, 設定ファイルのパス)` |
| `PredictionWorkflow` | 予測の流れを進める。予測に使うオッズを決め、予測用データを作り、その時点のモデルを読み込み、2つの予測確率を平均する | `run(レースID, 時点, 渡されたオッズ=省略可)` |
| `TrainingReport` | 学習の結果の入れ物（使った期間・期間ごとのデータ・当たり具合・保存したフォルダ）。予想で変わらないので `shared/evaluation/` にある | ― |

### command/ — コマンド（入口はこの予想、部品は `shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `CommandLine` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す | `run(引数)` |
| `TrainCommand` | `train`: 学習する。期間の引数（`--warmup-from` `--train-from` `--valid-from` `--test-from`）から `TrainingPeriod` を作る。元DB は学習データを読む段だけ開き、学習のあいだはロックを持たない | `run(引数)` |
| `PredictCommand` | `predict`: 1レースを予測する。`--odds 馬番:オッズ` で単勝オッズを渡せる | `run(引数)` |
| `CommonArguments`（`shared`） | 2つのサブコマンドに共通の引数（`--models` `--db` `--format` `--out`）。モデルの既定の置き場所に使う予想の名前を受け取る | `add_to(parser)` |
| `TrainingReportTables`（`shared`） | 学習の結果を表にする | `tables()` |
| `PredictionTable`（`shared`） | 予測の結果を、確率の高い順の表にする。確率の列の名前を受け取る | `table()` |

### repository/ — データの読み書き（1 SQL につき 1 リポジトリ。`shared`）

| クラス | 読む・書くもの | 主な public メソッド |
|---|---|---|
| `FactTableRepository` | 事実表（一時表）を用意する | `ensure()` |
| `RaceEntryTableRepository` | 予測する1レースの出走馬に、事実表と同じ列を付けた一時表を作る | `build(レースID, 馬場状態コード, 単勝人気=省略可)` |
| `EntryRepository` | 出走の行（事実表の列） | `read(対象)` |
| `CareerCountRepository` | 出走別着度数（`ck`）。通算と、そのレースの条件に合う欄の、出走数と3着以内の数 | `read(対象)` |
| `PastRunRepository` | 過去走 | `read(対象)` |
| `WorkoutRepository` | 調教（坂路 `hc`・ウッド `wc`） | `read(対象)` |
| `WorkoutCoverageRepository` | 調教の記録が DB にある期間（コースごとの最初の調教日）。「記録が無い」と「調教していない」を区別するため（[09-features.md](09-features.md) の I） | `read()` |
| `PeopleDayRepository` | 騎手か調教師の、日ごとの出走数と3着以内の数 | `read(対象)` |
| `AnnouncedGoingRepository` | 速報の馬場状態（`we`） | `read(レースID)` |
| `AnnouncedWeightRepository` | 速報の馬体重（`wh`） | `read(レースID)` |
| `AnnouncedOddsRepository` | 締め切り前の単勝オッズ（`o1` の確定前の断面のうち、いちばん新しいもの）。断面は jvdata-store の `jvstore realtime` で入る（[07-prediction-timing.md](07-prediction-timing.md#予測のときのオッズの与え方)） | `read(レースID)` |
| `ScratchRepository` | 速報の出走取消・競走除外（`av`） | `read(レースID)` |
| `ModelRepository` | 時点ごとの学習済みモデルと、学習に使った設定のファイル（SQL ではなくファイルに読み書きする） | `save(時点, モデル, 設定)`、`load(時点)` |
| `TargetScope` | 「どの出走について読むか」を表す値。学習では「ある日以降の全部の出走」、予測では「1レースの出走馬」 | `since(日)`、`of_table(表)` |
| `CareerCountSql` | `CareerCountRepository` の SQL の式を作る部品 | `select_list()` |

取得していない DB には `ck`・`hc`・`wc`・`we`・`wh`・`av` の表が無い。そのときは、同じ列を持つ空の関係で代わりにし、SQL 1本のまま「行なし」を返す。

### dataset/ — 学習データ・予測用データを作る（`RunnerSelector` はこの予想、ほかは `shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `DatasetBuilder` | 入口。学習データか予測用データを作る。下のクラスを順に呼ぶだけ。入れる行（`SampleSelector`）・目的変数（`TargetLabeler`）・特徴量（`FeatureBuilder`）は、作られるときに受け取る | `build_training_data(期間)`、`build_prediction_data(レースID, 時点, 単勝人気=省略可, 単勝オッズ=省略可)` |
| `SampleSelector`・`TargetLabeler` | 入れる行の選び方と、目的変数の付け方の決まり（インターフェース）。守るクラスは予想ごとに作る | `training_samples`・`prediction_runners`・`keep_samples` / `build`・`label_name` |
| `TrainingPeriod` | 学習データの期間を区切る4つの日（ウォームアップ・学習・検証・テストの始まり）を表す値。順になっていなければエラー。[08-training-data.md](08-training-data.md) の 4 | `starting(学習の始まり, 検証の始まり, テストの始まり, ウォームアップの始まり=省略可)`、`default()` |
| `HistoryRecordsLoader` | 学習用に、ある日以降の全部の出走の記録を集める | `load(最初の日)` |
| `RaceRecordsLoader` | 予測用に、1レースの出走馬の記録を集める。速報（馬場状態・馬体重・取消）と、渡された人気・オッズを反映する | `load(レースID, 単勝人気=省略可, 単勝オッズ=省略可)` |
| `EntryRecordsLoader` | リポジトリを順に呼んで、対象の出走の記録を集める。SQL は持たない | `load(対象)` |
| `AnnouncedWeightApplier` | 速報の馬体重を、出走の行に反映する | `apply(出走の行, 速報の馬体重)` |
| `ScratchApplier` | 速報の出走取消・競走除外を、出走の行に反映する | `apply(出走の行, 馬番)` |
| `AnnouncedOddsApplier` | 予測に使う単勝オッズ（手で渡したものか、締め切り前のもの）を、出走の行に反映する。無ければ行はそのまま | `apply(出走の行, 馬番→オッズ)` |
| `RunnerSelector`（この予想） | 入れる行を選ぶ（[06-flowchart.md](06-flowchart.md) の図1）。この予想は全頭を入れるので、`keep_samples` はそのまま返す | `training_samples(出走の行, 学習データの始まり)`、`prediction_runners(出走の行, レースID)`、`keep_samples(特徴量の付いた行)` |
| `Top3TargetBuilder` | 目的変数を付ける（[10-target.md](10-target.md)）。当てさせる列は「3着以内」で、「1着」の列も付ける。穴馬の予想（`docs/design/穴馬が3着以内に入るかを予想/`）も同じ目的変数を使うので、2026-09-23 に `shared` へ移した（元の名前は `TargetBuilder`） | `build(サンプルの行)`、`label_name` |
| `OddsInput`（この予想） | 利用者が `--odds 馬番:オッズ` で渡した「馬番 → 単勝オッズ」を表す値。書き方が違えばエラー | `of(引数の文字列)`、`as_mapping()` |
| `OddsResolver`（この予想） | 予測に使う「馬番 → 単勝オッズ」を決める。渡されたオッズ → 元DB の締め切り前のオッズ → 無し（元DB の出走の行のオッズ）の順（[06-flowchart.md](06-flowchart.md#図2-予測に使うオッズの決め方)） | `resolve(レースID, 渡されたオッズ)` |
| `dataset_builder()`（この予想） | `RunnerSelector`・共通の `Top3TargetBuilder`・特徴量の一覧（`CATALOG`）とまとまりの並びを渡して、共通の `DatasetBuilder` を組み立てる関数（`dataset_assembly.py`） | `dataset_builder(接続)` |
| `RequiredInfoCheck` | 予測に要る情報（馬番・馬場状態・馬体重・単勝オッズ）が DB にあるかを確かめる | `check(特徴量)` |
| `PeriodSplitter` | 学習データを時期（`TrainingPeriod` の検証・テストの始まり）で、学習データ・検証データ・テストデータに分ける。分け方は次の設計書で決める（いまは仮の区切り） | `split(学習データ)` |
| `TrainingData`・`PredictionData`・`SplitData` | 学習データ・予測用データ・期間で分けたデータの入れ物（[08-training-data.md](08-training-data.md) の「列の種類」） | ― |

### feature/ — 特徴量を作る（一覧 `CATALOG` はこの予想、ほかは `shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `FeatureBuilder` | 入口。まとまりごとのクラスを順に呼んで、1つの表にする。特徴量の一覧（`FeatureCatalog`）とまとまりのクラスは、作られるときに受け取る。時点を受け取り、その時点で使う特徴量だけを返す | `build(記録, 時点)` |
| `FeatureCatalog` | 1つの予想が使う特徴量の一覧を表す値。この予想の一覧は `CATALOG = FeatureCatalog(BASE_FEATURES + J_FEATURES)`（74個） | `names`、`categorical`、`columns_for(時点)`、`categorical_columns_of(特徴量の表)` |
| `PredictionTiming` | 予測する時点（木曜・前日・当日）を表す値。時点の前後を答える（[07-prediction-timing.md](07-prediction-timing.md)） | `is_at_or_after(時点)`、`parse(書き方)` |
| `Feature`・`FeatureKind` | 特徴量の一覧の1行（名前・まとまり・型・いつから分かるか）と、その型。どの予想でも使う 71個は `feature_catalog.py` の `BASE_FEATURES`（[09-features.md](09-features.md) の表の写し） | `is_known_at(時点)` |
| `MarketFeatures`（この予想） | まとまり J（市場の評価）の3個を作る: 単勝オッズ、人気順位（オッズの小さい順）、オッズから見た勝率（1/オッズをレース内で合計 1 に）。`FeatureGroup` を守る | `build(記録)` |
| `EntryRecords` | 特徴量を作る元の記録の入れ物 | ― |
| `EntryColumns` | 出走の記録から列を選び、名前を付け直す | `select(出走の行)` |
| `FeatureGroup` | まとまりのクラスに共通の決まり（インターフェース） | `build(記録)` |
| `group/` の10クラス | まとまり A〜J ごとに1クラス: `RaceConditionFeatures`（A）、`HorseFeatures`（B）、`PeopleFeatures`（C）、`PreviousRunFeatures`（D）、`RecentFormFeatures`（E）、`AptitudeFeatures`（F）、`FieldComparisonFeatures`（G）、`PedigreeFeatures`（H）、`WorkoutFeatures`（I）、`PopularityHistoryFeatures`（J。人気を使う予想だけが渡す。この予想は使わない） | `build(記録)` |
| `history/` の7クラス | 過去の記録から数える部品: `AsOfLookup`（開催日の N 日前までで、いちばん新しい記録を引く）、`DatedRecords`（鍵と日付を持つ記録の表）、`RecentRunSummary`（近5走のまとめ）、`PopularityRunSummary`（近5走の人気のまとめ。まとまり J の材料）、`Top3Rate`（近1年の3着以内の割合）、`WorkoutLookup`（14日以内の調教）、`WorkoutCoverage`（調教の記録が DB にある期間。出走ごとに、そのコースの記録があるかを判定する） | ― |

「開催日より前のものだけから計算する」決まり（[11-leak-prevention.md](11-leak-prevention.md) の 2）は、`AsOfLookup` の1か所で守る。

### ml_model/ — 機械学習のモデル（`shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `ProbabilityModel` | 2つのモデルに共通の決まり（インターフェース）。これを守るクラスなら、Workflow は LightGBM か CatBoost かを区別せずに扱える | `fit`・`predict_proba`・`save`・`load` |
| `LightGbmModel` | LightGBM で学習・予測する（[12-lightgbm.md](12-lightgbm.md)） | `fit(学習データ, 検証データ)`、`predict_proba(データ)`、`save(パス)`、`load(パス)` |
| `LightGbmEncoder` | 特徴量を、LightGBM が受け取れる形に変える。学習データから作ったカテゴリの一覧を持つ（[12-lightgbm.md の 3.](12-lightgbm.md)） | `fit(学習データ)`、`transform(データ)` |
| `CatBoostModel` | CatBoost で学習・予測する（[13-catboost.md](13-catboost.md)） | `LightGbmModel` と同じ |
| `CatBoostEncoder` | 特徴量を、CatBoost が受け取れる形に変える（[13-catboost.md の 3.](13-catboost.md)） | `transform(データ)` |
| `EnsembleModel` | 2つのモデルの予測確率を平均する | `predict_proba(データ)` |

### setting/ — 設定ファイル（初期値のファイルはこの予想、読むクラスは `shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `HyperparameterSettings` | 2つのモデルの設定。設定ファイルを読む入口（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)）。初期値のファイルは予想ごとなので、パスを受け取る（この予想は `setting/default_settings.toml`） | `load(パス, 初期値のファイル)` |
| `LightGbmSettings`・`CatBoostSettings` | モデルごとの設定の値 | ― |
| `SettingsFile` | TOML のファイルを辞書として読む | `read()` |
| `SettingsNameCheck` | 書かれた名前が、初期値のファイルにあるかを確かめる | `check(書かれた設定, 場所)` |
| `SettingsOverlay` | 初期値に、利用者が書いた項目を重ねる | `apply(書かれた設定)` |

### evaluation/ — 当たり具合を測る（`shared`）

評価指標は [穴馬の 16 の「2. 評価指標」](../穴馬が3着以内に入るかを予想/16-evaluation.md#2-評価指標) で決めた（どの予想でも同じ）。ログ損失・AUC・Brier スコアと、各レースで確率がいちばん高い馬の3着以内率・複勝回収率、人気がいちばん上の馬（この予想では 1番人気）の同じ値、同じ人気の中での AUC を出す。

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `ModelEvaluator` | 1つの時点のモデル（LightGBM・CatBoost）と、その平均の当たり具合を測る | `evaluate(時点, アンサンブル, データ)` |
| `MetricCalculator` | 予測確率と正解から、評価指標を計算する | `log_loss`・`auc`・`brier`・`top_pick_place_rate` |
| `Evaluation` | 1つの時点・1つのモデルの当たり具合の値 | ― |
| `TrainingReport` | 学習の結果の入れ物。予想ごとの `workflow/` が作り、`command/` の `TrainingReportTables` が表にする | ― |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-21 |
| 更新 | 2026-09-21: 実装に合わせて、1ファイル1クラス・1 SQL 1 リポジトリの決まりと、フォルダの構成を書き直した |
| 更新 | 2026-09-22: 予想で変わらないクラスを `src/yosou/shared/` に移したのに合わせて、パッケージ構成とクラスの置き場所を書き直した |
| 更新 | 2026-09-23: 単勝オッズを特徴量に足したのに合わせて、`MarketFeatures`・`OddsInput`・`OddsResolver`・`AnnouncedOddsApplier`・`AnnouncedOddsRepository` を足した |
