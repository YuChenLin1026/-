"""
S3 濾材／氣旋分離／氣源模型

量測／計算方法：
  1. 煙粒徑分布：對數常態（數量中位徑 CMD、幾何標準差 σg），以 Hatch–Choate 換算質量中位徑。
     兩組假設：有焰燃燒 CMD 0.10 µm、悶燒 CMD 0.30 µm，σg = 1.9（文獻常見範圍，需引用查證）。
  2. 各元件的分級效率 η(d)：
       氣旋  Lapple 模型 η = 1 / (1 + (d50/d)²)，
             d50 = sqrt( 9 μ W / (2π Ne Vi ρp) )，壓損 ΔP = K·½ρVi²，K = 16·H·W / De²
       初濾  經驗曲線（ISO Coarse 等級示意）η = 1 − exp(−(d/2.5µm)^1.2)
       HEPA  以 EN 1822 H13 定義的最易穿透粒徑效率 99.95% 作為全粒徑下限（保守）
     串聯穿透率 P = Π(1 − ηk)，對粒徑分布積分得「數量」與「質量」總穿透率。
  3. 氣體（CO）：機械濾材與 HEPA 對 CO 無作用；活性碳物理吸附對 CO 幾乎無效；
     觸媒（如霍加拉 Hopcalite）可在常溫氧化 CO，但受濕度、溫度、壽命影響，未經測試前不計效益。
  4. 呼吸區混合：C_呼吸 = SAF·C_供氣 + (1 − SAF)·C_環境（SAF 由 CFD 取得）
"""
import json
import os

import numpy as np

from common import CRIT, MUTED, OUT, RHO, MU, SERIES, TEXT2, plt, save

d = np.logspace(np.log10(0.01), np.log10(20), 600)   # µm
RHO_P = 1000.0  # 煙粒有效密度假設 kg/m3（實際碳黑聚集體有效密度可能更低）


def lognorm_pdf(d, cmd, sg):
    ls = np.log(sg)
    return np.exp(-(np.log(d / cmd)) ** 2 / (2 * ls ** 2)) / (d * ls * np.sqrt(2 * np.pi))


def cyclone(Q=60 / 3600, D=0.10, Ne=6):
    H, W, De = D / 2, D / 4, D / 2
    Vi = Q / (H * W)
    d50 = np.sqrt(9 * MU * W / (2 * np.pi * Ne * Vi * RHO_P)) * 1e6
    K = 16 * H * W / De ** 2
    dp = K * 0.5 * RHO * Vi ** 2
    return d50, Vi, dp


def eta_cyclone(d, d50):
    return 1 / (1 + (d50 / d) ** 2)


def eta_prefilter(d):
    return 1 - np.exp(-(d / 2.5) ** 1.2)


def eta_hepa(d):
    return np.full_like(d, 0.9995)


def integrate(eta, cmd, sg):
    n = lognorm_pdf(d, cmd, sg)
    m = n * d ** 3
    pen = 1 - eta
    return (np.trapezoid(n * pen, d) / np.trapezoid(n, d),
            np.trapezoid(m * pen, d) / np.trapezoid(m, d))


def main():
    res = {}
    d50, Vi, dpc = cyclone()
    res["cyclone"] = dict(D_m=0.10, Q_m3h=60, inlet_V=Vi, d50_um=d50, dP_Pa=dpc)
    d50s, Vis, dps = cyclone(D=0.06)
    res["cyclone_small"] = dict(D_m=0.06, Q_m3h=60, inlet_V=Vis, d50_um=d50s, dP_Pa=dps)

    smokes = {"有焰燃燒煙（CMD 0.10 µm）": (0.10, 1.9), "悶燒煙（CMD 0.30 µm）": (0.30, 1.9)}
    trains = {
        "氣旋（D=100 mm）": eta_cyclone(d, d50),
        "初濾": eta_prefilter(d),
        "初濾 + HEPA H13": 1 - (1 - eta_prefilter(d)) * (1 - eta_hepa(d)),
    }
    tab = []
    for sname, (cmd, sg) in smokes.items():
        mmd = cmd * np.exp(3 * np.log(sg) ** 2)
        for tname, eta in trains.items():
            pn, pm = integrate(eta, cmd, sg)
            tab.append(dict(smoke=sname, MMD_um=mmd, train=tname, removal_number=1 - pn, removal_mass=1 - pm))
    res["particle_removal"] = tab

    # ---- 圖：分級效率 vs 煙粒徑分布 ----
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax2 = ax.twinx()
    for (sname, (cmd, sg)), alpha in zip(smokes.items(), (0.22, 0.12)):
        m = lognorm_pdf(d, cmd, sg) * d ** 3
        m = m / m.max()
        ax2.fill_between(d, 0, m, color=MUTED, alpha=alpha, lw=0)
        ax2.annotate(sname.split("（")[0] + "\n質量分布", (d[np.argmax(m)], 0.9), ha="center", fontsize=8.5, color=TEXT2)
    ax2.set_ylim(0, 3.2)
    ax2.set_yticks([])
    ax2.grid(False)
    ax2.spines["right"].set_visible(False)
    for (tname, eta), col in zip(trains.items(), SERIES[:3]):
        ax.plot(d, eta * 100, color=col, label=tname)
    ax.axvspan(0.01, 1.0, color=CRIT, alpha=0.04, lw=0)
    ax.annotate(f"氣旋 d50 ≈ {d50:.1f} µm\n入口風速 {Vi:.0f} m/s、壓損 ≈ {dpc:.0f} Pa", (d50, 50), xytext=(10, -30),
                textcoords="offset points", fontsize=9, color=TEXT2,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_xscale("log")
    ax.set_xlim(0.01, 20)
    ax.set_xticks([0.01, 0.03, 0.1, 0.3, 1, 3, 10], ["0.01", "0.03", "0.1", "0.3", "1", "3", "10"])
    ax.minorticks_off()
    ax.set_ylim(0, 105)
    ax.set_xlabel("粒徑（µm）")
    ax.set_ylabel("抓得到的比例（%）")
    ax.set_title("火災煙粒大多小於 1 µm：氣旋抓不到，HEPA 抓得到", loc="left", fontsize=12)
    ax.legend(loc="center left", fontsize=9)
    save(fig, "s3_filtration.png")

    with open(os.path.join(OUT, "s3_results.json"), "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=lambda x: round(float(x), 4)))


if __name__ == "__main__":
    main()
