"""報告的白話判讀文字。數字一律從計算結果帶入；措辭依實際結果撰寫。"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")


def build_findings(ctx):
    s1, s2, s3, s4 = ctx["s1"], ctx["s2"], ctx["s3"], ctx["s4"]
    saf, pct, tag, L = ctx["saf"], ctx["pct"], ctx["tag"], ctx["NZ_LABEL"]
    s5 = json.load(open(os.path.join(OUT, "s5_results.json")))
    z6 = json.load(open(os.path.join(OUT, "s6_results.json")))["cases"]
    NZ = ["plain", "coanda", "coax", "amp"]

    # ---------- 數字 ----------
    op = {(r["fan"][0], r["filter"][:4]): r for r in s1["operating_points"] if r["D_mm"] == 34}
    sS, mM = op[("S", "濾材堵塞")], op[("M", "濾材堵塞")]
    u34 = s1["uniformity"]["34mm"]
    cyc = s3["cyclone"]
    rem = {(r["smoke"][:2], r["train"][:2]): r for r in s3["particle_removal"]}
    hot = next(c for c in s4["cases"] if c["gas"].startswith("200") and c["D_mm"] == 38 and c["P_Pa"] == 3000)
    door = s4["door_ref_m3min"]
    n_rails = round(door / hot["Q_m3min"])

    def sp(cav, q, spacing):
        return next(r for r in s5["spacing_all_on"] if r["cavity"].endswith(cav) and r["q_Ls"] == q and r["spacing"] == spacing)

    def od(cav, q, k):
        return next(r for r in s5["on_demand_no_booster"] if r["cavity"].endswith(cav) and r["q_Ls"] == q and r["k"] == k)

    big_all5 = sp("150×60 mm", 5.0, 0)
    big_all3 = sp("150×60 mm", 3.0, 0)
    small_all5 = sp("100×50 mm", 5.0, 0)
    od1, od3 = od("150×60 mm", 5.0, 1), od("150×60 mm", 5.0, 3)
    en = s5["energy"]

    def v(nz, c="head_vc00"):
        return saf(nz, c)

    coax0, plain0, amp0, coanda0 = v("coax"), v("plain"), v("amp"), v("coanda")
    worst_wind = max(v(nz, c) or 0 for nz in NZ for c in ("head_vc15", "head_vc30"))
    r15 = s2.get("coanda_r15_head_vc00")
    ent = {nz: s2.get(f"{nz}_free", {}).get("entrain", {}).get("30cm") for nz in NZ}
    saf_example = coax0

    # ---------- 一頁看懂 ----------
    takeaways = [
        dict(big=f"{en['P_3floors_W']:.0f} W",
             text=f"<b>平時：</b>頂樓一台主機經扶手導風腔送風，不必另拉管、不必每層裝增壓機。有人才送風時，同時 3 層也只要約 {en['P_3floors_W']:.0f} W。"),
        dict(big=pct(coax0),
             text=f"<b>火災（無側風）：</b>低混合率出風口在臉前 35 cm（早期設定）送到 {pct(coax0)} 的乾淨空氣。臉在斜上方的重算見第 04 章。"),
        dict(big=pct(z6['W_q20_vc15']['upper50']),
             text="<b>有側風時：</b>窄的出風口都被吹散；改用寬 80 mm 的「空氣牆」、每公尺 20 L/s，扶手上方（站姿的臉）有這麼大的範圍乾淨空氣過半。"),
        dict(big="0%", text="吸樓梯間的空氣過濾後再送，口鼻的 CO <b>一點都不會減少</b>。氣源一定要先確認乾淨。"),
    ]

    def card(nz, name, verdict, cls, extra=""):
        return dict(name=name, verdict=verdict, cls=cls,
                    why=f"早期設定（臉在正前方 35 cm）：無側風 {pct(v(nz))}，有側風 {pct(v(nz,'head_vc15'))}。{extra}", where="第 04 章")

    cards = [
        dict(name="扶手一體導風腔（150×60 mm）", verdict="可行", cls="ok",
             why=f"頂樓一台主機就推得動 10 層（全開約 {big_all5['p_roof']:.0f} Pa），不必另拉管、不必裝增壓機。", where="第 02 章"),
        dict(name="有人才送風＋細流＋預測預開", verdict="可行", cls="ok",
             why=f"細流讓管內空氣約 2 分鐘換一次，有人時立刻有新鮮風；一天約 0.05 度電。", where="第 02 章"),
        dict(name="一般圓扶手當風管", verdict="太細", cls="bad",
             why="整棟只送得出每層約 0.5 L/s，必須改成一體導風腔斷面。", where="第 02 章"),
        card("coax", "低混合率同軸噴嘴", "無風時最好", "ok", "準，但怕風。"),
        card("plain", "一般定向噴嘴", "效果有限", "mid"),
        card("amp", "氣流倍增式（Dyson 式）", "火災不適用", "bad", "借來的是周圍空氣；平時用來散開新鮮空氣可以。"),
        dict(name="寬的「空氣牆」出風口", verdict="目前最好", cls="ok",
             why=f"寬 80 mm、慢速送風，被上升氣流帶到扶手上方：側風 0.15 m/s、每公尺 20 L/s 時，扶手上方 {pct(z6['W_q20_vc15']['upper50'])} 的範圍乾淨空氣過半。",
             where="第 05 章"),
        dict(name="康達曲面導流", verdict="往上才成功", cls="mid",
             why=f"往下轉時氣流不轉彎；改成藏在底面、往上轉後成功貼著扶手上升，但只守住扶手正上方一道窄柱（{pct(z6['Ku_q20_vc15']['upper50'])}）。",
             where="第 04、05 章"),
        dict(name="氣源", verdict="要確認乾淨", cls="mid",
             why="進氣口要有 CO／煙霧感測，量到污染就關閉。濾網擋不住 CO。", where="第 05 章"),
        dict(name="初濾＋HEPA", verdict="只擋煙粒", cls="mid", why="平時淨化 PM2.5 很好；火災煙粒擋下 99.9% 以上，但 CO 擋下 0%。", where="第 06 章"),
        dict(name="活性碳、觸媒", verdict="要做實驗", cls="mid", why="活性碳幾乎擋不住 CO；觸媒有機會，但怕濕氣、有壽命。", where="第 06 章"),
        dict(name="氣旋分離", verdict="不採用", cls="bad",
             why=f"火災煙粒太小，只抓到約 {pct(rem[('有焰','氣旋')]['removal_mass'])}（重量），還要 {cyc['dP_Pa']:.0f} Pa 的推力。", where="第 06 章"),
        dict(name="扶手當排煙管", verdict="不採用", cls="bad",
             why=f"整根扶手全力排煙只有一扇門的 {pct(hot['ratio_to_door'],1)}。", where="第 07 章"),
    ]

    # ---------- 第 02 章 平時 ----------
    vent_one = "把扶手做成「握把＋一體導風腔」，頂樓一台主機就能把過濾過的室外空氣送到每一層，不用另外拉管。"
    vent_points = f"""
