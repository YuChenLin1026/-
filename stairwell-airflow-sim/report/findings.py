"""報告的白話判讀文字。數字一律從計算結果帶入；CFD 段落在結果完成後人工檢查用語。"""


def build_findings(ctx):
    s1, s2, s3, s4 = ctx["s1"], ctx["s2"], ctx["s3"], ctx["s4"]
    saf, pct, tag, L = ctx["saf"], ctx["pct"], ctx["tag"], ctx["NZ_LABEL"]
    NZ = ["plain", "coanda", "coax", "amp"]

    # ---------- S1 / S3 / S4 數字 ----------
    op = {(r["fan"][0], r["filter"][:4]): r for r in s1["operating_points"] if r["D_mm"] == 34}
    sS, mM = op[("S", "濾材堵塞")], op[("M", "濾材堵塞")]
    u34 = s1["uniformity"]["34mm"]
    cyc = s3["cyclone"]
    rem = {(r["smoke"][:2], r["train"][:2]): r for r in s3["particle_removal"]}
    hot = next(c for c in s4["cases"] if c["gas"].startswith("200") and c["D_mm"] == 38 and c["P_Pa"] == 3000)
    door = s4["door_ref_m3min"]
    n_rails = round(door / hot["Q_m3min"])

    # ---------- CFD 數字 ----------
    def v(nz, c="head_vc00"):
        return saf(nz, c)

    have = {nz: all(v(nz, c) is not None for c in ("head_vc00", "head_vc15", "head_vc30")) for nz in NZ}
    done = all(have.values())
    ranked0 = sorted([nz for nz in NZ if v(nz) is not None], key=lambda n: -v(n))
    best0 = ranked0[0] if ranked0 else None
    ranked15 = sorted([nz for nz in NZ if v(nz, "head_vc15") is not None], key=lambda n: -v(n, "head_vc15"))
    best15 = ranked15[0] if ranked15 else None
    saf_example = v(best15, "head_vc15") if best15 else 0.3

    def short(nz):
        if not have[nz]:
            return "計算中"
        return f"無側風 {pct(v(nz))}、側風 0.15 m/s {pct(v(nz,'head_vc15'))}、0.30 m/s {pct(v(nz,'head_vc30'))}"

    def nz_card(nz, name):
        if not have[nz]:
            return dict(name=name, verdict="計算中", cls="mid", why="電腦模擬還在計算。", where="第 02 章")
        a, b, c = v(nz), v(nz, "head_vc15"), v(nz, "head_vc30")
        if nz == best0 and a >= 0.4:
            verdict, cls = "相對最好", "ok"
        elif a < 0.15:
            verdict, cls = "效果差", "bad"
        else:
            verdict, cls = "效果有限", "mid"
        return dict(name=name, verdict=verdict, cls=cls,
                    why=f"臉在 35 cm 處吸到的乾淨空氣：沒有風時 {pct(a)}，側風 0.15 m/s 時 {pct(b)}，0.30 m/s 時 {pct(c)}。",
                    where="第 02 章")

    takeaways = [
        dict(big="0%", text="吸樓梯間的空氣、用濾網過濾再送出，口鼻的 CO <b>一點都不會減少</b>。CO 是氣體，濾網擋不住。"),
        dict(big=(pct(v(best0)) if best0 else "計算中"),
             text=(f"四種出風口裡表現最好的（{L[best0]}），臉在 35 cm、沒有風時，吸到的空氣約 {pct(v(best0))} 來自出風口；"
                   f"有 0.15 m/s 的側風時，最好的一種剩 {pct(v(best15,'head_vc15'))}。" if best0 and best15 else "出風口的電腦模擬計算中。")),
        dict(big=f"≈{n_rails}", text=f"一扇敞開的門的風量，相當於約 {n_rails} 根扶手同時全力排煙。扶手當排煙管<b>不可行</b>。"),
    ]

    cards = [
        dict(name="緊湊型離心風機", verdict="可行", cls="ok",
             why=f"每層一台中型鼓風機就夠：濾網堵塞時還有 {mM['Q_Ls']:.1f} L/s（需要 6 L/s），耗電約 {mM['P_elec_W']:.0f} W。", where="第 05 章"),
        nz_card("coax", "低混合率同軸噴嘴"),
        nz_card("coanda", "康達曲面導流"),
        nz_card("plain", "一般定向噴嘴"),
        nz_card("amp", "氣流倍增式噴嘴"),
        dict(name="初濾＋HEPA", verdict="只擋煙粒", cls="mid", why="火災煙粒擋下 99.9% 以上；CO 擋下 0%。", where="第 04 章"),
        dict(name="活性碳、觸媒", verdict="要做實驗", cls="mid",
             why="電腦算不出來。活性碳幾乎擋不住 CO；觸媒有機會，但怕濕氣、有壽命，必須實測。", where="第 04 章"),
        dict(name="氣源", verdict="必須獨立", cls="ok",
             why="吸樓梯間空氣過濾後送出，CO 一點都沒少。只有獨立乾淨氣源，出風口才有意義。", where="第 03 章"),
        dict(name="氣旋分離", verdict="不採用", cls="bad",
             why=f"火災煙粒太小，氣旋只抓到約 {pct(rem[('有焰','氣旋')]['removal_mass'])}（重量），還要 {cyc['dP_Pa']:.0f} Pa 的推力。", where="第 04 章"),
        dict(name="扶手當排煙管", verdict="不採用", cls="bad",
             why=f"風機開到 3000 Pa，整根扶手也只排得出約 {hot['Q_m3min']:.2f} m³/min，是一扇門的 {pct(hot['ratio_to_door'],1)}。", where="第 06 章"),
        dict(name="吸樓梯間空氣過濾後送去呼吸", verdict="不採用", cls="bad",
             why="CO、缺氧、高溫，濾網都處理不了。", where="第 03 章"),
    ]

    # ---------- 第 02 章 出風口 ----------
    if done:
        nozzle_one = FINAL_NOZZLE_ONE(s2, v, L, pct)
        nozzle_points = FINAL_NOZZLE_POINTS(s2, v, L, pct)
        nozzle_design = FINAL_NOZZLE_DESIGN(s2, v, L, pct)
    else:
        nozzle_one = "出風口的電腦模擬還在計算。"
        rows = "".join(f"<li><b>{L[nz]}</b>：{short(nz)}</li>" for nz in NZ)
        nozzle_points = f"<p>目前結果（臉在 35 cm 處吸到的乾淨空氣比例）：</p><ul>{rows}</ul>"
        nozzle_design = ["結果完成後補上。"]

    r15 = s2.get("coanda_r15_head_vc00")
    coanda_points = COANDA_POINTS(r15, v, pct)

    # ---------- 第 03 章 氣源 ----------
    source_points = f"""
<p><b>為什麼？</b>出風口只決定「吸到的空氣有幾成來自出風口」，但送出去的空氣本身乾不乾淨，是氣源決定的。</p>
<ul>
<li><b>吸樓梯間的空氣：</b>濾網只擋得住煙粒。CO 照樣穿過去，送出的空氣 CO 和周圍一樣多，所以不管出風口設計多好，口鼻的 CO 都一樣。缺氧和高溫也一樣，濾網補不了氧氣、也降不了溫。{tag("sim")}</li>
<li><b>獨立乾淨氣源：</b>送出的空氣沒有 CO，口鼻的 CO 就降低「乾淨空氣比例」那麼多。例如比例 {pct(saf_example)}，CO 就剩 {pct(1-saf_example)}。{tag("sim")}</li>
</ul>
<p><b>乾淨氣源從哪來？</b></p>
<ul>
<li><b>室外進氣：</b>進氣口本身可能被火災煙污染，要遠離窗戶、開口和排煙口，進氣端也要裝 CO 感測，污染時自動關閉。{tag("tbd")}</li>
<li><b>壓縮空氣鋼瓶：</b>空氣乾淨，但鋼瓶容量、壓力調節、認證與定期檢驗都要專業評估。之前討論的「約一小時」只是粗算。{tag("tbd")}</li>
<li><b>換一個思路：</b>如果目標真的是「在濃煙中呼吸」，在轉角主機裡放經過認證的逃生頭罩（例如符合 EN 403 的產品），比開放式送風更直接，也已經有標準可以依循。台灣的法規和產品認證要另外查證。{tag("inf")}{tag("tbd")}</li>
</ul>"""
    source_design = [
        "主機的進氣口<b>不能</b>從樓梯間吸氣後直接送給人；這條路已經被模擬排除。",
        "如果保留送風，提案要先回答「乾淨空氣從哪裡來」，這比出風口造型更重要。",
        "可以把「逃生頭罩收納」當成轉角主機的功能選項，跟送風方案並列比較。",
    ]

    # ---------- 第 04 章 濾網 ----------
    filter_points = f"""
<ul>
<li><b>HEPA 擋得住煙粒：</b>初濾＋HEPA 對兩種假設的火災煙，煙粒都擋下 99.9% 以上。{tag("sim")}{tag("std")}</li>
<li><b>氣旋擋不住：</b>氣旋靠旋轉把粒子甩出去，粒子越小越甩不出去。一般 10 cm 大小的氣旋，一半抓得到、一半抓不到的粒子大小約 {cyc["d50_um"]:.1f} µm，但火災煙粒大多不到 1 µm，所以有焰燃燒的煙只抓到約 {pct(rem[("有焰","氣旋")]["removal_mass"])}。做小一點可以抓更小的粒子，但需要的推力會暴增到約 {s3["cyclone_small"]["dP_Pa"]/1000:.1f} kPa。{tag("sim")}</li>
<li><b>CO 擋不住：</b>CO 是氣體分子，比任何濾網的孔都小很多。活性碳靠「吸附」抓氣體，但對 CO 幾乎沒用。{tag("inf")}</li>
<li><b>觸媒有機會，但要實驗：</b>霍加拉（Hopcalite）類觸媒能把 CO 變成 CO₂，認證的逃生頭罩就用這類材料。不過它怕濕氣、有壽命、反應會發熱，而且頭罩是密閉、只給一個人用的小風量裝置。這份報告不算它的效果。{tag("tbd")}</li>
</ul>"""
    filter_design = [
        "主機的濾網區可以保留（HEPA 處理煙粒），但宣傳上<b>不能說「淨化火場空氣」</b>。",
        "氣旋從設計中拿掉，省下體積和風機推力。",
        "濾網會堵塞：要有好換的濾網門，以及「濾網該換了」的提示燈（第 05 章的風機要能撐住堵塞時的阻力）。",
    ]

    # ---------- 第 05 章 風機與管子 ----------
    duct_one = f"每層一台約 {mM['P_elec_W']:.0f} W 的中型風機就夠，但扶手管子要夠粗，出風口裡要加一層均流層。"
    duct_points = f"""
<p>設定：每層平台一台主機，往上、往下各送一段；只在靠近平台的 0.6 m 開出風口。照每公尺 5 L/s 計算，一台主機要送 <b>6 L/s（約 22 m³/h）</b>。{tag("asm")}</p>
<ul>
<li><b>風機：</b>中型鼓風機（假設曲線 M）在濾網堵塞時還有 {mM["Q_Ls"]:.1f} L/s；小型的（曲線 S）濾網新的時候夠用，堵塞後只剩 {sS["Q_Ls"]:.1f} L/s，不夠。{tag("sim")}{tag("asm")}</li>
<li><b>管子粗細：</b>扶手內的風道從 38 mm 縮到 30 mm，阻力大約變成 2.5–3 倍。外觀可以改，風道截面要先保住。{tag("sim")}</li>
<li><b>均流層：</b>沒有均流層時，風會擠到出風段末端，最少的地方只有最多的 {u34["2.0"]*100:.0f}%。加一層約 20–30 Pa 阻力的均流層（多孔板、金屬網或蜂巢），每一段才會平均出風（{u34["30.0"]*100:.0f}%）。這層同時也是低混合率噴嘴需要的整流層。{tag("sim")}</li>
<li><b>出風口不能整條都開：</b>一台主機的風只夠約 2 m 出風口，應該集中在平台轉角、會停留或低姿勢的地方。{tag("inf")}</li>
</ul>"""
    duct_design = [
        "扶手風道內徑建議<b>不小於 34 mm</b>，在畫外型前先保留。",
        "出風口內加一層均流層（阻力約 20–30 Pa），可以和出風格柵整合成一個零件。",
        "每層一台主機、出風口集中在平台上下各約 0.6 m，其餘扶手只做光與觸覺導引。",
        "風機選型要用「濾網堵塞時」的阻力來選，不是用新濾網。",
    ]

    # ---------- 第 06 章 排煙 ----------
    exhaust_one = f"不行。整棟一根扶手全力排煙，量也只有一扇敞開的門的 {pct(hot['ratio_to_door'],1)}。"
    exhaust_points = f"""
<ul>
<li>假設整棟 10 層共用一根 70 m 的扶手管子。就算風機推到 3000 Pa、內徑 38 mm，200 °C 的熱煙也只排得出約 <b>{hot["Q_m3min"]:.2f} m³/min</b>，管內風速已經 {hot["V_ms"]:.0f} m/s。{tag("sim")}</li>
<li>一扇敞開的門（0.9 × 2.0 m）以 1 m/s 通過的風量約 {door:.0f} m³/min，差了兩個數量級。{tag("asm")}</li>
<li>熱煙流過金屬扶手會把扶手加熱，手握上去可能燙傷（燙傷溫度門檻要依 ISO 13732-1 查證）；管子有任何漏縫，煙也會直接漏到逃生路線上。{tag("inf")}{tag("tbd")}</li>
</ul>"""
    exhaust_design = [
        "提案中拿掉「扶手排煙」，排煙交給建築原有的排煙設備。",
        "扶手主機可以接收消防系統的訊號，只負責導引與狀態顯示。",
    ]

    # ---------- 第 07 章 ----------
    limits_points = """
<p><b>這次電腦模擬做不到的事：</b></p>
<ul>
<li><b>只算了一個剖面（2D）：</b>連續出風縫的情況比較接近；如果出風口是一個個圓孔，氣流會散得更快，乾淨空氣比例會更低。</li>
<li><b>沒有算溫度：</b>真實火場的煙是熱的、送出的空氣相對是冷的，冷空氣會往下沉。這會改變氣流路線。</li>
<li><b>沒有算呼吸：</b>吸氣時會把口鼻周圍的空氣一起吸進來，吸得比送風多時，會吸到更多周圍空氣。</li>
<li><b>人是不動的：</b>人沿著扶手走（約 1 m/s）帶起的風，2D 模型算不到，這很可能是最大的干擾。</li>
<li><b>格子大小：</b>1 mm 的格子對氣流倍增式的細縫還是太粗（細縫從 2 mm 放寬成 3 mm），這一組的不確定性最大。也還沒有做「格子再切細，結果會不會變」的檢查。</li>
<li><b>假設的數字：</b>風機曲線、濾網阻力、煙粒大小、側風速度都是先假設的，換成實際型號和量測值後要重算。</li>
</ul>
<p>所以這次的結果，適合用來<b>比較四種出風口的高低</b>、<b>排除不可行的方案</b>，不適合當成真實火場的預測數字。</p>"""
    next_points = """
<p><b>建議的下一步：</b></p>
<ol>
<li><b>桌上型實驗（上圖）：</b>3D 列印四種出風口（同樣送風量），配頭模型、口鼻取樣管和 CO₂ 感測器。箱子裡放 CO₂、出風口送乾淨空氣，用和電腦相同的方法算乾淨空氣比例；再用小風扇加側風。</li>
<li><b>3D、含溫度的電腦模擬：</b>確認熱煙層、冷空氣下沉、人走動時，四種出風口的排名有沒有改變。</li>
<li><b>先決定扶手剖面：</b>保留風道內徑（建議 ≥ 34 mm）和均流層的空間，再做外型。</li>
<li><b>決定氣源：</b>在室外進氣、壓縮空氣、或改用認證逃生頭罩之間選擇，並請消防設備師確認法規。</li>
<li><b>完成以上之前，不做任何真實煙霧或火場測試。</b></li>
</ol>"""

    return dict(takeaways=takeaways, cards=cards, nozzle_one=nozzle_one, nozzle_points=nozzle_points,
                nozzle_design=nozzle_design, coanda_points=coanda_points, saf_example=saf_example,
                source_points=source_points, source_design=source_design, filter_points=filter_points,
                filter_design=filter_design, duct_one=duct_one, duct_points=duct_points, duct_design=duct_design,
                exhaust_one=exhaust_one, door_m3min=door, rail_m3min=hot["Q_m3min"], exhaust_points=exhaust_points,
                exhaust_design=exhaust_design, limits_points=limits_points, next_points=next_points)


# ---------- CFD 判讀（結果完成後依實際數字撰寫） ----------
def COANDA_POINTS(r15, v, pct):
    if r15 is None:
        return "<p>計算中。</p>"
    r45 = v("coanda")
    txt = (f"<p>第一版康達出風口的曲面半徑只有 15 mm（出風縫 6 mm 的 2.5 倍）。模擬中氣流<b>沒有沿曲面轉彎</b>，"
           f"直接往下衝，口鼻吸到的乾淨空氣只有約 {pct(r15['mean'])}。曲面太彎，氣流「貼不住」。</p>")
    if r45 is not None:
        txt += f"<p>修正版把半徑加大到 45 mm（縫寬的 7.5 倍），口鼻的乾淨空氣比例變成 {pct(r45)}。</p>"
    else:
        txt += "<p>修正版（半徑 45 mm、縫寬的 7.5 倍）計算中。</p>"
    return txt


def FINAL_NOZZLE_ONE(s2, v, L, pct):
    return "（待撰寫）"


def FINAL_NOZZLE_POINTS(s2, v, L, pct):
    return "<p>（待撰寫）</p>"


def FINAL_NOZZLE_DESIGN(s2, v, L, pct):
    return ["（待撰寫）"]
