# 05 学習と予測のやりとり（シーケンス図）

**この文書で示すこと:** 学習・予測・テスト期間の確かめのとき、利用者・nvdata-store・元DB と、[04-classes.md](04-classes.md) のクラスが、どの順に、どのメソッドを呼ぶか。

**結論: 流れは「学習」「予測」「テスト期間の確かめ」の3つに分かれる。** 学習は共通の `TrainingWorkflow` が進め、1つの学習データから、3つの時点ごとに LightGBM と CatBoost を学習させて保存する。予測は共通の `PredictionWorkflow` が進め、その時点の予測用データを作り、保存した2つのモデルで予測確率を出して平均する。テスト期間の確かめは `BacktestWorkflow` が進める。中央の予想と違うのは、学習データが1つであること（材料を時点で使い分けない）、取り込みの道具が nvdata-store であること、記録を集めるときに調教を読まず、出走別着度数地方を読むことである。

- public メソッドの中の判断（if 文による分かれ道）は [06-flowchart.md](06-flowchart.md) を参照。2種類の図の使い分けは [01-overview.md](01-overview.md#図の使い分け) を参照。
- 用語の意味は [02-glossary.md](02-glossary.md) を参照。

## 図に出てくるもの

| 名前 | 種類 | 呼ばれ方 | 今あるか |
|---|---|---|---|
| 利用者 | 人 | ― | ― |
| nvdata-store | 隣のリポジトリの道具。地方競馬DATA を取得して、元DB に入れる | コマンド（`nvstore sync` か `nvstore realtime`）を1回実行する | ある |
| 元DB | nvdata-store が作った DuckDB（`nvdata.duckdb`）。この AI は読むだけ | SQL を1回流す | ある |
| `TrainingWorkflow` など | この AI のクラス。一覧と仕事は [04-classes.md](04-classes.md) を参照 | public メソッドを1回呼ぶ | 共通の部品はある。地方の部品はこれから作る |
| `LGBMClassifier`・`CatBoostClassifier` | ライブラリのクラス | `fit()` か `predict_proba()` を1回呼ぶ | ライブラリはある |
| モデルのファイル | 学習済みのモデルを保存したファイル | 1回書き込むか、1回読み込む | `train` を実行すると、`reports/地方競馬の近走と適性から3着以内を予想/models/` にできる |

## 図の読み方

中央の予想の [05 の「図の読み方」](../近走と適性から3着以内を予想/05-sequence.md#図の読み方) と同じ。実線の矢印1本 = 呼び出し1回、点線 = 戻り値、自分に戻る矢印 = メソッドの中で行う作業のうち設計として見せたいもの、`loop` = くり返し、`opt` = 利用者の手順の違い。

## 図1. 学習

```mermaid
sequenceDiagram
    actor U as 利用者
    participant W as TrainingWorkflow
    participant H as HyperparameterSettings
    participant D as DatasetBuilder
    participant L as HistoryRecordsLoader
    participant RS as RunnerSelector
    participant F as FeatureBuilder
    participant T as Top3TargetBuilder
    participant S as PeriodSplitter
    participant MR as ModelRepository
    U->>W: run（設定ファイルのパス）
    W->>H: load（設定ファイルのパス）
    H-->>W: 設定
    W->>D: build_training_data（期間）
    D->>L: load（ウォームアップの始まり）
    L->>L: 地方の事実表を用意し、リポジトリを順に呼んで記録を集める（図3）
    L-->>D: 出走の記録
    D->>RS: training_samples（出走の行、学習データの始まり）
    RS->>RS: 入れる行を選ぶ（06-flowchart.md の図1）
    RS-->>D: サンプルにする行
    D->>F: build（記録、当日）
    F-->>D: 特徴量（当日の全部。96個）
    D->>T: build（サンプルにする行）
    T-->>D: 目的変数
    D-->>W: 学習データ
    W->>S: split（学習データ）
    S-->>W: 学習データ・検証データ・テストデータ
    loop 3つの時点ごと（出馬表・前日・当日）
        W->>W: LightGbmModel を作り、その時点の列だけで学習させる（12-lightgbm.md の 4.）
        W->>W: CatBoostModel を作り、その時点の列だけで学習させる（13-catboost.md の 4.）
        W->>MR: save（時点、2つのモデル、設定）
        MR-->>W: 保存した
    end
    W->>W: 検証データで当たり具合を確かめる（16-evaluation.md）
    W-->>U: 確かめた結果
```

**説明。** この図は、1つの目的変数の学習である。`train`（`TrainCommand`）は、`local_dataset_builder` で学習データを1回読み、元DB を閉じてから、同じ学習データで次の4つの学習を順に行う（[04-classes.md](04-classes.md#command--コマンド入口はこの予想部品は-shared)）。

| 学習 | 学習データ | 時点 | 置き場所 |
|---|---|---|---|
| 3着以内のモデル | Q を外したもの（`FinishPowerFreeData`） | 出馬表・前日・当日 | `models/<時点>/` |
| 1着のモデル | 目的変数を「1着」に・基準を「オッズから見た勝率」に持ち替えたもの（`WinTargetData`。Q は残す） | 出馬表・前日・当日 | `models/1着/<時点>/` |
| 券種オッズなしの3着以内のモデル | N と Q を外したもの（`PoolFreeData`・`FinishPowerFreeData`） | 当日 | `models/券種オッズなし/race_day/` |
| 券種オッズなしの1着のモデル | N を外して1着に持ち替えたもの | 当日 | `models/券種オッズなし/1着/race_day/` |

学習データは、当日の時点の特徴量の全部で作る（単勝オッズと券種オッズは確定オッズ）。各時点のモデルには、そのうち、その時点で使う列だけを渡す（[07-prediction-timing.md の「時点ごとに使う特徴量」](07-prediction-timing.md#時点ごとに使う特徴量)）。モデルは、3つの時点 × 2つの目的変数 と、券種オッズなしの当日 × 2つの目的変数 で、合わせて 8組（LightGBM と CatBoost で 16個）になる。学習のあとに、複勝の見込みの倍率（`PlacePriceStep`）を保存する。

## 図2. 予測

出馬表・前日・当日のどれかの時点で、1レースを予測するときの流れ。

```mermaid
sequenceDiagram
    actor U as 利用者
    participant NS as nvdata-store
    participant DB as 元DB
    participant W as PredictionWorkflow
    participant OR as OddsResolver
    participant AO as AnnouncedOddsRepository
    participant D as DatasetBuilder
    participant L as RaceRecordsLoader
    participant RS as RunnerSelector
    participant F as FeatureBuilder
    participant C as RequiredInfoCheck
    participant MR as ModelRepository
    participant E as EnsembleModel
    U->>NS: nvstore sync（出馬表 RACE・出走別着度数地方 SNAP・マスタ DIFN）
    NS->>DB: 書き込む
    opt 前日と当日だけ
        U->>NS: nvstore realtime（開催日。馬場状態 0B14・出馬表の変更・時系列オッズ 0B41。当日は馬体重 0B11 も）
        NS->>DB: 馬場状態・取消・締め切り前の単勝オッズ（当日は馬体重も）を書き込む
    end
    opt 当日だけ
        U->>NS: nvstore realtime（全券種の速報オッズ 0B30）
        NS->>DB: 券種ごとの締め切り前のオッズを書き込む
    end
    U->>W: run（レースID、時点、--odds で渡したオッズ）
    W->>OR: resolve（レースID、渡されたオッズ）
    OR->>AO: read（レースID）
    AO->>DB: SQL（締め切り前の単勝オッズ）
    AO-->>OR: 馬番ごとのオッズ（無ければ空）
    OR->>OR: 使うオッズを決める（06-flowchart.md の図4）
    OR-->>W: 馬番 → 単勝オッズ（無ければ、無し）
    W->>D: build_prediction_data（レースID、時点、オッズ）
    D->>L: load（レースID、オッズ）
    L->>L: 速報を読み、出走馬の記録を集めて、速報とオッズを反映する（中央の 05 の図4）
    L-->>D: 出走の記録
    D->>RS: prediction_runners（出走の行、レースID）
    RS-->>D: 予測する馬の行
    D->>F: build（記録、時点）
    F-->>D: その時点で使う特徴量
    D->>C: check（特徴量）
    C-->>D: 要る情報（馬場状態・馬体重・オッズ）はそろっている
    D-->>W: 予測用データ（1行 = 1頭）
    W->>W: 当日に券種のオッズが無ければ、N を外して券種オッズなしのモデルにする（06-flowchart.md の図3）
    W->>MR: load（時点）
    MR-->>W: その時点の LightGbmModel と CatBoostModel
    W->>E: predict_proba（予測用データ。Q は外して渡す）
    E->>E: 2つのモデルの予測確率を出して平均する（12-lightgbm.md・13-catboost.md の 5.）
    E-->>W: 1頭ずつの予測確率
    W->>W: 1着のモデル（models/1着/）でも同じ手順で予測する（予測用データは WinTargetData で基準を持ち替える。Q は渡したまま）
    W->>W: 前日・当日なら、複勝の期待値（PlaceValueColumns）と単勝の期待値（WinValueColumns）を足す
    W-->>U: 1頭ずつの「3着以内に入る確率」「1着になる確率」と期待値
```

**説明。** 利用者は、まず nvdata-store の `nvstore sync` で、出馬表（`RACE`）・出走別着度数地方（`SNAP`）・マスタ（`DIFN`）を取り込む。前日と当日は、`nvstore realtime` で速報（馬場状態・取消・締め切り前のオッズ。当日は馬体重も）を取り込む。次に、レースIDと時点（前日・当日なら、必要に応じて `--odds` のオッズも）を付けて `PredictionWorkflow.run()` を呼ぶ。流れは中央の予想の [05 の図2](../近走と適性から3着以内を予想/05-sequence.md#図2-予測) と同じで、違いは、どの時点でも同じ `local_dataset_builder` を使うこと（材料を時点で切り替えない）と、展開の予想の結果（P）を足す段が無いことである。1レースの記録を集めて速報を反映する中の呼び出し（`RaceRecordsLoader` → `AnnouncedGoingRepository` → `RaceEntryTableRepository` → `EntryRecordsLoader` → 速報の反映）は、中央の予想の [05 の図4](../近走と適性から3着以内を予想/05-sequence.md#図4-1レースの記録を集める速報の反映) と同じである（`RaceEntryTableRepository` に `LOCAL_FACTS_SOURCE` を渡す点だけ違う）。

## 図3. 記録を集める（リポジトリとのやりとり）

図1の「地方の事実表を用意し、リポジトリを順に呼んで記録を集める」の中の呼び出しを示す。中央の予想の [05 の図3](../近走と適性から3着以内を予想/05-sequence.md#図3-記録を集めるリポジトリとのやりとり) と比べて、馬の力の材料（`AbilitySourcesLoader`）を呼ばず、出走別着度数は `nd` を読む `CareerCountRepository` を呼び、対戦レーティング（`HeadToHeadRunRepository`）と勝ち切る材料（`FinishRecordsLoader`）を呼ぶ。調教のリポジトリ（`WorkoutRepository`・`WorkoutCoverageRepository`）は共通の読み込みの中で呼ばれるが、地方の元DB に調教の表（`hc`・`wc`）が無いので空の表が返る（図では省く）。

```mermaid
sequenceDiagram
    participant HL as HistoryRecordsLoader
    participant FT as FactTableRepository
    participant L as EntryRecordsLoader
    participant R1 as EntryRepository
    participant R2 as CareerCountRepository（nd）
    participant R3 as PastRunRepository
    participant R5 as PeopleDayRepository（騎手）
    participant R6 as PeopleDayRepository（調教師）
    participant R6b as PedigreeDayRepository（父・母父）
    participant R7 as MarketRunRepository
    participant R8 as HeadToHeadRunRepository
    participant R9 as PoolProbabilityLoader
    participant R10 as FinishRecordsLoader
    participant DB as 元DB
    HL->>FT: ensure()
    FT->>DB: SQL（地方の事実表を作る。LOCAL_FACTS_SOURCE）
    HL->>L: load（対象）
    L->>R1: read（対象）
    R1->>DB: SQL（出走の行）
    R1-->>L: 出走の行
    L->>R2: read（対象）
    R2->>DB: SQL（出走別着度数地方。LOCAL_CAREER_LAYOUT の欄）
    R2-->>L: 通算と条件別の着回数
    L->>L: 出走の行に、着回数を付ける
    L->>R3: read（対象）
    R3->>DB: SQL（過去走）
    R3-->>L: 過去走
    L->>R5: read（対象）
    R5->>DB: SQL（騎手の日ごとの成績）
    R5-->>L: 騎手の成績
    L->>R6: read（対象）
    R6->>DB: SQL（調教師の日ごとの成績）
    R6-->>L: 調教師の成績
    L->>R6b: read（対象）
    R6b->>DB: SQL（父・母父の産駒の日ごとの成績）
    R6b-->>L: 産駒の成績
    L->>R7: read（対象）
    R7->>DB: SQL（期間の平地の全出走の単勝オッズと着順）
    R7-->>L: 過去の全出走のオッズと着順
    L->>R8: read（対象）
    R8->>DB: SQL（過去の全出走の着順）
    R8-->>L: 対戦レーティングの元の記録
    L->>R9: read（対象のレース）
    R9->>DB: SQL 6本（券種ごとの、確定か最新の断面のオッズから馬ごとの確率）
    R9-->>L: 券種ごとの馬の確率
    L->>R10: read（対象）
    R10->>DB: SQL 2本（馬の近10走と、騎手・調教師の近1年の勝ち切り）
    R10-->>L: 勝ち切る材料の元の記録
    L-->>HL: 出走の記録
```

**説明。** 学習でも予測でも、同じリポジトリを同じ順に呼ぶ。違うのは「対象」（`TargetScope`）だけで、学習では「ウォームアップの始まり（既定は 2016年1月1日）以降の全部の出走」、予測では「1レースの出走馬」になる。事実表は `LOCAL_FACTS_SOURCE` で作るので、行は地方 14場の確定成績（ばんえいを除く）、血統は `nu__3代血統情報`、クラスは競走条件名称から読んだものになる（[04-classes.md の 3.](04-classes.md#3-中央だけの決めごとを外から渡す形)）。調教の表（`hc`・`wc`）は元DB に無く、この予想は調教の特徴量（I）を持たないので、共通の読み込みが調教のリポジトリを呼んでも空の表が返るだけである。

## 図4. テスト期間の確かめ

`backtest` の流れ。保存したモデルで、学習に使っていないテスト期間の全レースを予測し直す（[16-evaluation.md の 4.](16-evaluation.md#4-テスト期間での確かめ)）。

```mermaid
sequenceDiagram
    actor U as 利用者
    participant B as BacktestWorkflow
    participant D as DatasetBuilder
    participant MR as ModelRepository
    participant E as EnsembleModel
    participant V as ModelEvaluator
    participant P as 予測の表のファイル
    U->>B: run（期間、テストの始まり）
    B->>D: build_training_data（期間）
    D-->>B: 学習データ（テスト期間を含む）
    B->>B: テスト期間の行だけを残す
    loop 3つの時点ごと × 2つの目的変数（3着以内・1着）
        B->>B: 当日なら、券種のオッズが無いレースの行を券種オッズなしのモデルに振り分ける（06-flowchart.md の図3）
        B->>MR: load（時点）
        MR-->>B: その時点の LightGbmModel と CatBoostModel
        B->>E: predict_proba（テスト期間の行。その時点の列だけ）
        E-->>B: 1頭ずつの予測確率（モデルごとと平均）
        B->>V: evaluate（時点、アンサンブル、テスト期間の行）
        V-->>B: 当たり具合（ログ損失・AUC・Brier・確率1位の3着以内率・人気の基準）
        B->>B: 市場の確率（オッズから見た3着以内率・勝率）の当たり具合も同じ指標で測る
        B->>P: 書き込む（<時点>.pkl・<時点>-1着.pkl。印の成績が読む形）
    end
    B-->>U: 時点ごとの当たり具合の表（モデルと市場の確率）
```

**説明。** 学習データを作る手順は図1と同じで、期間（`TrainingPeriod`）はテスト期間の終わりまでを含む。`PeriodSplitter` と同じ区切りでテスト期間の行だけを残し、保存したモデル（`train` が同じ期間で学んだもの）で予測する。予測の表は、印の成績（`tools/印の成績/mark_stats.py`）が読む列（レースID・開催日・馬ID・馬番・確率・区切り・期間・区分と、モデルごとの確率）で書く。印の成績の回し方は [16-evaluation.md の 6.](16-evaluation.md#6--の単勝回収率の確かめ期待度) を参照。

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-10-06 |
