"""作業用の DB のコピーで、出走の行の単勝オッズ・人気を「締め切りの K 分前」の値に差し替え、券種オッズの親の行を消す。

    uv run python "research/地方の直前の材料で買う/analysis/stale_odds_swap.py" <K> <作業用の DB のコピー>

元DB には触らない（コピーだけを書き換える）。通知のときと同じ状況（古いオッズで予想する）を過去のレースで再現するため。差し替えたコピーに向けて
``python -m yosou.local_form_aptitude_top3 backtest --timings 当日 --models <2024検証のモデル> --db <コピー> --predictions <pred-stale12>`` を回すと、
「締め切りの K 分前のオッズを材料にした当日の予想」が過去のレースぶん出る。
"""
import sys
from pathlib import Path
import duckdb, numpy as np, pandas as pd
S = Path(__file__).resolve().parents[3] / "reports" / "地方の12分前の材料で買う"
K = int(sys.argv[1])
RID = '"開催年" || "開催月日" || "競馬場コード" || "開催回[第N回]" || "開催日目[N日目]" || "レース番号"'
m = pd.read_pickle(S / "table.pkl").dropna(subset=[f"win_{K}"])
m = m[m[f"win_{K}"] > 0].copy()
m["pop"] = m.groupby("race_id")[f"win_{K}"].rank(method="first").astype(int)
t = pd.DataFrame({"race_id": m.race_id.astype(str), "no": m.horse_no.astype(int).map("{:02d}".format),
                  "odds": np.minimum(np.round(m[f"win_{K}"] * 10), 9999).astype(int).map("{:04d}".format), "pop": m["pop"].map("{:02d}".format)})
con = duckdb.connect(sys.argv[2])
con.register("t", t)
con.execute("CREATE OR REPLACE TEMP TABLE tt AS SELECT * FROM t")
before = con.execute(f'SELECT count(*) FROM se WHERE {RID} IN (SELECT race_id FROM tt)').fetchone()[0]
con.execute(f'UPDATE se SET "単勝オッズ" = tt.odds, "単勝人気順" = tt.pop FROM tt WHERE {RID} = tt.race_id AND se."馬番" = tt.no')
for h in ("o1", "o2", "o3", "o4", "o5", "o6"):
    n = con.execute(f'DELETE FROM {h} WHERE {RID} IN (SELECT DISTINCT race_id FROM tt)').fetchone()
    print(h, "親の行を消した", n)
print("差し替え", len(t), "頭 / 対象のレースの出走の行", before, "レース", t.race_id.nunique())
con.close()