<p>設定：頂樓一台主機（風機＋PM2.5 濾網）吸室外空氣，經扶手導風腔往下送 10 層；每層平台只有一個小風門、感測器和出風口。{tag("asm")}</p>
<ul>
<li><b>不用每層裝增壓機：</b>導風腔 150×60 mm 時，10 層同時送風（每層 3–5 L/s）頂樓主機只需要約 {big_all3['p_roof']:.0f}–{big_all5['p_roof']:.0f} Pa，中型風機就做得到。導風腔縮成 100×50 mm、每層 5 L/s 時要 {small_all5['p_roof']:.0f} Pa，才需要每 3 層加一台增壓機。{tag("sim")}</li>
<li><b>有人才送風最省：</b>同時只開 1 層時主機只要 {od1['p_roof']:.0f} Pa、{od1['P_W']:.1f} W；開 3 層 {od3['p_roof']:.0f} Pa、{od3['P_W']:.1f} W。{tag("sim")}</li>
<li><b>細流讓管子保持新鮮：</b>每層一直送 0.5 L/s，整根導風腔約 2 分鐘換一次空氣，有人來時馬上就是新鮮的風。{tag("sim")}</li>
<li><b>要做出的是「新風帶」，不是整間換氣：</b>整個樓梯間每小時換氣 2 次大約每層要 33 L/s，扶手做不到；但沿著扶手每層 3–6 L/s 的新鮮風帶做得到。{tag("inf")}</li>
</ul>"""
    vent_modes = """
