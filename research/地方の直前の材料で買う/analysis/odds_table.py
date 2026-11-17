"""時系列オッズの分割ファイル（odds_history_fetch.py が貯めたもの）から、馬ごとの「締め切りの k 分前の単勝・複勝オッズ」の表を作り、
着順・確定オッズ・複勝の払戻・オッズを使わない予想（出馬表の時点）と結ぶ。keiba-yosou の直下で動かす。

    uv run python "research/地方の直前の材料で買う/analysis/odds_table.py" <地方の元DB>     # reports/地方の12分前の材料で買う/table.pkl

元DB は読むだけ。確定オッズは元DB のものを使うので、オッズを差し替えた作業用の写し（stale_odds_swap.py）は渡さない。
"""
import sys
from datetime import date
from pathlib import Path
sys.path[:0] = ["tools", "src", "research"]
import duckdb, numpy as np, pandas as pd
from 地方の推奨買目.repository import FactsRowsRepository
from 地方の万馬券.analysis.repository import LocalTicketPayoutRepository
S = Path(__file__).resolve().parents[3] / "reports" / "地方の12分前の材料で買う"
OFFSETS = (3, 5, 8, 10, 12, 15, 20, 30, 45)
mem = duckdb.connect()
g = (S / "chunks").as_posix()
mem.execute(f"""CREATE VIEW s AS SELECT * FROM read_parquet('{g}/snaps-*.parquet') UNION ALL
    SELECT * FROM read_csv('{g}/snaps-*.csv', header=false, columns={{'key':'VARCHAR','kubun':'VARCHAR','announced':'VARCHAR','win_total':'BIGINT','horse_no':'INTEGER','win':'DOUBLE','plo':'DOUBLE','phi':'DOUBLE'}})""")
# 月日時分 → 分（同じ開催日の中の差だけ使う）
mem.execute("""CREATE TABLE t AS SELECT *, (CAST(substr(announced,3,2) AS INT)*24 + CAST(substr(announced,5,2) AS INT))*60 + CAST(substr(announced,7,2) AS INT) AS m FROM s WHERE win > 0""")
mem.execute("""CREATE TABLE close AS SELECT key, coalesce(min(m) FILTER (WHERE kubun='3'), max(m) FILTER (WHERE kubun='1')) AS close_m, max(m) FILTER (WHERE kubun='1') AS last_mid,
               count(DISTINCT announced) FILTER (WHERE kubun='1') AS n_mid FROM t GROUP BY key""")
parts = []
for k in OFFSETS:
    parts.append(mem.execute(f"""SELECT t.key, t.horse_no, {k} AS k, t.win, t.plo, t.phi, c.close_m - t.m AS age FROM t JOIN close c USING (key)
        WHERE t.kubun='1' AND t.m <= c.close_m - {k} QUALIFY row_number() OVER (PARTITION BY t.key, t.horse_no ORDER BY t.m DESC) = 1""").df())
long = pd.concat(parts)
wide = long.pivot_table(index=["key", "horse_no"], columns="k", values=["win", "plo", "phi", "age"])
wide.columns = [f"{a}_{b}" for a, b in wide.columns]
wide = wide.reset_index()
first = mem.execute("""SELECT key, horse_no, win AS win_first FROM t WHERE kubun='1' QUALIFY row_number() OVER (PARTITION BY key, horse_no ORDER BY m) = 1""").df()
last = mem.execute("""SELECT key, horse_no, win AS win_last, plo AS plo_last, phi AS phi_last FROM t WHERE kubun IN ('1','3') QUALIFY row_number() OVER (PARTITION BY key, horse_no ORDER BY m DESC) = 1""").df()
wide = wide.merge(first, on=["key", "horse_no"], how="left").merge(last, on=["key", "horse_no"], how="left").merge(mem.execute("SELECT key, n_mid FROM close").df(), on="key")
con = duckdb.connect(sys.argv[1], read_only=True)
f = FactsRowsRepository(con).load(date(2024, 1, 1), 5)
f = f.assign(race_id=f.race_id.astype(str))
f["key"] = f.race_id.str[:10] + f.race_id.str[14:16]
m = f.merge(wide, on=["key", "horse_no"], how="inner")
pl = LocalTicketPayoutRepository(con, "複勝").load(m.race_id.drop_duplicates())
pl = pl.assign(race_id=pl.race_id.astype(str)).rename(columns={"a": "horse_no", "payout": "place_pay"})
m = m.merge(pl, on=["race_id", "horse_no"], how="left").fillna({"place_pay": 0})
P = Path("reports/地方競馬の近走と適性から3着以内を予想/predictions-2024検証")
def read(name, col):
    t = pd.read_pickle(P / name)
    return pd.DataFrame({"race_id": t["レースID"].astype(str), "horse_no": pd.to_numeric(t["馬番"], errors="coerce"), col: t["確率"].astype(float)}).dropna().astype({"horse_no": int}).drop_duplicates(["race_id", "horse_no"])
m = m.merge(read("thursday.pkl", "p3_thu"), on=["race_id", "horse_no"], how="left").merge(read("thursday-1着.pkl", "p1_thu"), on=["race_id", "horse_no"], how="left")
for c in ("win_odds", "finish", "popularity"):
    m[c] = pd.to_numeric(m[c], errors="coerce").astype(float)
m["won"] = (m.finish == 1).astype(int); m["top3"] = (m.finish <= 3).astype(int)
m["win_pay"] = m.win_odds * 100 * m.won
m.to_pickle(S / "table.pkl")
print("レース", m.race_id.nunique(), "頭", len(m), "期間", m.race_date.min(), m.race_date.max())
r = m.dropna(subset=["win_12", "win_odds"])
r = r[r.win_odds > 0]
for k in OFFSETS:
    d = r.dropna(subset=[f"win_{k}"])
    print(f"締め切りの {k:>2}分前: |log(そのとき/確定)| の平均 {np.abs(np.log(d[f'win_{k}'] / d.win_odds)).mean():.3f}  断面の古さの中央 {d[f'age_{k}'].median():.0f}分")
