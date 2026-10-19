"""
S6 後處理：扶手前方半徑 50 cm 量測區的「守住程度」。

指標（皆用時間平均場）：
  區域平均乾淨空氣比例：量測區內 SAF 的面積平均。
  達標面積比例：量測區內 SAF ≥ 50%（可逃生時間約 ×2）的面積佔比；另列 ≥ 25%。
  上方／水平：區域分成「出口上方」（站姿的臉）與「出口水平前方」（低姿勢的臉）兩半。
換算到系統：每層平台出風口長度 1.2 m（上下各 0.6 m），每層需要 q × 1.2；
  用 S5 的扶手導風腔模型（150×60 mm、不裝增壓機）算頂樓主機在 500／1000 Pa 下能同時供應幾層。
"""
import json
import os
import sys

import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from common import OUT, ROOT, SERIES, SEQ_STOPS, SURFACE, TEXT1, TEXT2, MUTED, CRIT, DARK, plt, save
from s5_handrail_vent import system, CAVITIES

RUNS = os.path.join(ROOT, "runs_zone")
sys.path.insert(0, os.path.join(ROOT, "cases"))
import build_zone as BZ  # noqa: E402

SEQ = LinearSegmentedColormap.from_list("seq", SEQ_STOPS)
SOLID_CMAP = LinearSegmentedColormap.from_list("solid", ["#6b6a66", "#6b6a66"])
QS = [5, 10, 20, 40]
KIND_LABEL = {"C": "C 低混合同軸（寬 35 mm）", "W": "W 空氣牆（寬 80 mm）", "Wd": "W 空氣牆、向下 30°"}
KIND_COLOR = {"C": SERIES[2], "W": SERIES[0], "Wd": SERIES[1]}
L_OUT = 1.2


def load(name):
    d = os.path.join(RUNS, name)
    if not os.path.exists(os.path.join(d, "mean_c.f32")):
        return None
    m = json.load(open(os.path.join(d, "meta.json")))
    ny, nx = m["ny"], m["nx"]
    rd = lambda f: np.fromfile(os.path.join(d, f), np.float32).reshape(ny, nx)
    t = np.load(os.path.join(d, "type.npy"))
    c, ux, uy = rd("mean_c.f32"), rd("mean_ux.f32") * m["vel_scale"], rd("mean_uy.f32") * m["vel_scale"]
    X, Y = BZ.grid()
    zone = ((X - m["x0"]) ** 2 + (Y - m["y0"]) ** 2 <= m["zone_r"] ** 2) & (X > m["x0"] + 0.02) & (t != 1)
    upper = zone & (Y - m["y0"] > np.abs(X - m["x0"]) * 0.0) & (Y > m["y0"] + 0.05)
    level = zone & (np.abs(Y - m["y0"]) <= 0.15)
    p = np.loadtxt(os.path.join(d, "probe.txt"))
    w = p[:, 0] * m["dt"] >= m["t_warm"]
    zc = c[zone]
    res = dict(kind=m["kind"], q=m["q"] * 1000, vc=m["vc_ms"], mean=float(zc.mean()),
               frac50=float((zc >= 0.5).mean()), frac25=float((zc >= 0.25).mean()),
               upper50=float((c[upper] >= 0.5).mean()), level50=float((c[level] >= 0.5).mean()),
               ts_p10=float(np.percentile(p[w, 1], 10)), ts_mean=float(p[w, 1].mean()))
    return dict(meta=m, t=t, c=c, ux=ux, uy=uy, res=res)


def capacity():
    a, b = CAVITIES["導風腔 150×60 mm"]
    rows = []
    for q in QS:
        per_floor = q * 1e-3 * L_OUT
        out = dict(q=q, per_floor_Ls=per_floor * 1000)
        for P in (500, 1000):
            kmax = 0
            for k in range(1, 11):
                p_roof, _, vmax, _ = system(a, b, per_floor, list(range(1, k + 1)), None)
                if p_roof <= P:
                    kmax = k
            out[f"floors_{P}Pa"] = kmax
        rows.append(out)
    return rows


