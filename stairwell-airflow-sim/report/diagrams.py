"""報告用的圖解（inline SVG，顏色全部走 CSS 變數，深淺色主題自動切換）。"""
import math

ARROW_DEFS = """
<defs>
  <marker id="{id}a" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="g-accent-fill"/></marker>
  <marker id="{id}m" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="g-muted-fill"/></marker>
  <marker id="{id}c" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="g-crit-fill"/></marker>
</defs>"""


def defs(i):
    return ARROW_DEFS.format(id=i)


def saf_explainer():
    """乾淨空氣比例（SAF）是什麼。"""
    return f"""
<svg class="graphic" viewBox="0 0 760 290" role="img" aria-label="出風口送出的乾淨空氣一路上把周圍空氣拉進來混合，吸到口鼻時只剩一部分是乾淨空氣">
{defs("s")}
  <circle cx="70" cy="140" r="28" class="g-solid"/>
  <rect x="94" y="135" width="22" height="10" class="g-solid"/>
  <text x="70" y="196" text-anchor="middle" class="g-t">扶手出風口</text>
  <path d="M116,137 C220,128 330,105 430,92 L430,188 C330,175 220,152 116,143 Z" class="g-plume"/>
  <path d="M116,140 C200,139 260,138 300,140" class="g-core"/>
  <text x="122" y="116" class="g-s">剛出口：100% 乾淨</text>
  <g class="g-entrain">
    <path d="M262,36 C270,72 282,98 296,118" marker-end="url(#sm)"/>
    <path d="M370,30 C374,62 382,84 394,104" marker-end="url(#sm)"/>
    <path d="M262,252 C270,212 282,186 296,162" marker-end="url(#sm)"/>
    <path d="M370,262 C374,222 382,200 394,180" marker-end="url(#sm)"/>
  </g>
  <text x="330" y="22" text-anchor="middle" class="g-t">周圍空氣一路被拉進來混合</text>
  <circle cx="520" cy="140" r="64" class="g-head"/>
  <rect x="440" y="128" width="16" height="24" class="g-probe"/>
  <text x="520" y="146" text-anchor="middle" class="g-s">頭</text>
  <text x="448" y="228" text-anchor="middle" class="g-s">口鼻</text>
  <line x1="448" y1="156" x2="448" y2="214" class="g-leader"/>
  <rect x="630" y="50" width="54" height="180" rx="4" class="g-amb"/>
  <rect x="630" y="158" width="54" height="72" rx="4" class="g-clean"/>
  <text x="657" y="200" text-anchor="middle" class="g-on">40%</text>
  <text x="657" y="110" text-anchor="middle" class="g-t">60%</text>
  <text x="692" y="198" class="g-s">出風口</text>
  <text x="692" y="214" class="g-s">的空氣</text>
  <text x="692" y="106" class="g-s">周圍</text>
  <text x="692" y="122" class="g-s">空氣</text>
  <text x="657" y="38" text-anchor="middle" class="g-t">吸進去的空氣</text>
  <text x="657" y="256" text-anchor="middle" class="g-b">乾淨空氣比例 40%</text>
  <text x="657" y="274" text-anchor="middle" class="g-s">（示意數字）</text>
</svg>"""


