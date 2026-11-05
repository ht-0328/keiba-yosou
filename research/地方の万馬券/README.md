# 地方の万馬券

**何をする研究か。** 地方競馬の 3連単で万馬券・10万馬券を、回収率 100% 超で取れる、地方のための予想と買い方を作る。
中央の予想の材料・荒れ具合の予想・買い目の形は持ち込まず、地方のデータから地方の特徴を見つけて組み立てる。

**なぜ始めたか。** 利用者から「地方競馬の予想が弱い」「地方は中央以上に 3連複・3連単で買いたい。特に 3連単で万馬券・10万馬券を狙いたい」
「地方には地方のデータと地方的な予想の特徴があるはずだから、それを見つけて予想するのは当然。中央と同じモデルでやっていいわけがない」
「中央でもやったとおり、消せる危険な人気馬を消し、穴馬を見つけ、レースの荒れ度合いで 人気馬・人気馬・穴馬 や 穴・穴・人気馬 にする。
地方は頭数が少ないので人気馬は 1〜3番人気、中穴は 4〜7番人気くらい、それ以外を大穴」と言われた（2026-11-03）。

**計画**は `workspace/plans/地方競馬の予想を強くする計画.md`。進め方は [docs/01-事例.md](docs/01-事例.md)（段1）から順に docs/ に書く。
数値（地方競馬DATA 由来の成績・配当・回収率）は Git 対象外の `reports/地方の万馬券/` に出し、この README と docs には書かない。

## この文書で使う言葉の意味

| 言葉 | 意味 | この研究では（架空の例） |
|---|---|---|
| 人気馬・中穴・大穴 | 単勝人気で分けた3つの帯。人気馬 1〜3番人気、中穴 4〜7番人気、大穴 8番人気以下（`PopularityBand`。中穴の範囲は引数で変えられる） | 5番人気は中穴 |
| 決着の型 | 1〜3着が、どの帯から何頭来たか。「人1中1大1」（順不同）と「人中大」（1着→3着の順）の2つの書き方 | 1着 2番人気・2着 6番人気・3着 9番人気 → 人中大 |
| 配当の帯 | 3連単の払戻（100円あたり）で分けた4つ。固い 1万円未満、中荒れ 1〜10万円（万馬券）、大荒れ 10〜100万円（10万馬券）、超荒れ 100万円以上（`PayoutBand`） | 払戻 18万円 → 大荒れ |
| 崩れた人気馬 | 1〜3番人気で4着以下（競走中止も含む）になった馬 | |
| 来た穴馬 | 中穴・大穴で3着以内に入った馬 | |
| 事情 | レースの前に分かる、その馬の置かれた状況（遠征・転入初戦・連闘・昇級・乗り替わり・騎手の場内順位・前走の位置 など。`RunnerCircumstances`） | 名古屋の調教師の馬が大井で走る → 遠征 |
| 地区 | 同じ主催者のまとまり（南関東・北海道・岩手・石川・東海・兵庫・高知・佐賀。`VenueArea`）。遠征は地区をまたぐ出走 | 小林は南関東、西脇は兵庫 |
| 騎手の場内順位 | その競馬場で、前の年に何勝したかの順位（`JockeyVenueRank`）。出走の時点で分かる情報にするため前の年を使う | |

## フォルダの中身