def main():
    allres, loaded = {}, {}
    for name, kind, q, vc in BZ.CASES:
        r = load(name)
        if r is None:
            continue
        loaded[name] = r
        allres[name] = r["res"]
        s = r["res"]
        print(f"{name:13s} 平均 {s['mean']*100:5.1f}%  ≥50% 面積 {s['frac50']*100:5.1f}%  ≥25% {s['frac25']*100:5.1f}%  "
              f"上方≥50% {s['upper50']*100:5.1f}%  水平≥50% {s['level50']*100:5.1f}%")
    cap = capacity()
    for r in cap:
        print(f"q={r['q']} L/s/m → 每層 {r['per_floor_Ls']:.0f} L/s；500 Pa 可同時 {r['floors_500Pa']} 層，1000 Pa {r['floors_1000Pa']} 層")

    # ---- 圖 1：扶手上方（站姿臉）乾淨 ≥50% 的面積 vs 送風量 ----
    KIND_LABEL.update({"Ku": "康達往上（藏在底面）", "Cu": "低混合斜上 45°"})
    KIND_COLOR.update({"Ku": SERIES[4], "Cu": SERIES[6]})
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    for ax, vc in zip(axs, (0.15, 0.30)):
        for kind in ("W", "C"):
            pts = [(q, allres.get(f"{kind}_q{q:02d}_vc{int(vc*100):02d}")) for q in QS]
            pts = [(q, r) for q, r in pts if r]
            ax.plot([q for q, _ in pts], [r["upper50"] * 100 for _, r in pts], "o-", color=KIND_COLOR[kind], label=KIND_LABEL[kind])
            for q, r in pts:
                ax.annotate(f"{r['upper50']*100:.0f}%", (q, r["upper50"] * 100), xytext=(0, 7), textcoords="offset points",
                            ha="center", fontsize=8.5, color=TEXT2)
        extra = ("Ku", "Cu") if vc == 0.15 else ("Wd",)
        for kind in extra:
            pts = [(q, allres.get(f"{kind}_q{q:02d}_vc{int(vc*100):02d}")) for q in QS]
            pts = [(q, r) for q, r in pts if r]
            if pts:
                ax.plot([q for q, _ in pts], [r["upper50"] * 100 for _, r in pts], "s--", color=KIND_COLOR[kind], label=KIND_LABEL[kind])
        ax.set_xscale("log")
        ax.set_xticks(QS, [str(q) for q in QS])
        ax.minorticks_off()
        ax.set_xlabel("每公尺出風口的送風量（L/s）")
        ax.set_title(f"側風 {vc:.2f} m/s", loc="left", fontsize=11)
        ax.set_ylim(0, 70)
        ax.legend(fontsize=8.5, loc="upper left")
    axs[0].set_ylabel("扶手上方（站姿的臉）乾淨 ≥ 50% 的面積（%）")
    fig.suptitle("寬的「空氣牆」加上樓梯間的上升氣流，能在扶手上方撐出一層乾淨空氣", x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    save(fig, "s6_frac.png")

    # ---- 圖 2：平均場 2×2（側風 0.15：C/W × 20/40）----
    def panel(names, title, fname):
        fig, axs = plt.subplots(1, len(names), figsize=(4.0 * len(names), 5.6), sharey=True)
        im = None
        for ax, (n, lbl) in zip(np.atleast_1d(axs), names):
            ax.grid(False)
            ax.set_title(lbl, loc="left", fontsize=10)
            r = loaded.get(n)
            if r is None:
                ax.text(0.5, 0.5, "（計算中）", transform=ax.transAxes, ha="center", color=MUTED)
                continue
            m = r["meta"]
            ext = [0, m["nx"] * m["dx"] * 100, 0, m["ny"] * m["dx"] * 100]
            im = ax.imshow(np.ma.masked_where(r["t"] == 1, r["c"]), origin="lower", extent=ext, cmap=SEQ, vmin=0, vmax=1)
            ax.imshow(np.ma.masked_where(r["t"] != 1, np.ones_like(r["c"])), origin="lower", extent=ext, cmap=SOLID_CMAP, vmin=0, vmax=1)
            ax.contour(np.linspace(0, ext[1], m["nx"]), np.linspace(0, ext[3], m["ny"]), r["c"], levels=[0.5],
                       colors=[TEXT1], linewidths=1.0)
            th = np.linspace(-np.pi / 2, np.pi / 2, 100)
            ax.plot(m["x0"] * 100 + 50 * np.cos(th), m["y0"] * 100 + 50 * np.sin(th), color=CRIT, lw=1, ls="--")
            ax.text(2, 4, f"≥50%：{r['res']['frac50']*100:.0f}%", fontsize=10, color=TEXT1,
                    bbox=dict(fc=SURFACE + "cc", ec="none", pad=1.5))
            ax.set_xlim(0, 80)
            ax.set_ylim(5, 125)
            ax.set_xlabel("cm")
        np.atleast_1d(axs)[0].set_ylabel("cm（側風由下往上）")
        if im is not None:
            fig.colorbar(im, ax=axs, shrink=0.8, pad=0.02).set_label("乾淨空氣比例（細線＝50%）")
        fig.suptitle(title, x=0.01, ha="left", fontsize=12)
        save(fig, fname)

    panel([("C_q20_vc15", "C 低混合（窄）、20 L/s/m"), ("Ku_q20_vc15", "康達往上、20 L/s/m"),
           ("W_q20_vc15", "W 空氣牆、20 L/s/m"), ("W_q40_vc15", "W 空氣牆、40 L/s/m")],
          "側風 0.15 m/s：紅色虛線是扶手前方 50 cm 的範圍", "s6_fields_vc15.png")
    panel([("C_q40_vc30", "C 低混合、40 L/s/m"), ("W_q40_vc30", "W 空氣牆、40 L/s/m"),
           ("Wd_q40_vc30", "W 向下 30°、40 L/s/m"), ("C_q05_vc00", "對照：C、5 L/s/m、無側風")],
          "側風 0.30 m/s，以及無側風的對照", "s6_fields_vc30.png")

    json.dump(dict(cases=allres, capacity=cap, L_out=L_OUT), open(os.path.join(OUT, "s6_results.json"), "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