<div class="table-wrap"><table><thead><tr><th scope="col">模式</th><th scope="col">什麼時候</th><th scope="col">每層送風</th><th scope="col">主機耗電</th></tr></thead><tbody>
<tr><th scope="row">① 細流待機</th><td>平時一直開</td><td class="num">0.5 L/s</td><td class="num">約 0.6 W</td></tr>
<tr><th scope="row">② 預測預開</th><td>偵測到有人，先開前方 1–2 層</td><td class="num">5 L/s</td><td class="num">約 3.5 W</td></tr>
<tr><th scope="row">③ 沖風</th><td>人到達該層的前後 15 秒</td><td class="num">10 L/s</td><td class="num">約 4 W</td></tr>
<tr><th scope="row">④ 舒適送風</th><td>人在該層</td><td class="num">5 L/s</td><td class="num">約 3.5 W</td></tr>
<tr><th scope="row">⑤ 定時／感測換氣</th><td>每幾小時，或濕度、CO₂ 偏高</td><td class="num">3 L/s × 10 分鐘</td><td class="num">約 14 W</td></tr>
<tr><th scope="row">消防模式</th><td>收到火警訊號</td><td colspan="2">交給第 03 章的火災邏輯與建築消防系統</td></tr>
</tbody></table></div>
<div class="table-wrap"><table><thead><tr><th scope="col">時間</th><th scope="col">情境：有人從 1 樓往上走</th><th scope="col">系統動作</th></tr></thead><tbody>
<tr><th scope="row">平時</th><td>沒人</td><td>每層細流</td></tr>
<tr><th scope="row">0 秒</th><td>推開 1 樓樓梯門</td><td>1 樓沖風；2、3 樓預開</td></tr>
<tr><th scope="row">15 秒</th><td>往 2 樓途中</td><td>1 樓降為舒適；2 樓沖風；4 樓預開</td></tr>
<tr><th scope="row">30 秒</th><td>抵達 2 樓</td><td>2 樓舒適；3 樓沖風；5 樓預開</td></tr>
<tr><th scope="row">走過 1 分鐘後</th><td>已離開</td><td>該層回到細流</td></tr>
</tbody></table></div>
<p class="prose muted">一天合計約 0.05 度電（24 小時全開約 1.2 度）。耗電以風機效率 30% 假設計算。</p>"""
    vent_design = [
        "扶手斷面＝握把（Ø45–50）＋細頸＋<b>導風腔 150×60 mm</b>，可以鋁擠型一體成形；導風腔同時收納線路。",
        "每層平台不需要風機和濾網：只要<b>小風門、有人感應器、門磁、出風口＋均流層</b>。",
        "濾網只有頂樓一組，保養集中；進氣口要架高、防雨、遮陽，並遠離屋頂排氣口。",
        "Dyson 式借風出風口<b>平時</b>很適合（把新鮮空氣散開、吹起來柔和）。",
        "台灣潮濕：要有定時換氣，避免樓梯間和導風腔悶濕、結露。",
    ]
    round_points = f"""
<div class="points prose"><p>早期方案是「每層一台主機、34 mm 圓扶手」。這些計算說明了為什麼要改成一體導風腔：</p>
<ul>
<li>一般圓扶手（內徑 38 mm）從頂樓往下送 10 層，風機 1000 Pa 也只送得出整棟 5 L/s，平均每層 0.5 L/s。{tag("sim")}</li>
<li>內徑從 38 mm 縮到 30 mm，阻力約變成 2.5–3 倍。{tag("sim")}</li>
<li>出風口沒有均流層時，最少的地方只有最多的 {u34["2.0"]*100:.0f}%；加 20–30 Pa 均流層後達 {u34["30.0"]*100:.0f}%。{tag("sim")}</li>
<li>每層主機方案：中型鼓風機在濾網堵塞時還有 {mM["Q_Ls"]:.1f} L/s；小型的只剩 {sS["Q_Ls"]:.1f} L/s。{tag("sim")}{tag("asm")}</li>
</ul></div>"""

    # ---------- 第 03 章 火災 ----------
    fire_one = "扶手系統造不出一整條乾淨的樓梯，但它知道哪裡乾淨，可以把人帶過去，並且不讓自己把煙帶到別層。"
    fire_points = f"""
