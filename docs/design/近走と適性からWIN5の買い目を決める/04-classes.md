# 04 クラスとパッケージの設計

**この文書で決めること:** 今のモデル（今毎週の予想に使っているモデル）の1着の確率を、この予想がどう受け取るか。この予想だけに要るクラス（WIN5 の日を読む・レースごとに使う確率を選ぶ・確率をそろえる・配当を見積もる・買い目を組む・過去の WIN5 で精算する）は何か。それらをどのフォルダ（パッケージ）・ファイルに置くか。コマンドの引数は何か。

**結論: 今のモデルの予測を作る部品（`DatasetBuilder`・`FeatureBuilder`・`PredictionWorkflow`・LightGBM と CatBoost のモデルなど）の多くは、すでに `src/yosou/shared/` にある。今のモデルのパッケージと道具「今週の予想」だけが持っていた「予測の流れの組み立て」と「時点の選び方」は `shared` に移した（材料を作る部品だけは `yosou.form_aptitude_materials`）。この予想はそれを呼んで、今のモデルの学習済みモデルで1着の確率を出す（[15-decisions.md の 9](15-decisions.md#9-今のモデルの1着の確率の受け取り方)）。この予想だけに作るのは、WIN5 の日の流れを進める `Win5PredictionWorkflow` と、対象レース（`leg/`）・配当（`payout/`）・買い目（`formation/`）・精算（`settlement/`）の部品、リポジトリ、コマンドである。モデルを学ぶクラスは作らない。**

- 1ファイル1クラス、1クラス1つの仕事、1 SQL につき1つのリポジトリ、入れ子は1段まで、という分け方の決まりは手本と同じで、[手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) を参照。
- 今のモデルのクラスの仕事は [手本の 04 の「クラスの一覧」](../近走と適性から3着以内を予想/04-classes.md#クラスの一覧) を参照。この文書には、移すものと、この予想だけのクラスを書く。
- 用語の意味（public メソッド・オーケストレーション・リポジトリ）は [手本の 02 の「機械学習の用語」](../近走と適性から3着以内を予想/02-glossary.md#機械学習の用語) を、「今のモデル」は [02-glossary.md](02-glossary.md#今のモデルの用語) を参照。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。

## 1. 今のモデルの1着の確率の受け取り方

この予想は、道具「今週の予想」が出すのと同じ1着の確率を、WIN5 の1レース目の締め切り前に、対象レース5つについて出す必要がある。**予想のパッケージどうしで import はしない**（片方を直すともう片方が壊れる）ので、今のモデルのパッケージと道具にしか無かった次のものを `shared` に移し、今のモデル・道具「今週の予想」・この予想の3つから使う（[15-decisions.md の 9](15-decisions.md#9-今のモデルの1着の確率の受け取り方)）。移す作業は済んでいる。

| 移したもの | 前の置き場所 | 移した先 | この予想での使い方 |
|---|---|---|---|
| 特徴量の一覧（`ABILITY_CATALOG`・`RACE_DAY_CATALOG`・`RACE_DAY_WIN_CATALOG` など） | `form_aptitude_top3/feature/feature_catalog.py` | `shared/feature/form_aptitude_catalog.py` | 今のモデルの予測用データを作る |
| `DatasetBuilder` の組み立ての関数（`ability_dataset_builder()`・`race_day_dataset_builder()` など） | `form_aptitude_top3/dataset/dataset_assembly.py` | `shared/dataset/form_aptitude_assembly.py` | 同上 |
| 時点の並びとモデルの置き場所の名前（`ABILITY_TIMINGS`・`WIN_FOLDER`・`POOL_FREE_FOLDER` など） | `form_aptitude_top3/workflow/prediction_timings.py` | `shared/workflow/form_aptitude_timings.py` | 今のモデルの1着のモデルを、時点ごとのフォルダから読む |
| 予測の流れの組み立て（時点に合わせて `DatasetBuilder`・材料を足す関数・モデルを選んで `PredictionWorkflow` を作るところ） | `form_aptitude_top3/command/predict_command.py`、道具「今週の予想」の `RaceForecaster._workflow()` | `shared/workflow/form_aptitude_prediction.py` の `FormAptitudePrediction`（材料を作る部品の決まりは `shared/workflow/form_aptitude_materials.py` の `FormAptitudeMaterials`） | 対象レースの、今のモデルの1着の確率を出す（`run(接続, レースID, 時点)` が全頭の表を返す） |
| 材料（P・S・T・U・V）を作る部品 `MaterialAttachers` | `form_aptitude_top3/command/material_attachers.py` | `src/yosou/form_aptitude_materials/material_attachers.py`（`shared` ではない） | `FormAptitudePrediction` に、接続から作る関数として渡す。予想「展開から着順を予想」（`yosou.race_development`）の保存したモデルと材料のパッケージ（`development_score`・`track_bias` など）を使うので、`shared` に置くと `shared` が予想のパッケージを参照することになる。そこで `shared` には決まり（`FormAptitudeMaterials`）だけを置き、守るクラスを材料の部品のパッケージに置いた |
| レースごとの時点の選び方（オッズ・馬番・馬体重・馬場状態の有無から木曜・前日・当日を選ぶ） | 道具「今週の予想」の `TimingChooser`・`TimingChoice` | `shared/workflow/timing_chooser.py`・`timing_choice.py` | 対象レースで、今のモデルのどの時点を使うかを選ぶ |
| 引数 `--development-root`（`DevelopmentRootArgument`。前日のモデルが使う、予想「展開から着順を予想」の置き場所） | `form_aptitude_top3/command/development_root_argument.py` | `shared/command/development_root_argument.py` | `predict` の引数 |

今のモデルのパッケージと道具「今週の予想」も、移したあとの `shared` を使う形に直した（今のモデルのパッケージは `command/` と `setting/` だけになった）。こうすると、道具「今週の予想」・発走前の通知とこの予想は、同じ部品・同じ学習済みモデルで1着の確率を出すので、値が食い違わない。

| まとまり | 共通にするか | この予想だけのもの |
|---|---|---|
| `repository/`（データの読み書き） | 共通（出走・過去走・調教・速報・締め切り前のオッズ・券種オッズ・今のモデルのファイル） | WIN5 の日と過去の WIN5 を読む SQL、配当の見積もりの式のファイル |
| `dataset/`・`feature/`・`ml_model/`・`setting/` | 全部共通（移したものを含む）。材料を作る部品は `yosou.form_aptitude_materials` | 無し（この予想はモデルを学ばないので、ハイパーパラメータの設定ファイルも持たない。[14-hyperparameter-settings.md](14-hyperparameter-settings.md)） |
| `workflow/`（流れを進める） | 今のモデルの予測の流れ（移した `FormAptitudePrediction` と `PredictionWorkflow`）と時点の選び方 | WIN5 の日の予測の流れ `Win5PredictionWorkflow` |
| `leg/`・`payout/`・`formation/`・`settlement/` | 無し | 下の「3.」 |
| `command/` | 部品は共通、入口は予想ごと | コマンドの組み立てと引数 |

| 決まり | 理由 |
|---|---|
| `shared` のクラスは、予想のパッケージを参照しない | 片方の予想の都合が、もう片方に入り込まない |
| 予想のパッケージどうしも参照しない（`form_aptitude_win5_tickets` から `form_aptitude_top3` を import しない）。材料を作る部品 `yosou.form_aptitude_materials` は予想のパッケージではないので、`command/` から使ってよい | 両方で使う部品は `shared` に置く。予想を直したときに、ほかの予想が壊れない |
| この予想は、今のモデルの学習済みモデルを読むだけで、書かない | 今のモデルの学び直しは、今のモデルのコマンド（`python -m yosou.form_aptitude_top3 train`）が受け持つ |
| 1着の確率をレースの中でそろえるのは、今のモデルが2つのモデルの確率を平均したあとにする | 平均する前にそろえると、LightGBM と CatBoost のどちらかの確率の大きさの癖が、平均に残るため |
| 配当の見積もりと買い目の組み方は、確率の出どころを知らない | 今のモデルの確率でも、オッズから見た勝率でも、同じ部品で組の期待値を出せる。過去の WIN5 での確かめで、区切りごとの予測を渡すのにも使える（[16-evaluation.md の 1.](16-evaluation.md#1-期間の分け方)） |

## 2. パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。この予想のパッケージ名は、フォルダ名「近走と適性からWIN5の買い目を決める」（[15-decisions.md の 6](15-decisions.md#6-フォルダ名)）に合わせて `form_aptitude_win5_tickets`（form = 近走、aptitude = 適性、win5_tickets = WIN5 の買い目）とする。

```text
src/yosou/form_aptitude_win5_tickets/       近走と適性からWIN5の買い目を決める
├── __main__.py                     コマンドの入口（command/ を呼ぶだけ）
├── command/                        コマンド（fit-payout・predict）の引数と、配当の見積もりの式を作る段
├── workflow/                       WIN5 の日の予測の流れ（ほかを順に呼ぶだけ）
├── leg/                            対象レース1つ: 使う確率を選ぶ・今のモデルの1着の確率を出す・レースの中でそろえる
├── payout/                         配当の見積もり: 発売票数の見積もり・式の材料・式・上限と自分の1票
├── formation/                      買い目: 馬の並べ方・フォーメーション・日の期待値・組み方の探索・買う日の判断
├── settlement/                     過去の WIN5 での精算: 当たり・返還・払戻、比べる相手の買い目
├── repository/                     WIN5 の日・過去の WIN5 を読む SQL、配当の見積もりの式のファイル
└── tests/                          テスト。合成DB だけを使う（keiba-yosou の決まり）
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く。ファイルの名前は、クラスの名前を小文字と `_` にしたもの（`FormationSearch` → `formation_search.py`）。この予想が作るものは、配当の見積もりの式のファイル `payout_estimator.json` と、実際に予想した結果の記録（`記録/<開催日>.json`）で、どちらも Git の対象外の `reports/近走と適性からWIN5の買い目を決める/` に置く。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `form_aptitude_win5_tickets` → `form_aptitude_materials`（`command/` だけ）→ `shared`。`shared` から予想のパッケージと `form_aptitude_materials` を参照しない | 参照が循環すると、1つを直すと全部に響く |
| 予想のパッケージの中も一方向にする: `command` → `workflow` → `leg`・`formation`、`formation` → `payout`。`settlement` は `formation` と `payout` を使う。`repository` は `workflow` と `command` から使う | 手本と同じ決まり |
| 各フォルダの `__init__.py` で外に出すのは、ほかのフォルダから使うクラスだけにする | 外に見せるものが少ないほど、中を変えても外に響かない |
| この構成は、作りながら動かしてよい | 作る前に決めた構成は、少ない情報で決めたものだからである |

## 3. この予想だけのクラスの一覧

### workflow/ — 流れを進める

| 名前 | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `Win5PredictionWorkflow` | WIN5 の日の予測の流れを進める。その日の WIN5 を読み、対象レースごとに使う確率を選んで今のモデルの1着の確率を出してそろえ、発売票数を見積もり、買い目を組み、買うかどうかを決める | `run(開催日, 予算, 買う日の線)` | `Win5DayRepository`、`LegModelChooser`、`LegWinPredictor`、`RaceWinShare`、`Win5HistoryRepository`、`PoolSizeEstimate`、`FormationSearch`、`DayBuyJudge` |

`Win5PredictionWorkflow` は、ほかのクラスを呼んで受け渡すだけで、計算・判断・SQL は書かない。

### leg/ — 対象レース1つの1着の確率

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `LegModel` | 対象レースで使う確率を表す値（列挙。今のモデルの当日・今のモデルの前日・オッズだけ）と、選んだ理由の文 | ―（値） | ― |
| `LegModelChooser` | 対象レースが障害なら「オッズだけ」。平地なら、`shared` に移した時点の選び方で今のモデルの時点を選び、木曜（オッズが無い）なら止める（[06-flowchart.md の図1](06-flowchart.md#図1-対象レースで使う確率の選び方)） | `choose(接続, レースID)` | 移した `TimingChooser` |
| `LegWinPredictor` | 選んだ時点で、対象レースの全頭の今のモデルの1着の確率（2つのモデルの平均）を出す。当日に券種のオッズが無いときに券種オッズなしのモデルに切り替えるのは、今のモデルの流れの中で行われる。「オッズだけ」のときは、オッズから見た勝率をそのまま確率にする。`FormAptitudePrediction` は `command/` が作って渡す（材料を作る部品 `MaterialAttachers` を、接続から作る関数として渡す） | `predict(接続, レースID, LegModel)` | 移した `FormAptitudePrediction`、共通の `MarketWinProbability` |
| `RaceWinShare` | 1レースの全頭の1着の確率を、合計が 1 になるようにそろえ、オッズから見た勝率と上乗せの列を足す | `of(1レースの予測の結果)` | 共通の `MarketWinProbability` |

### payout/ — 配当の見積もり

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `PoolSizeEstimate` | その日の発売票数を、それより前の WIN5 の発売票数から見積もる（[09-features.md の 2.](09-features.md#2-配当の見積もりに使う値)） | `of(過去の WIN5, 開催日, 土曜か)` | ― |
| `PayoutFeatures` | 組の材料（市場の組の確率の逆数の対数、キャリーオーバーの比の対数）を作る | `of(市場の組の確率, キャリーオーバー, 発売票数の見積もり)` | ― |
| `PayoutEstimator` | 配当の見積もりの式。過去の当たり組で傾きと切片と戻すときの補正を決め（`fit`）、組の材料から式の値を出す（`estimate`）（[10-target.md の 2.](10-target.md#2-配当の見積もりで当てるもの)） | `fit(材料, 払戻)`、`estimate(材料)`、`to_dict()`、`from_dict(値)` | scikit-learn の `LinearRegression` |
| `PayoutCeiling` | 式の値に、払戻の上限と自分の1票の分を当てて、見積もりの配当にする（[06-flowchart.md の図2](06-flowchart.md#図2-組1つの配当の見積もり)） | `apply(式の値, 払戻に回るお金)` | ― |

### formation/ — 買い目

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `LegOrdering` | 対象レースの馬を、買い目に入れる順に並べる決まり（列挙。上乗せの順・1着の確率の順。[15-decisions.md の 5](15-decisions.md#5-買い目の組み方と予算の決め方)） | `order(1レースの確率の表)` | ― |
| `Formation` | フォーメーションを表す値。レースごとに選んだ馬番の並びと、点数（頭数のかけ算） | `points`、`combos()` | ― |
| `FormationValue` | フォーメーションの全部の組について、当たる確率と見積もりの配当を出し、買い目のどれかが当たる確率と日の期待値を返す | `of(Formation, そろえた確率, 市場の組の材料)` | `PayoutFeatures`、`PayoutEstimator`、`PayoutCeiling` |
| `FormationSearch` | 予算に収まる頭数の並び（各レース何頭か）を全部試し、各レースは `LegOrdering` の順に上から選んで、見積もりの払戻の合計がいちばん大きいフォーメーションを選ぶ（[06-flowchart.md の図3](06-flowchart.md#図3-買い目の組み方と買う日の判断)） | `best(5レースの確率の表, 予算)` | `LegOrdering`、`Formation`、`FormationValue` |
| `DayBuyJudge` | 日の期待値が買う日の線以上なら「買う」、未満なら「見送り」 | `judge(日の期待値, 線)` | ― |

### settlement/ — 過去の WIN5 での精算（[16-evaluation.md](16-evaluation.md) の確かめに使う）

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `Win5Settlement` | 過去の WIN5 の1回について、買い目が当たったか、返還があったかを元DB の当たり組と照らし、払戻（返還の代金を含む）を出す | `settle(Formation, 過去の WIN5 の1回)` | ― |
| `RuleFormations` | 比べる相手 (1)。ルール集の WIN5 のルール（1レースだけ穴馬3頭・残り上位人気2頭の 48点 × 5セット = 240点）の買い目を、オッズの順の人気から作る | `of(5レースの人気)` | `Formation` |
| `PopularityFormation` | 比べる相手 (2)。各レースの人気の上位から、予算に収まるいちばん大きいフォーメーション（各レースの頭数をなるべくそろえる）を作る | `of(5レースの人気, 予算)` | `Formation` |
| `Win5BacktestTables` | 買い方ごと・期間ごとの、買った日数・投資・払戻・回収率・的中率・開催日を単位にした 90% の幅を表にする | `tables(精算の結果)` | ― |

### repository/ — この予想だけの読み書き

| クラス | 読む・書くもの | 主な public メソッド |
|---|---|---|
| `Win5Day` | WIN5 の日を表す値。開催日、対象レース5つのレースID（発売の順）、キャリーオーバー金額初期、土曜か日曜・祝日か（手本の `TargetScope` と同じく、リポジトリが返す値なので `repository/` に置く） | ―（値） |
| `Win5DayRepository` | 元DB の `wf` と子表 `wf__重勝式対象レース情報` から、1つの開催日の WIN5（対象レース5つ・キャリーオーバー金額初期）を読み、`Win5Day` にする（SQL 1本） | `read(開催日)` |
| `Win5HistoryRepository` | 元DB の `wf`・`wf__重勝式対象レース情報`・`wf__重勝式払戻情報` と事実表から、ある日より前の WIN5 の回ごとに、対象レース・当たり組・払戻・発売票数・キャリーオーバー・返還と的中無の印・当たり組の5頭の確定単勝オッズを読む（SQL 1本。中止の回は読まない） | `read(この日より前)` |
| `Win5ForecastRecordRepository` | 実際に予想した結果（日のまとめ・買い目・対象レースごとの確率と、使ったオッズの断面）を `記録/<開催日>.json` に書く・読む（SQL は持たない）。確定オッズで確かめた成績と、実際に予想した成績を同じ表で比べるため（[15-decisions.md の 7](15-decisions.md#7-締め切り時点のオッズと確定オッズの差の扱い)） | `save(予測の結果)`、`load(開催日)` |
| `PayoutEstimatorRepository` | 配当の見積もりの式（傾き・切片・戻すときの補正・使った期間）を `payout_estimator.json` に書く・読む（SQL は持たない） | `save(式)`、`load()` |

### command/ — コマンド

| クラス | 置き場所 | 仕事 | 主な public メソッド |
|---|---|---|---|
| `CommandLine` | この予想 | 入口。引数を読み、サブコマンドを実行し、結果の表を出す | `run(引数)` |
| `FitPayoutCommand` | この予想 | `fit-payout`: 配当の見積もりの式を作る。`--before` の日より前の WIN5 の当たり組で `PayoutEstimator` を作り、`PayoutEstimatorRepository` で保存する。式の傾き・切片・外れの散らばり・使った回数の表を返す | `run(引数)` |
| `PredictCommand` | この予想 | `predict`: WIN5 の日を予測する。`--budget` と `--min-value` を受け取り、保存した式を読んで `Win5PredictionWorkflow` に渡す。結果は `Win5ForecastRecordRepository` で自動で記録する | `run(引数)` |
| `Win5ForecastTables` | この予想 | 予測の結果を、日のまとめ・選んだ買い目・対象レースごとの全頭の表・予算の候補ごとの表にする（下の「4.」） | `tables()` |
| `CommonArguments` | `shared` | 共通の引数（`--db` `--format` `--out`。`--models` はこの予想では式の置き場所） | `add_to(parser)` |
| `FigureCacheArgument` | `shared` | 今のモデルの予測に要る引数 `--figure-cache`（今のモデルのコマンドと同じ） | `add_to(parser)` |
| `DevelopmentRootArgument` | `shared` | 今のモデルの予測に要る引数 `--development-root`（前日のモデルが使う、予想「展開から着順を予想」の置き場所。今のモデルのコマンドと同じ） | `add_to(parser)` |

過去の WIN5 での確かめの入口は、この予想のコマンドではなく、道具「印の成績」に足す（`--win5`。[16-evaluation.md の 7.](16-evaluation.md#7-道具と全券種の回収率)）。道具は、この予想の `settlement/`・`formation/`・`payout/` の部品を呼ぶだけにする（同じ精算を2か所に書かない）。

## 4. コマンドの引数

コマンドは `uv run python -m yosou.form_aptitude_win5_tickets <fit-payout か predict> …` で動かす。共通の引数（`--db`・`--format`・`--out`）と引数の決まりは、[手本の 04 の「コマンドの引数」](../近走と適性から3着以内を予想/04-classes.md#コマンドの引数) と同じである。

| コマンド | 引数・出力 | この予想では |
|---|---|---|
| 共通 | `--models` の既定 | `reports/近走と適性からWIN5の買い目を決める`。配当の見積もりの式 `payout_estimator.json` を置く |
| 共通 | `--form-models` | 今のモデルの学習済みモデルの置き場所。既定は `reports/近走と適性から3着以内を予想/models`（今のモデルのコマンドの既定と同じ） |
| `fit-payout` | `--before 日` | この日より前の WIN5 で式を作る。既定は今日 |
| `fit-payout` | 出す表 | 配当の見積もりの式の表（傾き・切片・外れの散らばり・使った回数） |
| `predict` | `--date` | WIN5 の開催日（省略すると今日） |
| `predict` | `--budget 点数` | 1回の予算（点数）。省略すると、[16-evaluation.md の 4.](16-evaluation.md#4-買い目の組み方と買う日の線) で選んだ値 |
| `predict` | `--min-value 期待値` | 買う日の線。省略すると、[16-evaluation.md の 4.](16-evaluation.md#4-買い目の組み方と買う日の線) で選んだ値 |
| `predict` | `--figure-cache`・`--development-root` | 今のモデルの予測に要る置き場所。意味と既定は今のモデルのコマンドと同じ |
| `predict` | `--odds`・`--timing` | 受け取らない。対象レースが5つあり、オッズは元DB の締め切り前のオッズを、時点はレースごとに選ぶ（[07-prediction-timing.md](07-prediction-timing.md#対象レースごとの確率の選び方)） |
| `predict` | 出す表 | (1) 日のまとめ（キャリーオーバー・発売票数の見積もり・点数・金額・買い目のどれかが当たる確率・日の期待値・買う／見送り）、(2) 選んだ買い目（レースごとの馬番）、(3) 対象レースごとの全頭の表（馬番・馬名・使った時点・そろえた1着の確率・オッズから見た勝率・上乗せ・買い目に入れたか）、(4) 予算の候補ごとの、いちばん良い買い目の当たる確率と日の期待値 |
| `predict` | 止まるとき | その日の WIN5 が元DB に無い（jvdata-store で速報の WIN5 を取り込む案内を出す）、対象レースのどれかに締め切り前のオッズが無い（速報のオッズを取り込む案内を出す）、配当の見積もりの式が無い（`fit-payout` を案内する）、今のモデルの学習済みモデルが無い（今のモデルの `train` を案内する） |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-11-08 |
| 更新 | 2026-11-08: 15 の 3〜12 が決まり、パッケージ名をフォルダ名に合わせ、実際の予想の記録（15 の 7）を足した |
| 更新 | 2026-11-08: 15 の 1 が決まり、1着のモデルを学ぶクラスを外し、今のモデルの1着の確率を受け取る形にした |
| 更新 | 2026-11-08: 「1.」の部品を移した。材料を作る部品 `MaterialAttachers` は、予想「展開から着順を予想」を使うので `shared` でなく `yosou.form_aptitude_materials` に置き、`shared` には決まり `FormAptitudeMaterials` を置いた。`--development-root` の引数を表に入れた |
