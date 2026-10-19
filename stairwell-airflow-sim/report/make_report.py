"""
產生「扶手送風模擬報告」網頁：讀取 out/*.json 與圖檔，輸出 report/index.html 與 report/assets/。
CFD 尚未完成的項目會顯示「計算中」，重新執行即可更新。
"""
import html
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
ASSETS = os.path.join(HERE, "assets")
os.makedirs(ASSETS, exist_ok=True)


def J(name):
    p = os.path.join(OUT, name)
    return json.load(open(p)) if os.path.exists(p) else None


s1, s2, s3, s4, val = J("s1_results.json"), J("s2_results.json"), J("s3_results.json"), J("s4_results.json"), J("val_poiseuille.json")
s2 = s2 or {}

for f in os.listdir(OUT):
    if f.endswith((".png", ".mp4")) and not f.startswith(("_", "geom_check")):
        shutil.copy2(os.path.join(OUT, f), os.path.join(ASSETS, f))


def fig(name, alt, caption, wide=False):
    dark = name.replace(".png", "_dark.png")
    has_dark = os.path.exists(os.path.join(ASSETS, dark))
    if not os.path.exists(os.path.join(ASSETS, name)):
        return f'<figure class="fig pending"><div class="pending-box">計算中：{html.escape(alt)}</div><figcaption>{caption}</figcaption></figure>'
    imgs = f'<img class="img-light" src="assets/{name}" alt="{html.escape(alt)}" loading="lazy">'
    if has_dark:
        imgs += f'<img class="img-dark" src="assets/{dark}" alt="{html.escape(alt)}" loading="lazy">'
    else:
        imgs = imgs.replace('class="img-light"', 'class="img-any"')
    return f'<figure class="fig{" wide" if wide else ""}">{imgs}<figcaption>{caption}</figcaption></figure>'


def video(name, caption):
    if not os.path.exists(os.path.join(ASSETS, name)):
        return f'<figure class="fig pending"><div class="pending-box">動畫計算中</div><figcaption>{caption}</figcaption></figure>'
    return (f'<figure class="fig wide"><video src="assets/{name}" controls muted loop playsinline preload="metadata"></video>'
            f'<figcaption>{caption}</figcaption></figure>')


def tag(kind):
    label = {"sim": "模擬結果", "inf": "工程推論", "asm": "假設值", "std": "外部標準定義", "tbd": "尚待驗證"}[kind]
    return f'<span class="tag tag-{kind}">{label}</span>'


def pct(x, d=0):
    return "—" if x is None else f"{x*100:.{d}f}%"


NZ = ["plain", "coanda", "coax", "amp"]
NZ_LABEL = {"plain": "A 一般定向噴嘴", "coanda": "B 康達曲面導流", "coax": "C 低混合率同軸噴嘴", "amp": "D 氣流倍增式"}
CONDS = [("head_vc00", "無側風"), ("head_vc15", "側風 0.15 m/s"), ("head_vc30", "側風 0.30 m/s")]


def saf(nz, cond, key="mean"):
    r = s2.get(f"{nz}_{cond}")
    return None if r is None else r[key]