def source_compare(saf_example):
    """兩種氣源：取樓梯間空氣過濾 vs 獨立乾淨氣源。"""
    pct_left = round((1 - saf_example) * 100)

    def dots(x, y, n_smoke, n_co):
        out = []
        for k in range(n_smoke):
            out.append(f'<circle cx="{x + (k % 4) * 13}" cy="{y + (k // 4) * 13}" r="4.2" class="g-smoke"/>')
        for k in range(n_co):
            out.append(f'<circle cx="{x + (k % 4) * 13}" cy="{y + 30 + (k // 4) * 13}" r="4.2" class="g-co"/>')
        return "".join(out)

    return f"""
<svg class="graphic" viewBox="0 0 800 330" role="img" aria-label="取樓梯間空氣經濾網後，煙粒被擋下但一氧化碳全部穿過；獨立乾淨氣源才真的降低一氧化碳">
{defs("q")}
  <text x="20" y="28" class="g-b">A　吸樓梯間的空氣，過濾後送出</text>
  <rect x="20" y="44" width="150" height="96" rx="8" class="g-box"/>
  <text x="95" y="64" text-anchor="middle" class="g-t">樓梯間空氣</text>
  {dots(48, 78, 8, 4)}
  <line x1="172" y1="92" x2="222" y2="92" class="g-arrow" marker-end="url(#qm)"/>
  <rect x="226" y="44" width="110" height="96" rx="8" class="g-filter"/>
  <text x="281" y="64" text-anchor="middle" class="g-t">濾網</text>
  <text x="281" y="86" text-anchor="middle" class="g-s">擋下煙粒</text>
  <text x="281" y="104" text-anchor="middle" class="g-s">CO 穿過去</text>
  <line x1="338" y1="92" x2="388" y2="92" class="g-arrow" marker-end="url(#qm)"/>
  <rect x="392" y="44" width="150" height="96" rx="8" class="g-box"/>
  <text x="467" y="64" text-anchor="middle" class="g-t">送出的空氣</text>
  {"".join(f'<circle cx="{448 + k * 13}" cy="98" r="4.2" class="g-co"/>' for k in range(4))}
  <text x="467" y="124" text-anchor="middle" class="g-s">煙粒沒了，CO 還在</text>
  <line x1="544" y1="92" x2="594" y2="92" class="g-arrow" marker-end="url(#qm)"/>
  <circle cx="640" cy="92" r="40" class="g-head"/>
  <text x="640" y="98" text-anchor="middle" class="g-t">口鼻</text>
  <text x="690" y="84" class="g-crit-t">CO 100%</text>
  <text x="690" y="102" class="g-s">一點都沒少</text>

  <text x="20" y="196" class="g-b">B　獨立乾淨氣源（室外進氣、壓縮空氣）</text>
  <rect x="20" y="212" width="150" height="96" rx="8" class="g-box g-box-ok"/>
  <text x="95" y="232" text-anchor="middle" class="g-t">乾淨空氣</text>
  <text x="95" y="262" text-anchor="middle" class="g-s">沒有煙粒、沒有 CO</text>
  <line x1="172" y1="260" x2="388" y2="260" class="g-arrow-ok" marker-end="url(#qa)"/>
  <text x="280" y="250" text-anchor="middle" class="g-s">經扶手出風口送出</text>
  <rect x="392" y="212" width="150" height="96" rx="8" class="g-box"/>
  <text x="467" y="232" text-anchor="middle" class="g-t">到口鼻時</text>
  <text x="467" y="258" text-anchor="middle" class="g-s">混進一些周圍空氣</text>
  <text x="467" y="278" text-anchor="middle" class="g-s">（多少由出風口決定）</text>
  <line x1="544" y1="260" x2="594" y2="260" class="g-arrow-ok" marker-end="url(#qa)"/>
  <circle cx="640" cy="260" r="40" class="g-head"/>
  <text x="640" y="266" text-anchor="middle" class="g-t">口鼻</text>
  <text x="690" y="252" class="g-ok-t">CO {pct_left}%</text>
  <text x="690" y="270" class="g-s">降低的比例</text>
  <text x="690" y="286" class="g-s">＝乾淨空氣比例</text>
  <circle cx="30" cy="322" r="4.2" class="g-smoke"/><text x="40" y="326" class="g-s">煙粒</text>
  <circle cx="90" cy="322" r="4.2" class="g-co"/><text x="100" y="326" class="g-s">一氧化碳（CO）分子</text>
</svg>"""