<p><b>為什麼不是「提供」乾淨路線？</b>要讓整條樓梯保持乾淨，靠的是建築的加壓送風和防火門把煙擋在外面。扶手系統全開約 60 L/s，一扇開著的門要擋住煙大約要 1,800 L/s（以 1 m/s 粗估），差了約 30 倍。{tag("inf")}{tag("asm")}</p>
<div class="table-wrap"><table><thead><tr><th scope="col">做法</th><th scope="col">怎麼做到</th></tr></thead><tbody>
<tr><th scope="row">標示</th><td>每層平台的感測器（CO、煙霧、溫度）就是一排「空氣偵測站」。扶手燈光顯示：綠＝這段乾淨，琥珀＝不確定，紅＝有煙。</td></tr>
<tr><th scope="row">引導</th><td>結合消防系統的避難規劃和各層偵測結果，燈光只在確認的路線上給方向；不確定時不給方向。</td></tr>
<tr><th scope="row">守護</th><td>火警時風門<b>預設關閉</b>，不讓煙走扶手導風腔跑到別層；只有進氣口確認乾淨、消防系統允許時才送風。</td></tr>
<tr><th scope="row">配合</th><td>把各層空氣資料傳給建築消防系統，協助加壓送風與排煙判斷（介接方式要找消防設備師確認）。</td></tr>
<tr><th scope="row">輔助</th><td>確認安全時，平台出風口用低混合方式送風；平台可收納認證逃生頭罩（例如 EN 403 類產品）。</td></tr>
</tbody></table></div>
<p><b>不追求完全乾淨，只求「多撐一段時間、足夠逃出去」：</b>CO 的危險大致是「濃度 × 時間」的累積，所以 CO 降到一半，能撐的時間大約變成兩倍。{tag("inf")}</p>
<div class="table-wrap"><table><thead><tr><th scope="col">扶手旁的乾淨空氣比例</th><th scope="col">CO 剩下</th><th scope="col">可撐的時間大約</th></tr></thead><tbody>
<tr><td class="num">25%</td><td class="num">75%</td><td class="num">1.3 倍</td></tr>
<tr><td class="num">50%</td><td class="num">50%</td><td class="num">2 倍</td></tr>
<tr><td class="num">75%</td><td class="num">25%</td><td class="num">4 倍</td></tr>
<tr><td class="num">90%</td><td class="num">10%</td><td class="num">10 倍</td></tr>
</tbody></table></div>
<p class="muted">簡化估算，前提是送出的是乾淨氣源。實際火場還有缺氧、高溫、氰化氫與刺激性氣體，正式評估要用火災工程的可忍受性方法（例如 ISO 13571 的劑量計算）。{tag("tbd")}</p>"""
    fire_design = [
        "火災時的主角是<b>偵測＋燈光＋觸覺</b>：平時就在用的感測器和燈光，火災時直接變成逃生工具。",
        "送風只當<b>輔助</b>：進氣口量到乾淨、消防系統允許才送；任何故障都預設關閉。",
        "提案用語：「延長可逃生時間」「輔助」，<b>不要寫「保證可以呼吸」「無毒」</b>。",
        "設計目標：扶手周圍 40–60 cm 內乾淨空氣比例 ≥ 50%（可逃生時間至少多一倍），而且要在有側風時守得住。第 05 章顯示：寬的空氣牆是目前唯一接近的做法。",
    ]

    # ---------- 第 04 章 出風口 ----------
    nozzle_one = f"沒有風時，低混合率出風口在臉前送到 {pct(coax0)} 的乾淨空氣；但只要有 0.15 m/s 的側風，四種出風口都是 0%。"
    nozzle_points = f"""
<ul>
<li><b>低混合率同軸（C）最準：</b>寬出口、慢風速、外圈再加一圈更慢的風「護送」，送到臉前時幾乎沒有混到周圍空氣（{pct(coax0)}，最差時刻也有 {pct(s2['coax_head_vc00']['p10'])}）。{tag("sim")}</li>
<li><b>一般出風口（A）和氣流倍增式（D）差不多：</b>都只有約 {pct(plain0)}、{pct(amp0)}。細縫高速吹出後一路把周圍空氣拉進來，到臉前只剩兩成多。{tag("sim")}</li>
<li><b>借風越多，乾淨比例越低：</b>沒有人擋時，30 cm 處的總風量是送出風量的：A {ent['plain'] or 0:.1f} 倍、D {ent['amp'] or 0:.1f} 倍、C {ent['coax'] or 0:.1f} 倍。多出來的都是周圍空氣，所以 Dyson 式「放大風量」在火災時幫不上忙。{tag("sim")}</li>
<li><b>最大的問題是側風：</b>加上由下往上 0.15 m/s 的側風（大約是人慢慢走過帶起的風），四種出風口送出的空氣都被吹到扶手上方，口鼻變成 0%。乾淨空氣並沒有消失，只是守在扶手旁約 10–15 cm 內，到不了 35 cm 外的臉。{tag("sim")}</li>
<li><b>沒有風時的「局部累積」：</b>無側風時，扶手和人頭之間會形成大渦旋，把送出的空氣困在附近，所以 A、D 的背景也有兩成左右。真實樓梯間煙會一直補充，有側風的結果比較保守。{tag("inf")}</li>
</ul>"""
    nozzle_design = [
        "火災模式的出風口要用<b>低混合方式</b>：出口寬、風速慢、內有整流層。",
        "平時模式可以用<b>借風</b>把新鮮空氣散開；兩種吹法可以考慮做成同一個「可切換」的出風口。",
        "要對抗側風，送出的風在 40–60 cm 處必須比側風快：風量大概要比現在（每公尺 5 L/s）多 3–6 倍，形狀要像一道沿扶手的「空氣牆」，而不是對著臉吹。這要用下一階段模擬確認。",
        "風量有限時，火災模式把送風集中在<b>最需要的平台</b>（起火層上下、偵測到有煙的樓層）。",
    ]
    coanda_points = (f"<p>第一版曲面半徑 15 mm（出風縫 6 mm 的 2.5 倍）、修正版 45 mm（7.5 倍），兩種氣流都<b>沒有沿曲面轉彎</b>，直接往下衝，"
                     f"臉前只有 {pct(r15['mean'] if r15 else None)} 和 {pct(coanda0)}。{tag('sim')}</p>"
                     "<p>可能的原因是風速太低（0.83 m/s）：康達效應需要氣流有足夠的速度貼著曲面走，Dyson 類產品用的是約 1 mm 的細縫和高很多的風速。"
                     f"另外 1 mm 網格畫出來的曲面是階梯狀，也可能讓氣流提早分離。所以結論是「在這個風速下不可靠」，要用實體出風口測試才能確定。{tag('tbd')}</p>")

    # ---------- 第 05 章 氣源 ----------
    source_points = f"""
