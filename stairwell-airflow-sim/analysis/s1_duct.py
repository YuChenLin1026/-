"""
S1 扶手風道 + 風機工作點 + 出風均勻度（一維管網模型）

量測／計算方法：
  1. 系統阻力曲線 ΔP_sys(Q)：
       沿程損失  Darcy–Weisbach，摩擦係數：層流 64/Re，紊流 Haaland（粗糙度 1.5 µm 拉製金屬管），
                 2300<Re<4000 線性內插
       局部損失  ΔP = K·½ρV²（進氣格柵、三通閥、分歧三通、彎頭、接頭、出口）
       濾材      ΔP 與風量成正比（低速濾材的達西流），以「額定風量下壓損」標定
  2. 風機曲線：P = Pmax·(1-(Q/Qmax)²)，三條「假設」曲線（S/M/L），需換成實際型錄。
  3. 工作點：系統曲線與風機曲線交點（二分法）。
  4. 出風均勻度：把一段出風口離散成 N 個出風孔（死端分配歧管），
     由末端往上游逐孔計算：孔流量 Qi = sqrt(Pi/Ro)，
     上游壓力 = 下游壓力 + 摩擦損失 − 靜壓回升（回升係數 0.8），
     用二分法調整末端壓力使總流量 = 分支流量，得到 min/max 孔流量比。

服務範圍假設（每層一台主機，位於樓梯平台）：
  主機 → 三通閥 → 上、下兩分支；每分支扶手風道 3.5 m，含 4 個彎頭、3 個接頭，
  分支末段 0.6 m 開出風口；出風量設定 q = 5 L/s/m（與 CFD 相同）。
"""
import json
import os

import numpy as np

from common import CRIT, MUTED, NOZZLE_COLOR, OUT, RHO, NU, SERIES, TEXT1, TEXT2, plt, save

EPS = 1.5e-6
Q_PER_M = 5.0e-3        # m^3/s per m of outlet
L_OUT = 0.6             # 每分支出風口長度 m
L_BRANCH = 3.5          # 每分支風道長度 m
N_BRANCH = 2
Q_BRANCH = Q_PER_M * L_OUT
Q_TOTAL = Q_BRANCH * N_BRANCH

FANS = {  # 假設曲線：Pmax [Pa], Qmax [m^3/h]
    "S（小型 鼓風機，假設）": (400.0, 30.0),
    "M（中型 鼓風機，假設）": (900.0, 60.0),
    "L（管道離心，假設）": (1800.0, 120.0),
}
FILTERS = {  # 每段濾材在 60 m3/h 下的壓損 [Pa]
    "無濾材": dict(pre=0, hepa=0, carbon=0),
    "濾材全新": dict(pre=25, hepa=150, carbon=40),
    "濾材堵塞（HEPA×2、初濾×3）": dict(pre=75, hepa=300, carbon=40),
}
Q_FILTER_RATED = 60.0 / 3600


def friction_factor(Re, D):
    Re = np.maximum(Re, 1e-9)
    lam = 64.0 / Re
    turb = (-1.8 * np.log10((EPS / D / 3.7) ** 1.11 + 6.9 / Re)) ** -2
    w = np.clip((Re - 2300) / 1700, 0, 1)
    return np.where(Re < 2300, lam, (1 - w) * 64 / 2300 + w * turb) if np.ndim(Re) else (
        lam if Re < 2300 else (1 - w) * 64 / 2300 + w * turb)


def dyn(Q, D):
    V = Q / (np.pi * D * D / 4)
    return 0.5 * RHO * V * V, V


def branch_dp(Qb, D, dp_equalizer):
    pd, V = dyn(Qb, D)
    Re = V * D / NU
    f = friction_factor(Re, D)
    dp = f * L_BRANCH / D * pd
    dp += (1.0 + 4 * 0.3 + 3 * 0.1) * pd       # 分歧三通 + 彎頭 + 接頭
    dp += dp_equalizer * (Qb / Q_BRANCH) ** 2  # 出風口均流板（設計壓降，隨流量平方）
    return dp


def system_dp(Q, D, filt, dp_equalizer, D_host=0.05):
    pd_h, _ = dyn(Q, D_host)
    dp = 1.5 * pd_h                              # 進氣格柵
    dp += sum(filt.values()) * Q / Q_FILTER_RATED
    pd, _ = dyn(Q / N_BRANCH, D)
    dp += 2.0 * pd                               # 三通分流閥
    dp += branch_dp(Q / N_BRANCH, D, dp_equalizer)
    return dp