def size_ruler(d50):
    """粒徑尺：火災煙粒、PM2.5、氣旋切割粒徑、頭髮。"""
    x0, w = 70, 620

    def X(d):
        return x0 + (math.log10(d) + 2) / 4.0 * w   # 0.01 µm – 100 µm
    ticks = "".join(
        f'<line x1="{X(v):.1f}" y1="150" x2="{X(v):.1f}" y2="158" class="g-leader"/>'
        f'<text x="{X(v):.1f}" y="176" text-anchor="middle" class="g-s">{lbl}</text>'
        for v, lbl in [(0.01, "0.01"), (0.1, "0.1"), (1, "1"), (10, "10"), (100, "100 µm")])
    return f"""
<svg class="graphic" viewBox="0 0 760 230" role="img" aria-label="火災煙粒大多在 0.05 到 1 微米之間，比氣旋能抓的大小還小很多">
  <rect x="{X(0.05):.1f}" y="70" width="{X(1)-X(0.05):.1f}" height="70" rx="6" class="g-smokeband"/>
  <text x="{(X(0.05)+X(1))/2:.1f}" y="98" text-anchor="middle" class="g-t">火災煙粒大多在這裡</text>
  <text x="{(X(0.05)+X(1))/2:.1f}" y="118" text-anchor="middle" class="g-s">約 0.05–1 µm</text>
  <line x1="{x0}" y1="150" x2="{x0+w}" y2="150" class="g-axis"/>
  {ticks}
  <line x1="{X(d50):.1f}" y1="40" x2="{X(d50):.1f}" y2="150" class="g-crit-line"/>
  <text x="{X(d50)+6:.1f}" y="52" class="g-crit-t">氣旋：{d50:.1f} µm</text>
  <text x="{X(d50)+6:.1f}" y="68" class="g-s">比這小的大多抓不到</text>
  <line x1="{X(2.5):.1f}" y1="150" x2="{X(2.5):.1f}" y2="196" class="g-leader"/>
  <text x="{X(2.5):.1f}" y="212" text-anchor="middle" class="g-s">PM2.5 的 2.5 µm</text>
  <line x1="{X(70):.1f}" y1="150" x2="{X(70):.1f}" y2="196" class="g-leader"/>
  <text x="{X(70):.1f}" y="212" text-anchor="middle" class="g-s">頭髮粗細 約 70 µm</text>
  <rect x="{x0}" y="18" width="{X(0.3)-x0-8:.1f}" height="24" rx="4" class="g-okband"/>
  <text x="{x0+8}" y="35" class="g-s">HEPA：整段都抓得到（≥ 99.95%）</text>
</svg>"""