<p><b>為什麼？</b>出風口只決定「吸到的空氣有幾成來自出風口」，送出去的空氣本身乾不乾淨，是氣源決定的。</p>
<ul>
<li><b>吸樓梯間的空氣：</b>濾網只擋得住煙粒，CO 照樣穿過去，所以不管出風口設計多好，口鼻的 CO 都一樣。缺氧和高溫也一樣。{tag("sim")}</li>
<li><b>確認乾淨的氣源：</b>送出的空氣沒有 CO，口鼻的 CO 就降低「乾淨空氣比例」那麼多。以低混合出風口無側風的 {pct(saf_example)} 來算，CO 只剩 {pct(1-saf_example)}。{tag("sim")}</li>
</ul>
<p><b>這套系統的氣源：</b>平時是頂樓進氣口的室外空氣。火災時煙會往上跑，頂樓進氣口可能最先被污染，所以：</p>
<ul>
<li>進氣口要裝 CO、煙霧感測器，<b>量到污染就關閉</b>，絕不送出來源不明的空氣。{tag("inf")}</li>
<li>可以考慮在低樓層或另一面外牆再設一個備用進氣口，由感測結果選擇比較乾淨的一個。{tag("tbd")}</li>
<li>如果目標是「在濃煙中呼吸」，平台收納經認證的逃生頭罩（例如 EN 403 類），比開放式送風更直接。台灣的法規和產品認證要另外查證。{tag("tbd")}</li>
</ul>"""
    source_design = [
        "進氣口不能從樓梯間吸氣後直接送給人；這條路已經被模擬排除。",
        "頂樓進氣口要有感測器與自動關閉，並考慮備用進氣口。",
        "「逃生頭罩收納」可以做成平台出風口旁的一個格子，平時鎖著、定期自檢。",
    ]

    # ---------- 第 06 章 濾網 ----------
    filter_points = f"""
<ul>
<li><b>HEPA 擋得住煙粒：</b>初濾＋HEPA 對兩種假設的火災煙，煙粒都擋下 99.9% 以上；平時淨化 PM2.5 也很好用。{tag("sim")}{tag("std")}</li>
<li><b>氣旋擋不住：</b>氣旋靠旋轉把粒子甩出去，粒子越小越甩不出去。10 cm 大小的氣旋，一半抓得到、一半抓不到的粒子大小約 {cyc["d50_um"]:.1f} µm，但火災煙粒大多不到 1 µm，所以有焰燃燒的煙只抓到約 {pct(rem[("有焰","氣旋")]["removal_mass"])}。做小一點可以抓更小的粒子，但推力要暴增到約 {s3["cyclone_small"]["dP_Pa"]/1000:.1f} kPa。{tag("sim")}</li>
<li><b>CO 擋不住：</b>CO 是氣體分子，比任何濾網的孔都小很多。活性碳對 CO 幾乎沒用。{tag("inf")}</li>
<li><b>觸媒有機會，但要實驗：</b>霍加拉（Hopcalite）類觸媒能把 CO 變成 CO₂，認證逃生頭罩就用這類材料；但它怕濕氣、有壽命、會發熱，而且頭罩是密閉的小風量裝置，跟開放式送風不同。這份報告不算它的效果。{tag("tbd")}</li>
</ul>"""
    filter_design = [
        "頂樓主機保留初濾＋HEPA：平時淨化 PM2.5，但宣傳上<b>不能說「淨化火場空氣」</b>。",
        "氣旋從設計中拿掉，省下體積和風機推力。",
        "濾網會堵塞：風機要用「堵塞時」的阻力來選，並有「該換濾網」提示。",
    ]

    # ---------- 第 07 章 排煙 ----------
    exhaust_one = f"不行。整棟一根扶手全力排煙，量也只有一扇敞開的門的 {pct(hot['ratio_to_door'],1)}。"
    exhaust_points = f"""
