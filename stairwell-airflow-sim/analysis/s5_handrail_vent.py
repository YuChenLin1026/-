"""
S5 扶手新風帶（日常通風）：頂樓主機＋扶手一體導風腔，增壓機間距與「有人才啟動」的評估。

模型：
  10 層樓，頂樓主機從扶手導風腔往下送。每層一段 7 m（4 個彎、6 個接頭），
  第 i 段（由上往下）要負擔它下方所有「啟動中」樓層的風量。
  每層出風口有 30 Pa 均流層（確保各層出風平均）。
  增壓機每 N 層一台：每台只需推動到下一台之前的那幾段；增壓機本身進出口損失 K=1.5。
  壓損：Darcy–Weisbach（Haaland）＋局部損失；矩形導風腔用水力直徑。
有人才啟動：
  導風腔內原本的「舊空氣」要先被推出去，再加上新鮮空氣走到該層的時間，就是需要提前啟動的時間。
  耗電 = 風量 × 壓力 ÷ 效率（30%，假設）。
"""
import json
import os

import numpy as np

from common import OUT, RHO, NU, SERIES, TEXT1, TEXT2, MUTED, CRIT, plt, save
from s1_duct import friction_factor

FLOORS = 10
SEG_L = 7.0
DP_OUTLET = 30.0
ETA = 0.30
CAVITIES = {"導風腔 100×50 mm": (0.10, 0.05), "導風腔 150×60 mm": (0.15, 0.06)}


def seg_dp(Q, a, b, L=SEG_L, nb=4, nj=6):
    A = a * b
    Dh = 2 * a * b / (a + b)
    if Q <= 0:
        return 0.0, 0.0
    V = Q / A
    pd = 0.5 * RHO * V * V
    f = friction_factor(V * Dh / NU, Dh)
    return f * L / Dh * pd + (nb * 0.3 + nj * 0.1) * pd, V


def system(a, b, q, active, spacing):
    """active: 啟動中的樓層（1=最底層 … 10=頂樓）；spacing: 每 N 層一台增壓機（None=只有頂樓主機）。
    回傳 頂樓主機壓力、最大增壓機壓力、各段流速最大值。"""
    flows = []
    for i in range(FLOORS):            # 段 i：頂樓往下第 i 段，到達第 (10-i) 層
        floor_here = FLOORS - i
        flows.append(q * sum(1 for f in active if f <= floor_here))
    lowest = min(active)
    n_seg = FLOORS - lowest + 1         # 需要用到的段數
    groups = []
    step = spacing or FLOORS
    for g0 in range(0, n_seg, step):
        groups.append(list(range(g0, min(g0 + step, n_seg))))
    pressures, vmax = [], 0.0
    for gi, g in enumerate(groups):
        p = DP_OUTLET
        for i in g:
            dp, V = seg_dp(flows[i], a, b)
            p += dp
            vmax = max(vmax, V)
        if gi > 0:
            A = a * b
            V0 = flows[g[0]] / A
            p += 1.5 * 0.5 * RHO * V0 * V0
        pressures.append(p)
    return pressures[0], max(pressures[1:], default=0.0), vmax, flows


