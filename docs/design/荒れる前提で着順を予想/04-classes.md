# 04 クラスとパッケージの設計

**この文書で決めること:** ほかの予想とこの予想で、同じ仕事をするクラスをどこに置き、どう使うか。この予想だけに要るクラスは何か。それらをどのフォルダ（パッケージ）・ファイルに置くか。

**結論: 学習データを作る・学習する・予測するクラスは、ほかの予想のものをそのまま使う。荒れる前提の3着以内・1着は、手本の学習・予測のコマンド（`TrainCommand`・`PredictCommand`）に、この予想の名前と「荒れたレースの行だけを残す」決まり（`WildRaceRows`）を渡して使う。この予想だけに作るのは、`WildRaceRows` と買い方（一律・甲・乙・丙）のクラスである。開催日ごとのレース選びと買い目は、道具「帯狙い」（`tools/帯狙い/`）が、荒れ具合の予想の予測の流れ、今週の予想の `RaceForecaster`（この予想のモデルと今の予想のモデルの2回）、この予想の買い方を順に呼んで出す。**

用語の意味は [02-glossary.md](02-glossary.md) を参照。

## 1. ほかの予想の部品の使い方

| 使うもの | どこにあるか | この予想での使い方 |
|---|---|---|
| 手本の学習のコマンド `TrainCommand` | `src/yosou/form_aptitude_top3/command/train_command.py` | `TrainCommand(YOSOU_NAME, WildRaceRows())` として `train` に使う。学習データの作り方・材料の足し方・保存の形は手本のまま、学ぶ行と置き場所だけが変わる |
| 手本の予測のコマンド `PredictCommand` | `src/yosou/form_aptitude_top3/command/predict_command.py` | `PredictCommand(YOSOU_NAME)` として `predict` に使う。この予想の置き場所のモデルで、1レースの荒れる前提の確率を出す |
| 学ぶ行の選び方の決まり `TrainingRows` と既定の `AllRows` | `src/yosou/shared/dataset/` | `TrainCommand` が、学習データを作った直後（元DB を開いている間）に呼ぶ。手本は `AllRows`（全部の行）、この予想は `WildRaceRows` |
| 荒れ具合の予想の予測の流れ `PredictionWorkflow` と学習済みモデル | `src/yosou/upset_level/workflow/`、`reports/レースの荒れ具合を4段階で予想/models/` | 道具「帯狙い」が、レースごとに3連単が 1,000倍以上になる確率（大荒れ＋超荒れ）を出し、線以上のレースを選ぶ（[15-decisions.md の 1](15-decisions.md#1-レース選びに何を使うか)） |
| 1レースを予想する `RaceForecaster` | `tools/今週の予想/race_forecaster.py` | 道具「帯狙い」が、この予想の置き場所を渡して、選んだレースを予想する（印・危険な人気馬の判定も今週の予想と同じ）。今の予想の置き場所も渡して同じレースを予想し、その3着以内の確率を2着・3着の重みに使う（[15-decisions.md の 6](15-decisions.md#6-組の確率の2着3着の重み)） |

**手本のコマンドに足したのは、コンストラクタの2つの引数（予想の名前と学ぶ行の選び方）だけである。** 既定の値は手本のままなので、手本の学習と予測は変わらない。同じ材料の作り方を2か所に書かないために、こうした。

## 2. この予想だけのクラス

### dataset/ — 学ぶ行

| クラス | 仕事 | 主な public メソッド | 呼ぶクラス |
|---|---|---|---|
| `WildRaceRows` | 学習データから、荒れたレース（3連単の払戻が 10万円以上）の行だけを残す。`TrainingRows` を守る | `keep(con, data)` | `RacePayoutRepository` |

線（10万円・100万円）は `dataset/obi_rules.py`（定数だけ）。

### betting/ — 買い目

| クラス・関数 | 仕事 |
|---|---|
| `RaceHorses` | 1レースの出走馬ごとの、1着の確率（レースで合計 1）と3着以内の確率（と、あれば今の予想の3着以内の確率）。上位の馬番と、2着・3着の重み（`place_of()`）を返す |
| `TicketPlan` | 買い方の決まり（インターフェース）。`name`・`ordered`・`tickets(horses, odds)` |
| `FlatPlan` | 一律（3連単。既定）。全頭の組のうちオッズが 1,000倍以上の組を、組の確率（1着は荒れる前提の1着の確率、2着・3着は `place_of()` の重み）の高い順に、1点の金額（既定 100円）を一律にして予算に収まる点数だけ買う |
| `ObiStakePlan` | 甲（3連単）・丙（3連複）。3着以内の確率の上位8頭の組のうち、帯に要る金額が 1,000円以下の組を、当たる確率 ÷ 金額の高い順に、1万円に収まるまで買う |
| `FormationPlan` | 乙（3連単）。1着3頭 → 2着5頭 → 3着8頭（最大 72点）で、組の確率の上位10点を 300円、残りを 100円。トリガミの組は買わない |
| `trifecta_probability`・`trio_probability` | 1着の確率（と、渡せば2着・3着の重み）から、組の確率を Harville の式で作る（関数） |

予算・1点の金額の単位と上限・一律の買い方の線（1,000倍）と既定の金額は `betting/betting_rules.py`（定数だけ）。

### command/

| 名前 | 仕事 |
|---|---|
| `CommandLine` | 入口。`train`・`predict`（手本のコマンドに、この予想の名前と `WildRaceRows` を渡したもの） |
| `yosou_name.py` の `YOSOU_NAME` | この予想の名前（モデルの既定の置き場所 `reports/荒れる前提で着順を予想/models` に使う） |

### 道具「帯狙い」（`tools/帯狙い/`）

| クラス | 仕事 |
|---|---|
| `ObiDayRun` | 1日の帯狙いを進める（`ObiDayPicker` → 選んだレースごとに `RaceForecaster` を2回（この予想・今の予想） → 買い方）。ほかを順に呼ぶだけ |
| `ObiDayPicker` | 1日のレースごとに時点を選び、荒れ具合の予想で3連単が 1,000倍以上になる確率を出して高い順に並べ、線以上のレースを選ぶ |
| `ForecastHorses` | `RaceForecaster` の結果（この予想と今の予想）から、馬番・1着の確率・3着以内の確率・今の予想の3着以内の確率を取り出す |
| `AnnouncedComboOdds` | 1レースの組ごとのオッズを、締め切り前（なければ確定）の断面で読む |
| `ObiStore`・`ObiTables` | 結果を `reports/帯狙い/<開催日>.json` に書く・表にする |

## 3. パッケージ構成

```text
src/yosou/upset_premise/
├── __init__.py            # この予想の説明と、フォルダの一覧
├── __main__.py            # python -m yosou.upset_premise の入口
├── command/               # CommandLine・yosou_name.py
├── betting/               # RaceHorses・TicketPlan・FlatPlan・ObiStakePlan・FormationPlan・harville.py・betting_rules.py
├── dataset/               # WildRaceRows・obi_rules.py
└── tests/
```

| 決まり | 理由 |
|---|---|
| 1ファイルに1クラス、1クラスに1つの仕事。SQL は `yosou.shared.repository` だけ | ほかの予想と同じ（[手本の 04](../近走と適性から3着以内を予想/04-classes.md)） |
| 参照の向きは `command` → `betting` → `dataset` の一方向 | 下のものが上のものを知らないようにし、部品を取り替えやすくする |
| 手本の予想のパッケージは使ってよいが、そちらからこの予想を参照しない | 手本を、この予想が無くても動く形に保つ |
| モデルの置き場所は `reports/荒れる前提で着順を予想/models/`（Git の対象外）。形は手本と同じ（`<時点>/`・`1着/<時点>/`・`券種オッズなし/`・複勝の見込みの倍率） | JV-Data から作ったものなので公開しない。手本と同じ形なので、`RaceForecaster` に置き場所を渡せば予測できる |

## 文書情報

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-10-12 |