def fan_p(Q, fan):
    Pmax, Qmax = fan
    return Pmax * (1 - (Q / (Qmax / 3600)) ** 2)


def operating_point(D, fan, filt, dp_eq):
    lo, hi = 0.0, fan[1] / 3600
    for _ in range(80):
        m = 0.5 * (lo + hi)
        if fan_p(m, fan) > system_dp(m, D, filt, dp_eq):
            lo = m
        else:
            hi = m
    Q = 0.5 * (lo + hi)
    return Q, system_dp(Q, D, filt, dp_eq)


def manifold_uniformity(D, Qb, dp_out_nom, N=24, regain=0.8):
    """死端分配歧管：回傳各孔流量（由入口端到末端）。"""
    dx = L_OUT / N
    q_nom = Qb / N
    Ro = dp_out_nom / q_nom ** 2
    A = np.pi * D * D / 4

    def march(pN):
        qs = np.zeros(N)
        p = pN
        Qd = 0.0
        for i in range(N - 1, -1, -1):
            qs[i] = np.sqrt(max(p, 0) / Ro)
            Qd_up = Qd + qs[i]
            V_up, V_dn = Qd_up / A, Qd / A
            Re = max(V_up * D / NU, 1e-6)
            f = friction_factor(Re, D)
            p = p + f * dx / D * 0.5 * RHO * V_up ** 2 - regain * 0.5 * RHO * (V_up ** 2 - V_dn ** 2)
            Qd = Qd_up
        return qs, Qd

    lo, hi = 0.0, dp_out_nom * 20 + 50
    for _ in range(100):
        m = 0.5 * (lo + hi)
        _, Qd = march(m)
        if Qd < Qb:
            lo = m
        else:
            hi = m
    qs, _ = march(0.5 * (lo + hi))
    return qs


