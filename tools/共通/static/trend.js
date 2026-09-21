// 傾向スコアの画面（グラフ）。検索画面のタブと、CLI が書く HTML 1ファイルの両方がこのファイルを使う。
//
//   TrendView.render(container, data)   data は 共通/trend.py の TrendReport.to_dict()
//
// 色の役割: 青 = プラス（良い傾向）、赤 = マイナス（悪い傾向）、灰 = どちらでもない。
// 青の濃淡は順序（1着 > 2着 > 3着、頭向き > 相手向き > 無条件）。文字には色を付けず、色は印（四角）だけが持つ。
// 値はすべて textContent で入れる（馬名などを HTML として解釈しない）。
"use strict";
(function () {
  const STYLE_ID = "trend-view-style";
  const CSS = `
  .tv { --tv-surface: #1a1712; --tv-surface-2: #16130f; --tv-line: #332c22; --tv-grid: #2a241c; --tv-ink: #f2ece1; --tv-ink-2: #d9d0c4;
        --tv-muted: #a1968a; --tv-plus-1: #86b6ef; --tv-plus-2: #3987e5; --tv-plus-3: #1c5cab; --tv-minus: #e66767; --tv-neutral: #383835;
        --tv-accent: #d8b268; color: var(--tv-ink); font-size: 13px; line-height: 1.55; }
  .tv * { box-sizing: border-box; }
  .tv h2 { font-size: 16px; font-weight: 600; margin: 0 0 4px; }
  .tv h3 { font-size: 14px; font-weight: 600; margin: 0; }
  .tv .tv-card { background: var(--tv-surface); border: 1px solid var(--tv-line); border-radius: 10px; padding: 14px 18px; margin-bottom: 14px; }
  .tv .tv-sub { color: var(--tv-muted); font-size: 12.5px; margin: 0 0 10px; }
  .tv .tv-warn { border-left: 3px solid var(--tv-accent); padding: 6px 10px; background: var(--tv-surface-2); color: var(--tv-ink-2); border-radius: 4px; margin: 8px 0 0; }
  .tv .tv-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 10px; }
  .tv .tv-tile { background: var(--tv-surface-2); border: 1px solid var(--tv-grid); border-radius: 8px; padding: 10px 12px; }
  .tv .tv-tile .k { color: var(--tv-muted); font-size: 12px; }
  .tv .tv-tile .v { font-size: 24px; font-weight: 600; line-height: 1.2; }
  .tv .tv-tile .v small { font-size: 12px; font-weight: 400; color: var(--tv-muted); margin-left: 4px; }
  .tv .tv-tile .d { color: var(--tv-ink-2); font-size: 12px; }
  .tv .tv-legend { display: flex; flex-wrap: wrap; gap: 4px 14px; color: var(--tv-ink-2); font-size: 12px; margin: 4px 0 10px; }
  .tv .tv-key { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
  .tv .tv-rank { display: grid; grid-template-columns: 30px 64px minmax(120px, 1.1fr) 46px 58px 46px minmax(220px, 3fr) 52px; gap: 0 8px; align-items: center; }
  .tv .tv-rank.no-finish { grid-template-columns: 30px 64px minmax(120px, 1.1fr) 46px 58px minmax(220px, 3fr) 52px; }
  .tv .tv-rank > .h { color: var(--tv-muted); font-size: 11.5px; padding: 2px 0 6px; border-bottom: 1px solid var(--tv-grid); }
  .tv .tv-rank > .c { padding: 5px 0; border-bottom: 1px solid var(--tv-grid); min-height: 32px; display: flex; align-items: center; }
  .tv .tv-rank > .c.num { justify-content: flex-end; font-variant-numeric: tabular-nums; }
  .tv .tv-row { display: contents; cursor: pointer; }
  .tv .tv-row:hover > .c, .tv .tv-row:focus-visible > .c { background: var(--tv-surface-2); }
  .tv .tv-row:focus-visible { outline: none; }
  .tv .tv-name { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tv .tv-name small { font-weight: 400; color: var(--tv-muted); margin-left: 6px; }
  .tv .tv-waku { display: inline-block; min-width: 20px; text-align: center; border-radius: 3px; font-weight: 700; margin-right: 6px; padding: 0 3px; }
  .tv .w1 { background: #f4f4f4; color: #111; } .tv .w2 { background: #1b1b1b; color: #fff; border: 1px solid #555; } .tv .w3 { background: #d9423a; color: #fff; }
  .tv .w4 { background: #2f6fd0; color: #fff; } .tv .w5 { background: #e8d33a; color: #111; } .tv .w6 { background: #2f9d57; color: #fff; }
  .tv .w7 { background: #e88a2c; color: #111; } .tv .w8 { background: #ee9ab8; color: #111; }
  .tv .tv-score { font-size: 15px; font-weight: 700; justify-content: flex-end; font-variant-numeric: tabular-nums; }
  .tv .tv-div { display: flex; width: 100%; height: 14px; }
  .tv .tv-div .side { display: flex; gap: 2px; height: 100%; }
  .tv .tv-div .side.minus { justify-content: flex-end; border-right: 1px solid var(--tv-muted); padding-right: 2px; }
  .tv .tv-div .side.plus { padding-left: 2px; }
  .tv .seg { height: 100%; min-width: 2px; }
  .tv .seg:hover, .tv .bar:hover, .tv .cell:hover { filter: brightness(1.25); }
  .tv .side.plus .seg:last-child { border-radius: 0 4px 4px 0; } .tv .side.minus .seg:first-child { border-radius: 4px 0 0 4px; }
  .tv .tv-detail { grid-column: 1 / -1; background: var(--tv-surface-2); border-bottom: 1px solid var(--tv-grid); padding: 10px 12px 12px; }
  .tv .tv-hits { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 24px; }
  .tv .tv-hit { display: grid; grid-template-columns: 40px minmax(0, 1fr) 150px; gap: 8px; align-items: center; padding: 3px 0; border-bottom: 1px solid var(--tv-grid); }
  .tv .tv-hit .id { color: var(--tv-muted); font-family: Consolas, monospace; font-size: 12px; }
  .tv .tv-hit .t small { color: var(--tv-muted); display: block; font-size: 11.5px; }
  .tv table { width: auto; min-width: 0; font-family: inherit; }
  .tv th, .tv td { position: static; background: transparent; }
  .tv .tv-heat { border-collapse: separate; border-spacing: 2px; font-size: 12px; }
  .tv .tv-heat th, .tv .tv-heat td { border-bottom: none; white-space: normal; vertical-align: middle; }
  .tv .tv-heat th { color: var(--tv-muted); font-weight: 400; font-size: 11.5px; text-align: center; padding: 2px 4px; max-width: 86px; }
  .tv .tv-heat th.l, .tv .tv-heat td.l { text-align: left; white-space: nowrap; padding-right: 10px; color: var(--tv-ink); }
  .tv .cell { width: 72px; height: 22px; text-align: center; border-radius: 3px; font-variant-numeric: tabular-nums; }
  .tv .tv-filters { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: flex-end; margin-bottom: 12px; }
  .tv .tv-filters label { display: flex; flex-direction: column; gap: 2px; font-size: 12px; color: var(--tv-muted); }
  .tv .tv-filters label.inline { flex-direction: row; align-items: center; gap: 6px; color: var(--tv-ink-2); }
  .tv select, .tv input { font: inherit; font-size: 13px; color: var(--tv-ink); background: #221d17; border: 1px solid #3a332a; border-radius: 6px; padding: 4px 8px; }
  .tv .tv-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
  .tv .tv-trend { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr) 46px; gap: 8px; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--tv-grid); }
  .tv .tv-trend .t { min-width: 0; }
  .tv .tv-trend .t b { font-weight: 600; }
  .tv .tv-trend .t small { color: var(--tv-muted); display: block; font-size: 11.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tv .tv-trend .v { text-align: right; font-variant-numeric: tabular-nums; }
  .tv .chips { display: inline-flex; flex-wrap: wrap; gap: 3px; margin-top: 2px; }
  .tv .chip { border: 1px solid #3a332a; border-radius: 9px; padding: 0 6px; font-size: 11px; color: var(--tv-ink-2); background: #221d17; }
  .tv .badge { display: inline-block; font-size: 11px; border: 1px solid #3a332a; border-radius: 3px; padding: 0 5px; margin-left: 6px; color: var(--tv-ink-2); white-space: nowrap; }
  .tv .rate { position: relative; height: 12px; background: transparent; }
  .tv .rate .bars { display: flex; gap: 2px; height: 100%; }
  .tv .rate .bar { height: 100%; min-width: 1px; }
  .tv .rate .bar:last-child { border-radius: 0 4px 4px 0; }
  .tv .rate .base { position: absolute; top: -3px; bottom: -3px; width: 0; border-left: 1px solid var(--tv-ink-2); }
  .tv .tv-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 12px; }
  .tv .tv-factor { background: var(--tv-surface-2); border: 1px solid var(--tv-grid); border-radius: 8px; padding: 10px 12px; }
  .tv .tv-factor .head { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; margin-bottom: 6px; }
  .tv .tv-factor .head small { color: var(--tv-muted); font-family: Consolas, monospace; white-space: nowrap; }
  .tv .tv-lab { display: grid; grid-template-columns: 132px minmax(0, 1fr) 48px 92px; gap: 8px; align-items: center; padding: 4px 0; }
  .tv .tv-lab .n { min-width: 0; overflow-wrap: anywhere; }
  .tv .tv-lab .n.mine { font-weight: 700; }
  .tv .tv-lab .n .chips { display: flex; font-weight: 400; }
  .tv .tv-lab .p { text-align: right; font-variant-numeric: tabular-nums; }
  .tv .tv-lab .m { color: var(--tv-ink-2); font-size: 11.5px; line-height: 1.35; }
  .tv .tv-lab .m small { display: block; color: var(--tv-muted); font-size: 11px; white-space: nowrap; }
  .tv .axis { display: grid; grid-template-columns: 132px minmax(0, 1fr) 48px 92px; gap: 8px; color: var(--tv-muted); font-size: 11px; }
  .tv .axis .scale { display: flex; justify-content: space-between; border-top: 1px solid var(--tv-grid); padding-top: 1px; }
  .tv details > summary { cursor: pointer; color: var(--tv-ink-2); padding: 4px 0; }
  .tv details.group { margin-bottom: 8px; }
  .tv details.group > summary { font-size: 14px; font-weight: 600; color: var(--tv-ink); }
  .tv .tv-table { border-collapse: collapse; font-size: 12px; font-family: Consolas, monospace; width: max-content; min-width: 100%; }
  .tv .tv-table th, .tv .tv-table td { padding: 3px 8px; border-bottom: 1px solid var(--tv-grid); text-align: left; white-space: nowrap; }
  .tv .tv-table th { color: var(--tv-muted); font-weight: 600; }
  .tv .tv-scroll { overflow-x: auto; }
  .tv .empty { color: var(--tv-muted); padding: 6px 0; }
  .tv-tip { position: fixed; z-index: 1000; pointer-events: none; background: #0d0b08; color: #f2ece1; border: 1px solid #3a332a; border-radius: 6px;
            padding: 7px 10px; font-size: 12px; line-height: 1.5; max-width: 340px; box-shadow: 0 4px 14px rgba(0,0,0,.5); display: none; }
  .tv-tip .tt { color: #a1968a; } .tv-tip b { font-weight: 700; font-size: 13px; }
  @media (max-width: 900px) { .tv .tv-cols, .tv .tv-hits { grid-template-columns: 1fr; } }
  `;
  const LEVEL_SHORT = {same: "同レース", match4: "4つ一致", match3: "3つ以上一致", match2: "2つ以上一致"};
  const VERDICT_MARK = {"頭向き": "▲ 頭向き", "相手向き": "▲ 相手向き", "悪い": "▼ 悪い", "無条件": "● 無条件"};
  const USED = "used";
  const TOP_TRENDS = 12;

  // ---------------------------------------------------------------- 小さな道具
  function h(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") node.className = v;
      else if (k === "style") node.style.cssText = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children.flat()) if (c !== null && c !== undefined && c !== false) node.append(c.nodeType ? c : document.createTextNode(String(c)));
    return node;
  }
  const pct = (v) => (v === null || v === undefined ? "—" : (v * 100).toFixed(1) + "%");
  const signed = (v) => (v > 0 ? "+" + v : String(v));
  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    document.head.append(h("style", {id: STYLE_ID}, CSS));
  }

  // 1つだけの吹き出し。data-tip を持つ要素に乗るか、フォーカスすると出る。中身は行の配列（[見出し] か [名前, 値]）。
  let tipNode = null;
  const tips = new WeakMap();
  function tip(node, lines) { tips.set(node, lines); node.setAttribute("data-tip", "1"); if (!node.hasAttribute("tabindex")) node.setAttribute("tabindex", "0"); return node; }
  function showTip(target, x, y) {
    const lines = tips.get(target);
    if (!lines) return;
    if (!tipNode) { tipNode = h("div", {class: "tv-tip"}); document.body.append(tipNode); }
    tipNode.replaceChildren(...lines.map((line) => Array.isArray(line)
      ? h("div", {}, h("b", {}, line[1]), " ", h("span", {class: "tt"}, line[0])) : h("div", {class: "tt"}, line)));
    tipNode.style.display = "block";
    const box = tipNode.getBoundingClientRect();
    tipNode.style.left = Math.max(4, Math.min(x + 14, window.innerWidth - box.width - 8)) + "px";
    tipNode.style.top = Math.max(4, Math.min(y + 14, window.innerHeight - box.height - 8)) + "px";
  }
  function hideTip() { if (tipNode) tipNode.style.display = "none"; }
  function bindTips(root) {
    root.addEventListener("pointermove", (e) => { const t = e.target.closest("[data-tip]"); if (t) showTip(t, e.clientX, e.clientY); else hideTip(); });
    root.addEventListener("pointerleave", hideTip);
    root.addEventListener("focusin", (e) => { const t = e.target.closest("[data-tip]"); if (t) { const b = t.getBoundingClientRect(); showTip(t, b.left, b.bottom); } });
    root.addEventListener("focusout", hideTip);
  }
  function perfLines(title, perf, base) {
    const lines = [title];
    if (!perf) return lines.concat(["この母集団には出走がありません"]);
    lines.push(["出走数", perf.runs.toLocaleString()], ["着別度数（1着-2着-3着-着外）", perf.counts], ["勝率", pct(perf.win)], ["連対率", pct(perf.quinella)],
      ["複勝率", pct(perf.place)], ["単勝回収率", pct(perf.win_return)], ["複勝回収率", pct(perf.place_return)]);
    if (base) lines.push(`基準値: 勝率 ${pct(base.win)} / 連対率 ${pct(base.quinella)} / 複勝率 ${pct(base.place)}`);
    return lines;
  }

  // 率の横棒。1着・2着・3着の率を積む（積んだ長さ = 複勝率）。縦の細線が基準値の複勝率。
  function rateBar(perf, base, max, title) {
    const box = h("div", {class: "rate"});
    if (!perf) return box;
    const parts = [["1着", perf.win, "var(--tv-plus-1)"], ["2着", perf.quinella - perf.win, "var(--tv-plus-2)"], ["3着", perf.place - perf.quinella, "var(--tv-plus-3)"]];
    const bars = h("div", {class: "bars"});
    parts.forEach(([, value, color]) => { if (value > 0) bars.append(h("div", {class: "bar", style: `width:${(value / max) * 100}%;background:${color}`})); });
    box.append(bars);
    if (base) box.append(h("div", {class: "base", style: `left:${Math.min(100, (base.place / max) * 100)}%`}));
    return tip(box, perfLines(title, perf, base));
  }
  function niceMax(values) {
    const top = Math.max(0.1, ...values.filter((v) => v !== null && v !== undefined));
    return Math.min(1, Math.ceil(top * 10 + 0.0001) / 10);
  }

  // ---------------------------------------------------------------- 本体
  function render(container, data) {
    ensureStyle();
    const state = {group: "", target: "", mine: true, level: USED};
    const root = h("div", {class: "tv"});
    container.replaceChildren(root);
    bindTips(root);
    const horseByHid = Object.fromEntries(data.horses.map((x) => [x.hid, x]));
    const horseTag = (hid) => { const x = horseByHid[hid]; return x ? (x.no !== null ? String(x.no) : x.name) : "?"; };

    root.append(headerCard(data), rankingCard(data), heatCard(data));
    const trendHost = h("div");
    root.append(filterCard(data, state, () => drawTrends()), trendHost, sameRaceCard(data));
    function drawTrends() { trendHost.replaceChildren(highlightCard(data, state, horseTag), factorsCard(data, state, horseTag)); }
    drawTrends();
  }

  function headerCard(data) {
    const card = h("div", {class: "tv-card"}, h("h2", {}, "傾向スコア: " + data.title));
    const opt = data.options;
    card.append(h("p", {class: "tv-sub"},
      `プラス ${data.counts.plus} 項目・マイナス ${data.counts.minus} 項目。出走数 ${opt.min_runs} 以上の値を、基準値の ${opt.good} 倍以上で「良い」、${opt.bad} 倍以下で「悪い」と判定`
      + (opt.min_z > 0 ? `（偶然では起きにくい差だけ。強さ ${opt.min_z}）` : "") + (opt.scope ? `。母集団は「${LEVEL_SHORT[opt.scope]}」だけ` : "") + "。"));
    const tiles = h("div", {class: "tv-tiles"});
    data.levels.forEach((level) => {
      const tile = h("div", {class: "tv-tile"}, h("div", {class: "k"}, "母集団: " + level.title),
        h("div", {class: "v"}, level.races.toLocaleString(), h("small", {}, "レース")),
        h("div", {class: "d"}, level.perf ? `${level.runs.toLocaleString()} 頭・複勝率の基準 ${pct(level.perf.place)}` : "該当なし"));
      tiles.append(level.perf ? tip(tile, perfLines(level.title + "（全馬の基準値）", level.perf)) : tile);
    });
    card.append(tiles);
    const cond = data.inputs.condition ? `${data.inputs.condition}（手入力）` : data.header["馬場"];
    card.append(h("p", {class: "tv-sub", style: "margin:10px 0 0"}, `馬場状態: ${cond}　天候: ${data.header["天候"]}　状態: ${data.header["状態"]}`));
    if (data.missing.length) {
      card.append(h("div", {class: "tv-warn"}, `未入力の材料: ${data.missing.join("、")}。これを使う項目は 0 点です。`
        + (data.missing.includes("馬場") ? "馬場状態が無いので、馬場状態を問わない母集団（3つ以上一致から）で採点しています。" : "")
        + (data.missing.includes("枠") ? "枠番・馬番は金・土の出馬表を取得すると入ります。" : "")));
    }
    if (data.scratched.length) card.append(h("p", {class: "tv-sub", style: "margin:8px 0 0"}, "出走しない馬: " + data.scratched.map((s) => `${s.horse_name}（${s.abnormal_name}）`).join("、")));
    return card;
  }

  function rankingCard(data) {
    const card = h("div", {class: "tv-card"}, h("h2", {}, "ランキング（点数の高い順）"),
      h("p", {class: "tv-sub"}, "棒の右が当たったプラス要素の数、左がマイナス要素の数。合計 = プラス − マイナス。行を押すと、当たった項目と根拠の成績が開きます。"));
    card.append(h("div", {class: "tv-legend"},
      h("span", {}, h("i", {class: "tv-key", style: "background:var(--tv-plus-1)"}), "頭向き（勝率が良い傾向）"),
      h("span", {}, h("i", {class: "tv-key", style: "background:var(--tv-plus-2)"}), "相手向き（勝率は並だが連対率・複勝率が良い傾向）"),
      h("span", {}, h("i", {class: "tv-key", style: "background:var(--tv-plus-3)"}), "無条件のプラス（同レースの実績）"),
      h("span", {}, h("i", {class: "tv-key", style: "background:var(--tv-minus)"}), "マイナス（複勝率が悪い傾向など）")));
    const known = data.result_known;
    const grid = h("div", {class: "tv-rank" + (known ? "" : " no-finish")});
    const RIGHT = ["順位", "人気", "着順", "合計"];
    ["順位", "枠・馬番", "馬名", "人気", "推定脚質"].concat(known ? ["着順"] : [], ["マイナス ← → プラス", "合計"]).forEach((t) =>
      grid.append(h("div", {class: "h", style: RIGHT.includes(t) ? "text-align:right" : t.includes("←") ? "text-align:center" : ""}, t)));
    const widest = Math.max(1, ...data.horses.map((x) => Math.max(x.plus, x.minus)));
    data.horses.forEach((horse) => {
      const detail = h("div", {class: "tv-detail", hidden: true});
      const toggle = () => { detail.hidden = !detail.hidden; if (!detail.hidden && !detail.childNodes.length) detail.append(horseDetail(horse)); };
      const row = h("div", {class: "tv-row", tabindex: "0", role: "button", onclick: toggle, onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } }});
      const fixedPlus = horse.hits.filter((x) => x.sign > 0 && x.verdict === "無条件").length;
      const plusParts = [["頭向き", horse.head, "var(--tv-plus-1)"], ["相手向き", horse.partner, "var(--tv-plus-2)"], ["無条件", fixedPlus, "var(--tv-plus-3)"]];
      const side = (cls, parts) => h("div", {class: "side " + cls, style: "width:50%"}, parts.filter((p) => p[1] > 0).map(([name, count, color]) =>
        tip(h("div", {class: "seg", style: `width:${(count / widest) * 100}%;background:${color}`}),
          [`${horse.name}: ${name}`, ["項目", String(count)], horse.hits.filter((x) => (name === "マイナス" ? x.sign < 0 : x.sign > 0 && x.verdict === name)).map((x) => x.id).join(" ")])));
      row.append(
        h("div", {class: "c num"}, horse.rank),
        h("div", {class: "c"}, horse.frame ? h("span", {class: "tv-waku w" + horse.frame}, horse.frame) : null, horse.no !== null ? horse.no : "未定"),
        h("div", {class: "c"}, h("span", {class: "tv-name"}, horse.name, h("small", {}, `${horse.sex_age} ${horse.jockey || ""}`))),
        h("div", {class: "c num"}, horse.popularity !== null ? horse.popularity : "—"),
        h("div", {class: "c"}, horse.style_before));
      if (known) row.append(h("div", {class: "c num"}, horse.finish !== null ? horse.finish + "着" : "—"));
      row.append(h("div", {class: "c"}, h("div", {class: "tv-div"}, side("minus", [["マイナス", horse.minus, "var(--tv-minus)"]]), side("plus", plusParts))),
        h("div", {class: "c tv-score"}, signed(horse.score)));
      grid.append(row, detail);
    });
    card.append(grid);
    return card;
  }

  function horseDetail(horse) {
    if (!horse.hits.length) return h("div", {class: "empty"}, "当たった項目はありません。");
    const list = h("div", {class: "tv-hits"});
    const max = niceMax(horse.hits.map((x) => x.perf && x.perf.place));
    horse.hits.forEach((hit) => {
      const where = hit.level ? LEVEL_SHORT[hit.level] : "";
      list.append(h("div", {class: "tv-hit"}, h("span", {class: "id"}, hit.id),
        h("span", {class: "t"}, `${signed(hit.sign)}  ${hit.title}${hit.label ? "：" + hit.label : ""}`, h("span", {class: "badge"}, VERDICT_MARK[hit.verdict] || hit.verdict),
          h("small", {}, hit.perf ? `${where} ${hit.perf.runs} 走 ${hit.perf.counts}・複勝率 ${pct(hit.perf.place)}（基準 ${pct(hit.base.place)}）・勝率 ${pct(hit.perf.win)}（基準 ${pct(hit.base.win)}）` : "過去の成績を見ない項目")),
        rateBar(hit.perf, hit.base, max, `${hit.id} ${hit.title}${hit.label ? "：" + hit.label : ""}（${where}）`)));
    });
    return list;
  }

  function heatCard(data) {
    const card = h("div", {class: "tv-card"}, h("h2", {}, "グループ別の点"),
      h("p", {class: "tv-sub"}, "どの種類の項目で点を稼いだか・落としたか。青が濃いほどプラス、赤が濃いほどマイナス。似た項目（枠番と枠帯など）は同じ信号を重ねて数えるので、グループごとに見ます。"));
    const groups = Object.entries(data.groups);
    const peak = Math.max(1, ...data.horses.flatMap((x) => Object.values(x.groups).map(Math.abs)));
    const table = h("table", {class: "tv-heat"});
    table.append(h("tr", {}, h("th", {class: "l"}, "馬"), groups.map(([, name]) => h("th", {}, name)), h("th", {}, "合計")));
    data.horses.forEach((horse) => {
      const row = h("tr", {}, h("td", {class: "l"}, `${horse.no !== null ? horse.no : "—"} ${horse.name}`));
      groups.forEach(([key, name]) => {
        const value = horse.groups[key] || 0;
        const strength = Math.abs(value) / peak;
        const color = value === 0 ? "var(--tv-neutral)" : `color-mix(in oklab, ${value > 0 ? "var(--tv-plus-2)" : "var(--tv-minus)"} ${Math.round(25 + strength * 75)}%, var(--tv-neutral))`;
        const ids = horse.hits.filter((x) => String(x.group) === key).map((x) => x.id).join(" ");
        row.append(tip(h("td", {class: "cell", style: `background:${color};color:${strength > 0.45 ? "#fff" : "var(--tv-ink)"}`}, value === 0 ? "0" : signed(value)),
          [`${horse.name}: ${name}`, ["点", signed(value)], ids || "当たった項目なし"]));
      });
      row.append(h("td", {class: "cell", style: "font-weight:700"}, signed(horse.score)));
      table.append(row);
    });
    card.append(h("div", {class: "tv-scroll"}, table));
    return card;
  }

  function filterCard(data, state, redraw) {
    const select = (options, value, onchange) => { const s = h("select", {onchange: (e) => onchange(e.target.value)}); options.forEach(([v, t]) => s.append(h("option", {value: v, selected: v === value}, t))); return s; };
    const card = h("div", {class: "tv-card"}, h("h2", {}, "このレースの条件の傾向"),
      h("p", {class: "tv-sub"}, "下の2つの表示（良い・悪い傾向、要因ごとのグラフ）を絞り込みます。"));
    card.append(h("div", {class: "tv-filters"},
      h("label", {}, "グループ", select([["", "全部"]].concat(Object.entries(data.groups)), state.group, (v) => { state.group = v; redraw(); })),
      h("label", {}, "対象の馬", select([["", "全部"], ["all", "全馬"], ["longshot", "穴馬"], ["favorite", "人気馬"]], state.target, (v) => { state.target = v; redraw(); })),
      h("label", {}, "グラフに出す母集団", select([[USED, "判定に使った母集団"]].concat(data.levels.map((l) => [l.key, LEVEL_SHORT[l.key]])), state.level, (v) => { state.level = v; redraw(); })),
      h("label", {class: "inline"}, h("input", {type: "checkbox", checked: state.mine, onchange: (e) => { state.mine = e.target.checked; redraw(); }}), "今回の出走馬が当たる値だけ")));
    return card;
  }
  function visibleTrends(data, state) {
    return data.trends.filter((t) => (!state.group || String(t.group) === state.group) && (!state.target || t.target === state.target));
  }
  // グラフに出す母集団。「判定に使った母集団」なら値ごとに、判定できなかった値はいちばん広い母集団。
  function levelOf(label, state, data) {
    if (state.level !== USED) return state.level;
    if (label.level) return label.level;
    const wide = data.levels.map((l) => l.key).reverse().find((key) => label.rows[key]);
    return wide || null;
  }

  function highlightCard(data, state, horseTag) {
    const found = [];
    visibleTrends(data, state).forEach((trend) => trend.labels.forEach((label) => {
      if (!label.verdict || !label.level || (state.mine && !label.horses.length)) return;
      const perf = label.rows[label.level], base = trend.baselines[label.level];
      const lift = label.verdict === "頭向き" ? perf.win / base.win : perf.place / base.place;
      found.push({trend, label, perf, base, lift});
    }));
    const good = found.filter((x) => x.label.verdict !== "悪い").sort((a, b) => b.lift - a.lift);
    const bad = found.filter((x) => x.label.verdict === "悪い").sort((a, b) => a.lift - b.lift);
    const max = niceMax(found.map((x) => x.perf.place));
    const column = (title, note, items) => {
      const box = h("div", {}, h("h3", {}, `${title}（${items.length}）`), h("p", {class: "tv-sub"}, note));
      if (!items.length) box.append(h("div", {class: "empty"}, "該当なし"));
      const rows = items.map((x) => h("div", {class: "tv-trend"},
        h("div", {class: "t"}, h("b", {}, `${x.trend.title}：${x.label.label}`), h("span", {class: "badge"}, VERDICT_MARK[x.label.verdict]),
          h("small", {}, `${LEVEL_SHORT[x.label.level]} ${x.perf.runs} 走 ${x.perf.counts}・勝率 ${pct(x.perf.win)}（基準 ${pct(x.base.win)}）`),
          x.label.horses.length ? h("span", {class: "chips"}, x.label.horses.map((hid) => h("span", {class: "chip"}, horseTag(hid)))) : null),
        rateBar(x.perf, x.base, max, `${x.trend.title}：${x.label.label}（${LEVEL_SHORT[x.label.level]}）`),
        h("div", {class: "v"}, pct(x.perf.place))));
      box.append(...rows.slice(0, TOP_TRENDS));
      if (rows.length > TOP_TRENDS) box.append(h("details", {}, h("summary", {}, `残り ${rows.length - TOP_TRENDS} 件を見る`), ...rows.slice(TOP_TRENDS)));
      return box;
    };
    const card = h("div", {class: "tv-card"}, h("h2", {}, "良い傾向・悪い傾向"),
      h("p", {class: "tv-sub"}, "棒は 1着・2着・3着の率を積んだもの（全体の長さ = 複勝率、右の数字）。縦の細い線が基準値の複勝率。丸い札は、その値に当たる今回の出走馬の馬番。"));
    card.append(rateLegend(), h("div", {class: "tv-cols"},
      column("良い傾向", "基準値との差が大きい順。頭向きは勝率、相手向きは複勝率の差で並べます。", good),
      column("悪い傾向", "複勝率が基準値より低い順。", bad)));
    return card;
  }
  function rateLegend() {
    return h("div", {class: "tv-legend"},
      h("span", {}, h("i", {class: "tv-key", style: "background:var(--tv-plus-1)"}), "1着の率（勝率）"),
      h("span", {}, h("i", {class: "tv-key", style: "background:var(--tv-plus-2)"}), "2着の率"),
      h("span", {}, h("i", {class: "tv-key", style: "background:var(--tv-plus-3)"}), "3着の率"),
      h("span", {}, h("i", {class: "tv-key", style: "background:var(--tv-ink-2);width:1px"}), "基準値の複勝率"));
  }

  function factorsCard(data, state, horseTag) {
    const card = h("div", {class: "tv-card"}, h("h2", {}, "要因ごとのグラフ"),
      h("p", {class: "tv-sub"}, "要因（切り口）ごとの、値別の成績。太字は今回の出走馬が当たる値。棒に乗ると成績7つが出ます。「表で見る」で数字の表になります。"));
    card.append(rateLegend());
    const trends = visibleTrends(data, state);
    Object.entries(data.groups).forEach(([key, name]) => {
      const inGroup = trends.filter((t) => String(t.group) === key);
      if (!inGroup.length) return;
      const group = h("details", {class: "group", open: Boolean(state.group) || key === "1" || key === "2"}, h("summary", {}, `${key}. ${name}（${inGroup.length}）`));
      const grid = h("div", {class: "tv-grid"});
      inGroup.forEach((trend) => grid.append(factorCard(trend, state, data, horseTag)));
      group.append(grid);
      card.append(group);
    });
    return card;
  }
  function factorCard(trend, state, data, horseTag) {
    const ids = Object.values(trend.ids).join(" / ");
    const box = h("div", {class: "tv-factor"}, h("div", {class: "head"}, h("h3", {}, trend.title, trend.target !== "all" ? h("span", {class: "badge"}, trend.target_title) : null), h("small", {}, ids)));
    if (trend.skipped) box.append(h("div", {class: "tv-warn", style: "margin:0 0 6px"}, trend.skipped + "（今回の馬には当てはめていません）"));
    const labels = trend.labels.filter((label) => !state.mine || label.horses.length);
    if (!labels.length) { box.append(h("div", {class: "empty"}, state.mine ? "今回の出走馬が当たる値はありません。" : "該当なし")); return box; }
    const shown = labels.map((label) => { const level = levelOf(label, state, data); return {label, level, perf: level ? label.rows[level] : null, base: level ? trend.baselines[level] : null}; });
    const max = niceMax(shown.map((x) => x.perf && x.perf.place).concat(shown.map((x) => x.base && x.base.place)));
    shown.forEach((x) => {
      const mark = x.label.verdict && (state.level === USED || state.level === x.label.level) ? VERDICT_MARK[x.label.verdict] : "";
      box.append(h("div", {class: "tv-lab"},
        h("div", {class: "n" + (x.label.horses.length ? " mine" : "")}, x.label.label,
          x.label.horses.length ? h("span", {class: "chips"}, x.label.horses.map((hid) => h("span", {class: "chip"}, horseTag(hid)))) : null),
        rateBar(x.perf, x.base, max, `${trend.title}：${x.label.label}（${x.level ? LEVEL_SHORT[x.level] : "—"}）`),
        h("div", {class: "p"}, x.perf ? pct(x.perf.place) : "—"),
        h("div", {class: "m"}, mark || "—", h("small", {}, x.perf ? `${LEVEL_SHORT[x.level]}・${x.perf.runs.toLocaleString()} 走` : "出走なし"))));
    });
    box.append(h("div", {class: "axis"}, h("span"), h("span", {class: "scale"}, h("span", {}, "0%"), h("span", {}, "複勝率"), h("span", {}, pct(max))), h("span"), h("span")));
    const table = h("table", {class: "tv-table"}, h("tr", {}, ["値", "母集団", "出走数", "着別度数", "勝率", "連対率", "複勝率", "単勝回収率", "複勝回収率", "判定", "今回の馬"].map((t) => h("th", {}, t))));
    shown.forEach((x) => table.append(h("tr", {}, [x.label.label, x.level ? LEVEL_SHORT[x.level] : "", x.perf ? x.perf.runs : 0, x.perf ? x.perf.counts : "", x.perf ? pct(x.perf.win) : "",
      x.perf ? pct(x.perf.quinella) : "", x.perf ? pct(x.perf.place) : "", x.perf ? pct(x.perf.win_return) : "", x.perf ? pct(x.perf.place_return) : "",
      x.label.verdict + (x.label.level ? `（${LEVEL_SHORT[x.label.level]}）` : ""), x.label.horses.map(horseTag).join(" ")].map((v) => h("td", {}, v)))));
    box.append(h("details", {}, h("summary", {}, "表で見る"), h("div", {class: "tv-scroll"}, table)));
    return box;
  }

  function sameRaceCard(data) {
    const t = data.same_race;
    const card = h("div", {class: "tv-card"}, h("h2", {}, t.title), h("p", {class: "tv-sub"}, t.note));
    if (!t.rows.length) { card.append(h("div", {class: "empty"}, "（該当なし）")); return card; }
    const table = h("table", {class: "tv-table"}, h("tr", {}, t.columns.map((c) => h("th", {}, c))));
    t.rows.forEach((row) => table.append(h("tr", {}, row.map((v) => h("td", {}, v === null || v === undefined ? "" : v)))));
    card.append(h("div", {class: "tv-scroll"}, table));
    return card;
  }

  window.TrendView = {render};
})();
