# 04 クラスとパッケージの設計

**この文書で決めること:** 手本の予想・危険な人気馬の予想と、この予想で、同じ仕事をするクラスをどこに置くか。この予想だけに要るクラスは何か。それらをどのフォルダ（パッケージ）・ファイルに置くか。学習と予測のコマンドの引数のうち、手本と違うものは何か。

**結論: データを読む・特徴量を作る・学習する・予測するのクラスは、手本と危険な人気馬の予想と共通で、すでに `src/yosou/shared/` にある。この予想では、危険な人気馬の予想だけが持っている「人気に関する部品」と、手本だけが持っている「3着以内の目的変数を付ける部品」も `shared` に移し、3つの予想から使う。この予想だけに作るのは、穴馬の行を選ぶ・区分を決める・区分で絞る、の仕事のクラスと、予測の流れを進める `PredictionWorkflow`、コマンドである。学習の流れ（`TrainingWorkflow`）は共通のものをそのまま使う。**

- 1ファイル1クラス、1クラス1つの仕事、1 SQL につき1つのリポジトリ、という分け方の決まりは手本と同じで、[手本の 04 の「分け方の決まり」](../近走と適性から3着以内を予想/04-classes.md#分け方の決まり) を参照。
- 共通のクラスの一覧（どのクラスが何をするか）は [手本の 04 の「クラスの一覧」](../近走と適性から3着以内を予想/04-classes.md#クラスの一覧) を参照。人気に関するクラスの仕事は [人気馬の 04 の「3. この予想だけのクラスの一覧」](../人気馬が4着以下になるかを予想/04-classes.md#3-この予想だけのクラスの一覧) を参照。この文書には、この予想だけのクラスと、移すものを書く。
- 用語の意味（public メソッド・オーケストレーション・インターフェース・リポジトリ・エンコーダー）は [手本の 02 の「機械学習の用語」](../近走と適性から3着以内を予想/02-glossary.md#機械学習の用語) を参照。
- クラスどうしが、どの順にどのメソッドを呼ぶかは [05-sequence.md](05-sequence.md) を参照。

**2026-09-24 の追記。** 既存モデルの修正計画での直し（[15-decisions.md の 12](15-decisions.md#12-既存モデルの修正計画での直し)）で、この予想は、共通の基準（`Top3Baseline`）・まとまり K（`OddsFeatures`）・区分ごとの学習と予測（`SegmentedTraining`・`SegmentedPrediction`）・複勝の期待値（`place_value/`・`PlacePriceStep`）を使うようになり、この予想だけのものとして区分での分け方（`SEGMENTS`）が増えた。下の表は、2026-09-28 にコードで確かめて、それらを書き足したものである。

**2026-09-30 の追記。** 手本と同じまとまり L（騎手・調教師・血統の市場に対する成績。共通の `PeopleMarketFeatures`）を足した。材料の過去の全出走は、共通の `MarketRunRepository` で読む（ローダーに `market_runs=` で渡す）。クラスの仕事は [手本の 04 の「クラスの一覧」](../近走と適性から3着以内を予想/04-classes.md#クラスの一覧) を参照。

**2026-10-01 の追記。** この予想だけのまとまり M（複勝オッズから見た評価。`feature/` の `PlaceOddsFeatures`・`PlaceMarketRate`。[15-decisions.md の 16](15-decisions.md#16-複勝オッズを特徴量に入れるか)）と、「買い」の判定（`buy_line/`・`repository/`・`command/` の `BuyLineStep`・`BuyLineReportTable`。[15-decisions.md の 17](15-decisions.md#17-買いの線の決め方)）を足した。共通の部品は2か所だけ変えた。`CalibrationCheck` の材料の表に開催日の列を足し（開催日を単位にした回収率の幅を出すため）、`RequiredInfoCheck` の案内に「複勝の最低オッズ」を足した（その列を持たない予想は素通りする）。

## 1. 共通の部品と、この予想だけの部品の分け方

手本と危険な人気馬の予想に共通の部品は、すでに `src/yosou/shared/` にある（[人気馬の 04 の「1. 共通の部品と、この予想だけの部品の分け方」](../人気馬が4着以下になるかを予想/04-classes.md#1-共通の部品とこの予想だけの部品の分け方)）。この予想は、その2つの予想の中間（人気を使い、3着以内を当てる）なので、両方から部品を借りることになる。**予想のパッケージどうしで import はしない**（片方を直すともう片方が壊れる）。そこで、次を `shared` に移す（[15-decisions.md](15-decisions.md#6-共通部分の置き方)）。これが、この予想を作るときの最初の作業になる。

| 移すもの | 今の置き場所 | 移す先 | この予想での使い方 |
|---|---|---|---|
| `PopularityApplier`・`PopularityInput` | `favorites_out_of_top3/dataset/` | `shared/dataset/` | 予測のときの人気を決める。`PopularityInput` は「馬番:人気」に加えて「馬名:人気」（木曜用。馬番が無い）も受け取れるように広げる |
| `AnnouncedOddsRepository` | `favorites_out_of_top3/repository/` | `shared/repository/` | 締め切り前のオッズから人気を作る |
| `PopularityHistoryFeatures`・`PopularityRunSummary`・J の一覧 `POPULARITY_FEATURES` | `favorites_out_of_top3/feature/` | `shared/feature/group/`・`shared/feature/history/`・`shared/feature/feature_catalog.py` | まとまり J（[09-features.md](09-features.md#j-人気と人気の履歴4個)）を作る |
| `TargetBuilder`（3着以内なら 1。1着の列も付ける） | `form_aptitude_top3/dataset/` | `shared/dataset/`。名前は `Top3TargetBuilder` に変える | 目的変数を付ける（[10-target.md](10-target.md#作り方)） |
| 多頭数の線引き（14頭） | `favorites_out_of_top3/dataset/favorite_rule.py` の定数 `LARGE_FIELD_FROM` | `shared/dataset/` の定数 | `LongshotRule` と `FavoriteRule` が同じ値を使う。線引きを1か所で持つ |

移したあとの、まとまりごとの置き場所は次のとおり。

| まとまり | 共通にするか | この予想だけのもの |
|---|---|---|
| `repository/`（データの読み書き） | 共通（締め切り前のオッズを読むものと、2026-09-30 からは L の材料を読む `MarketRunRepository` を含む。M の材料の複勝オッズは、すでにある `PlaceOddsRepository` が読む） | 「買い」の線のファイルを読み書きする `BuyLineRepository`（2026-10-01。SQL は持たない） |
| `dataset/`（学習データ・予測用データを作る） | 大半を共通（2026-09-24 からは、基準の決まり `TargetBaseline` と、3着以内の基準 `Top3Baseline`、オッズを決める `OddsResolver`・`OddsInput` も共通） | 穴馬の決まり・区分・行の選択・区分での絞り込み |
| `feature/`（特徴量を作る） | 共通（まとまり A〜J と、2026-09-24 からは K の `OddsFeatures`、2026-09-30 からは L の `PeopleMarketFeatures`） | この予想の特徴量の一覧 `CATALOG` と、この予想だけのまとまり M（`PlaceOddsFeatures`・`PlaceMarketRate`。2026-10-01） |
| `ml_model/`・`setting/`・`evaluation/` | 共通 | 初期値の設定ファイルだけ（[14-hyperparameter-settings.md](14-hyperparameter-settings.md)） |
| `place_value/`（複勝の期待値。2026-09-24） | 共通（手本と同じ `PlaceValueColumns` など） | 無し |
| `buy_line/`（「買い」の判定。2026-10-01） | 無し | 線を選ぶ `BuyLineChooser`、印を付ける `BuyJudge`、回収率の幅を出す `DayBootstrapInterval` |
| `workflow/`（流れを進める） | 学習は共通（2026-09-24 からは、区分ごとに学習・予測する `SegmentedTraining`・`SegmentedPrediction` も共通）、予測は予想ごと | `PredictionWorkflow`、予測を出す時点の並び、区分での分け方 `SEGMENTS` |
| `command/` | 部品は共通、入口は予想ごと | コマンドの組み立てと引数（`--pops`・`--zone`・`--min-value`）、「買い」の線を決める段 `BuyLineStep` と、その線で買ったときの成績の表 `BuyLineReportTable` |

**共通のクラスが、予想ごとの違いを知らずに済むようにする。** そのために、`shared` のインターフェース（`Protocol`）を、この予想のクラスが守る（手本・危険な人気馬の予想と同じ仕組み）。

| インターフェース（`shared` にある） | 決まり（public メソッド） | この予想で守るクラス |
|---|---|---|
| `SampleSelector` | `training_samples(出走の行, 学習データの始まり)`、`prediction_runners(出走の行, レースID)`、`keep_samples(特徴量の付いた行)` | `LongshotSelector` |
| `TargetLabeler` | `build(サンプルの行)`、`label_name` | 共通の `Top3TargetBuilder` をそのまま使う |
| `FeatureGroup` | `build(記録)` | 共通の `PopularityHistoryFeatures`（J）と `OddsFeatures`（K。2026-09-24）と `PeopleMarketFeatures`（L。2026-09-30）をそのまま使う。この予想で新しく足すまとまりは M の `PlaceOddsFeatures`（2026-10-01） |
| `TargetBaseline` | `known_from`（基準が分かる最初の時点）、`build(レースの全頭の行)` | 共通の `Top3Baseline` をそのまま使う（2026-09-24。手本と同じ基準） |
| `ProbabilityModel` | `fit`・`predict_proba`・`save`・`load` | 共通の `LightGbmModel`・`CatBoostModel` をそのまま使う |

| 決まり | 理由 |
|---|---|
| `shared` のクラスは、予想のパッケージを参照しない | 片方の予想の都合が、もう片方に入り込まない |
| 予想のパッケージどうしも参照しない（`longshots_in_top3` から `favorites_out_of_top3` を import しない） | 両方で使う部品は `shared` に置く。予想を直したときに、ほかの予想が壊れない |
| `DatasetBuilder` は、行を選ぶクラス（`SampleSelector`）と目的変数を付けるクラス（`TargetLabeler`）を、作られるときに受け取る | 予想ごとの違いが、渡すクラスの中に収まる |
| `keep_samples()` は、特徴量を作ったあとに呼ぶ | レース内順位は、レースの全出走馬から計算する。穴馬だけに絞るのは、そのあとになる（[08-training-data.md](08-training-data.md#3-どのサンプルを入れるか)） |
| 区分で絞るのは、予測確率を出したあとにする | 2026-09-24 からは、中穴と大穴で別のモデルを学習し、穴馬すべてに、その区分のモデルで確率を出す。`--zone` は出力の絞り込みだけである（[15-decisions.md](15-decisions.md#3-区分ごとに別のモデルにするか)） |
| 基準（`Top3Baseline`）は、穴馬に絞る前のレースの全頭で作ってから、穴馬の行だけにする（`DatasetBuilder` が行う） | オッズから見た3着以内率は、同じレースのほかの馬のオッズも使って出すため |
| 「穴馬の区分」の列は、共通の `DatasetBuilder` に「出走の行から残す列」として渡し、学習データの評価用の列と予測の結果に足す | 区分は `LongshotSelector` が出走の行に足す。`DatasetBuilder` は列の名前を受け取るだけで、「どの予想か」を知らずに済む |
| 手本と危険な人気馬の予想も、移したあとの `shared` を使う形に直す | 同じ仕事のクラスが2つに増えると、直すときに片方を忘れる |

## 2. パッケージ構成

予想方法のコードは `src/yosou/` の下に置く（keiba-yosou の決まり）。この予想のパッケージ名は、予想のやり方が分かる `longshots_in_top3`（longshots = 穴馬、in top3 = 3着以内に入る）とする。

```text
src/yosou/shared/                   3つの予想から使う部品
├── repository/                     データの読み書き。1 SQL につき 1 リポジトリ（締め切り前のオッズを含む）
├── dataset/                        学習データ・予測用データを作る（人気を決める部品、3着以内の目的変数と基準、多頭数の線引きを含む）
├── feature/                        特徴量を作る（まとまり A〜L と、過去の記録から数える部品）
├── ml_model/                       LightGBM・CatBoost・エンコーダー・2つの平均
├── place_value/                    複勝の期待値（2026-09-24）
├── setting/                        設定ファイルを読む
├── evaluation/                     当たり具合を測る
├── workflow/                       学習の流れ（TrainingWorkflow）と、区分ごとの学習・予測（SegmentedTraining・SegmentedPrediction）
├── command/                        コマンドの部品のうち、予想に依らないもの（共通の引数・結果の表・複勝の見込みの倍率を決める段）
└── tests/                          共通の部品のテストと、テスト用の合成のシーズン

src/yosou/longshots_in_top3/        穴馬が3着以内に入るかを予想する
├── __main__.py                     コマンドの入口（command/ を呼ぶだけ）
├── command/                        コマンド（train・predict・calibration）の引数
├── workflow/                       予測の流れ（ほかを順に呼ぶだけ）と、予測を出す時点と、区分での分け方（SEGMENTS）
├── dataset/                        穴馬の決まり・区分・行を選ぶ・区分で絞る
├── feature/                        この予想の特徴量の一覧と、この予想だけのまとまり M（複勝オッズから見た評価）
├── buy_line/                       「買い」の判定（線を選ぶ・印を付ける・回収率の幅）
├── repository/                     「買い」の線のファイルの読み書き（SQL は持たない）
├── setting/                        ハイパーパラメータの初期値のファイル
└── tests/                          テスト。合成DB だけを使う（keiba-yosou の決まり）
```

各フォルダには `__init__.py` を置き、その先頭に「クラス → 仕事」の表を書く。ファイルの名前は、クラスの名前を小文字と `_` にしたもの（`LongshotSelector` → `longshot_selector.py`）。学習したモデルは、Git の対象外の `reports/穴馬が3着以内に入るかを予想/models/` の下に、区分ごと・時点ごとに保存する（`<mid・big>/<thursday・day_before・race_day>/`）。直下には、複勝の見込みの倍率のファイル `place_price.json` と、「買い」の線のファイル `buy_lines.json`（2026-10-01）を置く。

| 決まり | 理由 |
|---|---|
| 参照の向きは一方向にする: `longshots_in_top3` → `shared`。`shared` から予想のパッケージを参照しない | 参照が循環すると、1つを直すと全部に響く |
| 予想のパッケージの中も一方向にする: `command` → `workflow` → `dataset` → `feature`。`buy_line` は `workflow` と `command` から、`repository` は `command` から使う | 手本と同じ決まり |
| 各フォルダの `__init__.py` で外に出すのは、ほかのフォルダから使うクラスだけにする | 外に見せるものが少ないほど、中を変えても外に響かない |
| この構成は、作りながら動かしてよい | 作る前に決めた構成は、少ない情報で決めたものだからである |

## 3. この予想だけのクラスの一覧

### dataset/ — 穴馬の決まり・区分・行を選ぶ・区分で絞る

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `LongshotRule` | 穴馬の決まりを表す値。頭数の線引き（共通の定数 14）と、頭数ごとの「穴馬の最初の人気」（4 か 6）・「大穴の最初の人気」（7 か 10）を持つ（[08-training-data.md](08-training-data.md#3-どのサンプルを入れるか)） | `popularity_range(出走頭数)`、`is_longshot(人気, 出走頭数)`、`are_longshots(人気の列, 出走頭数の列)`、`zone_of(人気, 出走頭数)`、`zones_of(人気の列, 出走頭数の列)` | ― |
| `LongshotZone` | 区分を表す値（列挙。中穴・大穴）。`--zone` の文字を読む。指定が無ければ「絞らない」 | `label`、`parse(書き方)` | ― |
| `LongshotSelector` | 学習データ・予測用データに入れる行を選び、「穴馬か」「穴馬の区分」の列を足す。特徴量を作ったあとに、穴馬の行だけを残す（[06-flowchart.md](06-flowchart.md#図1-学習データに入れる行の選び方)）。予測では、人気の分からない馬が1頭でもいれば止める（[06-flowchart.md](06-flowchart.md#図2-予測用データに人気を当てる)） | `training_samples(出走の行, 学習データの始まり)`、`prediction_runners(出走の行, レースID)`、`keep_samples(特徴量の付いた行)` | `LongshotRule`、共通の `FlatRunnerFilter` |
| `LongshotZoneFilter` | 予測の結果を、指定された区分の行だけにする。指定が無ければそのまま返す | `apply(予測の結果, 区分)` | ― |
| `column_names.py` の `IS_LONGSHOT`・`LONGSHOT_ZONE` | 「穴馬か」「穴馬の区分」の列の名前 | ―（値） | ― |
| `dataset_assembly.py` の `dataset_builder()` | この予想の部品（`LongshotSelector`、共通の `Top3TargetBuilder`、`CATALOG`、まとまり A〜F・H・I と共通の `PopularityHistoryFeatures`・`OddsFeatures`・`PeopleMarketFeatures` と M の `PlaceOddsFeatures`、残す列「穴馬の区分」、基準の作り方 `Top3Baseline`）を渡して、共通の `DatasetBuilder` を組み立てる。ローダーには L の材料を読む `MarketRunRepository(接続, PEOPLE_WINDOW_DAYS)` を渡す | `dataset_builder(接続)` | 上のクラスと共通の `DatasetBuilder` |

決めた「馬番（木曜は馬名）→ 人気」は、`PredictionWorkflow` が共通の `DatasetBuilder.build_prediction_data()` に渡し、出走の行に当てるのは共通の `RaceEntryTableRepository` である（危険な人気馬の予想と同じ。[05-sequence.md](05-sequence.md#図2-予測)）。「穴馬の区分」の列は `LongshotSelector` が足し、特徴量としてはモデルに渡さない。学習データを区分に分けること（2026-09-24 から）と、出力の表と評価に使う（[08-training-data.md](08-training-data.md#2-列の種類)）。

### feature/ — 特徴量の一覧と、まとまり M

| 名前 | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `CATALOG`（`feature/__init__.py`） | この予想の特徴量の一覧。共通の A〜I（`BASE_FEATURES`）に共通の J（`POPULARITY_FEATURES`）と K（`ODDS_FEATURES`。2026-09-24）と L（`PEOPLE_MARKET_FEATURES`。2026-09-30）と、この予想だけの M（`PLACE_ODDS_FEATURES`。2026-10-01）を足したもの（当日は 86個。[09-features.md](09-features.md)） | ―（値） | 共通の `FeatureCatalog` |
| `place_odds_catalog.py` の `PLACE_ODDS_FEATURES` | M の4個の一覧（名前・まとまり・数値・前日から分かる） | ―（値） | 共通の `Feature` |
| `PlaceOddsFeatures` | M を作る。複勝の最低・最高オッズ、複勝オッズから見た3着以内率、それと単勝オッズから見た3着以内率の比（[09-features.md の M](09-features.md#m-複勝オッズから見た評価4個)）。`FeatureGroup` を守る | `build(記録)` | `PlaceMarketRate`、共通の `MarketPlaces` |
| `PlaceMarketRate` | 複勝オッズの真ん中の逆数を、同じレースで合計が当たりの頭数（8頭以上は 3、7頭以下は 2）になるようにそろえる | `of(出走の行)` | ― |

`FeatureBuilder` には、この `CATALOG` と、共通の A〜F・H・I の8つに共通の `PopularityHistoryFeatures`・`OddsFeatures`・`PeopleMarketFeatures` と `PlaceOddsFeatures` を足したまとまりの並びを渡す。G（`FieldComparisonFeatures`）は `FeatureBuilder` が内部で持つ。M の材料の複勝オッズは、どの予想でも出走の行に付いている（共通の `EntryRecordsLoader` が `PlaceOddsRepository` で読む）ので、読み出しは増えない。

### buy_line/ — 「買い」の判定（2026-10-01）

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `BuyLineChooser` | 複勝の期待値の線の候補ごとに、検証期間の点数・的中率・回収率を出し、決まり（回収率が 100% を超え、150点以上残る線のうち回収率がいちばん高い線。[16-evaluation.md の 3](16-evaluation.md#3-買いの線引き)）に合う線を選ぶ。無ければ線なし | `rates(期待値, 払戻)`、`choose(期待値, 払戻)` | ― |
| `BuyJudge` | 予測の結果に、その馬の区分の線（「買いの線」）と、複勝の期待値が線以上なら「買い」の印を足す | `judge(期待値, 区分)` | ― |
| `DayBootstrapInterval` | 回収率の 90% の幅を、開催日を単位にしたブートストラップで出す（研究「既存モデルの改善」と同じ出し方） | `of(開催日, 払戻)` | ― |

### repository/ — この予想だけのファイルの読み書き（2026-10-01）

| クラス | 仕事 | 主な public メソッド |
|---|---|---|
| `BuyLineRepository` | 時点 → 区分 → 線を `models/buy_lines.json` に書く・読む。線なしの区分は書かない（人気馬の予想の `DangerThresholdRepository` と同じ形） | `save(線)`、`load()` |

### workflow/ — 流れを進める

| 名前 | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `PredictionWorkflow` | 予測の流れを進める。オッズを決め、人気を決め、予測用データを作り、区分ごとのモデルで2つの予測確率を平均し（`SegmentedPrediction`）、前日・当日は複勝の期待値を足し（`PlaceValueColumns`）、その時点の `BuyJudge` で「買いの線」と「買い」を足し、区分で絞る | `run(レースID, 時点, 渡された人気, 区分, 渡されたオッズ)` | 共通の `OddsResolver`・`PopularityApplier`・`DatasetBuilder`・`SegmentedPrediction`・`PlaceValueColumns`、`BuyJudge`、`LongshotZoneFilter` |
| `prediction_timings.py` の `TIMINGS` | この予想が学習し、予測を出す時点（木曜・前日・当日）の並び。手本と同じ3つ | ―（値） | ― |
| `model_segments.py` の `SEGMENTS` | 学習データを中穴と大穴で分ける決まり（共通の `ModelSegments`。区分の列は「穴馬の区分」、フォルダは `mid`・`big`。2026-09-24） | ―（値） | ― |

`PredictionWorkflow` は、ほかのクラスを呼んで受け渡すだけで、計算・判断・SQL は書かない。

**学習の流れ（`TrainingWorkflow`）は、共通のものをそのまま使う。** この予想は `TIMINGS`（3つ）と、初期値の設定ファイルを渡す。2026-09-24 からは、共通の `SegmentedTraining` が学習データを `SEGMENTS` の区分ごとに分け、区分ごとに `TrainingWorkflow` を回す。モデルは 2つの区分 × 3つの時点 × 2つで、12個になる（[05-sequence.md の図1](05-sequence.md#図1-学習)）。

### command/ — コマンド

| クラス | 置き場所 | 仕事 | 主な public メソッド |
|---|---|---|---|
| `CommandLine` | この予想 | 入口。引数を読み、サブコマンドを実行し、結果の表を出す | `run(引数)` |
| `TrainCommand` | この予想 | `train`: 学習する。期間の引数（`PeriodArguments`）から `TrainingPeriod` を作り、共通の `SegmentedTraining` で区分ごとに学習し、共通の `PlacePriceStep` で複勝の見込みの倍率を保存し、最後に `BuyLineStep` で「買い」の線を保存する | `add_parser(subparsers)`、`run(引数)` |
| `PredictCommand` | この予想 | `predict`: 1レースの穴馬を予測する。`--pops` で全頭の人気を受け取って `PopularityInput` にし、`--odds` を `OddsInput`、`--zone` を `LongshotZone` にする。保存した複勝の見込みの倍率を読んで `PlaceValueColumns` を作り、保存した線（`BuyLineRepository`）か `--min-value` の線で時点ごとの `BuyJudge` を作る | `add_parser(subparsers)`、`run(引数)` |
| `CalibrationCommand` | この予想 | `calibration`: 保存したモデルで、学習に使っていない検証・テストの期間の穴馬を3つの時点で予測し、確率のずれと複勝の期待値の当たり具合を表にする（[16-evaluation.md の 5](16-evaluation.md#5-確率のずれの確かめ方)）。保存した「買い」の線で買ったときの成績の表（`BuyLineReportTable`）も出す | `add_parser(subparsers)`、`run(引数)` |
| `BuyLineStep` | この予想 | 学習のあとに、保存したモデルで検証期間を予測して複勝の期待値を出し（共通の `CalibrationCheck` の検証の行だけを使う）、時点 × 区分ごとに `BuyLineChooser` で線を選んで `BuyLineRepository` に保存する。線の候補ごとの成績の表と、選んだ線の表を返す | `run(学習データ, 期間, モデルの置き場所)` |
| `BuyLineReportTable` | この予想 | 共通の `CalibrationCheck` の材料の表と保存した線から、線以上の穴馬を買ったときの点数・的中率・回収率・開催日単位の 90% の幅・10番人気以下の割合を、時点 × 期間 × 区分（と全体）ごとの表にする | `table()` |
| `PeriodArguments` | この予想 | `train` と `calibration` に共通の、期間の区切りの引数（`--warmup-from` `--train-from` `--valid-from` `--test-from`）。読んだ値から `TrainingPeriod` を作る | `add_to(parser)`、`period(引数)` |
| `CommonArguments` | `shared` | サブコマンドに共通の引数（`--models` `--db` `--format` `--out`） | `add_to(parser)` |
| `TrainingReportTables` | `shared` | 学習の結果を表にする | `tables()` |
| `PredictionTable` | `shared` | 予測の結果を、3着以内に入る確率の高い順の表にする。`extra_columns` に「人気順位」「穴馬の区分」と、前日・当日は「オッズから見た3着以内率」「複勝的中の確率」「複勝の期待値」を渡して、その列も出す | `table()` |

`calibration` が使う共通の部品は次のとおり。どれも、目的変数が 3着以内の予想（全頭の予想など）でもそのまま使える形にして `shared` に置いた。

| クラス | 置き場所 | 仕事 | 主な public メソッド |
|---|---|---|---|
| `SegmentedHoldoutPrediction` | `shared/workflow/` | 学習データのうち検証・テストの期間の行を、区分（中穴・大穴）ごとの保存したモデルで予測する。区分は評価用の列で分ける（学習のときの `SegmentedTraining` と同じ） | `predict(学習データ, 時点)` |
| `CalibrationCheck` | `shared/workflow/` | 期間 × 時点ごとに予測し、開催日・正解・確率・人気・払戻と、オッズが分かる時点（前日・当日）なら複勝的中の確率と期待値を並べた材料の表を作る | `run(時期で分けたデータ)` |
| `ProbabilityBands` | `shared/evaluation/` | 予想した確率と実際の割合を、確率の帯ごとに並べる。帯ごとのずれの平均（ECE）も出す | `table(正解, 確率)`、`gap(正解, 確率)` |
| `ValueBands` | `shared/evaluation/` | 複勝の期待値と、実際の的中率・回収率を、期待値の帯ごとに並べる。線以上を全部買ったときの成績も出す | `table(期待値, 的中の確率, 払戻)`、`at_least(…, 線)` |
| `CalibrationReportTables` | `shared/command/` | 材料の表を、4つの表（まとめ・確率の帯ごと・人気ごと・期待値の帯ごと）にする | `tables()` |

`--timing` は、時点の書き方を共通の `PredictionTiming.parse()` で読む。`--zone` の書き方が違うときに止めるのは `LongshotZone.parse()` で、誤りは `共通.cli` が1行で見せる（同じ判断を2か所に書かない）。

## 4. 選ばなかった選び方で変わるクラス

[15-decisions.md](15-decisions.md) で選ばなかった選び方にしたとき、上の一覧がどう変わるかを残しておく。

| 選び方 | 変わるクラス |
|---|---|
| 区分ごとに1つのモデルにする（[15 の 3](15-decisions.md#3-区分ごとに別のモデルにするか) のはじめの決定。2026-09-24 に「中穴と大穴で別のモデル」に決め直した） | `SEGMENTS` が要らなくなり、`SegmentedTraining`・`SegmentedPrediction` には区分「全体」1つだけの `ModelSegments()` を渡す（手本と同じ）。モデルは `models/<時点>/` に置く。上の一覧の、ほかのクラスは変わらない |
| 穴馬の区分を特徴量に入れる（[15 の 5](15-decisions.md#5-穴馬の区分を特徴量に入れるか)） | `feature/longshot_zone_features.py` に、`FeatureGroup` を守る `LongshotZoneFeatures`（出走の行の区分の列を、カテゴリ特徴量「穴馬の区分」にする）を足し、`CATALOG` に1個足して 76個にする |
| 確率を較正する（[15 の 15](15-decisions.md#15-確率を較正するか)） | `shared/ml_model/` に較正のクラス（Platt scaling なら傾きと切片を持つ）と、区分 × 時点ごとに較正をファイルに読み書きするリポジトリを足す。`TrainCommand` が学習のあとに検証期間の予測で較正を学んで保存し、`SegmentedPrediction`（予測）と `SegmentedHoldoutPrediction`（`calibration`）が平均の確率に当てる。複勝の期待値は、その確率から出す（`PlaceValueColumns` は変えない）。比べたときの較正の部品は、研究「既存モデルの改善」の `analysis/calibration/` にある |

## 5. コマンドの引数

コマンドは `uv run python -m yosou.longshots_in_top3 <train か predict か calibration> …` で動かす。**引数の多くは手本と同じである。** 共通の引数（`--models`・`--db`・`--format`・`--out`）、`train` の `--config` と期間の4つ、`predict` の `rid`・`--date`・`--venue`・`--race`・`--timing`・`--odds`、引数の決まりは、[手本の 04 の「コマンドの引数」](../近走と適性から3着以内を予想/04-classes.md#コマンドの引数) を参照。下の表は `--help` の出力とコードで確かめた、この予想で違うところだけである。

| コマンド | 引数・出力 | この予想では |
|---|---|---|
| 共通 | `--models` の既定 | `reports/穴馬が3着以内に入るかを予想/models`。中は `<区分>/<時点>/`（区分は `mid`（中穴）・`big`（大穴）、時点は `thursday`・`day_before`・`race_day`）に分かれ、直下に複勝の見込みの倍率のファイル `place_price.json` と「買い」の線のファイル `buy_lines.json` を置く |
| `train` | 学習するモデル | 2つの区分 × 3つの時点 × 2つのモデル = 12個（[15-decisions.md の 3](15-decisions.md#3-区分ごとに別のモデルにするか)） |
| `train` | 出す表 | 区分ごとに、手本と同じ4つの表（学習データの期間・検証データでの当たり具合・人気の基準との比べ方・保存したモデル）。そのあとに、手本と同じ複勝の見込みの倍率の表と、「買い」の線の候補ごとの検証データの成績の表・選んだ線の表 |
| `predict` | `--pops 人気 …` | 利用者が見た単勝人気を**全頭ぶん**。前日・当日は `馬番:人気`、木曜は `馬名:人気`。空白かコンマで区切る。省略したときの決め方は [07-prediction-timing.md の「予測のときの人気の与え方」](07-prediction-timing.md#予測のときの人気の与え方) |
| `predict` | `--odds 馬番:オッズ …` | 意味は手本と同じ。この予想では、`--pops` を省くと、このオッズの小さい順を人気にする。全頭ぶん渡す |
| `predict` | `--zone` | `中穴` か `大穴`。その区分の穴馬だけを出す。省略すると穴馬すべてを出す。出力を絞るだけで、学習には関係しない |
| `predict` | `--min-value 期待値` | 複勝の期待値がこの値以上の穴馬に「買い」を付ける。省略すると、学習のときに保存した時点 × 区分ごとの線を使う（2026-10-01。[16-evaluation.md の 3](16-evaluation.md#3-買いの線引き)） |
| `predict` | 出す表 | 1レースの穴馬を「3着以内に入る確率」（平均）の高い順に並べた表。列は、順位・馬番・馬名・人気順位・穴馬の区分と、前日・当日ならオッズから見た3着以内率・複勝的中の確率・複勝の期待値・買いの線・買い、そのあとに 3着以内に入る確率（平均）・LightGBM・CatBoost の確率。前日・当日に複勝オッズが DB に無ければ、取り込み方を案内して止まる（M を作れないため） |
| `calibration` | 引数 | `train` と同じ期間の4つ（`--warmup-from` `--train-from` `--valid-from` `--test-from`）と共通の引数。学習のときと同じ区切りを渡すと、学習に使っていない検証・テストの期間で測る |
| `calibration` | 出す表 | 時点 × 区分 × 期間ごとの4つの表（まとめ・確率の帯ごと・人気ごと・期待値の帯ごと）。表の読み方は [16-evaluation.md の 5](16-evaluation.md#5-確率のずれの確かめ方)。最後に、保存した「買い」の線で買ったときの成績の表（読み方は [16-evaluation.md の 3](16-evaluation.md#3-買いの線引き)） |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-09-23 |
| 更新 | 2026-09-28: 「5. コマンドの引数」を足した |
| 更新 | 2026-09-28: 2026-09-24 の直し（基準・中穴と大穴ごとのモデル・複勝の期待値）で増えたクラスとフォルダ（`SEGMENTS`、共通の `Top3Baseline`・`OddsFeatures`・`SegmentedTraining`・`SegmentedPrediction`・`place_value/` など）を書き足し、「4.」の区分の行を決め直したあとの形に直した |
| 更新 | 2026-09-28: 確率のずれを確かめる `calibration` コマンドと、その部品を足した（issue #31） |
| 更新 | 2026-09-30: まとまり L（騎手・調教師・血統の市場に対する成績）の4個を足したのに合わせて、共通の `PeopleMarketFeatures`・`MarketRunRepository` を書き足し、`CATALOG` の中身と特徴量の数を 82個にそろえた |
| 更新 | 2026-10-01: この予想だけのまとまり M（`PlaceOddsFeatures`・`PlaceMarketRate`）と、「買い」の判定（`buy_line/`・`repository/`・`BuyLineStep`・`BuyLineReportTable`・`--min-value`）を足し、特徴量の数を 86個にした |
