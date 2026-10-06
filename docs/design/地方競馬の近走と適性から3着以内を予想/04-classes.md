# 04 クラスとパッケージの設計

**この文書で決めること:** データを読む・特徴量を作る・学習する・予測するを、どのクラスにやらせるか。中央の予想の部品のうち、何をそのまま使い、何を地方のために足すか。クラスをどのフォルダ（パッケージ）・ファイルに置くか。コマンドが、どんな引数を受け取り、何を出すか。

**結論: 学習の流れは共通の `TrainingWorkflow`、予測の流れは共通の `PredictionWorkflow`、テスト期間の確かめは `BacktestWorkflow` が進める。** 中央の予想の部品は、中央だけの決めごと（競馬場の範囲・クラスの読み方・血統の表・出走別着度数の欄）を外から渡せる形に直して、そのまま使う。地方だけの決めごとは、この予想のパッケージ `src/yosou/local_form_aptitude_top3/` と、事実表の部品 `tools/共通/local_codes.py` に置く。中央の予想のパッケージにあって地方でも同じ部品（行の選び方・オッズの決め方・1着のモデル用の持ち替え など）は、`shared` に移して両方から使う。

- 用語の意味は [02-glossary.md](02-glossary.md) を参照。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。
- 分け方の決まり（1ファイル1クラス・1 SQL 1 リポジトリ・Workflow は受け渡すだけ・`Manager` を付けない など）は、中央の予想の [04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) と同じである。

## 1. 共通の部品と、地方だけの部品の分け方

| 区分 | 何か | 置き場所 |
|---|---|---|
| そのまま使う共通の部品 | `DatasetBuilder`・`FeatureBuilder`・まとまり A〜H・J・L・N・O・Q のクラス・`LightGbmModel`・`CatBoostModel`・`EnsembleModel`・`TrainingWorkflow`・`SegmentedPrediction`・`ModelRepository`・複勝と単勝の期待値・評価のクラス | `src/yosou/shared/` |
| 中央だけの決めごとを外から渡せる形に直す部品 | 事実表の SQL（`facts.py`）、`FactTableRepository`・`RaceEntryTableRepository`、`CareerCountSql`・`CareerCountRepository`、`EntryRecordsLoader`・`HistoryRecordsLoader`・`RaceRecordsLoader`、`PredictionTiming`、`CommonArguments`、`db.open_db`、`codes.venue_code` | `tools/共通/`・`src/yosou/shared/` |
| 中央の予想のパッケージから `shared` に移す部品 | `RunnerSelector`・`OddsInput`・`OddsResolver`・`PoolAvailability`・`PoolFreeData`・`FinishPowerFreeData`・`WinTargetData`・`PaceAttachment`・`PredictionWorkflow`・`ExplainedPrediction` | `src/yosou/shared/dataset/`・`src/yosou/shared/workflow/`（中央の予想のパッケージからは、同じ名前で読めるようにしておく） |
| 地方だけの部品 | 事実表の元データの決めごと（`LOCAL_FACTS_SOURCE`）、クラスの読み取り、出走別着度数地方の欄、特徴量の一覧、時点の表示名、`backtest`、初期値の設定ファイル | `tools/共通/local_codes.py`・`src/yosou/local_form_aptitude_top3/` |

**中央だけの決めごとを外から渡す形にするのは、中央の動きを変えずに地方を足すためである。** 事実表（`facts.py`）は、渡さなければ元DB の表から中央か地方かを見分ける（競走馬マスタ地方 `nu` があれば地方。`detect_source`）ので、`tools/` の道具（成績集計・印の成績 など）は直さずに地方の元DB も読める。出走別着度数の欄と元DB の既定は、渡さなければ中央のままである。中央の予想・道具・テストはそのまま通る。

## 2. パッケージ構成