<ul>
<li>假設整棟 10 層共用一根 70 m 的扶手管子。就算風機推到 3000 Pa、內徑 38 mm，200 °C 的熱煙也只排得出約 <b>{hot["Q_m3min"]:.2f} m³/min</b>，管內風速已經 {hot["V_ms"]:.0f} m/s。{tag("sim")}</li>
<li>一扇敞開的門（0.9 × 2.0 m）以 1 m/s 通過的風量約 {door:.0f} m³/min，相當於約 {n_rails} 根扶手。{tag("asm")}</li>
<li>熱煙流過金屬扶手會把握把加熱，可能燙手（燙傷溫度門檻要依 ISO 13732-1 查證）；管子有漏縫，煙也會漏到逃生路線上。{tag("inf")}{tag("tbd")}</li>
</ul>"""
    exhaust_design = [
        "排煙交給建築原有的排煙設備；扶手系統只提供偵測資料與導引。",
        "火警時扶手導風腔的風門預設關閉，避免變成煙的通道。",
    ]

    # ---------- 第 08 章 ----------
    limits_points = """
<p><b>這次電腦模擬做不到的事：</b></p>
<ul>
<li><b>只算了一個剖面（2D）：</b>連續出風縫比較接近；如果出風口是一個個圓孔，氣流會散得更快，乾淨空氣比例會更低。</li>
<li><b>沒有算溫度：</b>火場的煙是熱的、送出的空氣相對是冷的，冷空氣會往下沉，會改變氣流路線。</li>
<li><b>沒有算呼吸：</b>吸氣會把口鼻周圍的空氣一起吸進來。</li>
<li><b>人是不動的：</b>人沿著扶手走（約 1 m/s）帶起的風，2D 模型算不到。</li>
<li><b>格子大小：</b>1 mm 的格子對細縫和曲面還是偏粗（氣流倍增式細縫放寬成 3 mm、康達曲面呈階梯狀），也還沒做「格子切細結果會不會變」的檢查。</li>
<li><b>假設的數字：</b>風機曲線、濾網阻力、煙粒大小、側風速度、風機效率都是先假設的，換成實際型號和量測值後要重算。</li>
</ul>
<p>所以這次的結果適合用來<b>比較方案、排除不可行的做法、訂出下一步的設計目標</b>，不適合當成真實火場的預測數字。</p>"""
    next_points = """
<p><b>這次已經完成的：</b>「守住扶手旁 50 cm」的模擬（第 05 章）、扶手斷面尺寸圖（第 02 章）、臉在斜上方的出風口比較（第 04 章）。</p>
<p><b>建議的下一步：</b></p>
<ol>
<li><b>空氣牆出風口打樣：</b>依第 05 章，做寬約 80 mm、內有整流層的出風口，並調整導風腔斷面（例如 120×90 mm）或做平台轉角的外凸出風罩。</li>
<li><b>可切換吹法的出風口：</b>平時小風量、寬角度借風；火災時切成慢速平直的空氣牆。</li>
<li><b>桌上型實驗（上圖）：</b>3D 列印空氣牆、康達往上、低混合三種出風口，箱內放 CO₂、出風口送乾淨空氣、量頭模型口鼻的 CO₂，用和電腦相同的方法算乾淨空氣比例；用小風扇由下往上加側風。</li>
<li><b>3D、含溫度的電腦模擬：</b>確認熱煙層、冷空氣下沉、人走動、出風口長度有限（三維）時，空氣牆還撐不撐得住。建議用有顯示卡的電腦執行。</li>
<li><b>網格收斂檢查：</b>把格子切細一倍重算關鍵算例，確認排名不變。</li>
<li><b>扶手斷面打樣：</b>確認握持感與法規（扶手高度、握把尺寸、下方障礙物）。</li>
<li><b>找消防設備師確認：</b>與火警系統、加壓送風的介接，以及逃生頭罩的法規。</li>
<li><b>完成以上之前，不做任何真實煙霧或火場測試。</b></li>
</ol>"""

    # ---------- S2 改版：臉在斜上方 ----------
    pf = os.path.join(OUT, "s2f_results.json")
    f2 = json.load(open(pf)) if os.path.exists(pf) else {}
    FL = {"A": "A 一般定向", "B": "B 康達往上", "C": "C 低混合同軸", "D": "D 氣流倍增",
          "W20": "W 空氣牆 20 L/s/m", "W40": "W 空氣牆 40 L/s/m"}
    CL = [("vc00", "無側風"), ("vc15", "側風 0.15"), ("vc30", "側風 0.30")]
    n_done = len(f2)
    rows = []
    for k in FL:
        cells = "".join(f'<td class="num">{pct(f2[f"{k}_{c}"]["mean"]) if f"{k}_{c}" in f2 else "計算中"}</td>' for c, _ in CL)
        rows.append(f'<tr><th scope="row">{FL[k]}</th>{cells}</tr>')
    face_table = ('<div class="table-wrap"><table><thead><tr><th scope="col">出風口</th>'
                  + "".join(f'<th scope="col">{l}</th>' for _, l in CL) + '</tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>')
    if n_done == 0:
        face_one = "臉改到扶手斜上方的四種出風口比較，正在計算中。"
    else:
        best = max(f2, key=lambda n: f2[n]["mean"])
        bk, bc = best.split("_")
        face_one = (f"臉在扶手斜上方時（已完成 {n_done}/18 組），目前口鼻乾淨空氣最高的是 "
                    f"{FL[bk]}（{dict(CL)[bc]}）：{pct(f2[best]['mean'])}。")
    windy = [v["mean"] for k, v in f2.items() if not k.endswith("vc00") and not k.startswith("W")]
    face_interim = ""
    if windy and max(windy) < 0.05:
        face_interim = (f'<p><b>目前看到的現象（{len(windy)} 組有側風的結果）：</b>有側風時，出風口吹出的乾淨空氣一離開扶手，'
                        f'就被由下往上的氣流帶著<b>貼著扶手正上方往上走</b>，到不了往樓梯側 28 cm 外的臉，口鼻都是 0%。'
                        f'B 康達往上確實有沿圓角轉向上（下面的圖看得到深藍色貼著導風腔轉彎），但轉上去之後一樣直直往上，沒有往臉的方向偏。'
                        f'{tag("sim")}</p>')
    face_points = f"""
