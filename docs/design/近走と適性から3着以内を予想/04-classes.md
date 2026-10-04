# 04 クラスとパッケージの設計

**この文書で決めること:** データを読む・特徴量を作る・学習する・予測するを、どのクラスにやらせるか。それらのクラスを順に呼んで流れを進める（オーケストレーションする）のは、どのクラスか。クラスを、どのフォルダ（パッケージ）・ファイルに置くか。学習と予測のコマンドが、どんな引数を受け取り、何を出すか。

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
| ほかの予想のパッケージは参照しない。例外として、`command/` だけは予想「展開から着順を予想」（`yosou.race_development`）の `PaceForecastHistory`・`DevelopmentPaceWorkflow` を呼ぶ | 木曜のモデルの材料 P（展開の予想の結果）を、展開の予想の部品のまま使うため（写すと食い違う）。展開の予想はこの予想の `dataset/` だけを参照するので、読み込みの順が輪にならない。参照する場所を `train_command.py`・`predict_command.py` に集めた |

## パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。この予想のパッケージ名は、予想のやり方が分かる `form_aptitude_top3`（form = 近走、aptitude = 適性、top3 = 3着以内）とする。

**下の一覧のクラスのうち、予想で変わらないものは `src/yosou/shared/` に置き、ほかの予想（[人気馬が4着以下になるかを予想](../人気馬が4着以下になるかを予想/04-classes.md#1-共通の部品とこの予想だけの部品の分け方)）と共通で使う。** この予想のパッケージには、この予想だけの決めごと（入れる行の選び方・目的変数・特徴量の一覧・初期値の設定ファイル）と、それらを渡して共通の部品を組み立てるところ（`command/`・`workflow/`・`dataset/dataset_assembly.py`）だけが残る。

```text
src/yosou/shared/               両方の予想から使う部品
├── command/                    コマンドの部品のうち、予想に依らないもの（共通の引数・結果の表）
├── evaluation/                 当たり具合を測る。学習の結果の入れ物（TrainingReport）
├── ml_model/                   機械学習のモデル（LightGBM・CatBoost・エンコーダー・平均）
├── dataset/                    学習データ・予測用データを作る（入れる行と目的変数はインターフェースで受け取る）
├── feature/                    特徴量を作る（まとまり A〜N と、過去の記録から数える部品）
│   ├── group/                  まとまり A〜N ごとに1クラス
│   ├── ability/                まとまり M（馬の力の材料）を作る部品
│   └── history/                過去の記録から数える部品
├── repository/                 データの読み書き。1 SQL につき 1 リポジトリ
├── setting/                    ハイパーパラメータの設定ファイルを読む（初期値のファイルは予想ごと）
├── place_value/                複勝の期待値（3着以内の確率 × 見込みの払戻倍率）
├── win_value/                  単勝の期待値（1着になる確率 × 単勝オッズ）・期待度（高・低）
├── workflow/                   学習の流れ（TrainingWorkflow）
└── tests/                      共通の部品のテストと、テスト用の合成DB（synthetic_season/）

src/yosou/form_aptitude_top3/   近走と適性から3着以内を予想する
├── __main__.py                 コマンドの入口（command/ を呼ぶだけ）
├── command/                    コマンド（train・predict）の引数。入口
├── workflow/                   予測の流れ（ほかを順に呼ぶだけ）と、予測を出す時点
├── dataset/                    入れる行の選び方・目的変数（3着以内）・予測に使うオッズの決め方と、DatasetBuilder の組み立て（3つ）・券種の支持を外す部品・1着のモデル用に目的変数と基準を持ち替える部品
├── feature/                    この予想の特徴量の一覧（今の材料 CATALOG・券種の支持を足した POOL_CATALOG・馬の力の材料 ABILITY_CATALOG）
├── setting/                    ハイパーパラメータの初期値のファイル
└── tests/                      この予想の組み立てのテスト。合成DB だけを使う（keiba-yosou の決まり）
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く。ファイルの名前は、クラスの名前を小文字と `_` にしたもの（`TrainingWorkflow` → `training_workflow.py`）。学習したモデルは、Git の対象外の `reports/近走と適性から3着以内を予想/models/` に、時点ごとに保存する。3着以内のモデルは `models/<時点>/`、1着のモデルは `models/1着/<時点>/`（当日の券種オッズなしは、それぞれ `models/券種オッズなし/race_day/`・`models/券種オッズなし/1着/race_day/`）。

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
| `TrainingWorkflow` | 学習の流れを進める。設定を読み、渡された期間（`TrainingPeriod`）で学習データを作り、期間で分け、渡された時点ごとに2つのモデルを学習して保存し、検証データで当たり具合を確かめる。この予想は、材料ごとに3回使う（馬の力の材料で木曜・前日、今の材料で当日、券種の支持を外した学習データで当日の「券種オッズなし」。[05-sequence.md の図1](05-sequence.md#図1-学習)）。**中身が2つ目の予想と同じなので `shared/workflow/` にある。** 学習する時点の並びとハイパーパラメータの初期値のファイルは、作られるときに受け取る。元DB が要るのは学習データを読む段だけなので、読む段と学習する段を分けて呼べる | `run(設定ファイルのパス)`、`read_training_data()`、`train(学習データ, 設定ファイルのパス)` |
| `PredictionWorkflow` | 予測の流れを進める。予測に使うオッズを決め、予測用データを作り、当日に券種のオッズが無ければ券種の支持を外して「券種オッズなし」のモデルに切り替え（[06-flowchart.md の図3](06-flowchart.md#図3-当日のモデルの選び方)）、その時点の3着以内のモデルと1着のモデルを読み込み、それぞれ2つの予測確率を平均する。1着の予測には、`WinTargetData` で基準を「オッズから見た勝率」に持ち替えた予測用データを渡す。前日・当日は、複勝の期待値（`PlaceValueColumns`）と単勝の期待値（`WinValueColumns`）の列を足す。予測用データを作る `DatasetBuilder` は、時点に合わせてコマンドが選んで渡す | `run(レースID, 時点, 渡されたオッズ=省略可)`、`explain(…)`（同じ予測に、特徴量の値と寄与を添える） |
| `TIMINGS`・`ABILITY_TIMINGS`・`FORM_TIMINGS`・`POOL_FREE_FOLDER`・`WIN_FOLDER` | 予測を出す時点（3つ）、馬の力の材料のモデルで予測する時点（木曜・前日）、今の材料のモデルで予測する時点（当日）、券種のオッズが無いときの当日のモデルの置き場所（`券種オッズなし`）、1着のモデルの置き場所（`1着`。券種オッズなしの1着は `券種オッズなし/1着`）（`prediction_timings.py`） | ― |
| `PROBABILITY`・`WIN_PROBABILITY` | 予測の結果の確率の列の名前（「3着以内に入る確率」「1着になる確率」）（`prediction_workflow.py`） | ― |
| `TrainingReport` | 学習の結果の入れ物（使った期間・期間ごとのデータ・当たり具合・保存したフォルダ）。予想で変わらないので `shared/evaluation/` にある | ― |

### command/ — コマンド（入口はこの予想、部品は `shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `CommandLine` | 入口。引数を読み、サブコマンドを実行し、結果の表を出す | `run(引数)` |
| `TrainCommand` | `train`: 学習する。期間の引数（`--warmup-from` `--train-from` `--ability-train-from` `--valid-from` `--test-from`）から、今の材料と馬の力の材料の2つの `TrainingPeriod` を作る。学習データごとに、3着以内のモデルと、`WinTargetData` で持ち替えた1着のモデル（`<置き場所>/1着/`）を学ぶ。元DB は学習データを読む段だけ開き、学習のあいだはロックを持たない | `run(引数)` |
| `PredictCommand` | `predict`: 1レースを予測する。`--odds 馬番:オッズ` で単勝オッズを渡せる。時点で `DatasetBuilder` を選ぶ（木曜・前日は `ability_dataset_builder`、当日は `race_day_dataset_builder`） | `run(引数)` |
| `FigureCacheArgument` | 2つのサブコマンドに共通の引数 `--figure-cache`（スピード指数をとっておく場所） | `add_to(parser)` |
| `DevelopmentRootArgument` | 2つのサブコマンドに共通の引数 `--development-root`（予想「展開から着順を予想」の置き場所。木曜のモデルが展開の予想の結果を読む） | `add_to(parser)` |
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
| `AbilityRunRepository` | まとまり M の材料の、2011年からの全出走と対象の出走（事実表の列に、馬主・生産者・母を付けて）。木曜など馬毎レース情報がまだ無いときの馬主は、競走馬マスタの今の馬主 | `read(対象)` |
| `SpeedFigureRepository` | 過去の全部の走のスピード指数。SQL と計算は道具「能力指数」の `FigureCache`（`tools/共通/ability/`）に任せ、とっておいたファイル（`reports/能力指数/cache/`）を共有する | `read()` |
| `WorkoutSummaryRepository` | 対象の出走ごとの、レースの前日までの 14日・30日の坂路とウッドの調教のまとめ（まとまり M） | `read(対象)` |
| `SalePriceRepository` | セリの取引価格（`hs`。まとまり M） | `read()` |
| `HorseFinishRepository`・`PeopleFinishRepository` | 対象の出走ごとの勝ち切る材料（まとまり Q）。馬の近10走の1着数・2着数・勝ち切り率・惜敗数・勝ち着差の平均・人気で負けた数と、騎手・調教師の近1年の勝ち切り率と1番人気のときの勝率。事実表の確定成績から、開催日の前日までの記録で数える | `read(対象)` |
| `FirstHorsePoolRepository`・`AllHorsesPoolRepository` | 券種オッズ（`o1`〜`o6`。確定、無ければ最新の断面）から、馬ごとの確率。1着の馬だけを見る馬単・3連単と、組の全部の馬に配る馬連・ワイド・3連複・複勝。まとまり N の材料。SQL の共通の前半は `PoolOddsRowsSql`、券種ごとの決まりは `PoolSpec`・`POOLS`。custom_binary も同じものを使う | `read(券種, 対象のレース)` |
| `MarketRunRepository` | 過去の平地の全出走の単勝オッズ・着順・騎手・調教師・父・母の父。まとまり L（騎手・調教師・血統の市場に対する成績）の材料。オッズから見た3着以内率はレースの全頭のオッズから出すので、期間の全レースを読む（[09-features.md の L](09-features.md#l-騎手調教師血統の市場に対する成績4個)）。L を使う予想だけが渡す | `read(対象)` |
| `ModelRepository` | 時点ごとの学習済みモデルと、学習に使った設定のファイル（SQL ではなくファイルに読み書きする） | `save(時点, モデル, 設定)`、`load(時点)` |
| `TargetScope` | 「どの出走について読むか」を表す値。学習では「ある日以降の全部の出走」、予測では「1レースの出走馬」 | `since(日)`、`of_table(表)` |
| `CareerCountSql` | `CareerCountRepository` の SQL の式を作る部品 | `select_list()` |

取得していない DB には `ck`・`hc`・`wc`・`we`・`wh`・`av`・`sk`・`hs`・`o1`〜`o6` の表が無い。そのときは、同じ列を持つ空の関係で代わりにし、SQL 1本のまま「行なし」を返す。

### dataset/ — 学習データ・予測用データを作る（`RunnerSelector` はこの予想、ほかは `shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `DatasetBuilder` | 入口。学習データか予測用データを作る。下のクラスを順に呼ぶだけ。入れる行（`SampleSelector`）・目的変数（`TargetLabeler`）・特徴量（`FeatureBuilder`）は、作られるときに受け取る | `build_training_data(期間)`、`build_prediction_data(レースID, 時点, 単勝人気=省略可, 単勝オッズ=省略可)` |
| `SampleSelector`・`TargetLabeler` | 入れる行の選び方と、目的変数の付け方の決まり（インターフェース）。守るクラスは予想ごとに作る | `training_samples`・`prediction_runners`・`keep_samples` / `build`・`label_name` |
| `TrainingPeriod` | 学習データの期間を区切る4つの日（ウォームアップ・学習・検証・テストの始まり）を表す値。順になっていなければエラー。[08-training-data.md](08-training-data.md) の 4 | `starting(学習の始まり, 検証の始まり, テストの始まり, ウォームアップの始まり=省略可)`、`default()` |
| `HistoryRecordsLoader` | 学習用に、ある日以降の全部の出走の記録を集める。`market_runs=`（`MarketRunRepository`）を受け取ったときだけ、まとまり L の材料も読む（この予想は渡す） | `load(最初の日)` |
| `RaceRecordsLoader` | 予測用に、1レースの出走馬の記録を集める。速報（馬場状態・馬体重・取消）と、渡された人気・オッズを反映する。`market_runs=` の扱いは `HistoryRecordsLoader` と同じ | `load(レースID, 単勝人気=省略可, 単勝オッズ=省略可)` |
| `EntryRecordsLoader` | リポジトリを順に呼んで、対象の出走の記録を集める。SQL は持たない。`MarketRunRepository`・`AbilitySourcesLoader`・`PoolProbabilityLoader` は、受け取ったときだけ呼ぶ（ほかの予想は SQL が増えない） | `load(対象)` |
| `AbilitySourcesLoader` | まとまり M の元の記録（全出走・スピード指数・調教のまとめ・セリの取引）を、4つのリポジトリを順に呼んで集める | `load(対象)` |
| `PoolProbabilityLoader` | 6つの券種のリポジトリを呼んで、券種ごとの馬の確率を1つの表にする（まとまり N。custom_binary の追加の元データ「券種オッズ」も使う） | `read(対象のレース)` |
| `FinishRecordsLoader` | 馬と人の2つのリポジトリを呼んで、勝ち切る材料（まとまり Q）を出走ごとの1つの表にする。当日の組み立てだけが渡す | `read(対象)` |
| `AnnouncedWeightApplier` | 速報の馬体重を、出走の行に反映する | `apply(出走の行, 速報の馬体重)` |
| `ScratchApplier` | 速報の出走取消・競走除外を、出走の行に反映する | `apply(出走の行, 馬番)` |
| `AnnouncedOddsApplier` | 予測に使う単勝オッズ（手で渡したものか、締め切り前のもの）を、出走の行に反映する。無ければ行はそのまま | `apply(出走の行, 馬番→オッズ)` |
| `RunnerSelector`（この予想） | 入れる行を選ぶ（[06-flowchart.md](06-flowchart.md) の図1）。この予想は全頭を入れるので、`keep_samples` はそのまま返す | `training_samples(出走の行, 学習データの始まり)`、`prediction_runners(出走の行, レースID)`、`keep_samples(特徴量の付いた行)` |
| `Top3TargetBuilder` | 目的変数を付ける（[10-target.md](10-target.md)）。当てさせる列は「3着以内」で、「1着」の列も付ける。穴馬の予想（`docs/design/穴馬が3着以内に入るかを予想/`）も同じ目的変数を使うので、`shared` に置く | `build(サンプルの行)`、`label_name` |
| `Top3Baseline`・`WinBaseline` | 目的変数の基準（ロジット）。`Top3Baseline` はオッズから見た3着以内率（3着以内のモデル）、`WinBaseline` はオッズから見た勝率（1着のモデル）。どちらも前日から使え、オッズの無い馬は頭数から見た割合（3 ÷ 頭数、1 ÷ 頭数）にする。`TargetBaseline` の決まりを守る | `build(同じレースの全頭の行)`、`known_from` |
| `WinTargetData`（この予想） | 3着以内のモデル用に作った学習データ・予測用データを、1着のモデル用に持ち替える。目的変数を「1着」に、基準を評価用の列（学習）か `market`（予測）の「確定の単勝オッズ」から作った `WinBaseline` に替える。特徴量はそのまま（当日は Q を含んだまま渡す） | `training(学習データ)`、`prediction(予測用データ)` |
| `OddsInput`（この予想） | 利用者が `--odds 馬番:オッズ` で渡した「馬番 → 単勝オッズ」を表す値。書き方が違えばエラー | `of(引数の文字列)`、`as_mapping()` |
| `OddsResolver`（この予想） | 予測に使う「馬番 → 単勝オッズ」を決める。渡されたオッズ → 元DB の締め切り前のオッズ → 無し（元DB の出走の行のオッズ）の順（[06-flowchart.md](06-flowchart.md#図2-予測に使うオッズの決め方)） | `resolve(レースID, 渡されたオッズ)` |
| `dataset_builder()`（この予想） | `RunnerSelector`・共通の `Top3TargetBuilder`・特徴量の一覧（`CATALOG`）とまとまりの並び（`_FEATURE_GROUPS`。L の `PeopleMarketFeatures` を含む）を渡して、共通の `DatasetBuilder` を組み立てる関数（`dataset_assembly.py`）。ローダーには `MarketRunRepository(接続, PEOPLE_WINDOW_DAYS)` を渡す。今の材料の 79個で、展開の予想と研究もこれを使う | `dataset_builder(接続)` |
| `pool_dataset_builder()`（この予想） | `dataset_builder()` に N（`PoolSupportFeatures`）を足し、ローダーに `PoolProbabilityLoader` を渡す（`POOL_CATALOG`。研究の比べに使う） | `pool_dataset_builder(接続)` |
| `race_day_dataset_builder()`（この予想） | `pool_dataset_builder()` にさらに M（`HorseAbilityFeatures` に、今の材料と名前の重ならない 200列だけを出させる）と Q（`FinishPowerFeatures`）を足し、ローダーに `AbilitySourcesLoader` と `FinishRecordsLoader` も渡す。当日のモデルの学習データと予測用データ（`RACE_DAY_WIN_CATALOG`。3着以内のモデルに渡す前に `FinishPowerFreeData` で Q を外す） | `race_day_dataset_builder(接続, スピード指数の置き場所=省略可)` |
| `ability_dataset_builder()`（この予想） | M（`HorseAbilityFeatures`）と O（`HeadToHeadRatingFeatures`）と J の `DatasetBuilder`。ローダーに `AbilitySourcesLoader` と `HeadToHeadRunRepository` を渡す。G は使わない。基準はオッズの分かる前日から使う。木曜・前日のモデルの学習データと予測用データ（`ABILITY_CATALOG`）。学習データの始まりは `ABILITY_TRAIN_FIRST_DAY`（2012年1月1日） | `ability_dataset_builder(接続, スピード指数の置き場所=省略可)` |
| `PoolFreeData`（この予想） | 学習データ・予測用データから N の6列を外し、一覧からも N を除く（券種のオッズが無いときの当日のモデル。279個） | `training(学習データ)`、`prediction(予測用データ)` |
| `FinishPowerFreeData`（この予想） | 学習データ・予測用データから Q の10列を外し、一覧からも Q を除く（3着以内のモデルに渡すとき。Q は1着のモデルだけが使う。295個 → 285個） | `training(学習データ)`、`prediction(予測用データ)` |
| `PaceAttachment`（この予想） | 学習データ・予測用データに、展開の予想の結果（P）の 20列を足し、一覧にも P を足す（`PACE_TIMINGS` の時点＝木曜のモデル）。展開の予測は、学習では `PaceForecastHistory`、予測では `DevelopmentPaceWorkflow`（`yosou.race_development`）がコマンドから渡される | `apply(データ, 展開の予測の表)` |
| `PoolAvailability`（この予想） | 予測用データの N の6列のどれか1列でも全部の馬で欠損値なら「券種のオッズが無い」と答える | `missing(予測用データ)` |
| `RequiredInfoCheck` | 予測に要る情報（馬番・馬場状態・馬体重・単勝オッズ）が DB にあるかを確かめる | `check(特徴量)` |
| `PeriodSplitter` | 学習データを時期（`TrainingPeriod` の検証・テストの始まり）で、学習データ・検証データ・テストデータに分ける。分け方は次の設計書で決める（いまは仮の区切り） | `split(学習データ)` |
| `TrainingData`・`PredictionData`・`SplitData` | 学習データ・予測用データ・期間で分けたデータの入れ物（[08-training-data.md](08-training-data.md) の「列の種類」） | ― |

### feature/ — 特徴量を作る（一覧 `CATALOG` はこの予想、ほかは `shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `FeatureBuilder` | 入口。まとまりごとのクラスを順に呼んで、1つの表にする。特徴量の一覧（`FeatureCatalog`）とまとまりのクラスは、作られるときに受け取る。時点を受け取り、その時点で使う特徴量だけを返す | `build(記録, 時点)` |
| `FeatureCatalog` | 1つの予想が使う特徴量の一覧を表す値。この予想の一覧は3つ: `CATALOG = FeatureCatalog(BASE_FEATURES + J_FEATURES + PEOPLE_MARKET_FEATURES)`（当日は 79個）、`POOL_CATALOG`（`CATALOG` に N の `POOL_SUPPORT_FEATURES` を足した 85個。研究の比べに使う）、`RACE_DAY_CATALOG`（`POOL_CATALOG` に M のうち今の材料と名前の重ならない 200個 `RACE_DAY_ABILITY_FEATURES` を足した 285個。当日の3着以内のモデル）、`RACE_DAY_WIN_CATALOG`（`RACE_DAY_CATALOG` に Q の `FINISH_POWER_FEATURES` を足した 295個。当日の1着のモデル）、`ABILITY_CATALOG = FeatureCatalog(ABILITY_FEATURES + HEAD_TO_HEAD_FEATURES + J_FEATURES)`（木曜は 199個）。L・M・N・O は共通の `feature_catalog.py` にある | `names`、`categorical`、`columns_for(時点)`、`categorical_columns_of(特徴量の表)` |
| `PredictionTiming` | 予測する時点（木曜・前日・当日）を表す値。時点の前後を答える（[07-prediction-timing.md](07-prediction-timing.md)） | `is_at_or_after(時点)`、`parse(書き方)` |
| `Feature`・`FeatureKind` | 特徴量の一覧の1行（名前・まとまり・型・いつから分かるか）と、その型。どの予想でも使う 71個は `feature_catalog.py` の `BASE_FEATURES`（[09-features.md](09-features.md) の表の写し） | `is_known_at(時点)` |
| `EntryRecords` | 特徴量を作る元の記録の入れ物。`market_runs` は、まとまり L の材料の過去の全出走（L を使う予想だけが読む。ほかの予想では空の表）。`ability_sources` はまとまり M の元の記録（`AbilitySources`。M を使うモデルだけ）、`pool_probabilities` は券種ごとの馬の確率（N を使うモデルだけ） | ― |
| `EntryColumns` | 出走の記録から列を選び、名前を付け直す | `select(出走の行)` |
| `FeatureGroup` | まとまりのクラスに共通の決まり（インターフェース） | `build(記録)` |
| `group/` の13クラス | まとまり A〜L ごとに1クラス: `RaceConditionFeatures`（A）、`HorseFeatures`（B）、`PeopleFeatures`（C）、`PreviousRunFeatures`（D）、`RecentFormFeatures`（E）、`AptitudeFeatures`（F）、`FieldComparisonFeatures`（G）、`PedigreeFeatures`（H）、`WorkoutFeatures`（I）、`MarketFeatures`（J。市場の評価の4個。オッズを使う予想が渡す。この予想は使う）、`PopularityHistoryFeatures`（J。人気と人気の履歴。人気を使う予想だけが渡す。この予想は使わない）、`OddsFeatures`（K。この予想は使わない）、`PeopleMarketFeatures`（L。騎手・調教師・血統の市場に対する成績の4個。この予想は使う）、`HorseAbilityFeatures`（M。馬の力の材料の 202個。この予想の木曜・前日のモデルが使う）、`PoolSupportFeatures`（N。券種ごとのオッズから見た支持の6個。この予想の当日のモデルが使う）、`HeadToHeadRatingFeatures`（O。対戦レーティングの7個。部品は `feature/head_to_head/`、元の記録は `HeadToHeadRunRepository`。この予想の木曜・前日のモデルが使う）、`PaceForecastFeatures`（P。展開の予想の結果の 20個。部品は `feature/pace_forecast/`、元の予測は `EntryRecords.pace_forecasts`。この予想の木曜のモデルは、同じ部品 `PaceForecastTableBuilder` を `PaceAttachment` から使う）、`FinishPowerFeatures`（Q。勝ち切る材料の 10個。元の記録は `EntryRecords.finish_records`。この予想の当日の1着のモデルだけが使う） | `build(記録)` |
| `ability/` の14 | まとまり M を作る部品: `AbilitySources`（元の記録の入れ物）、`AbilityTableBuilder`（入口。下の部品を順に呼ぶ）、`AbilityRunFocus`（予測のとき、対象の出走の材料に要る出走だけに絞る。値は変わらない）、`SpeedFigureHistory`（スピード指数）、`RaceStrength`（レースの強さ）、`RacePace`（ペース）、`PastRunHistory`（過去走）、`CumulativeRecordRates`（通算の成績）、`RecentRecordRates`・`RecentPeopleRates`（直近の成績）、`RaceRelativeColumns`（レース内の比べ）、`RaceLevelColumns`（展開の手がかり）、`SalePriceColumns`（セリの価格）と、列の名前の一覧 `ability_columns.py`。研究「馬の力と展開でオッズに勝つ」の表の作り方を移したもの（[09-features.md の M](09-features.md#m-馬の力の材料202個木曜前日のモデル)） | ― |
| `history/` の10クラス | 過去の記録から数える部品: `AsOfLookup`（開催日の N 日前までで、いちばん新しい記録を引く）、`DatedRecords`（鍵と日付を持つ記録の表）、`RecentRunSummary`（近5走のまとめ）、`PopularityRunSummary`（近5走の人気のまとめ。まとまり J の材料）、`Top3Rate`（近1年の3着以内の割合）、`PedigreeTop3Rate`（父・母の父の産駒の近1年の3着以内の割合）、`MarketExcessRate`（騎手・調教師・血統の近1年の市場に対する超過3着以内率。まとまり L の材料）、`ConditionUpsetRate`（同じ条件のレースの近1年の中荒れ以上の割合。荒れ具合の予想の材料）、`WorkoutLookup`（14日以内の調教）、`WorkoutCoverage`（調教の記録が DB にある期間。出走ごとに、そのコースの記録があるかを判定する） | ― |

「開催日より前のものだけから計算する」決まり（[11-leak-prevention.md](11-leak-prevention.md) の 2）は、`AsOfLookup` の1か所で守る。

### ml_model/ — 機械学習のモデル（`shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `ProbabilityModel` | 2つのモデルに共通の決まり（インターフェース）。これを守るクラスなら、Workflow は LightGBM か CatBoost かを区別せずに扱える | `fit`・`predict_proba`・`save`・`load` |
| `LightGbmModel` | LightGBM で学習・予測する（[12-lightgbm.md](12-lightgbm.md)） | `fit(学習データ, 検証データ)`、`predict_proba(データ)`、`save(パス)`、`load(パス)` |
| `LightGbmEncoder` | 特徴量を、LightGBM が受け取れる形に変える。学習データから作ったカテゴリの一覧を持つ（[12-lightgbm.md の 3.](12-lightgbm.md)） | `fit(学習データ)`、`transform(データ)` |
| `CatBoostModel` | CatBoost で学習・予測する（[13-catboost.md](13-catboost.md)） | `LightGbmModel` と同じ |
| `CatBoostEncoder` | 特徴量を、CatBoost が受け取れる形に変える（[13-catboost.md の 3.](13-catboost.md)） | `transform(データ)` |
| `EnsembleModel` | 2つのモデルの予測確率を、同じ重みで平均する（決まりは [03-library-basics.md の 6.](03-library-basics.md#6-2つの予測確率を合わせる)） | `predict_proba(データ)`、`predict_members(データ)`（モデルごとの確率）、`combine(モデルごとの確率)`（平均） |

### setting/ — 設定ファイル（初期値のファイルはこの予想、読むクラスは `shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `HyperparameterSettings` | 2つのモデルの設定。設定ファイルを読む入口（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)）。初期値のファイルは予想ごとなので、パスを受け取る（この予想は `setting/default_settings.toml`） | `load(パス, 初期値のファイル)` |
| `LightGbmSettings`・`CatBoostSettings` | モデルごとの設定の値 | ― |
| `SettingsFile` | TOML のファイルを辞書として読む | `read()` |
| `SettingsNameCheck` | 書かれた名前が、初期値のファイルにあるかを確かめる | `check(書かれた設定, 場所)` |
| `SettingsOverlay` | 初期値に、利用者が書いた項目を重ねる | `apply(書かれた設定)` |

### place_value/・win_value/ — 期待値（`shared`）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `PlaceValueColumns` | 予測の結果に足す、オッズから見た3着以内率と複勝の期待値の列（前日・当日だけ）。複勝の見込みの倍率（`PlacePriceEstimator`。`train` が `PlacePriceStep` で保存）を使う | `of(3着以内の確率, 予測用データ)` |
| `WinExpectedValue` | 単勝の期待値 = 1着になる確率 × 単勝オッズ。オッズの無い馬は欠損値 | `of(1着になる確率, 単勝オッズ)` |
| `WinValueColumns` | 予測の結果に足す、1着になる確率と単勝の期待値の列（前日・当日だけ。木曜は確率だけ）。単勝オッズは予測用データの `market` から取る | `of(1着になる確率, 予測用データ)` |
| `ExpectationLevel` | レースの期待度（高・低）を、◎ の単勝の期待値から決める。高は 1.00 以上、低は 1.00 未満（線は固定。[16-evaluation.md の 6.](16-evaluation.md#6--の単勝回収率の確かめ期待度)）。期待値が無ければ（木曜）欠損値 | `of(◎の期待値)` |

### evaluation/ — 当たり具合を測る（`shared`）

評価指標は [穴馬の 16 の「2. 評価指標」](../穴馬が3着以内に入るかを予想/16-evaluation.md#2-評価指標) で決めた（どの予想でも同じ）。ログ損失・AUC・Brier スコアと、各レースで確率がいちばん高い馬の3着以内率・複勝回収率、人気がいちばん上の馬（この予想では 1番人気）の同じ値、同じ人気の中での AUC を出す。

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `ModelEvaluator` | 1つの時点のモデル（LightGBM・CatBoost）と、その平均の当たり具合を測る | `evaluate(時点, アンサンブル, データ)` |
| `MetricCalculator` | 予測確率と正解から、評価指標を計算する | `log_loss`・`auc`・`brier`・`top_pick_place_rate` |
| `Evaluation` | 1つの時点・1つのモデルの当たり具合の値 | ― |
| `TrainingReport` | 学習の結果の入れ物。予想ごとの `workflow/` が作り、`command/` の `TrainingReportTables` が表にする | ― |

## コマンドの引数

コマンドは `train`（学習）と `predict`（1レースの予測）の2つで、リポジトリ直下から `uv run python -m yosou.form_aptitude_top3 <train か predict> …` で動かす。引数の一覧は `--help` で出る（下の表は、`--help` の出力と `command/` のコードで確かめた）。ほかの予想も、同じ名前の引数は同じ意味で使う。

### 2つに共通の引数

`shared` の `CommonArguments` が足す。ほかの道具（`tools/`）と同じ名前にそろえてある。

| 引数 | 既定 | 意味 |
|---|---|---|
| `--models` | `reports/<予想の名前>/models`（この予想は `reports/近走と適性から3着以内を予想/models`） | 学習したモデルの置き場所。`train` は書き、`predict` は読む。JV-Data から作ったもので公開しないので、Git の対象外の `reports/` に置く |
| `--db` | `../jvdata-store/jvdata.duckdb`（環境変数 `YOSOU_DB` があればそのパス） | 元DB のパス。読むだけで、書き込まない |
| `--format` | `markdown` | 出力の形式。`markdown`・`csv`・`json` のどれか |
| `--out` | 無し（標準出力） | 出力をこのファイルに書く |

### train の引数

| 引数 | 既定 | 意味 |
|---|---|---|
| `--config` | 無し（初期値の設定ファイル `setting/default_settings.toml`） | ハイパーパラメータの設定ファイル（TOML）。書いた項目だけが初期値から置き換わる（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)） |
| `--warmup-from`・`--train-from`・`--ability-train-from`・`--valid-from`・`--test-from` | [08-training-data.md の「4. 期間の指定」](08-training-data.md#4-期間の指定) の表 | 学習データの期間の区切り。`--train-from` と `--warmup-from` は今の材料（当日）、`--ability-train-from` は馬の力の材料（木曜・前日。ウォームアップはその前の年の1月1日から）。検証データとテストデータの使い方は [16-evaluation.md の「1. 期間の分け方」](16-evaluation.md#1-期間の分け方) |
| `--development-root` | `reports/展開から着順を予想` | 予想「展開から着順を予想」の置き場所。`train` は年ごとの確かめの予測（`out_of_sample/`）、`predict` は保存した展開のモデル（`models/`）を読む（木曜のモデルだけ） |
| `--figure-cache` | `reports/能力指数/cache` | スピード指数をとっておく場所（木曜・前日のモデルが使う。道具「能力指数」とファイルを共有する）。`predict` にもある |

`train` が出す表は、学習データの期間・検証データでの当たり具合・人気の基準との比べ方・保存したモデル（ここまで `TrainingReportTables`）を「今の材料」「券種オッズなし」「馬の力の材料」「馬の力の材料 ＋ 展開の予想（木曜）」の学習ごとに、3着以内のモデルと1着のモデル（題に「1着:」が付く）の両方で出し、最後に複勝の見込みの倍率（`PlacePriceStep`）を出す。表の見方は [16-evaluation.md](16-evaluation.md#2-評価指標) を参照。

### predict の引数

| 引数 | 既定 | 意味 |
|---|---|---|
| `rid`（位置引数） | ― | 予測するレースの rid（16桁） |
| `--date`・`--venue`・`--race` | ― | rid を省くときに、開催日（YYYY-MM-DD）・競馬場の名前かコード・レース番号の3つでレースを指定する。rid も3つもそろっていなければ止まる |
| `--timing`（必須） | ― | 予測する時点。`木曜`・`前日`・`当日`（英語の `thursday`・`day_before`・`race_day` でもよい）。その時点で学習したモデルを使う（[07-prediction-timing.md](07-prediction-timing.md)） |
| `--odds 馬番:オッズ …` | 無し | 利用者が見た単勝オッズ。空白で区切っても（`--odds 3:2.4 7:5.1`）、コンマで区切っても（`--odds 3:2.4,7:5.1`）よい。前日と当日に使う。省略したときの決め方は [07-prediction-timing.md の「予測のときのオッズの与え方」](07-prediction-timing.md#予測のときのオッズの与え方) |

当日に券種のオッズ（速報の全券種のオッズ `0B30`）が無いレースは、券種の支持を使わない「券種オッズなし」のモデルで予測する（止まらない）。

`predict` が出す表は、1レースの出走馬を「3着以内に入る確率」（LightGBM と CatBoost の平均）の高い順に並べた1つである。列は、順位・馬番・馬名と、前日・当日なら単勝オッズ・オッズから見た3着以内率・複勝的中の確率・複勝の期待値・1着になる確率・単勝の期待値、そのあとに 3着以内に入る確率（平均）・LightGBM・CatBoost の確率が続く。木曜はオッズを使わないので、オッズの列と期待値の列は出ず、1着になる確率だけが出る。複勝の期待値は、`train` で保存した複勝の見込みの倍率があるときだけ出る。1着になる確率と単勝の期待値は、1着のモデル（`models/1着/`）があるときだけ出る（前の版で学習したモデルでは出ない）。

### 引数の決まり

| 決まり | 理由 |
|---|---|
| 引数の名前を途中まで書く省略（`--tim` など）は受け付けない | 書き間違いを、別の引数と取り違えないようにする |
| 引数の書き方の誤り（知らない引数・`--timing` の書き間違いなど）は、使い方を出して止まる。足りない情報（元DB・オッズ・学習したモデルが無いなど）は、「エラー:」で始まる1行の案内を出して止まる（終了コード 1。`tools/共通/cli.py`） | 何を直せばよいかを、その場で分かるようにする。黙って別の値で続けない |
| 元DB は、`train` では学習データを読む段だけ開き、学習のあいだは閉じておく | 学習は何分もかかる。そのあいだ、ほかの道具が元DB を開けなくならないようにする |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-21 |
| 更新 | 2026-09-21: 実装に合わせて、1ファイル1クラス・1 SQL 1 リポジトリの決まりと、フォルダの構成を書き直した |
| 更新 | 2026-09-22: 予想で変わらないクラスを `src/yosou/shared/` に移したのに合わせて、パッケージ構成とクラスの置き場所を書き直した |
| 更新 | 2026-09-23: 単勝オッズを特徴量に足したのに合わせて、`MarketFeatures`・`OddsInput`・`OddsResolver`・`AnnouncedOddsApplier`・`AnnouncedOddsRepository` を足した |
| 更新 | 2026-09-28: 「コマンドの引数」を足した。`EnsembleModel` の行に平均のしかたを書いた。特徴量の数を 75個にそろえた |
| 更新 | 2026-09-30: まとまり L（騎手・調教師・血統の市場に対する成績）の4個を足したのに合わせて、`PeopleMarketFeatures`・`MarketExcessRate`・`MarketRunRepository`・`EntryRecords.market_runs` を足し、`CATALOG` の式と特徴量の数を 79個にそろえた。`group/`・`history/` のクラスの数を今のファイルに合わせて数え直し、`shared` に移っていた `MarketFeatures` を `group/` の行にまとめた |
| 更新 | 2026-10-01: 研究「一番人気を疑う」の2つの直し方を移したのに合わせて、まとまり M（`HorseAbilityFeatures` と `ability/`）・N（`PoolSupportFeatures`）、そのリポジトリとローダー、`pool_dataset_builder`・`ability_dataset_builder`・`PoolFreeData`・`PoolAvailability`・`FigureCacheArgument`、時点ごとのモデルの決めごと、`train` の `--ability-train-from`・`--figure-cache` を足した。券種オッズのリポジトリを custom_binary から `shared` に移した |
| 更新 | 2026-10-02: 当日のモデルにも馬の力の材料（M。今の材料と名前の重なる2つを除く 200個）を足した（PR #52 の残課題。7つの区切りで基準を満たした）。当日は 285個、券種オッズなしは 279個 |
| 更新 | 2026-10-02: 対戦レーティング（まとまり O）の `HeadToHeadRatingFeatures`・`feature/head_to_head/`・`HeadToHeadRunRepository`・`EntryRecords.head_to_head_runs` を足し、`ABILITY_CATALOG` と `ability_dataset_builder` に O を足した（木曜・前日のモデル） |
| 更新 | 2026-10-02: 展開の予想の結果（まとまり P）の `PaceForecastFeatures`・`feature/pace_forecast/`・`EntryRecords.pace_forecasts`、`PaceAttachment`・`DevelopmentRootArgument`・`PACE_TIMINGS` を足し、木曜のモデルの学習と予測で P を足すようにした |
| 更新 | 2026-10-03: 1着のモデル（15 の 14）のために、`WinBaseline`・`WinTargetData`・`WIN_FOLDER`・`WIN_PROBABILITY`、`win_value/`（`WinExpectedValue`・`WinValueColumns`・`ExpectationLevel`）を足した。`train`・`predict` の出力に1着のモデルの行と列を足した |
| 更新 | 2026-10-04: 勝ち切る材料 Q（15 の 15）のために、`HorseFinishRepository`・`PeopleFinishRepository`・`FinishRecordsLoader`・`FinishPowerFeatures`・`RACE_DAY_WIN_CATALOG`・`FinishPowerFreeData` を足した。`train`・`predict` は3着以内のモデルに渡す前に Q を外す |
