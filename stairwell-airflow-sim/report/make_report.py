"""
產生「扶手送風模擬報告」網頁：讀取 out/*.json 與圖檔，輸出 report/index.html 與 report/assets/。
寫法：每章先給一句話結論，再用圖解說明，數字放後面，技術細節收在可展開區塊。
CFD 尚未完成的項目會顯示「計算中」，重新執行即可更新。
"""
import html
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
ASSETS = os.path.join(HERE, "assets")
os.makedirs(ASSETS, exist_ok=True)
sys.path.insert(0, HERE)
import diagrams as D  # noqa: E402


def J(name):
    p = os.path.join(OUT, name)
    return json.load(open(p)) if os.path.exists(p) else None


s1, s2, s3, s4, val = (J("s1_results.json"), J("s2_results.json") or {}, J("s3_results.json"),
                       J("s4_results.json"), J("val_poiseuille.json"))

for f in os.listdir(OUT):
    if f.endswith((".png", ".mp4")) and not f.startswith(("_", "geom_check")):
        shutil.copy2(os.path.join(OUT, f), os.path.join(ASSETS, f))


# ---------------- 小工具 ----------------
def fig(name, alt, caption):
    dark = name.replace(".png", "_dark.png")
    if not os.path.exists(os.path.join(ASSETS, name)):
        return f'<figure class="fig"><div class="pending-box">計算中：{html.escape(alt)}</div><figcaption>{caption}</figcaption></figure>'
    if os.path.exists(os.path.join(ASSETS, dark)):
        imgs = (f'<img class="img-light" src="assets/{name}" alt="{html.escape(alt)}" loading="lazy">'
                f'<img class="img-dark" src="assets/{dark}" alt="{html.escape(alt)}" loading="lazy">')
    else:
        imgs = f'<img class="img-any" src="assets/{name}" alt="{html.escape(alt)}" loading="lazy">'
    return f'<figure class="fig">{imgs}<figcaption>{caption}</figcaption></figure>'


def video(name, caption):
    if not os.path.exists(os.path.join(ASSETS, name)):
        return f'<figure class="fig"><div class="pending-box">動畫計算中</div><figcaption>{caption}</figcaption></figure>'
    return (f'<figure class="fig"><video src="assets/{name}" controls muted loop playsinline preload="metadata"></video>'
            f'<figcaption>{caption}</figcaption></figure>')


def tag(kind):
    label = {"sim": "模擬結果", "inf": "工程推論", "asm": "假設值", "std": "外部標準", "tbd": "尚待驗證"}[kind]
    return f'<span class="tag tag-{kind}">{label}</span>'


def pct(x, d=0):
    return "—" if x is None else f"{x*100:.{d}f}%"


def graphic(svg, caption):
    return f'<figure class="fig">{svg}<figcaption>{caption}</figcaption></figure>'


def oneliner(text):
    return f'<p class="oneliner">{text}</p>'


def design_box(items):
    lis = "".join(f"<li>{i}</li>" for i in items)
    return f'<aside class="design"><h4>對設計的意思</h4><ul>{lis}</ul></aside>'


def details(summary, body):
    return f'<details class="more"><summary>{summary}</summary><div class="more-body">{body}</div></details>'


NZ = ["plain", "coanda", "coax", "amp"]
NZ_LABEL = {"plain": "A 一般定向噴嘴", "coanda": "B 康達曲面導流", "coax": "C 低混合率同軸噴嘴", "amp": "D 氣流倍增式"}
CONDS = [("head_vc00", "無側風"), ("head_vc15", "側風 0.15 m/s"), ("head_vc30", "側風 0.30 m/s")]
CFD_DONE = all(f"{nz}_{c}" in s2 for nz in NZ for c, _ in CONDS)


def saf(nz, cond, key="mean"):
    r = s2.get(f"{nz}_{cond}")
    return None if r is None else r[key]