def main():
    res = {"assumptions": dict(q_per_m_Ls=Q_PER_M * 1000, L_out_per_branch=L_OUT,
                               L_branch=L_BRANCH, Q_total_Ls=Q_TOTAL * 1000,
                               fans=FANS, filters_Pa_at_60m3h=FILTERS)}
    Ds = [0.030, 0.034, 0.038]
    dp_eq = 30.0

    # ---- 圖 1：D=34 mm 的系統曲線 vs 風機曲線 ----
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    Qs = np.linspace(0.0, 120 / 3600, 300)
    fan_styles = ["-", "--", ":"]
    for (fname, fan), ls in zip(FANS.items(), fan_styles):
        m = fan_p(Qs, fan) >= 0
        ax.plot(Qs[m] * 1000, fan_p(Qs[m], fan), color=TEXT1, ls=ls, lw=1.6)
        ax.annotate(f"風機 {fname.split('（')[0]}", (Qs[m][-1] * 1000, 0), xytext=(-4, 8),
                    textcoords="offset points", ha="right", fontsize=9, color=TEXT2)
    for (lbl, filt), col in zip(FILTERS.items(), SERIES[:3]):
        ax.plot(Qs * 1000, [system_dp(q, 0.034, filt, dp_eq) for q in Qs], color=col, label=f"系統阻力：{lbl}")
    ax.axvline(Q_TOTAL * 1000, color=CRIT, lw=1.2, ls="-.")
    ax.annotate(f"需求 {Q_TOTAL*1000:.0f} L/s\n(2 分支 × 0.6 m × 5 L/s/m)", (Q_TOTAL * 1000, 1650),
                xytext=(6, 0), textcoords="offset points", fontsize=9, color=CRIT)
    ax.set_xlim(0, 34)
    ax.set_ylim(0, 1900)
    ax.set_xlabel("主機總風量 Q（L/s）")
    ax.set_ylabel("靜壓（Pa）")
    ax.set_title("S1｜風機曲線與系統阻力（扶手風道內徑 34 mm、每層一台主機）", loc="left", fontsize=12)
    ax.legend(loc="upper right", fontsize=9)
    save(fig, "s1_fan_system.png")

    # ---- 表：各管徑 × 濾材 × 風機 的工作點 ----
    table = []
    for D in Ds:
        for flbl, filt in FILTERS.items():
            for fname, fan in FANS.items():
                Q, dp = operating_point(D, fan, filt, dp_eq)
                P_elec = Q * dp / 0.30
                table.append(dict(D_mm=D * 1000, filter=flbl, fan=fname, Q_Ls=Q * 1000, dP_Pa=dp,
                                  outlet_m=Q / Q_PER_M, P_elec_W=P_elec, meets=Q >= Q_TOTAL))
    res["operating_points"] = table

    # ---- 圖 2：沿程壓損對管徑的敏感度 ----
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    Dg = np.linspace(0.024, 0.044, 60)
    for qb, col in zip([2e-3, 3e-3, 5e-3], SERIES[:3]):
        ax.plot(Dg * 1000, [branch_dp(qb, d, 0) for d in Dg], color=col, label=f"分支風量 {qb*1000:.0f} L/s")
    ax.set_xlabel("扶手風道內徑（mm）")
    ax.set_ylabel("一個分支的風道壓損（Pa）")
    ax.set_yscale("log")
    ax.set_yticks([1, 3, 10, 30, 100, 300, 1000], ["1", "3", "10", "30", "100", "300", "1000"])
    ax.minorticks_off()
    ax.set_title("S1｜風道壓損對內徑非常敏感（3.5 m 分支，不含濾材與均流板）", loc="left", fontsize=12)
    ax.legend(fontsize=9)
    save(fig, "s1_diameter.png")

    # ---- 圖 3：出風均勻度 vs 均流板壓降 ----
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw=dict(width_ratios=[1.1, 1]))
    pds = np.array([1, 2, 5, 10, 20, 30, 50, 100], float)
    uni = {}
    for D, col in zip(Ds, SERIES[:3]):
        u = []
        for p in pds:
            qs = manifold_uniformity(D, Q_BRANCH, p)
            u.append(qs.min() / qs.max())
        uni[D] = u
        axs[0].plot(pds, np.array(u) * 100, "o-", color=col, ms=5, label=f"內徑 {D*1000:.0f} mm")
    axs[0].axhline(90, color=MUTED, lw=1, ls="--")
    axs[0].annotate("目標：最小/最大 ≥ 90%", (1.1, 91), fontsize=9, color=TEXT2)
    axs[0].set_xscale("log")
    axs[0].set_xticks([1, 2, 5, 10, 20, 50, 100], ["1", "2", "5", "10", "20", "50", "100"])
    axs[0].minorticks_off()
    axs[0].set_xlabel("出風口均流板設計壓降（Pa）")
    axs[0].set_ylabel("出風均勻度 最小/最大（%）")
    axs[0].set_title("出風口需要「刻意加阻力」才會均勻", loc="left", fontsize=11)
    axs[0].legend(fontsize=9)
    for p, col in zip([2, 30], [SERIES[1], SERIES[2]]):
        qs = manifold_uniformity(0.034, Q_BRANCH, p)
        x = (np.arange(len(qs)) + 0.5) / len(qs) * L_OUT * 100
        axs[1].plot(x, qs / qs.mean() * 100, color=col, label=f"均流板 {p} Pa")
    axs[1].set_xlabel("沿出風段位置（cm，0 = 進風端）")
    axs[1].set_ylabel("各孔流量／平均（%）")
    axs[1].set_title("內徑 34 mm、分支 3 L/s", loc="left", fontsize=11)
    axs[1].legend(fontsize=9)
    save(fig, "s1_uniformity.png")
    res["uniformity"] = {f"{int(D*1000)}mm": dict(zip(map(float, pds), map(float, u))) for D, u in uni.items()}
    pd34, V34 = dyn(Q_BRANCH, 0.034)
    res["branch_velocity_34mm"] = dict(V=float(V34), dyn_Pa=float(pd34))

    with open(os.path.join(OUT, "s1_results.json"), "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)
    for r in table:
        if r["D_mm"] == 34:
            print(f"{r['D_mm']:.0f}mm {r['filter']:22s} {r['fan']:18s} Q={r['Q_Ls']:5.1f}L/s dP={r['dP_Pa']:6.0f}Pa "
                  f"出風口可供 {r['outlet_m']:.2f} m  P≈{r['P_elec_W']:.1f} W  {'OK' if r['meets'] else '不足'}")
    print("branch V(34mm)=%.2f m/s pd=%.1f Pa" % (V34, pd34))
    print({k: [round(x, 2) for x in v.values()] for k, v in res["uniformity"].items()})


if __name__ == "__main__":
    main()