def main():
    res = {"assumptions": dict(floors=FLOORS, seg_L=SEG_L, dp_outlet=DP_OUTLET, eta=ETA)}

    # ---- 1. 增壓機間距（全部 10 層同時運轉）----
    rows = []
    for cname, (a, b) in CAVITIES.items():
        for q in (3e-3, 5e-3):
            for sp in (None, 5, 3, 2, 1):
                p_roof, p_boost, vmax, _ = system(a, b, q, list(range(1, FLOORS + 1)), sp)
                rows.append(dict(cavity=cname, q_Ls=q * 1000, spacing=sp or 0, p_roof=p_roof, p_boost=p_boost, vmax=vmax))
    res["spacing_all_on"] = rows

    # ---- 2. 有人才啟動：同時只有 k 層運轉（最壞情況：最底下的 k 層，風要走最遠）----
    rows2 = []
    for cname, (a, b) in CAVITIES.items():
        for q in (3e-3, 5e-3):
            for k in (1, 2, 3, 5, 10):
                act = list(range(1, k + 1))
                p_roof, _, vmax, _ = system(a, b, q, act, None)
                rows2.append(dict(cavity=cname, q_Ls=q * 1000, k=k, p_roof=p_roof, vmax=vmax,
                                  P_W=q * k * p_roof / ETA))
    res["on_demand_no_booster"] = rows2

    # ---- 3. 提前啟動時間：先把導風腔裡的舊空氣推走 ----
    rows3 = []
    for cname, (a, b) in CAVITIES.items():
        A = a * b
        for q in (3e-3, 5e-3):
            for k in (1, 3):
                Qtot = q * k
                # 舊空氣體積＝頂樓到最底層運轉樓層的導風腔體積；以總風量推出
                vol = A * SEG_L * FLOORS
                t_flush = vol / Qtot
                rows3.append(dict(cavity=cname, q_Ls=q * 1000, k=k, duct_vol_L=vol * 1000, t_flush_s=t_flush))
    res["prestart"] = rows3

    # ---- 4. 一天的耗電：一直開 vs 有人才開 ----
    a, b = CAVITIES["導風腔 150×60 mm"]
    q = 5e-3
    p_all, _, _, _ = system(a, b, q, list(range(1, FLOORS + 1)), None)
    P_all = q * FLOORS * p_all / ETA
    p3, _, _, _ = system(a, b, q, [1, 2, 3], None)
    P3 = q * 3 * p3 / ETA
    res["energy"] = dict(P_continuous_W=P_all, kWh_day_continuous=P_all * 24 / 1000,
                         P_3floors_W=P3, kWh_day_ondemand_2h=P3 * 2 / 1000)

    # ---- 圖：增壓機間距 ----
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    labels = ["不裝", "每 5 層", "每 3 層", "每 2 層", "每層"]
    sps = [0, 5, 3, 2, 1]
    for ax, (cname, _) in zip(axs, CAVITIES.items()):
        for qq, col in zip((3.0, 5.0), (SERIES[0], SERIES[1])):
            rr = [next(r for r in rows if r["cavity"] == cname and r["q_Ls"] == qq and r["spacing"] == s) for s in sps]
            ax.plot(range(5), [r["p_roof"] for r in rr], "o-", color=col, label=f"每層 {qq:.0f} L/s：頂樓主機")
            ax.plot(range(5), [r["p_boost"] if r["spacing"] else np.nan for r in rr], "s--", color=col, alpha=0.8,
                    label=f"每層 {qq:.0f} L/s：最吃力的增壓機")
        ax.axhspan(0, 150, color=SERIES[2], alpha=0.10, lw=0)
        ax.text(4.1, 75, "小型安靜風機\n可以負擔", fontsize=8.5, color=TEXT2, ha="right", va="center")
        ax.set_xticks(range(5), labels)
        ax.set_yscale("log")
        ax.set_yticks([30, 100, 300, 1000, 3000], ["30", "100", "300", "1000", "3000"])
        ax.minorticks_off()
        ax.set_title(cname + "，10 層全開", loc="left", fontsize=11)
        ax.set_xlabel("增壓機裝多密")
    axs[0].set_ylabel("需要的壓力（Pa）")
    h, l = axs[1].get_legend_handles_labels()
    fig.suptitle("增壓機不必每層裝：導風腔夠大時，頂樓主機一台就推得動", x=0.01, ha="left", fontsize=12)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.legend(h, l, loc="lower center", ncol=4, fontsize=9, frameon=False)
    save(fig, "s5_spacing.png")

    # ---- 圖：有人才啟動 ----
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    for (cname, _), col in zip(CAVITIES.items(), (SERIES[0], SERIES[2])):
        rr = [r for r in rows2 if r["cavity"] == cname and r["q_Ls"] == 5.0]
        ax.plot([r["k"] for r in rr], [r["p_roof"] for r in rr], "o-", color=col, label=f"{cname}（每層 5 L/s）")
    ax.axhline(500, color=CRIT, lw=1, ls="--")
    ax.text(10, 520, "中型風機約 500 Pa", ha="right", fontsize=9, color=CRIT)
    ax.set_xlabel("同時有人、正在送風的樓層數")
    ax.set_ylabel("頂樓主機需要的壓力（Pa）")
    ax.set_xticks([1, 2, 3, 5, 10])
    ax.set_title("有人才送風：同時開的樓層越少，主機越輕鬆（不裝增壓機）", loc="left", fontsize=12)
    ax.legend(fontsize=9)
    save(fig, "s5_ondemand.png")

    with open(os.path.join(OUT, "s5_results.json"), "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)

    print("== 1. 增壓機間距（10 層全開）==")
    for r in rows:
        sp = "不裝" if r["spacing"] == 0 else f"每{r['spacing']}層"
        print(f"{r['cavity']} 每層{r['q_Ls']:.0f}L/s {sp:5s} 頂樓 {r['p_roof']:6.0f} Pa  增壓機最大 {r['p_boost']:5.0f} Pa  最大風速 {r['vmax']:4.1f} m/s")
    print("== 2. 有人才啟動，不裝增壓機（最底下 k 層）==")
    for r in rows2:
        print(f"{r['cavity']} 每層{r['q_Ls']:.0f}L/s 同時{r['k']:2d}層 頂樓 {r['p_roof']:6.0f} Pa 風速 {r['vmax']:4.1f} m/s 耗電 {r['P_W']:5.1f} W")
    print("== 3. 提前啟動 ==")
    for r in rows3:
        print(f"{r['cavity']} 每層{r['q_Ls']:.0f}L/s 同時{r['k']}層 導風腔 {r['duct_vol_L']:.0f} L 推完要 {r['t_flush_s']:.0f} s")
    print("== 4. 耗電 ==", {k: round(v, 2) for k, v in res["energy"].items()})


if __name__ == "__main__":
    main()