def uniformity(u_low, u_high, dp_low, dp_high):
    """出風均勻度：沒有均流層 vs 有均流層。"""
    def row(y, lens, label, sub):
        arrows = []
        for k, L in enumerate(lens):
            x = 150 + k * 62
            arrows.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y - L:.0f}" class="g-arrow-ok" marker-end="url(#ua)"/>')
        return (f'<rect x="120" y="{y}" width="540" height="14" rx="7" class="g-solid"/>'
                + "".join(arrows)
                + f'<text x="20" y="{y - 30}" class="g-t">{label}</text><text x="20" y="{y - 12}" class="g-s">{sub}</text>')
    n = 9
    low = [14 + (66 - 14) * (k / (n - 1)) ** 1.6 for k in range(n)]
    high = [40 + 3 * (k / (n - 1)) for k in range(n)]
    return f"""
<svg class="graphic" viewBox="0 0 760 250" role="img" aria-label="沒有均流層時空氣大多從出風段末端衝出，加上均流層後每一段出風量接近">
{defs("u")}
  {row(110, low, "沒有均流層", f"最少只有最多的 {u_low*100:.0f}%")}
  {row(220, high, "加一層均流層", f"約 {dp_high:.0f} Pa，均勻度 {u_high*100:.0f}%")}
  <text x="120" y="134" class="g-s">← 風從主機這端進來</text>
  <text x="660" y="134" text-anchor="end" class="g-s">出風段末端 →</text>
  <text x="690" y="70" class="g-s">空氣擠到</text>
  <text x="690" y="86" class="g-s">末端衝出</text>
</svg>"""


def exhaust_scale(door_m3min, rail_m3min):
    """一扇門 vs 一根扶手的排風量。"""
    n = round(door_m3min / rail_m3min)
    dots = []
    cols = 25
    for k in range(n):
        x = 330 + (k % cols) * 15
        y = 60 + (k // cols) * 15
        dots.append(f'<circle cx="{x}" cy="{y}" r="4.5" class="g-raildot"/>')
    rows = math.ceil(n / cols)
    return f"""
<svg class="graphic" viewBox="0 0 760 {max(240, 80 + rows * 15 + 40)}" role="img" aria-label="一扇敞開的門的風量相當於約 {n} 根扶手同時全力排煙">
  <rect x="40" y="40" width="90" height="180" rx="3" class="g-door"/>
  <text x="85" y="134" text-anchor="middle" class="g-t">門</text>
  <text x="85" y="238" text-anchor="middle" class="g-s">0.9 × 2.0 m</text>
  <text x="150" y="110" class="g-b">≈ {door_m3min:.0f} m³/min</text>
  <text x="150" y="130" class="g-s">（風速 1 m/s 時）</text>
  <text x="330" y="36" class="g-t">＝ 約 {n} 根扶手同時全力排煙</text>
  {"".join(dots)}
  <text x="330" y="{60 + rows * 15 + 14}" class="g-s">每個點＝一根整棟 70 m 的扶手風道，風機開到 3000 Pa（約 {rail_m3min:.2f} m³/min）</text>
</svg>"""


def stair_layout():
    """樓梯側視：主機與出風口位置。"""
    return f"""
<svg class="graphic" viewBox="0 0 760 320" role="img" aria-label="每層平台一台主機，出風口集中在平台上下各 0.6 公尺">
{defs("l")}
  <path d="M40,290 L120,290 L120,270 L160,270 L160,250 L200,250 L200,230 L240,230 L240,210 L280,210 L280,190 L320,190 L320,170 L420,170" class="g-stair"/>
  <path d="M420,170 L460,170 L460,150 L500,150 L500,130 L540,130 L540,110 L580,110 L580,90 L620,90 L620,70 L720,70" class="g-stair"/>
  <path d="M60,250 L330,130 L430,130 L720,30" class="g-rail"/>
  <path d="M262,160 L330,130 L430,130 L470,116" class="g-outlet"/>
  <rect x="352" y="134" width="58" height="36" rx="4" class="g-host"/>
  <text x="381" y="157" text-anchor="middle" class="g-on">主機</text>
  <line x1="381" y1="172" x2="381" y2="232" class="g-leader"/>
  <text x="381" y="250" text-anchor="middle" class="g-t">每層平台一台（約 20 W）</text>
  <text x="381" y="268" text-anchor="middle" class="g-s">風機、控制、預留空氣模組</text>
  <line x1="290" y1="140" x2="230" y2="80" class="g-leader"/>
  <text x="150" y="66" class="g-ok-t">出風口集中在平台附近</text>
  <text x="150" y="84" class="g-s">往上、往下各約 0.6 m</text>
  <line x1="600" y1="56" x2="640" y2="20" class="g-leader"/>
  <text x="560" y="16" class="g-s">其餘扶手只做導引（光、觸覺）</text>
  <text x="40" y="314" class="g-s">示意圖，比例不精確</text>
</svg>"""


def coanda_lesson():
    """康達曲面：半徑太小噴流分離 vs 半徑夠大。"""
    return f"""
<svg class="graphic" viewBox="0 0 760 250" role="img" aria-label="曲面半徑只有出風縫 2.5 倍時氣流直接往下衝，不會沿曲面轉彎">
{defs("k")}
  <text x="40" y="26" class="g-b">第一版：R 15 mm（縫寬的 2.5 倍）</text>
  <path d="M110,60 L110,110 A30,30 0 0 0 140,140 L140,60 Z" class="g-solid"/>
  <rect x="92" y="60" width="4" height="50" class="g-solid"/>
  <line x1="103" y1="64" x2="103" y2="210" class="g-crit-arrow" marker-end="url(#kc)"/>
  <path d="M106,118 C120,138 140,145 220,145" class="g-dash"/>
  <text x="150" y="190" class="g-crit-t">氣流直接往下衝</text>
  <text x="150" y="208" class="g-s">沒有轉彎，臉收不到</text>
  <text x="228" y="149" class="g-s">（預期的路徑）</text>
  <text x="420" y="26" class="g-b">修正版：R 45 mm（縫寬的 7.5 倍）</text>
  <path d="M470,50 L470,100 A80,80 0 0 0 550,180 L550,50 Z" class="g-solid"/>
  <rect x="452" y="50" width="4" height="50" class="g-solid"/>
  <path d="M463,54 L463,104 A88,88 0 0 0 551,190 L700,190" class="g-ok-arrow" marker-end="url(#ka)"/>
  <text x="740" y="226" text-anchor="end" class="g-s">曲面夠緩，氣流才有機會貼著轉彎</text>
</svg>"""


def test_rig():
    """建議的桌上型示蹤氣體實驗。"""
    return f"""
<svg class="graphic" viewBox="0 0 760 300" role="img" aria-label="桌上型實驗：箱內釋放 CO2，出風口送乾淨空氣，在假人口鼻處量測 CO2">
{defs("t")}
  <rect x="150" y="40" width="460" height="220" rx="10" class="g-box"/>
  <text x="380" y="30" text-anchor="middle" class="g-t">透明壓克力箱</text>
  <rect x="40" y="200" width="60" height="50" rx="6" class="g-box"/>
  <text x="70" y="270" text-anchor="middle" class="g-s">CO₂ 鋼瓶</text>
  <line x1="100" y1="222" x2="170" y2="222" class="g-arrow" marker-end="url(#tm)"/>
  <text x="180" y="226" class="g-s">釋放 CO₂ 當作「煙」</text>
  <circle cx="220" cy="140" r="20" class="g-solid"/>
  <rect x="238" y="135" width="16" height="10" class="g-solid"/>
  <text x="220" y="185" text-anchor="middle" class="g-s">3D 列印出風口</text>
  <text x="220" y="201" text-anchor="middle" class="g-s">A／B／C／D</text>
  <line x1="60" y1="140" x2="198" y2="140" class="g-arrow-ok" marker-end="url(#ta)"/>
  <text x="40" y="128" class="g-s">乾淨空氣</text>
  <path d="M256,140 C320,136 380,134 430,136" class="g-core"/>
  <circle cx="490" cy="140" r="52" class="g-head"/>
  <text x="490" y="146" text-anchor="middle" class="g-s">頭模型</text>
  <rect x="640" y="110" width="90" height="60" rx="6" class="g-box"/>
  <text x="685" y="136" text-anchor="middle" class="g-t">CO₂ 感測器</text>
  <text x="685" y="156" text-anchor="middle" class="g-s">口鼻取樣</text>
  <path d="M440,146 L440,240 L685,240 L685,172" class="g-tube"/>
  <rect x="555" y="196" width="50" height="22" rx="4" class="g-box"/>
  <text x="580" y="212" text-anchor="middle" class="g-s">小風扇</text>
  <line x1="568" y1="192" x2="568" y2="140" class="g-arrow" marker-end="url(#tm)"/>
  <text x="576" y="168" class="g-s">側風</text>
</svg>"""


def handrail_section():
    """扶手一體導風腔斷面（示意，1 px ≈ 1 mm）。"""
    return f"""
<svg class="graphic" viewBox="0 0 760 330" role="img" aria-label="扶手斷面：上方是握把和導引燈，細頸下方是 150 乘 60 毫米的導風腔，內含均流層和線路槽，出風縫朝使用者">
{defs("h")}
  <circle cx="230" cy="70" r="24" class="g-solid"/>
  <path d="M212,56 A24,24 0 0 1 248,56" class="g-led"/>
  <rect x="223" y="94" width="14" height="40" class="g-solid"/>
  <rect x="155" y="134" width="150" height="60" rx="10" class="g-cavity"/>
  <rect x="165" y="144" width="28" height="16" rx="3" class="g-solid"/>
  <line x1="290" y1="140" x2="290" y2="188" class="g-mesh"/>
  <line x1="306" y1="164" x2="360" y2="164" class="g-arrow-ok" marker-end="url(#ha)"/>
  <line x1="306" y1="178" x2="350" y2="196" class="g-arrow-ok" marker-end="url(#ha)"/>
  <circle cx="210" cy="176" r="3" class="g-accent-fill"/><circle cx="240" cy="168" r="3" class="g-accent-fill"/><circle cx="262" cy="180" r="3" class="g-accent-fill"/>
  <line x1="170" y1="226" x2="170" y2="236" class="g-leader"/><line x1="290" y1="226" x2="290" y2="236" class="g-leader"/>
  <line x1="170" y1="231" x2="290" y2="231" class="g-leader"/>
  <text x="230" y="252" text-anchor="middle" class="g-s">150 mm</text>

  <line x1="256" y1="58" x2="420" y2="40" class="g-leader"/>
  <text x="426" y="36" class="g-t">導引燈（燈罩下的 LED）</text>
  <text x="426" y="54" class="g-s">平時顯示空氣品質，火災時標示路線</text>
  <line x1="254" y1="76" x2="420" y2="84" class="g-leader"/>
  <text x="426" y="80" class="g-t">握把 Ø45–50 mm</text>
  <text x="426" y="98" class="g-s">表面觸覺紋理，一樓末端換紋理</text>
  <line x1="238" y1="114" x2="420" y2="128" class="g-leader"/>
  <text x="426" y="124" class="g-t">細頸</text>
  <text x="426" y="142" class="g-s">留出手指握住的空間（法規要查證）</text>
  <line x1="300" y1="150" x2="420" y2="172" class="g-leader"/>
  <text x="426" y="168" class="g-t">均流層＋出風縫（朝使用者）</text>
  <text x="426" y="186" class="g-s">阻力約 20–30 Pa，讓每段平均出風</text>
  <line x1="240" y1="194" x2="420" y2="216" class="g-leader"/>
  <text x="426" y="212" class="g-t">導風腔 150 × 60 mm</text>
  <text x="426" y="230" class="g-s">從頂樓貫穿到底層，不另拉管</text>
  <line x1="180" y1="152" x2="140" y2="270" class="g-leader"/>
  <text x="40" y="288" class="g-t">線路槽</text>
  <text x="40" y="306" class="g-s">燈光、感測器電源與訊號</text>
  <text x="426" y="290" class="g-s">示意圖；可用鋁擠型一體成形</text>
</svg>"""


def dual_mode():
    """平時／火災雙模式的建築剖面示意。"""
    def building(x0, floors_state, title, sub, fire=False):
        out = [f'<text x="{x0}" y="26" class="g-b">{title}</text><text x="{x0}" y="44" class="g-s">{sub}</text>']
        out.append(f'<rect x="{x0 + 80}" y="58" width="70" height="26" rx="4" class="g-host"/>'
                   f'<text x="{x0 + 115}" y="76" text-anchor="middle" class="g-on">頂樓主機</text>')
        out.append(f'<line x1="{x0 + 115}" y1="84" x2="{x0 + 115}" y2="96" class="g-railv"/>')
        top, h = 96, 44
        for k, st in enumerate(floors_state):
            y = top + k * h
            fl = 5 - k
            x1, x2 = (x0 + 115, x0 + 255) if k % 2 == 0 else (x0 + 255, x0 + 115)
            out.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y + h}" class="g-railv"/>')
            nx = x2
            cls = {"on": "g-node-ok", "trickle": "g-node-idle", "clean": "g-node-ok", "unk": "g-node-warn",
                   "smoke": "g-node-crit"}[st]
            out.append(f'<circle cx="{nx}" cy="{y + h}" r="9" class="{cls}"/>')
            out.append(f'<text x="{x0 + 185}" y="{y + h - 8}" text-anchor="middle" class="g-s">{fl}F</text>')
            lab = {"on": "有人：送風 5 L/s", "trickle": "細流 0.5 L/s", "clean": "乾淨：綠光標示",
                   "unk": "不確定：琥珀燈", "smoke": "有煙：風門關閉"}[st]
            tx = nx + 16 if nx > x0 + 185 else nx - 16
            anchor = "start" if nx > x0 + 185 else "end"
            out.append(f'<text x="{tx}" y="{y + h + 4}" text-anchor="{anchor}" class="g-s">{lab}</text>')
        return "".join(out)
    left = building(20, ["trickle", "on", "on", "trickle", "trickle"], "平時：流通與淨化空氣", "有人的樓層送風，其他樓層細流")
    right = building(425, ["unk", "smoke", "clean", "clean", "clean"], "火災：標示並守護疏散路線", "各層偵測站判斷，燈光只指向乾淨的路")
    return f"""
<svg class="graphic" viewBox="0 0 820 340" role="img" aria-label="同一套扶手系統，平時依有人與否送風，火災時各層偵測空氣並用燈光標示乾淨路線、有煙的樓層關閉風門">
{left}{right}
  <line x1="410" y1="20" x2="410" y2="330" class="g-sep"/>
</svg>"""


def handrail_dims():
    """扶手斷面尺寸圖（比例正確：1 mm = 2 px）。"""
    k = 2.0
    ox, oy = 150, 40                     # 導風腔左上角
    W, H, wall = 150, 60, 2.5
    grip_d, neck_w, neck_h = 48, 16, 38
    cx = ox + (W / 2) * k
    grip_cy = oy + (H + neck_h + grip_d / 2) * k   # 先算總高再翻轉
    total_h = (grip_d + neck_h + H) * k
    top = 40
    g_cy = top + grip_d / 2 * k
    n_top = top + grip_d * k - 6
    c_top = top + (grip_d + neck_h) * k
    def dim_h(x1, x2, y, label):
        return (f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" class="g-dimline"/>'
                f'<line x1="{x1}" y1="{y-6}" x2="{x1}" y2="{y+6}" class="g-dimline"/><line x1="{x2}" y1="{y-6}" x2="{x2}" y2="{y+6}" class="g-dimline"/>'
                f'<text x="{(x1+x2)/2}" y="{y-6}" text-anchor="middle" class="g-dim">{label}</text>')
    def dim_v(x, y1, y2, label, side=1):
        tx = x + 8 * side
        anchor = "start" if side > 0 else "end"
        return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" class="g-dimline"/>'
                f'<line x1="{x-6}" y1="{y1}" x2="{x+6}" y2="{y1}" class="g-dimline"/><line x1="{x-6}" y1="{y2}" x2="{x+6}" y2="{y2}" class="g-dimline"/>'
                f'<text x="{tx}" y="{(y1+y2)/2+4}" text-anchor="{anchor}" class="g-dim">{label}</text>')
    cl = cx - W / 2 * k
    cr = cx + W / 2 * k
    slot_y = c_top + (H - 14) * k
    return f"""
<svg class="graphic" viewBox="0 0 760 430" role="img" aria-label="扶手斷面尺寸圖：握把直徑 48 毫米、細頸 38 毫米高、導風腔 150 乘 60 毫米，出風縫 6 毫米朝使用者">
{defs("d")}
  <circle cx="{cx}" cy="{g_cy}" r="{grip_d/2*k}" class="g-solid-light"/>
  <path d="M{cx-grip_d/2*k*0.72},{g_cy-grip_d/2*k*0.69} A{grip_d/2*k},{grip_d/2*k} 0 0 1 {cx+grip_d/2*k*0.72},{g_cy-grip_d/2*k*0.69}" class="g-led"/>
  <rect x="{cx-neck_w/2*k}" y="{n_top}" width="{neck_w*k}" height="{neck_h*k+6}" class="g-solid-light"/>
  <rect x="{cl}" y="{c_top}" width="{W*k}" height="{H*k}" rx="8" class="g-solid-light"/>
  <rect x="{cl+wall*k}" y="{c_top+wall*k}" width="{(W-2*wall)*k}" height="{(H-2*wall)*k}" rx="6" class="g-cavity"/>
  <rect x="{cl+wall*k+6}" y="{c_top+wall*k+6}" width="{22*k}" height="{14*k}" rx="3" class="g-solid-light"/>
  <line x1="{cr-12*k}" y1="{c_top+wall*k+4}" x2="{cr-12*k}" y2="{c_top+(H-wall)*k-4}" class="g-mesh"/>
  <rect x="{cr-wall*k-1}" y="{slot_y}" width="{wall*k+2}" height="{6*k}" class="g-slot"/>
  <line x1="{cr+4}" y1="{slot_y+6}" x2="{cr+70}" y2="{slot_y+6}" class="g-arrow-ok" marker-end="url(#da)"/>
  {dim_v(cx - grip_d/2*k - 30, top, top + grip_d*k, "Ø48", -1)}
  {dim_v(cx - grip_d/2*k - 30, top + grip_d*k, c_top, "38", -1)}
  {dim_v(cl - 30, c_top, c_top + H*k, "60", -1)}
  {dim_h(cl, cr, c_top + H*k + 30, "150")}
  {dim_h(cx - neck_w/2*k, cx + neck_w/2*k, n_top + 30, "16")}
  {dim_v(cr + 110, slot_y, slot_y + 6*k, "出風縫 6", 1)}
  <text x="{cr+20}" y="{c_top+18}" class="g-s">均流層</text>
  <text x="{cl+wall*k+6}" y="{c_top+wall*k+6+14*k+16}" class="g-s">線路槽 22×14</text>
  <text x="{cx+grip_d/2*k+14}" y="{top+12}" class="g-s">導引燈（燈罩下）</text>
  <text x="{cx+grip_d/2*k+14}" y="{top+70}" class="g-s">握把：手可完整握住</text>
  <text x="{cx+neck_w/2*k+14}" y="{n_top+46}" class="g-s">細頸：手指勾住的空間</text>
  <text x="{cx}" y="{c_top+H*k/2+40}" text-anchor="middle" class="g-s">導風腔（壁厚 2.5，鋁擠型）</text>
  <text x="560" y="40" class="g-b">尺寸（mm）</text>
  <text x="560" y="64" class="g-s">總高約 146，最寬 150</text>
  <text x="560" y="84" class="g-s">導風腔內徑約 145 × 55</text>
  <text x="560" y="104" class="g-s">出風縫朝使用者（樓梯側）</text>
  <text x="560" y="140" class="g-t">待查證</text>
  <text x="560" y="160" class="g-s">扶手高度、握把直徑範圍、</text>
  <text x="560" y="178" class="g-s">握把下方障礙物距離，</text>
  <text x="560" y="196" class="g-s">以建築技術規則為準</text>
  <text x="20" y="420" class="g-s">比例：1 mm ＝ 2 px，所有尺寸為概念值</text>
</svg>"""