| 場所 | 何があるか |
|---|---|
| `cases.py` | 入口（段1）。10万馬券以上のレースの事例の表を書く |
| `theories.py` | 入口（段2）。理論を 2019年以降の全レースで、同じ人気・同じオッズの馬全体と比べる |
| `trifecta.py` | 入口（段3・段4）。全頭の予想の確率から 3連単・3連複の買い目を組み、買い方ごとの成績を出す（`--only L T S3` で買い方を絞れる） |
| `calibration.py` | 入口（段3 の補足）。組の確率を「当たった／外れた」で直し（予想の確率と市場の確率の対数のロジスティック回帰）、直した期待値が 1 以上の組がどれだけ残るか・それを買うと年ごとにどうなるかを出す |
| `stages.py` | 入口（計画の 6.）。予想方法の段ごとの精度: ④荒れ具合（券種ごとの4段階）・②危険な人気馬（1〜3番人気の4着以下）・③穴馬（4番人気以下の3着以内）を、全頭の予想①と同じ地方の記録（当日の馬場傾向 U つき）から学び、2024〜2026年の年ごとの精度と予測の表を書く（`--stage` で段を選べる） |
| `positions.py` | 入口（段5。[docs/05](docs/05-1着2着3着を分けて市場に合わせる.md)）。全頭の予想の確率（LightGBM と CatBoost を分ける）と単勝・3連単・馬単・3連複・複勝の票の見立てから、1着・2着・3着の条件つきロジットで組の確率を出し、全券種（単勝〜3連単）の期待値の買い目を、年を入れ替えて（`--protocol 前の年` なら前の年だけで）当てはめた未見の成績で出す |
| `analysis/case_study.py` `theory_study.py` `trifecta/trifecta_study.py` | 段1・段2・段3 の流れ |
| `analysis/stages/` | 段ごとの精度（①の学習データの保存 `training_data_cache.py`・人気帯のデータ `band_data.py`・消と穴の精度 `band_precision.py`・②③の流れ `band_study.py`・地方の線引き `local_upset_rule.py`・当日の馬場傾向のレースの値 `used_slope_features.py`・④のデータ `upset_data.py`・市場の割れ方だけの基準 `market_only_baseline.py`・④の流れ `upset_study.py`） |
| `analysis/runner_enrichment.py` | 出走の表を作る（事実表 → 地区・場内順位・帯・事情） |
| `analysis/theory.py` `theory_catalog.py` `theory_check_table.py` `popularity_baseline.py` `odds_baseline.py` `race_theory_table.py` | 理論と、その検証の表 |
| `analysis/trifecta/` | 組の確率（`harville_combos.py`・3着以内に合わせた勝つ力 `fitted_strength.py`）・市場の見立て（馬 `race_market.py`・組 `combo_market.py`）・買い方（`strategy.py` `strategy_catalog.py`）・買い目（`ticket_plan.py`）・成績（`simulator.py`）・組の確率の直し（`combo_calibration.py` `calibration_study.py`） |
| `analysis/positions/` | 段5（1着・2着・3着を分けて市場に合わせる）の研究に残る部分: 流れ `positions_study.py`・成績 `ticket_summary.py`。条件つきロジット・票の表・特徴量・係数・1着2着3着のモデル・券種ごとの確率・買い方・全頭の予想のモデルごとの確率の読み出しは、本番の道具 `tools/地方の推奨買目/` に移した（研究はそれを使う） |
| `analysis/popularity_band.py` `payout_band.py` `venue_area.py` | 人気の帯・配当の帯・地区の決めごと |
| `analysis/jockey_venue_rank.py` `runner_circumstances.py` | 騎手の場内順位と、馬の事情（真偽の列） |
| `analysis/outcome_pattern_table.py` `circumstance_share_table.py` `race_condition_table.py` `case_list_table.py` | 表（決着の型・事情の割合・レースの条件・事例の一覧） |
| `analysis/case_report.py` | 表を Markdown にまとめて書く |
| `analysis/repository/` | 元DB を読むリポジトリ（1 SQL につき 1 クラス。事実表・3連単と3連複の払戻・調教師と馬の所属）。券種と3連単の確定オッズのリポジトリは `tools/地方の推奨買目/repository/` に移し、ここから同じ名前で使える |
| `docs/` | 進め方と結果の読み方（01 事例・02 理論・03 3連単の買い方・04 予想方法の段ごとの精度・05 1着2着3着を分けて市場に合わせる） |
| `tests/` | 架空の値で部品を確かめるテスト（実DB は要らない） |
| `reports/地方の万馬券/`（Git 対象外） | `事例.md`・`事例の馬.csv`・`事例のレース.csv`・`理論の検証.md`・`3連単の買い方.md`・`3連単の買い方の買い目.csv`・`3連単の買い方-2024検証*.md`（2024〜2026年）・`組の確率の直し.md`・`全券種の買い方.md`・`全券種の買い方の買い目.csv`（段5。`-前の年`・`-3連単の票だけ` は当てはめ方と材料を変えたもの） |

## 動かし方

リポジトリ直下（`keiba-yosou/`）から実行する。元DB は nvdata-store の `nvdata.duckdb`（読むだけ）。

```bash
uv run python research/地方の万馬券/cases.py                 # 段1: 事例の表（2024年以降・11頭以上。数分）
uv run python research/地方の万馬券/cases.py --middle 4-6    # 中穴を 4〜6番人気にして比べる
uv run python research/地方の万馬券/theories.py              # 段2: 理論の検証（2019年以降。数分）
uv run python research/地方の万馬券/trifecta.py              # 段3: 3連単・3連複の買い方の成績（2026年。10〜20分）
uv run python research/地方の万馬券/trifecta.py --test-from 2024-01-01 --unseen-from 2026-01-01 --predictions reports/地方競馬の近走と適性から3着以内を予想/predictions-2024検証 --unseen-predictions reports/地方競馬の近走と適性から3着以内を予想/predictions-2024検証 --report-name 3連単の買い方-2024検証
                                                            # 2023年前半までで学んだモデルで 2024〜2026年（年ごとの表つき。約1時間）
uv run python research/地方の万馬券/calibration.py           # 段3 の補足: 組の確率の直し（2024年で当てはめ、2024〜2026年。10〜20分）
uv run python research/地方の万馬券/stages.py                # 計画の 6.: ④荒れ具合・②危険な人気馬・③穴馬 を学んで年ごとの精度（初回は学習データ作りに 30〜60分）
uv run python research/地方の万馬券/trifecta.py --test-from 2024-01-01 --unseen-from 2026-01-01 --predictions reports/地方競馬の近走と適性から3着以内を予想/predictions-2024検証-馬場傾向 --unseen-predictions reports/地方競馬の近走と適性から3着以内を予想/predictions-2024検証-馬場傾向 --stage-predictions reports/地方の万馬券/predictions --only L* T* M* TM* --report-name 3連単の買い方-予想方法
                                                            # ②③④の予測で消・穴・レース・型を決める買い方（M・TM）を、①だけの L・T と年ごとに比べる
uv run python research/地方の万馬券/positions.py             # 段5: 1着・2着・3着を分けて市場に合わせ、全券種の買い方を年を入れ替えて評価（15〜25分）
uv run python research/地方の万馬券/positions.py --protocol 前の年 --report-name 全券種の買い方-前の年          # 前の年だけで当てはめる
uv run python research/地方の万馬券/positions.py --trifecta-only --report-name 全券種の買い方-3連単の票だけ   # 馬単・3連複・複勝の票を足さない
uv run python -m pytest research/地方の万馬券 -q            # 部品のテスト
```