```text
tools/共通/
├── facts.py                    事実表の SQL。元データの決めごと（FactsSource）を受け取る。既定は中央（JRA_FACTS_SOURCE）
├── local_codes.py              地方のコード値と決めごと: 競馬場の範囲（ばんえいを除く）、クラスの並び順、クラス名の SQL、LOCAL_FACTS_SOURCE
├── codes.py                    競馬場の名前 → コード は、中央と地方の両方の名前を受ける
└── db.py                       元DB の既定（中央 ../jvdata-store/jvdata.duckdb、地方 ../nvdata-store/nvdata.duckdb）と環境変数

src/yosou/shared/               両方の予想から使う部品（中央の予想の 04 の構成と同じ）
├── dataset/                    … に RunnerSelector・OddsInput・OddsResolver・PoolAvailability・PoolFreeData・FinishPowerFreeData・WinTargetData・PaceAttachment が増える
├── workflow/                   … に PredictionWorkflow・ExplainedPrediction・BacktestWorkflow が増える
└── repository/                 CareerCountSql は欄の決めごと（CareerCountLayout）を受け取る。既定は中央の ck

src/yosou/local_form_aptitude_top3/   地方競馬の近走と適性から3着以内を予想する
├── __main__.py                 コマンドの入口（command/ を呼ぶだけ）
├── command/                    コマンド（train・predict・backtest）の引数。入口。元DB の既定は地方
├── workflow/                   予測を出す時点と表示名（出馬表・前日・当日）、券種オッズなし・1着のモデルの置き場所
├── dataset/                    DatasetBuilder の組み立て（1つ）。地方の事実表と出走別着度数地方を渡す
├── repository/                 出走別着度数地方（nd）の欄の決めごと（LOCAL_CAREER_LAYOUT）
├── feature/                    この予想の特徴量の一覧（土台 65個・J・L・N・O・Q）
├── setting/                    ハイパーパラメータの初期値のファイル
└── tests/                      この予想の組み立てのテスト。地方の合成DB（tools/合成DB/local_synth.py）だけを使う
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く。ファイルの名前は、クラスの名前を小文字と `_` にしたもの。学習したモデルは、Git の対象外の `reports/地方競馬の近走と適性から3着以内を予想/models/` に、時点ごとに保存する。3着以内のモデルは `models/<時点>/`、1着のモデルは `models/1着/<時点>/`、当日の券種オッズなしは `models/券種オッズなし/race_day/`・`models/券種オッズなし/1着/race_day/`。時点のフォルダ名は共通の値（`thursday`・`day_before`・`race_day`）のままにする（出馬表は `thursday`）。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `local_form_aptitude_top3` → `shared`。`shared` から予想のパッケージを参照しない。中央の予想のパッケージ（`form_aptitude_top3`）も参照しない | 片方の予想の都合が、もう片方に入り込まない |
| 中央と地方で同じ部品は `shared` に1つだけ置き、2つのパッケージに写さない | 片方だけ直すと食い違う |
| 中央だけの決めごとは、`shared`・`tools/共通` の中に if 文で書かず、値（`FactsSource`・`CareerCountLayout`）として外から渡す。事実表は渡さなければ元DB の表で見分け、ほかは渡さなければ中央の既定 | 共通のクラスの中に「中央か地方か」の if 文が増えない。中央の動きが変わらない |
| 地方だけの決めごとのうち、事実表に関わるもの（競馬場の範囲・クラスの読み方・血統の表）は `tools/共通/local_codes.py` に置く | 事実表の SQL は `tools/` の道具（成績集計・出走検索 など）からも使うので、`src/yosou/` の下には置かない（keiba-yosou の決まり） |

## 3. 中央だけの決めごとを外から渡す形

| 部品 | 渡すもの | 中央（既定） | 地方 |
|---|---|---|---|
| `facts.facts_sql()`・`ensure_facts()`・`build_entry_facts()` | `FactsSource`（元データの決めごと）: 読む競馬場の範囲の SQL、競馬場コード → 名前、血統の表の名前、クラス名の SQL の作り方、見分けに使う表の名前。省略すると `detect_source()` が元DB の表から見分ける | `JRA_FACTS_SOURCE`: 競馬場 01〜10、`VENUE_NAMES`、`um__3代血統情報`、競走条件コードとグレードコードから | `LOCAL_FACTS_SOURCE`（`local_codes.py`）: 競馬場 30〜61（83 は除く）、`LOCAL_VENUE_NAMES`、`nu__3代血統情報`、競走条件名称とグレードコードから。`nu` があれば地方 |
| `FactTableRepository`・`RaceEntryTableRepository` | `FactsSource` | 既定 | `LOCAL_FACTS_SOURCE` |
| `CareerCountSql` | `CareerCountLayout`（欄の決めごと）: 通算の欄の名前、競馬場別の欄（競馬場の名前と芝ダ → 欄の名前）、距離帯の区切り、馬場状態の欄 | `JRA_CAREER_LAYOUT`: 中央合計着回数、東京芝 など、1200以下〜2801以上の9帯 | `LOCAL_CAREER_LAYOUT`（この予想の `repository/`）: 総合着回数、大井ダ・盛岡芝 など、1000以下〜2201以上の11帯 |
| `CareerCountRepository` | 表の名前と `CareerCountSql` | `ck` | `nd` |
| `EntryRecordsLoader`・`HistoryRecordsLoader`・`RaceRecordsLoader` | `facts_source`・`career_counts`（出走別着度数を読むリポジトリ） | 既定 | 地方の2つ |
| `PredictionTiming.parse()` | ― | 木曜・前日・当日 | 「出馬表」も `thursday` として受ける（共通の `LOCAL_FIRST_TIMING_LABEL`）。表示名はこの予想の `TIMING_LABELS` で、`TrainingReportTables`・`PredictionTable`・`BacktestReportTables` に渡す |
| `RaceConditionFeatures` | クラスの並び順の付け直し（`class_order_fixes`） | `JRA_CLASS_ORDER_FIXES`（格付けの無い重賞 14 → G3 の 8、条件不明 99 → 欠損値） | `LOCAL_CLASS_ORDER_FIXES`（条件不明 99 → 欠損値だけ。14 は A1 なので付け直さない） |
| `CommonArguments`・`db.open_db()` | 元DB の既定（パスと環境変数の名前） | `../jvdata-store/jvdata.duckdb`・`YOSOU_DB` | `../nvdata-store/nvdata.duckdb`・`YOSOU_LOCAL_DB` |
| `codes.venue_code()` | ― | 中央の名前かコード | 地方の名前かコードも受ける（`LOCAL_VENUE_NAMES`） |

## 4. クラスの一覧

中央の予想と共通のクラス（`DatasetBuilder`・`FeatureBuilder`・まとまりのクラス・`LightGbmModel`・`CatBoostModel`・`EnsembleModel`・`TrainingWorkflow`・`ModelRepository`・評価・期待値・設定）の仕事と public メソッドは、中央の予想の [04 の「クラスの一覧」](../近走と適性から3着以内を予想/04-classes.md#クラスの一覧) を参照。ここには、この予想のために足すクラスと、`shared` に移すクラスを書く。

### workflow/ — 流れを進める（`shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `PredictionWorkflow`（中央から移す） | 予測の流れを進める。予測に使うオッズを決め、予測用データを作り、当日に券種のオッズが無ければ券種オッズなしのモデルに切り替え（[06-flowchart.md の図3](06-flowchart.md#図3-当日のモデルの選び方)）、その時点の3着以内のモデルと1着のモデルで2つの予測確率を平均する。前日・当日は複勝と単勝の期待値を足す。展開の予想の結果（P）を足す `pace` は、この予想では渡さない | `run(レースID, 時点, 渡されたオッズ=省略可)`、`explain(…)` |
| `BacktestWorkflow`（新しく作る。`shared`） | テスト期間の確かめの流れを進める。学習データ（テスト期間を含む）からテスト期間の行だけを残し、時点ごとに保存したモデル（3着以内・1着。当日は券種オッズの無いレースの行を `PoolFreeRows` で券種オッズなしのモデルに振り分ける）で予測し、当たり具合（`ModelEvaluator.evaluate_probabilities`）と市場の確率の当たり具合を測り、印の成績が読む形の予測の表を書く。結果は `BacktestReport`（`shared/evaluation/`）、表は `BacktestReportTables`（`shared/command/`）（[16-evaluation.md の 4.](16-evaluation.md#4-テスト期間での確かめ)） | `run(学習データ, 期間)` |
| `TIMINGS`・`TIMING_LABELS`・`POOL_FREE_FOLDER`・`WIN_FOLDER`（この予想） | 予測を出す時点（3つ）、時点の表示名（出馬表・前日・当日）、券種オッズなし・1着のモデルの置き場所（`prediction_timings.py`） | ― |

### command/ — コマンド（入口はこの予想、部品は `shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `CommandLine` | 入口。引数を読み、サブコマンド（train・predict・backtest）を実行し、結果の表を出す | `run(引数)` |
| `TrainCommand` | `train`: 学習する。1つの学習データ（`local_dataset_builder`）から、3つの時点の3着以内のモデルと1着のモデル（`WinTargetData`）、当日の券種オッズなしのモデル（`PoolFreeData`）を学ぶ。3着以内のモデルに渡す前に `FinishPowerFreeData` で Q を外す。学習のあとに複勝の見込みの倍率（`PlacePriceStep`）を保存する。元DB は学習データを読む段だけ開く | `run(引数)` |
| `PredictCommand` | `predict`: 1レースを予測する。`--odds 馬番:オッズ` で単勝オッズを渡せる。時点はどれでも同じ `local_dataset_builder` | `run(引数)` |
| `BacktestCommand` | `backtest`: テスト期間の確かめ。`BacktestWorkflow` を呼び、当たり具合の表を出し、予測の表を `reports/地方競馬の近走と適性から3着以内を予想/predictions/` に書く | `run(引数)` |
| `CommonArguments`（`shared`） | 共通の引数（`--models` `--db` `--format` `--out`）。予想の名前と、元DB の既定（`db.LOCAL`）を受け取る | `add_to(parser)` |
| `PeriodArguments`（この予想） | `train` と `backtest` に共通の、学習データの期間の引数（`--warmup-from` `--train-from` `--valid-from` `--test-from`）と、引数から `TrainingPeriod` を作ること | `add_to(parser)`、`period_of(args)` |

### dataset/ — 学習データ・予測用データを作る（組み立てはこの予想、ほかは `shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `local_dataset_builder()`（この予想） | 共通の `DatasetBuilder` を、地方の決めごとで組み立てる関数（`dataset_assembly.py`）。ローダーに `LOCAL_FACTS_SOURCE`・出走別着度数地方の `CareerCountRepository`・`MarketRunRepository`（L）・`PoolProbabilityLoader`（N）・`HeadToHeadRunRepository`（O）・`FinishRecordsLoader`（Q）を渡し、行の選び方は `RunnerSelector`、目的変数は `Top3TargetBuilder`、特徴量の一覧は `CATALOG`、基準は `Top3Baseline`。学習データはこの1つから作り、各時点にはその時点で使う列だけを渡す | `local_dataset_builder(接続)` |
| `RunnerSelector`（中央から移す） | 入れる行を選ぶ（[06-flowchart.md の図1](06-flowchart.md#図1-学習データに入れる行の選び方)）。障害レースと出走しなかった馬を除き、学習では学習データの始まり以降の行だけにする。ばんえいは事実表の段で除いてあるので、ここでは見ない | `training_samples(出走の行, 学習データの始まり)`、`prediction_runners(出走の行, レースID)`、`keep_samples(行)` |
| `OddsInput`・`OddsResolver`（中央から移す） | 利用者が渡した単勝オッズと、予測に使うオッズの決め方（[06-flowchart.md の図4](06-flowchart.md#図4-予測に使うオッズの決め方)） | `of(…)`・`resolve(レースID, 渡されたオッズ)` |
| `PoolAvailability`・`PoolFreeData`（中央から移す） | 券種のオッズが無いかの判定と、N の6列を外した学習データ・予測用データ | `missing(予測用データ)`・`training(…)`・`prediction(…)` |
| `FinishPowerFreeData`・`WinTargetData`（中央から移す） | Q の 10列を外す（3着以内のモデルに渡すとき）。目的変数を「1着」に・基準を「オッズから見た勝率」に持ち替える（1着のモデル） | `training(…)`・`prediction(…)` |
| `EntryRecordsLoader`（`shared`。直す） | リポジトリを順に呼んで記録を集める。出走別着度数のリポジトリ（`career_counts`）を受け取る。渡さなければ中央の `ck` | `load(対象)` |
| `PoolFreeRows`（新しく作る。`shared`） | 学習データの行ごとに、そのレースの券種のオッズが無いか（券種オッズなしのモデルで予測する行か）を答える。`PoolAvailability` の判定をレースの混ざった学習データの形で行うもの（`backtest` が使う） | `of(学習データ)` |

### repository/ — データの読み書き（1 SQL につき 1 リポジトリ。`shared` を直す。欄の決めごとはこの予想）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `FactTableRepository`・`RaceEntryTableRepository`（直す） | 事実表と、1レースの出走馬の一時表を用意する。`FactsSource` を受け取り、`facts.py` に渡す | `ensure()`・`build(レースID, 馬場状態コード, 単勝人気=省略可)` |
| `CareerCountSql`（直す） | 出走別着度数の表から、そのレースの条件に合う欄の着回数を取り出す式を作る。欄の決めごと（`CareerCountLayout`）を受け取る | `source_columns()`、`select_list()` |
| `CareerCountLayout`（新しく作る。`shared`） | 欄の決めごとを表す値: 表の名前、通算の欄の名前、競馬場別の欄がある競馬場とその芝ダ、距離帯の区切り。馬場状態の欄はどちらも同じ。中央の既定は `JRA_CAREER_LAYOUT` | ― |
| `LOCAL_CAREER_LAYOUT`（この予想の `repository/local_career_layout.py`） | 出走別着度数地方（`nd`）の欄の決めごと: 通算は総合着回数、競馬場別は `<競馬場の名前><ダ か 芝>・着回数`（14場のダートと盛岡の芝）、距離帯は 1000以下・1001-1200・1201-1300・1301-1400・1401-1500・1501-1600・1601-1700・1701-1800・1801-2000・2001-2200・2201以上、馬場状態は ダ良〜ダ不・芝良〜芝不 | ― |
| `CareerCountRepository`（直す） | 対象の出走ごとの出走別着度数を読む。欄の決めごと（`CareerCountLayout`。表の名前 `ck` か `nd` を含む）を受け取る | `read(対象)` |
| `FinalOddsRepository`・`TicketOddsRepository`・`PayoutRepository`・`PayoutFlagRepository`（直す） | 期間の全レースの券種オッズと払戻を読む（道具「印の成績」の買い目の払戻・トリガミ・不成立の確かめ）。中央の競馬場だけに絞っていたのを、事実表と同じ見分け（`facts.venue_filter(接続, 別名)`。元DB に `nu` があれば地方の範囲）に替える | `read(…)` |
| ほかのリポジトリ（`EntryRepository`・`PastRunRepository`・`PeopleDayRepository`・`PedigreeDayRepository`・`MarketRunRepository`・`HeadToHeadRunRepository`・`HorseFinishRepository`・`PeopleFinishRepository`・`PlaceOddsRepository`・`AnnouncedGoingRepository`・`AnnouncedWeightRepository`・`AnnouncedOddsRepository`・`ScratchRepository`・券種オッズの2つ・`ModelRepository`） | 事実表か、中央と同じ名前の表（`o1`〜`o6`・`hr`・`we`・`wh`・`av`）を、レースを指定して読むので、直さずそのまま使う | ― |

### feature/ — 特徴量の一覧（この予想。作るクラスは `shared`）

| 名前 | 仕事 |
|---|---|
| `LOCAL_BASE_FEATURES` | 土台の 65個。共通の `BASE_FEATURES`（71個）から調教（I）の6個を除き、枠番・馬番の「いつから分かるか」を出馬表（`thursday`）に付け直したもの（[07-prediction-timing.md](07-prediction-timing.md#時点ごとに使う特徴量)） |
| `CATALOG` | この予想の特徴量の一覧（96個）: `LOCAL_BASE_FEATURES` + `MARKET_FEATURES`（J）+ `PEOPLE_MARKET_FEATURES`（L）+ `HEAD_TO_HEAD_FEATURES`（O）+ `POOL_SUPPORT_FEATURES`（N）+ `FINISH_POWER_FEATURES`（Q。この予想では当日の1着のモデルだけが使うので、「いつから分かるか」を当日にして出馬表・前日のモデルには渡さない）。学習データと予測用データはこの一覧で作り、3着以内のモデルに渡す前に Q を、券種のオッズが無いときに N を外す |
| `TIMING_LABELS`（`workflow/`） | 時点の表示名。`thursday` → 出馬表、`day_before` → 前日、`race_day` → 当日 |

### tools/共通/local_codes.py — 地方のコード値と決めごと

| 名前 | 仕事 |
|---|---|
| `LOCAL_VENUE_RANGE`・`BANEI_VENUE_CODE` | 地方の競馬場コードの範囲（30〜61）と、除くばんえい（83） |
| `LOCAL_CLASS_ORDER` | クラス名 → 並び順（[09-features.md の A](09-features.md#a-レースの条件9個) の表） |
| `local_class_name_sql(名称の式, グレードの式)` | 競走条件名称とグレードコードからクラス名を返す SQL の式（[06-flowchart.md の図2](06-flowchart.md#図2-クラスの読み取り)） |
| `LOCAL_FACTS_SOURCE` | 事実表の元データの決めごと（上の「3.」） |

### 合成DB（テスト用）

`tools/合成DB/local_synth.py` が、地方の表（`ra`・`se`・`hr`・`o1`〜`o6`・`nd`・`nu`）を持つ小さな DuckDB を作る。中央の合成DB（`synth.py`）の部品を使い、競馬場コード・競走条件名称・出走別着度数地方の列だけを地方の形にする。値は架空。この予想のテストは、この合成DB だけを使う。

## コマンドの引数

コマンドは `train`（学習）・`predict`（1レースの予測）・`backtest`（テスト期間の確かめ）の3つで、リポジトリ直下から `uv run python -m yosou.local_form_aptitude_top3 <train か predict か backtest> …` で動かす。引数の名前と意味は、中央の予想の [04 の「コマンドの引数」](../近走と適性から3着以内を予想/04-classes.md#コマンドの引数) と同じにする。違いは次のとおり。

| 引数 | この予想での既定・意味 |
|---|---|
| `--models` | `reports/地方競馬の近走と適性から3着以内を予想/models` |
| `--db` | `../nvdata-store/nvdata.duckdb`（環境変数 `YOSOU_LOCAL_DB` があればそのパス）。読むだけ |
| `--timing` | `出馬表`・`前日`・`当日`（英語の `thursday`・`day_before`・`race_day` でもよい。`木曜` も `出馬表` として受ける） |
| `--warmup-from`・`--train-from`・`--valid-from`・`--test-from` | [08-training-data.md の「4. 期間の指定」](08-training-data.md#4-期間の指定)。学習データは1つなので、`--ability-train-from` は無い |
| `--figure-cache`・`--development-root` | 無い（M・P を使わない） |
| `--venue` | 競馬場の名前かコード（地方の名前: 大井・名古屋 など） |
| `backtest` の `--test-from` | テスト期間の始まり（既定は学習と同じ 2026-01-01）。終わりは DB にある最後の日 |
| `backtest` の `--predictions` | 予測の表を書く場所（既定 `reports/地方競馬の近走と適性から3着以内を予想/predictions`）。時点ごとに `<時点>.pkl`（3着以内）と `<時点>-1着.pkl` を書く |

`train` が出す表は、学習データの期間・検証データでの当たり具合・人気の基準との比べ方・保存したモデル（`TrainingReportTables`）を、3着以内のモデルと1着のモデル（題に「1着:」が付く）の両方で、「今の材料」と「券種オッズなし」の学習ごとに出し、最後に複勝の見込みの倍率を出す。`predict` が出す表は、中央の予想と同じ列（順位・馬番・馬名、前日・当日なら単勝オッズ・オッズから見た3着以内率・複勝的中の確率・複勝の期待値・1着になる確率・単勝の期待値、3着以内に入る確率・LightGBM・CatBoost の確率）。出馬表の時点はオッズを使わないので、オッズの列と期待値の列は出ない。`backtest` が出す表は [16-evaluation.md の 4.](16-evaluation.md#4-テスト期間での確かめ) を参照。

引数の決まり（省略を受け付けない・誤りは1行で止まる・元DB は読む段だけ開く）も中央と同じである。

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-10-06 |