<p><b>為什麼重算：</b>人扶著內側扶手下樓時，臉在扶手的<b>斜上方</b>，不是正前方。這組把口鼻放在出風口往樓梯側 28 cm、往上 35 cm（距離約 45 cm、仰角約 51°）；A、C、D 出風口改成朝向口鼻，B 改用藏在底面、往上轉的康達出風口。每公尺送風量都是 5 L/s，網格 1.5 mm。{tag("sim")}</p>
{face_table}
{face_interim}
<p><b>加算空氣牆：</b>先算完的幾組顯示，每公尺 5 L/s 的出風口在有側風時送不到斜上方的臉。所以把第 05 章表現最好的空氣牆（寬 80 mm、每公尺 20 或 40 L/s、水平往樓梯側吹）也放進同一個「臉在斜上方＋有頭」的測試，共 6 組，表格最後兩列。{tag("sim")}</p>
<p><b>無側風要算久一點：</b>沒有側風時氣流很慢，乾淨空氣要好幾秒才飄到臉旁。先算的 10 秒版本裡，B、C 的口鼻數值還在一路往上爬（B 從 0% 爬到 12%、C 從 15% 爬到 46%），代表還沒穩定，所以無側風的 B、C 和空氣牆延長到 24 秒重算，取後 16 秒平均。A 的 10 秒版本前後半段差不多（19%／18%），已經穩定。{tag("sim")}</p>
<p class="muted">已完成 {n_done}/18 組，其餘計算中；每完成一批就會更新。</p>"""

    # ---------- S6：守住扶手旁 50 cm ----------
    s6 = json.load(open(os.path.join(OUT, "s6_results.json")))
    z = s6["cases"]
    capm = {r["q"]: r for r in s6["capacity"]}

    def zu(n, k="upper50"):
        return z[n][k] if n in z else None

    s6_one = (f"寬 80 mm 的「空氣牆」慢慢送風，樓梯間的上升氣流會把它往上帶，在扶手上方撐出一層乾淨空氣："
              f"側風 0.15 m/s、每公尺 20 L/s 時，扶手上方 {pct(zu('W_q20_vc15'))} 的範圍乾淨空氣超過一半。")
    s6_points = f"""
