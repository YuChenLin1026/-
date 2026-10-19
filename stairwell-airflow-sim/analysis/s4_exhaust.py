"""
S4 扶手當排煙管的容量上限

量測／計算方法：
  整棟 10 層共用一根扶手風道，總長 70 m（每層 7 m），每層 4 個彎頭（K=0.3）、6 個接頭（K=0.1），
  進出口 K=1.5。氣體分別以 20 °C 空氣與 200 °C 熱煙（以空氣物性近似：ρ=0.746、ν=3.5e-5）計算。
  給定風機可提供的總壓（500–3000 Pa），用二分法求可通過的最大風量。
  對照組：一扇敞開的門（0.9 m × 2.0 m），平均通過風速 1 m/s 時的風量（量級參考，不是法規值）。
"""
import json
import os

import numpy as np

from common import CRIT, MUTED, OUT, SERIES, TEXT2, plt, save
from s1_duct import friction_factor

L, NB, NJ = 70.0, 40, 60
GASES = {"20 °C 空氣": (1.204, 1.51e-5), "200 °C 熱煙（近似）": (0.746, 3.5e-5)}


def dp(Q, D, rho, nu):
    V = Q / (np.pi * D * D / 4)
    pd = 0.5 * rho * V * V
    f = friction_factor(V * D / nu, D)
    return f * L / D * pd + (1.5 + NB * 0.3 + NJ * 0.1) * pd


def qmax(P, D, rho, nu):
    lo, hi = 0.0, 1.0
    for _ in range(80):
        m = 0.5 * (lo + hi)
        lo, hi = (m, hi) if dp(m, D, rho, nu) < P else (lo, m)
    return 0.5 * (lo + hi)


def main():
    Ps = np.linspace(100, 3000, 60)
    door = 0.9 * 2.0 * 1.0 * 60  # m3/min
    res = {"door_ref_m3min": door, "cases": []}
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    styles = {0.034: "-", 0.038: "--"}
    for (gname, (rho, nu)), col in zip(GASES.items(), (SERIES[0], SERIES[1])):
        for D, ls in styles.items():
            q = np.array([qmax(P, D, rho, nu) for P in Ps]) * 60
            ax.plot(Ps, q, color=col, ls=ls, label=f"{gname}、內徑 {D*1000:.0f} mm")
            for P in (1000, 3000):
                Q = qmax(P, D, rho, nu)
                res["cases"].append(dict(gas=gname, D_mm=D * 1000, P_Pa=P, Q_m3min=Q * 60,
                                         V_ms=Q / (np.pi * D * D / 4), ratio_to_door=Q * 60 / door))
    ax.set_xlabel("風機可提供的總壓（Pa）")
    ax.set_ylabel("可排出風量（m³/min）")
    ax.set_ylim(0, 0.8)
    ax.set_title(f"S4｜整棟一根扶手（70 m）最多只能排不到 1 m³/min；一扇敞開的門約 {door:.0f} m³/min", loc="left", fontsize=11.5)
    ax.legend(fontsize=9, loc="upper left")
    save(fig, "s4_exhaust.png")
    with open(os.path.join(OUT, "s4_results.json"), "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)
    for c in res["cases"]:
        print(f"{c['gas']:12s} D={c['D_mm']:.0f} P={c['P_Pa']} Q={c['Q_m3min']:.3f} m3/min V={c['V_ms']:.1f} m/s 門的 {c['ratio_to_door']*100:.2f}%")


if __name__ == "__main__":
    main()