# ---------------- 表格 ----------------
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
    head = "".join(f'<th scope="col">{l}</th>' for _, l in CONDS)
    return (f'<div class="table-wrap"><table><thead><tr><th scope="col">出風口</th>{head}'
            f'<th scope="col">30 cm 處總風量 ÷ 送出風量</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def verify_table():
    if not s2:
        return '<p class="muted">CFD 計算中，完成後自動填入。</p>'
    rows = "".join(f'<tr><th scope="row">{n}</th><td class="num">{r["supply_flux_ratio"]:.2f}</td>'
                   f'<td class="num">{pct(r["first_half"],1)} / {pct(r["second_half"],1)}</td></tr>' for n, r in sorted(s2.items()))
    return ('<div class="table-wrap"><table><thead><tr><th scope="col">算例</th><th scope="col">出口通量 ÷ 設定送風量</th>'
            '<th scope="col">口鼻乾淨空氣比例：前半段 / 後半段</th></tr></thead><tbody>' + rows + "</tbody></table></div>")


def op_table():
    rows = []
    for r in s1["operating_points"]:
        if r["D_mm"] != 34:
            continue
        ok = '<span class="pill ok">夠</span>' if r["meets"] else '<span class="pill bad">不夠</span>'
        rows.append(f'<tr><th scope="row">{r["fan"].split("（")[0]}</th><td>{r["filter"]}</td><td class="num">{r["Q_Ls"]:.1f}</td>'
                    f'<td class="num">{r["dP_Pa"]:.0f}</td><td class="num">{r["outlet_m"]:.2f}</td><td class="num">{r["P_elec_W"]:.0f}</td><td>{ok}</td></tr>')
    return ('<div class="table-wrap"><table><thead><tr><th scope="col">風機</th><th scope="col">濾網狀態</th><th scope="col">風量 L/s</th>'
            '<th scope="col">壓力 Pa</th><th scope="col">能供多長出風口 m</th><th scope="col">耗電約 W</th><th scope="col">需要 6 L/s</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def filt_table():
    rows = "".join(f'<tr><td>{r["smoke"].split("（")[0]}</td><td>{r["train"]}</td><td class="num">{pct(r["removal_mass"],1)}</td>'
                   f'<td class="num">0%</td></tr>' for r in s3["particle_removal"])
    return ('<div class="table-wrap"><table><thead><tr><th scope="col">煙的種類</th><th scope="col">處理方式</th>'
            '<th scope="col">煙粒擋下多少（重量）</th><th scope="col">CO 擋下多少</th></tr></thead><tbody>' + rows + "</tbody></table></div>")


PARAMS = [
    ("網格", "1 mm 正方格，640 × 400 ＝ 25.6 萬格", "asm"),
    ("流場方法", "D2Q9 格子波茲曼法（LBM），正則化碰撞＋Smagorinsky 大渦模擬（Cs = 0.17）", "inf"),
    ("示蹤劑", "有限體積 MUSCL（minmod 限制器），對流形式 u·∇c＋擴散；分子擴散 2×10⁻⁵ m²/s，紊流擴散＝渦黏度/0.7", "inf"),
    ("空氣", "20 °C，動黏度 1.5×10⁻⁵ m²/s，等溫、不含浮力", "asm"),
    ("送風量", "每公尺出風口 5 L/s（四種出風口相同，公平比較）", "asm"),
    ("模擬時間", "10 秒（同軸組 16 秒，因為氣流慢），前 3 秒（同軸組 4 秒）為暖機不列入平均", "asm"),
    ("時間步長", "依各組最高速度換算，格子速度上限 0.1（控制壓縮性誤差）", "inf"),
    ("邊界", "四周開放＋ 2.5 cm 吸收層（提高黏度並往遠場狀態鬆弛，避免渦旋與壓力波反射）；側風由下邊界均勻送入", "inf"),
    ("固體", "半格反彈（halfway bounce-back）：扶手、噴嘴壁、頭部", "inf"),
    ("取樣", "口鼻區方框每 0.01 秒記錄一次平均濃度", "asm"),
]


def params_table():
    rows = "".join(f'<tr><th scope="row">{k}</th><td>{v}</td><td>{tag(t)}</td></tr>' for k, v, t in PARAMS)
    return f'<div class="table-wrap"><table><thead><tr><th scope="col">項目</th><th scope="col">設定</th><th scope="col">性質</th></tr></thead><tbody>{rows}</tbody></table></div>'


SETUP_SVG = """
<svg class="graphic" viewBox="0 0 760 500" role="img" aria-label="電腦模型的剖面：左邊是扶手和出風口，右邊 35 公分處是頭，口鼻前方有量測框">
  <defs>
    <marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="g-accent-fill"/></marker>
    <marker id="ah2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="g-muted-fill"/></marker>
  </defs>
  <rect x="60" y="40" width="640" height="400" class="g-domain"/>
  <rect x="85" y="65" width="590" height="350" class="g-sponge"/>
  <text x="90" y="82" class="g-s">邊緣 2.5 cm 是「吸收層」：讓氣流自然離開，不會反彈回來</text>
  <circle cx="98" cy="240" r="25" class="g-solid"/>
  <rect x="115" y="236" width="25" height="8" class="g-solid"/>
  <text x="70" y="290" class="g-t">扶手 Ø50 mm</text>
  <text x="70" y="306" class="g-t">＋出風口（4 種）</text>
  <line x1="142" y1="240" x2="402" y2="240" class="g-arrow-ok" marker-end="url(#ah)"/>
  <text x="190" y="230" class="g-t">送風：每公尺出風口 5 L/s</text>
  <circle cx="490" cy="240" r="80" class="g-head"/>
  <text x="490" y="236" text-anchor="middle" class="g-t">頭</text>
  <text x="490" y="254" text-anchor="middle" class="g-s">直徑 16 cm</text>
  <rect x="385" y="228" width="20" height="24" class="g-probe"/>
  <line x1="395" y1="226" x2="395" y2="180" class="g-leader"/>
  <text x="395" y="172" text-anchor="middle" class="g-t">口鼻量測框</text>
  <text x="395" y="156" text-anchor="middle" class="g-s">臉前 0.5–2.5 cm</text>
  <line x1="140" y1="120" x2="410" y2="120" class="g-leader"/>
  <line x1="140" y1="112" x2="140" y2="128" class="g-leader"/><line x1="410" y1="112" x2="410" y2="128" class="g-leader"/>
  <text x="275" y="110" text-anchor="middle" class="g-t">35 cm（低姿勢，臉靠近扶手）</text>
  <g class="g-cross">
    <line x1="230" y1="470" x2="230" y2="420" marker-end="url(#ah2)"/>
    <line x1="380" y1="470" x2="380" y2="420" marker-end="url(#ah2)"/>
    <line x1="530" y1="470" x2="530" y2="420" marker-end="url(#ah2)"/>
  </g>
  <text x="560" y="462" class="g-t">側風：0／0.15／0.30 m/s</text>
  <text x="560" y="478" class="g-s">代表樓梯間的上升氣流、人走動的擾動</text>
  <text x="60" y="30" class="g-s">模型範圍 64 × 40 cm 的剖面，切成 1 mm 小格（共 25.6 萬格）</text>
</svg>"""

from findings import build_findings  # noqa: E402

FIND = build_findings(dict(s1=s1, s2=s2, s3=s3, s4=s4, saf=saf, pct=pct, tag=tag, CFD_DONE=CFD_DONE, NZ_LABEL=NZ_LABEL))

val_txt = (f"速度分布和解析解差 {val['L2_rel_error']*100:.1f}%，流量差 {abs(val['flux_ratio']-1)*100:.1f}%" if val else "計算中")
flux_vals = [r["supply_flux_ratio"] for r in s2.values()]
flux_txt = f"{min(flux_vals):.2f}–{max(flux_vals):.2f}" if flux_vals else "計算中"
conv_vals = [abs(r["first_half"] - r["second_half"]) for k, r in s2.items() if "head" in k]
conv_txt = f"{max(conv_vals)*100:.1f} 個百分點" if conv_vals else "計算中"
status_note = "" if CFD_DONE else '<p class="banner">出風口的電腦模擬（CFD）還在計算，標示「計算中」的地方完成後會更新。</p>'

cards = "".join(
    f'<article class="tcard"><div class="tcard-top"><h3>{c["name"]}</h3><span class="pill {c["cls"]}">{c["verdict"]}</span></div>'
    f'<p>{c["why"]}</p><span class="tsrc">{c["where"]}</span></article>' for c in FIND["cards"])
takeaways = "".join(
    f'<div class="take"><div class="big">{t["big"]}</div><p>{t["text"]}</p></div>' for t in FIND["takeaways"])

method_tech = (
    "<h4>電腦模型的設定</h4>" + params_table() +
    f"""<h4>怎麼確認模型算得對</h4>
<ul>
<li><b>先考一題有標準答案的：</b>用同一支程式算「兩片平板之間的氣流」，這題有數學解答。結果{val_txt}。{tag("sim")}</li>
<li><b>空氣有沒有憑空消失：</b>出風口外 1 mm 量到的送風量，除以設定的送風量，16 組落在 {flux_txt}（1.00 代表完全吻合）。{tag("sim")}</li>
<li><b>算得夠不夠久：</b>把平均時段切成前後兩半各算一次，差距最多 {conv_txt}。差距小代表數字已經穩定。{tag("sim")}</li>
</ul>""" + fig("val_poiseuille.png", "平板間氣流的驗證", "考題：兩片平板之間的速度分布。點＝本程式，虛線＝數學解答。") + verify_table() +
    """<h4>計算途中發現並修正的問題</h4>
<p>每次修正後都全部重新計算，報告裡的數字都來自最後的版本。</p>
<ol>
<li>出風口的設定會讓空氣慢慢「漏掉」，風送不出去 → 改寫出風口的計算方式。</li>
<li>氣流倍增式原本 2 mm 的細縫只有 2 小格，計算爆掉 → 細縫改成 3 mm（總送風量不變）。</li>
<li>出風口通道內的「染色」濃度會自己慢慢變淡 → 改用不會漂移的寫法，通道內維持 100%。</li>
<li>模型邊緣會把渦旋反彈回來，康達組計算爆掉 → 邊緣加上吸收層。修正後考題誤差從 2.3% 降到 0.45%。</li>
<li>康達第一版曲面太彎，氣流不轉彎（這是物理結果，不是程式錯誤）→ 保留結果當設計教訓，另做修正版比較。</li>
</ol>
<h4>其他三組模擬怎麼算</h4>
<div class="cols">
<div class="card"><h5>風機與扶手管子</h5><p>用管路公式計算風在扶手管子裡被擋掉多少力氣（直管摩擦＋彎頭、接頭、濾網），和風機的能力曲線找交點，就是實際風量。出風均勻度把 0.6 m 出風段切成 24 個小孔逐一計算。</p></div>
<div class="card"><h5>濾網與氣旋</h5><p>假設火災煙粒的大小分布（有焰燃燒、悶燒兩種）{}，乘上氣旋、初濾、HEPA 各自「每種大小抓得到幾成」，加總得到總共擋下多少。HEPA 用 EN 1822 H13 的定義 {}。</p></div>
<div class="card"><h5>扶手排煙容量</h5><p>假設整棟 10 層共用一根 70 m 的扶手管子（40 個彎、60 個接頭），用 20 °C 空氣和 200 °C 熱煙分別計算，風機推力從 100 加到 3000 Pa，看最多能排多少，再和一扇敞開的門比較 {}。</p></div>
</div>""".format(tag("asm"), tag("std"), tag("asm")))

CSS = open(os.path.join(HERE, "style.css"), encoding="utf-8").read()

PAGE = f"""<title>扶手送風模擬報告</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Noto+Sans+TC:wght@400;500;700;900&display=swap">
<style>
{CSS}
</style>

<div class="wrap">
<header class="top">
  <div class="eyebrow">樓梯逃生導引扶手系統｜第二階段送風研究</div>
  <h1>扶手送風模擬報告</h1>
  <p class="question">扶手送風，到底能不能讓低姿勢逃生的人吸到比較乾淨的空氣？用電腦模擬一項一項檢查。</p>
  <div class="meta"><span>日期 <b>2026-10-19</b></span><span>專案 <b>長庚大學工業設計學系 林煜宸</b></span><span>模擬與撰寫 <b>Claude（AI）</b></span></div>
  {status_note}
</header>
<nav class="toc" aria-label="章節">
  <a href="#summary">一頁看懂</a><a href="#method">怎麼測的</a><a href="#nozzle">四種出風口</a><a href="#source">空氣從哪來</a>
  <a href="#filter">濾網擋什麼</a><a href="#duct">風機與管子</a><a href="#exhaust">能不能排煙</a><a href="#next">下一步</a>
</nav>

<section id="summary">
  <h2><span class="no">00</span>一頁看懂</h2>
  <div class="takes">{takeaways}</div>
  <h3>每項技術的判定</h3>
  <div class="tcards">{cards}</div>
  <div class="gloss">
    <h3>名詞小抄</h3>
    <dl>
      <dt>乾淨空氣比例</dt><dd>吸進去的空氣裡，有幾成是出風口送出來的。報告裡最重要的數字（英文 SAF）。</dd>
      <dt>側風</dt><dd>樓梯間本來就有的氣流，例如熱煙往上升、人走過帶動的風。</dd>
      <dt>壓損</dt><dd>風在管子、濾網裡被擋掉的力氣，單位 Pa。越大，風機要越用力。</dd>
      <dt>均流層</dt><dd>出風口內的一層多孔板或網子，讓每一段出風口出一樣多的風。</dd>
      <dt>CO</dt><dd>一氧化碳，火災中最主要的致命氣體之一。是氣體分子，濾網擋不住。</dd>
      <dt>µm（微米）</dt><dd>千分之一毫米。頭髮大約 70 µm，火災煙粒大多不到 1 µm。</dd>
    </dl>
  </div>
  <p class="prose muted">標記：{tag("sim")}電腦算出來的　{tag("inf")}依原理推論　{tag("asm")}先假設的數字　{tag("std")}引用標準定義　{tag("tbd")}要再查證或實驗。所有結果都是研究用的電腦模型，<b>不代表已驗證的火場呼吸防護能力</b>。</p>
</section>

<section id="method">
  <h2><span class="no">01</span>怎麼測的</h2>
  {oneliner("在電腦裡做一個扶手和人頭的剖面，把出風口送出的空氣「染色」，看它有幾成能跑到臉前。")}
  {graphic(D.saf_explainer(), "乾淨空氣從出風口出來後，一路把周圍空氣拉進來混合。到口鼻時剩下的比例，就是「乾淨空氣比例」。")}
  <div class="points prose">
    <p>為什麼不能只看出風口？因為出風口的空氣再乾淨，走到臉前時也已經混進周圍的空氣。所以這份報告<b>只看口鼻位置</b>量到的比例。</p>
    <p>有了這個比例，口鼻吸到的污染就能直接算：</p>
  </div>
  <div class="formula">口鼻的污染 ＝ 乾淨空氣比例 × 送出空氣的污染 ＋（1 − 乾淨空氣比例）× 周圍的污染</div>
  {graphic(SETUP_SVG, "電腦模型：扶手剖面在左，逃生者低姿勢時臉在出風口前 35 cm。紅框是量測口鼻的位置。")}
  {fig("s2_geometry.png", "四種出風口的剖面", "四種出風口。為了公平，每一種每公尺都送出一樣多的風（5 L/s），只有形狀不同。")}
  <div class="points prose">
    <p><b>電腦裡做了這些事：</b></p>
    <ul>
      <li>把 64 × 40 cm 的剖面切成 25.6 萬個 1 mm 小格，逐格計算空氣怎麼流動。</li>
      <li>出風口的空氣濃度設成 100%，周圍空氣設成 0%，讓這個「顏色」跟著氣流跑。</li>
      <li>每 0.01 秒記錄一次口鼻框裡的濃度，算 10 秒（慢的同軸組算 16 秒），前 3–4 秒不算，取後面的平均。</li>
      <li>4 種出風口 × 4 種情況（沒有人、有人無側風、側風 0.15、側風 0.30）＝ 16 組。</li>
    </ul>
    <p>實體實驗可以用一模一樣的方法量：在箱子裡放 CO₂ 當作「煙」，出風口送乾淨空氣，在頭模型口鼻處量 CO₂。電腦和實驗用同一把尺，之後才能互相對照（見第 07 章）。</p>
  </div>
  {details("展開技術細節：模型設定、驗證方法、修正紀錄", method_tech)}
</section>

<section id="nozzle">
  <h2><span class="no">02</span>四種出風口比一比</h2>
  {oneliner(FIND["nozzle_one"])}
  {fig("s2_saf_bars.png", "四種出風口在三種側風下的乾淨空氣比例", "每條橫條代表 100% 的吸入空氣，彩色部分是來自出風口的乾淨空氣。黑色短線是最差 10% 的時刻（氣流晃開的瞬間）。")}
  <div class="points prose">{FIND["nozzle_points"]}</div>
  {fig("s2_head_vc00_fields.png", "無側風時的平均乾淨空氣分布", "無側風時，平均下乾淨空氣分布在哪裡。顏色越深，代表出風口的空氣越多；灰色細線是平均氣流方向。")}
  {fig("s2_head_vc15_fields.png", "側風 0.15 m/s 時的平均乾淨空氣分布", "加上由下往上 0.15 m/s 的側風（大約是人慢慢走過帶起的風），送出的空氣被吹彎。")}
  {video("s2_head_vc15.mp4", "動畫（側風 0.15 m/s）：平均圖看不到的晃動與渦旋。每格 0.08 秒。")}
  <h3>康達曲面的教訓</h3>
  {graphic(D.coanda_lesson(), "示意圖：曲面半徑和出風縫寬度的比例，決定氣流會不會沿曲面轉彎。")}
  {fig("s2_coanda_lesson.png", "康達第一版與修正版的模擬比較", "實際模擬：第一版 R15 和修正版 R45（無側風）。")}
  <div class="points prose">{FIND["coanda_points"]}</div>
  {design_box(FIND["nozzle_design"])}
  {details("展開更多圖：側風 0.30 m/s、沒有人時的氣流、完整數字表",
           fig("s2_head_vc30_fields.png", "側風 0.30 m/s", "側風 0.30 m/s 時的平均分布。") +
           fig("s2_free_fields.png", "自由噴流", "沒有人、沒有側風時，每種出風口本身的氣流能走多遠。") +
           fig("s2_decay.png", "乾淨空氣隨距離衰減", "沒有人、沒有側風時，各距離最乾淨的位置。") +
           video("s2_free.mp4", "動畫：沒有人、沒有側風。") + saf_table())}
</section>

<section id="source">
  <h2><span class="no">03</span>空氣從哪裡來，比出風口更重要</h2>
  {oneliner("吸樓梯間的空氣過濾後再送出，口鼻的 CO 一點都不會少。只有獨立的乾淨氣源才有用。")}
  {graphic(D.source_compare(FIND["saf_example"]), "濾網只擋得住煙粒，擋不住 CO。送出去的空氣如果本來就含 CO，再好的出風口也沒用。")}
  {fig("s2_exposure.png", "兩種氣源下口鼻的 CO", "口鼻 CO ÷ 周圍 CO。紅：吸樓梯間空氣＋濾網；藍：獨立乾淨氣源。用側風 0.15 m/s 的乾淨空氣比例代入公式計算。")}
  <div class="points prose">{FIND["source_points"]}</div>
  {design_box(FIND["source_design"])}
</section>

<section id="filter">
  <h2><span class="no">04</span>濾網能擋什麼</h2>
  {oneliner("HEPA 擋得住煙粒，擋不住 CO。氣旋連煙粒都抓不到，不採用。")}
  {graphic(D.size_ruler(s3["cyclone"]["d50_um"]), "火災煙粒比氣旋能抓的大小小了好幾倍；HEPA 則整段都抓得到。")}
  {fig("s3_filtration.png", "各種過濾方式能抓到的粒子大小", "曲線：每種方式對各種大小的粒子抓得到幾成。灰色山形：兩種火災煙的粒子大小分布（假設值）。")}
  {filt_table()}
  <div class="points prose">{FIND["filter_points"]}</div>
  {design_box(FIND["filter_design"])}
</section>

<section id="duct">
  <h2><span class="no">05</span>風機與扶手管子</h2>
  {oneliner(FIND["duct_one"])}
  {graphic(D.stair_layout(), "建議配置：每層平台一台主機，出風口集中在平台附近，其他扶手只負責導引。")}
  {fig("s1_fan_system.png", "風機與阻力曲線", "黑線是三種風機（假設值）的能力，彩色線是管子＋濾網的阻力。交點就是實際能送出的風量；紅色虛線是需要的 6 L/s。")}
  {graphic(D.uniformity(s1["uniformity"]["34mm"]["2.0"], s1["uniformity"]["34mm"]["30.0"], 2, 30), "出風口裡沒有均流層時，風會擠到末端才衝出來。")}
  {fig("s1_uniformity.png", "均流層與出風均勻度", "左：均流層阻力越大，出風越平均。右：沒有均流層（2 Pa）和有均流層（30 Pa）時，每一段出風口的出風量。")}
  <div class="points prose">{FIND["duct_points"]}</div>
  {design_box(FIND["duct_design"])}
  {details("展開更多：管子粗細的影響、各風機工作點表", fig("s1_diameter.png", "管徑與壓損", "內徑從 38 mm 縮到 30 mm，阻力大約變成 2.5–3 倍。") + op_table())}
</section>

<section id="exhaust">
  <h2><span class="no">06</span>扶手能不能拿來排煙</h2>
  {oneliner(FIND["exhaust_one"])}
  {graphic(D.exhaust_scale(FIND["door_m3min"], FIND["rail_m3min"]), "一扇敞開的門和扶手排煙量的比較。")}
  {fig("s4_exhaust.png", "扶手排煙容量", "整棟一根扶手（70 m）在不同風機推力下最多能排多少。")}
  <div class="points prose">{FIND["exhaust_points"]}</div>
  {design_box(FIND["exhaust_design"])}
</section>

<section id="next">
  <h2><span class="no">07</span>還不知道的事，和下一步</h2>
  {oneliner("電腦模擬適合用來比較和排除方案，真正的效果要靠實驗確認。")}
  <div class="points prose">{FIND["limits_points"]}</div>
  {graphic(D.test_rig(), "建議的桌上型實驗：用 CO₂ 當作「煙」，量頭模型口鼻處的濃度，用和電腦相同的方法算乾淨空氣比例。")}
  <div class="points prose">{FIND["next_points"]}</div>
</section>

<footer>
  <p>模擬程式與原始資料：<code>stairwell-airflow-sim/</code>（git 分支 <code>claude/new-session-qe5tom</code>）。<code>solver/lbm2d.c</code> 是 CFD 程式，<code>cases/build.py</code> 產生出風口形狀，<code>analysis/</code> 是各項計算與畫圖，<code>report/</code> 產生本頁。</p>
  <p>本報告是設計研究用的電腦模擬，不是消防工程設計文件，也不是任何火場使用許可或安全認證。</p>
</footer>
</div>
"""

with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
    f.write(PAGE)
print("wrote", os.path.join(HERE, "index.html"), "CFD_DONE=", CFD_DONE)