def saf_table():
    rows = []
    for nz in NZ:
        cells = []
        for c, _ in CONDS:
            m, p = saf(nz, c), saf(nz, c, "p10")
            cells.append(f'<td class="num">{pct(m)}<span class="sub">最差 {pct(p)}</span></td>' if m is not None
                         else '<td class="num muted">計算中</td>')
        ent = s2.get(f"{nz}_free", {}).get("entrain", {}).get("30cm")
        cells.append(f'<td class="num">{"—" if ent is None else f"{ent:.1f} 倍"}</td>')
        rows.append(f'<tr><th scope="row">{NZ_LABEL[nz]}</th>{"".join(cells)}</tr>')
    head = "".join(f"<th scope=\"col\">{l}</th>" for _, l in CONDS)
    return (f'<div class="table-wrap"><table><thead><tr><th scope="col">噴嘴</th>{head}'
            f'<th scope="col">30 cm 處總風量÷供氣量</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def verify_table():
    rows = []
    for name, r in sorted(s2.items()):
        rows.append(f'<tr><th scope="row">{name}</th><td class="num">{r["supply_flux_ratio"]:.2f}</td>'
                    f'<td class="num">{pct(r["first_half"],1)} / {pct(r["second_half"],1)}</td></tr>')
    if not rows:
        return '<p class="muted">CFD 計算中，完成後自動填入。</p>'
    return ('<div class="table-wrap"><table><thead><tr><th scope="col">算例</th><th scope="col">示蹤劑通量 ÷ 設定供氣量</th>'
            '<th scope="col">呼吸區 SAF：前半段 / 後半段平均</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


def op_table():
    if not s1:
        return ""
    rows = []
    for r in s1["operating_points"]:
        if r["D_mm"] != 34:
            continue
        ok = '<span class="pill ok">足夠</span>' if r["meets"] else '<span class="pill bad">不足</span>'
        rows.append(f'<tr><th scope="row">{r["fan"].split("（")[0]}</th><td>{r["filter"]}</td><td class="num">{r["Q_Ls"]:.1f}</td>'
                    f'<td class="num">{r["dP_Pa"]:.0f}</td><td class="num">{r["outlet_m"]:.2f}</td><td class="num">{r["P_elec_W"]:.0f}</td><td>{ok}</td></tr>')
    return ('<div class="table-wrap"><table><thead><tr><th scope="col">風機</th><th scope="col">濾材狀態</th><th scope="col">風量 L/s</th>'
            '<th scope="col">靜壓 Pa</th><th scope="col">可供出風口長度 m</th><th scope="col">耗電約 W</th><th scope="col">需求 6 L/s</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def filt_table():
    if not s3:
        return ""
    rows = []
    for r in s3["particle_removal"]:
        rows.append(f'<tr><td>{r["smoke"]}</td><td>{r["train"]}</td><td class="num">{pct(r["removal_mass"],1)}</td>'
                    f'<td class="num">{pct(r["removal_number"],1)}</td><td class="num">0%</td></tr>')
    return ('<div class="table-wrap"><table><thead><tr><th scope="col">煙的種類</th><th scope="col">處理方式</th><th scope="col">微粒去除（質量）</th>'
            '<th scope="col">微粒去除（數量）</th><th scope="col">CO 去除</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


# ---------- 依結果產生的結論文字 ----------
def best_nozzle(cond):
    vals = {nz: saf(nz, cond) for nz in NZ if saf(nz, cond) is not None}
    return max(vals, key=vals.get) if vals else None


cyc = s3["cyclone"] if s3 else {}
flaming_cyc = next((r for r in (s3 or {}).get("particle_removal", []) if r["train"].startswith("氣旋") and "有焰" in r["smoke"]), None)
s4_max = max((c["Q_m3min"] for c in (s4 or {}).get("cases", [])), default=None)
s4_ratio = max((c["ratio_to_door"] for c in (s4 or {}).get("cases", [])), default=None)
fanM = next((r for r in (s1 or {}).get("operating_points", []) if r["D_mm"] == 34 and r["fan"].startswith("M") and "堵塞" in r["filter"]), None)

CFD_DONE = all(f"{nz}_{c}" in s2 for nz in NZ for c, _ in CONDS)


def nz_row(nz, role):
    v0, v15, v30 = saf(nz, "head_vc00"), saf(nz, "head_vc15"), saf(nz, "head_vc30")
    if v0 is None:
        return f"口鼻區供氣比例：計算中"
    return f"口鼻區供氣比例 無側風 {pct(v0)}、側風 0.15 m/s {pct(v15)}、0.30 m/s {pct(v30)}"


import sys
sys.path.insert(0, HERE)
from findings import build_findings  # 依結果撰寫的判讀文字（人工撰寫，避免模板化結論）

FIND = build_findings(dict(s1=s1, s2=s2, s3=s3, s4=s4, saf=saf, pct=pct, tag=tag, CFD_DONE=CFD_DONE))

VERDICTS = [
    ("緊湊型 BLDC 離心風機", "可行", "ok",
     f"每層一台、中型鼓風機量級即可；濾材堵塞時仍有 {fanM['Q_Ls']:.1f} L/s（需求 6 L/s），耗電約 {fanM['P_elec_W']:.0f} W。" if fanM else "", "S1"),
    ("低混合率同軸噴嘴", FIND["coax"]["verdict"], FIND["coax"]["cls"], nz_row("coax", "") + "。" + FIND["coax"]["short"], "S2"),
    ("康達曲面導流", FIND["coanda"]["verdict"], FIND["coanda"]["cls"], nz_row("coanda", "") + "。" + FIND["coanda"]["short"], "S2"),
    ("一般定向噴嘴", FIND["plain"]["verdict"], FIND["plain"]["cls"], nz_row("plain", "") + "。" + FIND["plain"]["short"], "S2"),
    ("氣流倍增式噴嘴", FIND["amp"]["verdict"], FIND["amp"]["cls"], nz_row("amp", "") + "。" + FIND["amp"]["short"], "S2"),
    ("初濾＋HEPA", "只管微粒", "mid", "火災煙微粒去除 99.9% 以上；CO 去除 0%。", "S3"),
    ("活性碳、觸媒", "需實測", "mid", "電腦模擬無法證明效果；活性碳對 CO 幾乎無效，觸媒受濕度與壽命影響，必須做實驗。", "S3"),
    ("氣源", "必須獨立", "ok", "同一個噴嘴改用樓梯間空氣過濾後送出，口鼻區 CO 仍是環境的 100%；只有獨立乾淨氣源才有降低效果。", "S2＋S3"),
    ("氣旋分離", "不採用", "bad",
     f"火災煙微粒多在 1 µm 以下；D=100 mm 氣旋 d50≈{cyc.get('d50_um',0):.1f} µm，只抓到約 {pct(flaming_cyc['removal_mass']) if flaming_cyc else '—'} 質量，壓損約 {cyc.get('dP_Pa',0):.0f} Pa。", "S3"),
    ("扶手當排煙管", "不採用", "bad",
     f"整棟一根扶手 70 m，風機給到 3000 Pa 也只排得出約 {s4_max:.2f} m³/min，約一扇敞開的門的 {pct(s4_ratio,1)}。" if s4_max else "", "S4"),
    ("吸樓梯間空氣、過濾後送去呼吸", "不採用", "bad", "CO 與缺氧都無法用濾材解決；模擬顯示口鼻區 CO 完全沒有降低。", "S2＋S3"),
]


def verdict_rows():
    out = []
    for name, v, cls, why, src in VERDICTS:
        out.append(f'<tr><th scope="row">{name}</th><td><span class="pill {cls}">{v}</span></td><td>{why}</td><td class="src">{src}</td></tr>')
    return "".join(out)


SETUP_SVG = """
<svg class="diagram" viewBox="0 0 760 500" role="img" aria-label="CFD 斷面設定示意：扶手與噴嘴在左，頭部在右 35 公分處，口鼻量測區在臉前">
  <defs>
    <marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" class="d-accent-fill"/></marker>
    <marker id="ah2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" class="d-muted-fill"/></marker>
  </defs>
  <rect x="60" y="40" width="640" height="400" class="d-domain"/>
  <rect x="85" y="65" width="590" height="350" class="d-sponge"/>
  <text x="90" y="82" class="d-small">吸收層 2.5 cm（開放邊界，讓出流與捲吸自然進出）</text>
  <circle cx="98" cy="240" r="25" class="d-solid"/>
  <rect x="115" y="236" width="25" height="8" class="d-solid"/>
  <text x="70" y="290" class="d-label">扶手 Ø50 mm</text>
  <text x="70" y="306" class="d-label">＋ 噴嘴（四種）</text>
  <line x1="142" y1="240" x2="402" y2="240" class="d-axis" marker-end="url(#ah)"/>
  <text x="200" y="230" class="d-label">噴流主軸（每公尺出風口 5 L/s）</text>
  <circle cx="490" cy="240" r="80" class="d-head"/>
  <text x="490" y="236" text-anchor="middle" class="d-label">頭部</text>
  <text x="490" y="254" text-anchor="middle" class="d-small">以直徑 16 cm 圓柱近似</text>
  <rect x="385" y="228" width="20" height="24" class="d-probe"/>
  <line x1="395" y1="226" x2="395" y2="180" class="d-leader"/>
  <text x="395" y="172" text-anchor="middle" class="d-label">口鼻量測區</text>
  <text x="395" y="156" text-anchor="middle" class="d-small">臉前 0.5–2.5 cm、上下 ±1.2 cm</text>
  <line x1="140" y1="120" x2="410" y2="120" class="d-dim"/>
  <line x1="140" y1="112" x2="140" y2="128" class="d-dim"/><line x1="410" y1="112" x2="410" y2="128" class="d-dim"/>
  <text x="275" y="112" text-anchor="middle" class="d-label">35 cm（低姿勢：臉靠近扶手）</text>
  <g class="d-cross">
    <line x1="230" y1="470" x2="230" y2="420" marker-end="url(#ah2)"/>
    <line x1="380" y1="470" x2="380" y2="420" marker-end="url(#ah2)"/>
    <line x1="530" y1="470" x2="530" y2="420" marker-end="url(#ah2)"/>
  </g>
  <text x="560" y="462" class="d-label">側風 0／0.15／0.30 m/s</text>
  <text x="560" y="478" class="d-small">（樓梯間上升氣流、人體擾動的簡化）</text>
  <text x="60" y="30" class="d-small">計算域 64 × 40 cm，網格 1 mm（640 × 400 ＝ 25.6 萬格）</text>
</svg>
"""

PARAMS = [
    ("網格", "1 mm 正方格，640 × 400 = 25.6 萬格", "asm"),
    ("流場方法", "D2Q9 格子波茲曼法（LBM），正則化碰撞＋Smagorinsky 大渦模擬（Cs = 0.15）", "inf"),
    ("示蹤劑", "有限體積 MUSCL（minmod 限制器）對流＋擴散；分子擴散 2×10⁻⁵ m²/s，紊流擴散＝渦黏度/0.7", "inf"),
    ("空氣", "20 °C，動黏度 1.5×10⁻⁵ m²/s，等溫、不含浮力", "asm"),
    ("供氣量", "每公尺出風口 5 L/s（四種噴嘴相同，公平比較）", "asm"),
    ("模擬時間", "8 秒（同軸組 10 秒），前 3 秒（同軸組 4 秒）為暖機不列入平均", "asm"),
    ("時間步長", "依各組最高速度換算，格子速度上限 0.1（控制壓縮性誤差）", "inf"),
    ("邊界", "四周開放（平衡態外插）＋吸收層；側風由下邊界以均勻速度送入", "inf"),
    ("固體", "半格反彈（halfway bounce-back），扶手、噴嘴壁、頭部", "inf"),
    ("取樣", "口鼻區方框每 0.01 秒記錄一次平均濃度", "asm"),
]


def params_rows():
    return "".join(f'<tr><th scope="row">{k}</th><td>{v}</td><td>{tag(t)}</td></tr>' for k, v, t in PARAMS)


val_txt = (f"L2 相對誤差 {val['L2_rel_error']*100:.1f}%，通道內流量與入口差 {abs(val['flux_ratio']-1)*100:.1f}%"
           if val else "計算中")
flux_vals = [r["supply_flux_ratio"] for r in s2.values()]
flux_txt = (f"{min(flux_vals):.2f}–{max(flux_vals):.2f}" if flux_vals else "計算中")
conv_vals = [abs(r["first_half"] - r["second_half"]) for k, r in s2.items() if "head" in k]
conv_txt = (f"{max(conv_vals)*100:.1f} 個百分點" if conv_vals else "計算中")

status_note = "" if CFD_DONE else '<p class="banner">CFD 仍在背景計算，標示「計算中」的項目會在完成後更新。</p>'

PAGE = f"""<title>扶手送風模擬報告</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Noto+Sans+TC:wght@400;500;700;900&display=swap">
<style>
/* Layout: 單欄技術報告，正文 70ch，圖表可放寬到 1040px；結論表在最前，方法章節獨立 */
:root {{
  --bg: #f6f7f5; --surface: #ffffff; --fg: #141816; --fg2: #49504c; --muted: #747c77; --line: #dce1dd;
  --accent: #0d7f4f; --accent-soft: #e2f2e9; --warn: #9a5b00; --warn-soft: #fbefdc; --crit: #b42f2b; --crit-soft: #fbe6e5;
  --show-light: block; --show-dark: none;
  --f-body: "IBM Plex Sans", "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", system-ui, sans-serif;
  --f-display: "Noto Sans TC", "IBM Plex Sans", "PingFang TC", sans-serif;
  --f-mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #0f1311; --surface: #161b18; --fg: #ebefec; --fg2: #b4bdb7; --muted: #87918b; --line: #29312c;
  --accent: #45cf90; --accent-soft: #13291e; --warn: #e6a743; --warn-soft: #2b2112; --crit: #f0716c; --crit-soft: #2e1716;
  --show-light: none; --show-dark: block; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #0f1311; --surface: #161b18; --fg: #ebefec; --fg2: #b4bdb7; --muted: #87918b; --line: #29312c;
  --accent: #45cf90; --accent-soft: #13291e; --warn: #e6a743; --warn-soft: #2b2112; --crit: #f0716c; --crit-soft: #2e1716;
  --show-light: none; --show-dark: block; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--fg); font-family: var(--f-body); font-size: 16px; line-height: 1.75;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 0 64px; }}
.wrap {{ max-width: 1040px; margin: 0 auto; }}
.prose {{ max-width: 70ch; }}
header.top {{ padding-block: 48px 28px; border-bottom: 1px solid var(--line); display: grid; gap: 14px; }}
.eyebrow {{ font-size: 13px; letter-spacing: .08em; color: var(--accent); font-weight: 600; }}
h1 {{ font-family: var(--f-display); font-weight: 900; font-size: clamp(30px, 5vw, 46px); line-height: 1.2; margin: 0; text-wrap: balance; }}
.meta {{ color: var(--fg2); font-size: 14px; display: flex; flex-wrap: wrap; gap: 6px 22px; }}
.meta b {{ color: var(--fg); font-weight: 500; }}
nav.toc {{ display: flex; flex-wrap: wrap; gap: 8px; padding-block: 18px; border-bottom: 1px solid var(--line); }}
nav.toc a {{ color: var(--fg2); text-decoration: none; font-size: 14px; padding: 4px 10px; border: 1px solid var(--line); border-radius: 999px; }}
nav.toc a:hover, nav.toc a:focus-visible {{ color: var(--accent); border-color: var(--accent); outline: none; }}
section {{ padding-block: 40px 8px; display: grid; gap: 18px; }}
h2 {{ font-family: var(--f-display); font-weight: 700; font-size: clamp(22px, 3.2vw, 28px); margin: 0; line-height: 1.35; text-wrap: balance; }}
h2 .no {{ font-family: var(--f-mono); font-weight: 500; color: var(--accent); margin-right: 10px; font-size: .8em; }}
h3 {{ font-size: 18px; margin: 10px 0 0; font-weight: 700; }}
p {{ margin: 0; }}
.lead {{ font-size: 17px; color: var(--fg); }}
.muted {{ color: var(--muted); }}
.banner {{ background: var(--warn-soft); color: var(--fg); border: 1px solid var(--warn); border-radius: 8px; padding: 10px 14px; font-size: 14px; }}
.table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); }}
table {{ border-collapse: collapse; width: 100%; font-size: 14.5px; }}
th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }}
thead th {{ font-size: 13px; color: var(--fg2); font-weight: 600; background: var(--bg); white-space: nowrap; }}
tbody tr:last-child th, tbody tr:last-child td {{ border-bottom: 0; }}
tbody th {{ font-weight: 600; white-space: nowrap; }}
td.num {{ font-family: var(--f-mono); font-variant-numeric: tabular-nums; white-space: nowrap; }}
td.src {{ font-family: var(--f-mono); font-size: 13px; color: var(--muted); white-space: nowrap; }}
.sub {{ display: block; font-size: 12px; color: var(--muted); }}
.pill {{ display: inline-block; font-size: 13px; font-weight: 600; padding: 1px 9px; border-radius: 999px; white-space: nowrap; border: 1px solid; }}
.pill.ok {{ color: var(--accent); background: var(--accent-soft); border-color: var(--accent); }}
.pill.mid {{ color: var(--warn); background: var(--warn-soft); border-color: var(--warn); }}
.pill.bad {{ color: var(--crit); background: var(--crit-soft); border-color: var(--crit); }}
.tag {{ display: inline-block; font-size: 12px; padding: 0 7px; border-radius: 4px; border: 1px solid var(--line); color: var(--fg2); white-space: nowrap; margin-left: 4px; vertical-align: 1px; }}
.tag-sim {{ border-color: var(--accent); color: var(--accent); }}
.tag-tbd {{ border-color: var(--warn); color: var(--warn); }}
.fig {{ margin: 0; display: grid; gap: 8px; }}
.fig img, .fig video {{ width: 100%; max-width: 100%; height: auto; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); }}
.fig .img-light {{ display: var(--show-light); }}
.fig .img-dark {{ display: var(--show-dark); }}
.fig .img-any {{ display: block; }}
figcaption {{ font-size: 13.5px; color: var(--fg2); max-width: 80ch; }}
.pending-box {{ border: 1px dashed var(--line); border-radius: 8px; padding: 40px 16px; text-align: center; color: var(--muted); }}
.method {{ border: 1px solid var(--line); border-radius: 10px; background: var(--surface); padding: 18px 20px; display: grid; gap: 12px; }}
.method dl {{ display: grid; grid-template-columns: 7.5em 1fr; gap: 8px 16px; margin: 0; }}
.method dt {{ color: var(--muted); font-size: 14px; }}
.method dd {{ margin: 0; min-width: 0; }}
.formula {{ font-family: var(--f-mono); background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 10px 14px; overflow-x: auto; font-size: 14px; }}
.diagram {{ width: 100%; height: auto; max-width: 100%; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; }}
.d-domain {{ fill: none; stroke: var(--fg2); stroke-width: 1.2; }}
.d-sponge {{ fill: none; stroke: var(--line); stroke-width: 1.2; stroke-dasharray: 5 4; }}
.d-solid {{ fill: var(--muted); }}
.d-head {{ fill: var(--line); stroke: var(--muted); stroke-width: 1; }}
.d-probe {{ fill: none; stroke: var(--crit); stroke-width: 2; }}
.d-axis {{ stroke: var(--accent); stroke-width: 2; }}
.d-accent-fill {{ fill: var(--accent); }}
.d-muted-fill {{ fill: var(--muted); }}
.d-leader, .d-dim {{ stroke: var(--fg2); stroke-width: 1; }}
.d-cross line {{ stroke: var(--muted); stroke-width: 1.6; }}
.d-label {{ fill: var(--fg); font-size: 14px; font-family: var(--f-body); }}
.d-small {{ fill: var(--fg2); font-size: 12px; font-family: var(--f-body); }}
.cols {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
.cols > * {{ min-width: 0; }}
.card {{ border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; background: var(--surface); display: grid; gap: 6px; }}
.card h4 {{ margin: 0; font-size: 15px; }}
ul, ol {{ margin: 0; padding-left: 1.3em; display: grid; gap: 4px; }}
code {{ font-family: var(--f-mono); font-size: .9em; background: var(--bg); border: 1px solid var(--line); border-radius: 4px; padding: 0 4px; overflow-wrap: anywhere; }}
footer {{ margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; }}
@media (max-width: 560px) {{ .method dl {{ grid-template-columns: 1fr; gap: 2px; }} .method dd {{ margin-bottom: 8px; }} tbody th {{ white-space: normal; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ scroll-behavior: auto !important; }} }}
</style>

<div class="wrap">
<header class="top">
  <div class="eyebrow">樓梯逃生導引扶手系統｜第二階段送風研究</div>
  <h1>扶手送風模擬報告</h1>
  <div class="meta"><span>日期 <b>2026-10-19</b></span><span>專案 <b>長庚大學工業設計學系 林煜宸</b></span><span>模擬與撰寫 <b>Claude（AI）</b></span></div>
  <p class="prose lead">這份報告用電腦模擬檢查第二階段送風的每一項技術：風機與扶手風道夠不夠力、四種出風口能把多少乾淨空氣送到低姿勢逃生者的口鼻、濾材和氣旋能處理什麼，以及扶手能不能當排煙管。每個數字都附上「怎麼算出來的」與限制。</p>
  {status_note}
</header>
<nav class="toc" aria-label="章節">
  <a href="#summary">結論</a><a href="#method">量測方法</a><a href="#nozzle">噴嘴 CFD</a><a href="#source">氣源</a>
  <a href="#filter">濾材與氣旋</a><a href="#duct">風道與風機</a><a href="#exhaust">排煙容量</a><a href="#limits">限制與下一步</a>
</nav>

<section id="summary">
  <h2><span class="no">01</span>結論先看</h2>
  <p class="prose">下表對應技術確認表中「送風（第二階段研究）」的每一列。標記說明：{tag("sim")}{tag("inf")}{tag("asm")}{tag("std")}{tag("tbd")}。所有結果都是研究用的電腦模型，<b>不代表已驗證的火場呼吸防護能力</b>。</p>
  <div class="table-wrap"><table>
    <thead><tr><th scope="col">技術</th><th scope="col">判定</th><th scope="col">模擬依據</th><th scope="col">來源</th></tr></thead>
    <tbody>{verdict_rows()}</tbody></table></div>
  <div class="prose">{FIND["summary_html"]}</div>
</section>

<section id="method">
  <h2><span class="no">02</span>量測方法：每個數字怎麼來的</h2>
  <p class="prose">四組模擬各自回答一個問題。下面先說明共通的量測指標，再逐組列出模型、條件、量測位置、怎麼確認模型可信，以及它量不到的東西。</p>

  <div class="method">
    <h3>核心指標：供氣比例 SAF（Supply Air Fraction）</h3>
    <p class="prose">模擬裡把出風口送出的空氣「染色」：出風口空氣濃度設為 1，周圍空氣設為 0，讓這個無害的示蹤劑隨氣流移動、混合。口鼻位置量到的時間平均濃度，就是吸進去的空氣裡有多少比例來自出風口。</p>
    <div class="formula">SAF = 口鼻區示蹤劑濃度的時間平均（0～1）<br>例：SAF 60% → 吸入空氣 60% 來自出風口、40% 是周圍空氣</div>
    <p class="prose">把 SAF 和氣源一起看，就能算出口鼻區的污染濃度：</p>
    <div class="formula">C口鼻 = SAF × C供氣 + (1 − SAF) × C環境</div>
    <p class="prose">實驗室測試可以用同一個定義：在環境中釋放示蹤氣體（例如 CO₂），出風口送乾淨空氣，於假人口鼻處量測，<code>SAF = (C環境 − C口鼻) ÷ (C環境 − C供氣)</code>。模擬和實驗用同一把尺，之後才能互相對照。</p>
  </div>

  <h3>S2 噴嘴 CFD：模型設定</h3>
  <p class="prose">模擬的是垂直於扶手長軸的一個斷面（2D）。扶手上的連續出風縫在斷面上就是一道平面噴流，這也是選擇 2D 的理由。逃生者以低姿勢靠近扶手，臉部在出風口前 35 cm。</p>
  {SETUP_SVG}
  {fig("s2_geometry.png", "四種噴嘴的斷面幾何", "四種噴嘴的斷面。為了公平比較，四組每公尺出風口的供氣量都是 5 L/s，只有出口形狀與速度分布不同。", wide=True)}
  <div class="table-wrap"><table><thead><tr><th scope="col">項目</th><th scope="col">設定</th><th scope="col">性質</th></tr></thead><tbody>{params_rows()}</tbody></table></div>

  <div class="method">
    <h3>S2 怎麼確認模型可信</h3>
    <dl>
      <dt>求解器驗證</dt><dd>用同一支程式算平行板管流，跟解析解（拋物線速度分布）比對：{val_txt}。{tag("sim")}</dd>
      <dt>質量守恆</dt><dd>出口下游 3 cm 斷面的示蹤劑通量 ∫c·u dy 除以設定供氣量，16 個算例落在 {flux_txt}（1.00 為完全守恆）。{tag("sim")}</dd>
      <dt>時間收斂</dt><dd>呼吸區 SAF 的平均時段切成前後兩半各算一次，相差最多 {conv_txt}。差距越小，代表模擬時間夠長、平均值穩定。{tag("sim")}</dd>
      <dt>Bug 紀錄</dt><dd>第一次執行發現噴口入口密度逐步流失、噴流送不出去。已改成由下游鄰格外插密度的速度入口，全部重新計算；報告中的數字都來自修正後的版本。</dd>
    </dl>
  </div>
  {fig("val_poiseuille.png", "平行板管流驗證", "求解器驗證：平行板間的速度分布（點）與解析解（虛線）。")}
  {verify_table()}

  <div class="cols">
    <div class="card"><h4>S1 風道與風機（一維管網）</h4>
      <p>沿程損失用 Darcy–Weisbach 公式（層流 64/Re、紊流 Haaland 式），局部損失用 K·½ρV²，濾材壓損與風量成正比。風機用三條假設曲線，與系統阻力曲線求交點得到工作點。出風均勻度把 0.6 m 出風段切成 24 孔，從末端往上游逐孔計算壓力與流量。</p></div>
    <div class="card"><h4>S3 濾材與氣旋（分級效率）</h4>
      <p>煙粒徑用對數常態分布（有焰 CMD 0.10 µm、悶燒 0.30 µm，σg 1.9）{tag("asm")}。氣旋用 Lapple 模型，HEPA 用 EN 1822 H13 的最易穿透粒徑效率 99.95% 當全粒徑下限 {tag("std")}。各元件穿透率相乘後對粒徑分布積分。CO 不被機械濾材捕集。</p></div>
    <div class="card"><h4>S4 排煙容量（管流極限）</h4>
      <p>整棟 10 層共用一根 70 m 扶手風道，含 40 個彎頭、60 個接頭。分別以 20 °C 空氣和 200 °C 熱煙的物性計算，給定風機總壓 100–3000 Pa，用二分法求最大風量，與一扇敞開的門（0.9 × 2.0 m、1 m/s）的風量比較 {tag("asm")}。</p></div>
  </div>
</section>

<section id="nozzle">
  <h2><span class="no">03</span>噴嘴 CFD：誰能把乾淨空氣送到口鼻</h2>
  <div class="prose">{FIND["nozzle_html"]}</div>
  {fig("s2_saf_bars.png", "口鼻區供氣比例長條圖", "長條＝口鼻區 SAF 的時間平均；黑色短線＝最差 10% 時刻（第 10 百分位），代表氣流擺動時最不利的情況。", wide=True)}
  {saf_table()}
  {fig("s2_head_vc00_fields.png", "無側風時的平均供氣比例場", "無側風、臉在 35 cm：顏色越深代表出風口空氣比例越高；紅框是口鼻量測區；灰線是平均流線。", wide=True)}
  {fig("s2_head_vc15_fields.png", "側風 0.15 m/s 時的平均供氣比例場", "加入由下往上 0.15 m/s 的側風後，噴流被吹彎的程度。", wide=True)}
  {fig("s2_head_vc30_fields.png", "側風 0.30 m/s 時的平均供氣比例場", "側風 0.30 m/s。", wide=True)}
  {video("s2_head_vc15.mp4", "瞬時動畫（側風 0.15 m/s）：平均值看不到的擺動與渦旋。每格 0.08 秒。")}
  {fig("s2_free_fields.png", "自由噴流的平均供氣比例場", "自由噴流（沒有人、沒有側風）：用來看每種噴嘴本身的「乾淨空氣核心」能延伸多遠。", wide=True)}
  {fig("s2_decay.png", "自由噴流 SAF 隨距離衰減", "自由噴流各斷面的最高 SAF。氣流倍增式在 30 cm 處的總風量是供氣量的數倍，但多出來的都是被捲進來的周圍空氣。")}
  {video("s2_free.mp4", "自由噴流瞬時動畫。")}
</section>

<section id="source">
  <h2><span class="no">04</span>氣源：決定成敗的不是噴嘴</h2>
  <div class="prose">{FIND["source_html"]}</div>
  {fig("s2_exposure.png", "不同氣源下口鼻區 CO 相對環境濃度", "口鼻區 CO ÷ 環境 CO。紅：取樓梯間空氣經濾材後送出（CO 穿透 100%）；藍：獨立乾淨氣源（CO=0）。側風 0.15 m/s 的 SAF 代入上面的混合公式。", wide=True)}
</section>

<section id="filter">
  <h2><span class="no">05</span>濾材與氣旋</h2>
  <div class="prose">{FIND["filter_html"]}</div>
  {fig("s3_filtration.png", "分級效率與煙粒徑分布", "曲線＝各元件的捕集效率；灰色區塊＝兩種火災煙的質量粒徑分布（假設值）。", wide=True)}
  {filt_table()}
</section>

<section id="duct">
  <h2><span class="no">06</span>風道與風機</h2>
  <div class="prose">{FIND["duct_html"]}</div>
  {fig("s1_fan_system.png", "風機曲線與系統阻力", "三條風機曲線為假設值，需換成實際型錄曲線再算一次。紅色虛線為需求風量。")}
  {op_table()}
  {fig("s1_diameter.png", "風道壓損對內徑的敏感度", "內徑從 38 mm 縮到 30 mm，壓損約增加 2.5–3 倍。")}
  {fig("s1_uniformity.png", "出風均勻度", "左：均流板壓降與出風均勻度；右：沒有均流板時，空氣大多從出風段末端跑出去。", wide=True)}
</section>

<section id="exhaust">
  <h2><span class="no">07</span>扶手當排煙管：容量差兩個數量級</h2>
  <div class="prose">{FIND["exhaust_html"]}</div>
  {fig("s4_exhaust.png", "扶手排煙容量", "整棟一根扶手的最大可排風量。")}
</section>

<section id="limits">
  <h2><span class="no">08</span>限制與下一步</h2>
  <div class="prose">{FIND["limits_html"]}</div>
</section>

<footer>
  <p>模擬程式與原始資料：<code>stairwell-airflow-sim/</code>（git 分支 <code>claude/new-session-qe5tom</code>）。<code>solver/lbm2d.c</code> 為 CFD 求解器，<code>cases/build.py</code> 產生幾何，<code>analysis/</code> 為 S1–S4 計算與繪圖，<code>report/make_report.py</code> 產生本頁。</p>
  <p>本報告是設計研究用的電腦模擬，不是消防工程設計文件，也不是任何火場使用許可或安全認證。</p>
</footer>
</div>
"""

with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
    f.write(PAGE)
print("wrote", os.path.join(HERE, "index.html"), "CFD_DONE=", CFD_DONE)
