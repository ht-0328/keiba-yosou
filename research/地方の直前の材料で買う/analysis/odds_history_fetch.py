"""地方の時系列オッズ（0B41。単勝・複勝）を、過去のレースぶんまとめて取り、作業用の DuckDB に貯める（元DB には書かない）。

    uv run --directory ../nvdata-store python <このファイル> --keys keys.txt --out <reports/地方の12分前の材料で買う/chunks> --until 08:15

--keys は 1行に1つの要求キー（開催日 8桁＋競馬場コード 2桁＋レース番号 2桁）。1つのプロセスで数千レースを超えると開けるファイルの数の上限に当たるので、キーを分けて何回かに分ける。

1レースごとに、最後の途中の断面から 60分前までの断面と、最初の断面だけを残す。取り終えたキーは done 表に書き、やり直すと続きから。
--until の時刻（今日のその時刻。過ぎていれば明日）になったら止まる（開催中の速報の取得のじゃまをしない）。
"""
import argparse, csv, sys, time
from datetime import datetime, timedelta
from pathlib import Path
import duckdb
from nvstore.link_process import LinkProcess
from nvstore.link32.nvlink_error import NVLinkError

def parse(record: bytes):
    kubun = chr(record[2]); announced = record[27:35].decode("ascii", "replace")
    total = record[927:938].decode("ascii", "replace").strip()
    rows = []
    for i in range(28):
        w = record[43 + 8 * i: 51 + 8 * i].decode("ascii", "replace"); p = record[267 + 12 * i: 279 + 12 * i].decode("ascii", "replace")
        if not w[:2].strip().isdigit(): continue
        win = int(w[2:6]) / 10 if w[2:6].isdigit() else None
        lo = int(p[2:6]) / 10 if p[2:6].isdigit() else None
        hi = int(p[6:10]) / 10 if p[6:10].isdigit() else None
        rows.append((int(w[:2]), win, lo, hi))
    return kubun, announced, int(total) if total.isdigit() else None, rows

def minutes(a: str) -> int:
    return ((int(a[:2]) * 31 + int(a[2:4])) * 24 + int(a[4:6])) * 60 + int(a[6:8])

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--keys", required=True); ap.add_argument("--out", required=True); ap.add_argument("--until", default="08:15")
    args = ap.parse_args()
    now = datetime.now(); h, m = map(int, args.until.split(":")); stop = now.replace(hour=h, minute=m, second=0)
    if stop <= now: stop += timedelta(days=1)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("CREATE TABLE IF NOT EXISTS snaps(key VARCHAR, kubun VARCHAR, announced VARCHAR, win_total BIGINT, horse_no INTEGER, win DOUBLE, plo DOUBLE, phi DOUBLE)")
    con.execute("CREATE TABLE IF NOT EXISTS done(key VARCHAR, snapshots INTEGER, status VARCHAR)")
    done = {k for (k,) in con.execute(f"SELECT key FROM read_parquet('{out.as_posix()}/done-*.parquet')").fetchall()} if list(out.glob("done-*.parquet")) else set()
    for path in out.glob("done-*.csv"):
        with open(path, newline="", encoding="utf-8") as handle:
            done |= {row[0] for row in csv.reader(handle)}
    snap_rows, done_rows = [], []
    def dump():
        stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        if not done_rows: return
        for name, rows in (("snaps", snap_rows), ("done", done_rows)):
            with open(out / f"{name}-{stamp}.csv.tmp", "w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerows(rows)
        for name in ("snaps", "done"):
            (out / f"{name}-{stamp}.csv.tmp").rename(out / f"{name}-{stamp}.csv")
        snap_rows.clear(); done_rows.clear()
    keys = [k for k in Path(args.keys).read_text().split() if k not in done]
    print(f"残り {len(keys):,} レース。{stop:%m-%d %H:%M} まで", flush=True)
    started = time.time()
    for n, key in enumerate(keys, 1):
        if datetime.now() >= stop:
            print("時刻になったので止めます", flush=True); break
        link = LinkProcess()
        snaps, status = [], "ok"
        try:
            if link.rt_open("0B41", key):
                for record in link.records():
                    if record[:2] == b"O1": snaps.append(parse(record))
            else:
                status = "なし"
        except NVLinkError as error:
            status = f"失敗 {error}"[:80]
        except Exception as error:  # noqa: BLE001
            status = f"失敗 {type(error).__name__} {error}"[:80]
        finally:
            link.close()
        mids = [s for s in snaps if s[1].isdigit() and s[1] != "00000000"]
        if mids:
            middle = [s for s in mids if s[0] == "1"] or mids
            last = max(minutes(s[1]) for s in middle); first = min(s[1] for s in mids)
            keep = [s for s in mids if minutes(s[1]) >= last - 60 or s[1] == first or s[0] != "1"]
            rows = [(key, k, a, t, no, w, lo, hi) for k, a, t, horses in keep for no, w, lo, hi in horses]
            snap_rows.extend(rows)
        done_rows.append((key, len(snaps), status))
        if n % 300 == 0: dump()
        if n % 50 == 0:
            print(f"{n:,}/{len(keys):,} {key} {status} 断面 {len(snaps)} 経過 {time.time() - started:.0f}秒（1レース {(time.time() - started) / n:.2f}秒）", flush=True)
    dump(); con.close()

main()