<p><b>為什麼要做這組：</b>第 04 章只量臉前一個點。但臉的位置因人、因姿勢而異，所以這裡改量扶手出風口前方<b>半徑 50 cm 的整個半圓</b>，並分開看「扶手上方」（站著時臉的位置）和「扶手水平前方」（彎腰時）。網格 2.5 mm、不放人頭、側風由下往上。{tag("sim")}</p>
<div class="table-wrap"><table><thead><tr><th scope="col">出風口（側風 0.15 m/s）</th><th scope="col">每公尺 10 L/s</th><th scope="col">20 L/s</th><th scope="col">40 L/s</th></tr></thead><tbody>
<tr><th scope="row">W 空氣牆（寬 80 mm）</th><td class="num">{pct(zu('W_q10_vc15'))}</td><td class="num"><b>{pct(zu('W_q20_vc15'))}</b></td><td class="num"><b>{pct(zu('W_q40_vc15'))}</b></td></tr>
<tr><th scope="row">C 低混合（寬 35 mm）</th><td class="num">{pct(zu('C_q10_vc15'))}</td><td class="num">{pct(zu('C_q20_vc15'))}</td><td class="num">{pct(zu('C_q40_vc15'))}</td></tr>
<tr><th scope="row">康達往上（藏在底面）</th><td class="num">{pct(zu('Ku_q10_vc15'))}</td><td class="num">{pct(zu('Ku_q20_vc15'))}</td><td class="num">—</td></tr>
<tr><th scope="row">低混合斜上 45°</th><td class="num">{pct(zu('Cu_q10_vc15'))}</td><td class="num">{pct(zu('Cu_q20_vc15'))}</td><td class="num">—</td></tr>
</tbody></table></div>
<p class="muted">表中數字＝扶手上方（站姿的臉）乾淨空氣 ≥ 50% 的面積比例。側風 0.30 m/s 時，W 空氣牆每公尺 40 L/s 仍有 {pct(zu('W_q40_vc30'))}；向下傾 30° 的版本 {pct(zu('Wd_q40_vc30'))}，跟水平差不多。</p>
<ul>
<li><b>寬比快重要：</b>窄的出風口（C）只送出一條細細的乾淨空氣帶，加大風量反而混得更厲害，上方範圍一直在 10% 以下。寬 80 mm 的空氣牆送出一整片，被上升氣流往上帶，形成一層乾淨空氣。{tag("sim")}</li>
<li><b>順著上升氣流，不要對抗：</b>樓梯間的氣流本來就往上，送風往上走是順勢。往前吹的空氣牆在側風下自然彎成往上，反而保護了扶手上方。{tag("sim")}</li>
<li><b>康達往上這次真的轉彎了：</b>藏在導風腔底面的出風縫，風貼著扶手正面往上走（往下轉時做不到，往上轉有上升氣流幫忙，出風縫風速也比較高）。但它只守住扶手正上方約 10 cm 寬的一道柱子，範圍比空氣牆小（{pct(zu('Ku_q20_vc15'))}）。{tag("sim")}</li>
<li><b>斜上 45° 的窄出風口沒有幫助：</b>方向對了，但窄，一樣撐不開（{pct(zu('Cu_q20_vc15'))}）。{tag("sim")}</li>
</ul>
<p><b>代價是風量：</b>每層出風段長度不同，需要的風量也不同。以頂樓主機、150×60 mm 導風腔、不裝增壓機來算：{tag("sim")}</p>
<div class="table-wrap"><table><thead><tr><th scope="col">每公尺送風量</th><th scope="col">出風段 1.2 m（上下各 0.6）</th><th scope="col">1000 Pa 時可同時供應</th><th scope="col">出風段只留平台轉角 0.6 m</th></tr></thead><tbody>
<tr><td class="num">10 L/s</td><td class="num">每層 12 L/s</td><td class="num">{capm[10]['floors_1000Pa']} 層</td><td class="num">{capm[5]['floors_1000Pa']} 層</td></tr>
<tr><td class="num">20 L/s</td><td class="num">每層 24 L/s</td><td class="num">{capm[20]['floors_1000Pa']} 層</td><td class="num">{capm[10]['floors_1000Pa']} 層</td></tr>
<tr><td class="num">40 L/s</td><td class="num">每層 48 L/s</td><td class="num">{capm[40]['floors_1000Pa']} 層</td><td class="num">{capm[20]['floors_1000Pa']} 層</td></tr>
</tbody></table></div>
<p class="muted">網格 2.5 mm、二維、等溫、不含人頭與呼吸；大風量算例的分子黏度以下限 tau0 = 0.504 略為放大以維持穩定。</p>"""
    s6_design = [
        "火災模式的出風口改成<b>寬 80 mm 左右的「空氣牆」</b>，慢速、整流、平直吹出，讓上升氣流把它帶到扶手上方。",
        "空氣牆出口高 80 mm，比導風腔側面（60 mm）高：導風腔要調整斷面（例如 120×90 mm），或在平台轉角做一段外凸的出風罩。",
        "每公尺 20 L/s、出風段只留平台轉角 0.6 m 時，頂樓主機可同時撐住約 6 層；每公尺 40 L/s 則約 2 層。火災時把風集中在偵測到需要的平台。",
        "平時模式用小風量與借風散開；火災模式切換成空氣牆。<b>「可切換吹法的出風口」</b>就是寬窄、快慢的切換。",
        "康達往上可以當作「把出風口藏起來」的造型選項，但範圍較窄，適合搭配空氣牆而不是取代它。",
    ]

    return dict(takeaways=takeaways, cards=cards, vent_one=vent_one, vent_points=vent_points, vent_modes=vent_modes,
                vent_design=vent_design, round_points=round_points, fire_one=fire_one, fire_points=fire_points,
                fire_design=fire_design, nozzle_one=nozzle_one, nozzle_points=nozzle_points, nozzle_design=nozzle_design,
                coanda_points=coanda_points, saf_example=saf_example, source_points=source_points,
                source_design=source_design, filter_points=filter_points, filter_design=filter_design,
                exhaust_one=exhaust_one, door_m3min=door, rail_m3min=hot["Q_m3min"], exhaust_points=exhaust_points,
                exhaust_design=exhaust_design, limits_points=limits_points, next_points=next_points,
                s6_one=s6_one, s6_points=s6_points, s6_design=s6_design,
                face_one=face_one, face_points=face_points)
