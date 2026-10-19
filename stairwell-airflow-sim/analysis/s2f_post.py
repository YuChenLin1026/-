"""
S2 改版（臉在扶手斜上方）後處理：口鼻乾淨空氣比例、平均場圖、橫條小圖、動畫。
量測定義與舊 S2 相同：口鼻框（頭部朝出風口一側、離頭表面 0.5–2.5 cm）內示蹤劑濃度的時間平均。
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from common import OUT, ROOT, SERIES, SEQ_STOPS, SURFACE, TEXT1, TEXT2, MUTED, CRIT, DARK, plt, save

RUNS = os.path.join(ROOT, "runs_face")
NZ = ["A", "B", "C", "D"]
LABEL = {"A": "A 一般定向（朝口鼻）", "B": "B 康達往上（藏在底面）", "C": "C 低混合同軸（朝口鼻）", "D": "D 氣流倍增（朝口鼻）"}
COLOR = {"A": SERIES[0], "B": SERIES[1], "C": SERIES[2], "D": SERIES[3]}
CONDS = [("vc00", "無側風"), ("vc15", "側風 0.15 m/s"), ("vc30", "側風 0.30 m/s")]
SEQ = LinearSegmentedColormap.from_list("seq", SEQ_STOPS)
SOLID_CMAP = LinearSegmentedColormap.from_list("solid", ["#6b6a66", "#6b6a66"])


def load(name):
    d = os.path.join(RUNS, name)
    if not os.path.exists(os.path.join(d, "mean_c.f32")):
        return None
    m = json.load(open(os.path.join(d, "meta.json")))
    ny, nx = m["ny"], m["nx"]
    rd = lambda f: np.fromfile(os.path.join(d, f), np.float32).reshape(ny, nx)
    p = np.loadtxt(os.path.join(d, "probe.txt"))
    w = p[:, 0] * m["dt"] >= m["t_warm"]
    pc = p[w, 1]
    half = len(pc) // 2
    return dict(meta=m, t=np.load(os.path.join(d, "type.npy")), c=rd("mean_c.f32"),
                ux=rd("mean_ux.f32") * m["vel_scale"], uy=rd("mean_uy.f32") * m["vel_scale"],
                res=dict(mean=float(pc.mean()), p10=float(np.percentile(pc, 10)),
                         first_half=float(pc[:half].mean()), second_half=float(pc[half:].mean())))


def field_panel(loaded, cond, lbl):
    if not any(f"{nz}_{cond}" in loaded for nz in NZ):
        return
    fig, axs = plt.subplots(1, 4, figsize=(15, 3.85), sharey=True)
    im = None
    for ax, nz in zip(axs, NZ):
        ax.grid(False)
        ax.set_title(LABEL[nz], loc="left", fontsize=10)
        r = loaded.get(f"{nz}_{cond}")
        any_m = next(v["meta"] for k, v in loaded.items() if k.endswith(cond))
        if r is None:
            ax.text(0.5, 0.5, "（計算中）", transform=ax.transAxes, ha="center", color=MUTED)
            ax.set_xlim(0, any_m["nx"] * any_m["dx"] * 100)
            ax.set_ylim(5, any_m["ny"] * any_m["dx"] * 100 - 5)
            ax.set_aspect("equal")
            ax.set_xlabel("cm")
            continue
        m = r["meta"]
        ext = [0, m["nx"] * m["dx"] * 100, 0, m["ny"] * m["dx"] * 100]
        im = ax.imshow(np.ma.masked_where(r["t"] == 1, r["c"]), origin="lower", extent=ext, cmap=SEQ, vmin=0, vmax=1)
        ax.imshow(np.ma.masked_where(r["t"] != 1, np.ones_like(r["c"])), origin="lower", extent=ext, cmap=SOLID_CMAP, vmin=0, vmax=1)
        X, Y = np.meshgrid((np.arange(m["nx"]) + 0.5) * m["dx"] * 100, (np.arange(m["ny"]) + 0.5) * m["dx"] * 100)
        sk = 8
        ax.streamplot(X[::sk, ::sk], Y[::sk, ::sk], r["ux"][::sk, ::sk], r["uy"][::sk, ::sk],
                      color=(0.75, 0.75, 0.72, 0.35) if DARK else (0.32, 0.32, 0.30, 0.35), density=1.0, linewidth=0.5, arrowsize=0.6)
        mx, my = np.array(m["mouth"]) * 100
        ax.plot(mx, my, "o", ms=7, mfc="none", mec=CRIT, mew=1.6)
        ax.text(mx - 2, my - 6, f"口鼻 {r['res']['mean']*100:.0f}%", ha="right", fontsize=10, color=TEXT1,
                bbox=dict(fc=SURFACE + "cc", ec="none", pad=1.5))
        ax.set_xlim(0, ext[1])
        ax.set_ylim(5, ext[3] - 5)
        ax.set_xlabel("cm")
    axs[0].set_ylabel("cm")
    if im is not None:
        fig.colorbar(im, ax=axs, shrink=0.8, pad=0.01).set_label("乾淨空氣比例")
    fig.suptitle(f"臉在扶手斜上方、{lbl}：紅圈是口鼻位置", x=0.01, y=0.99, ha="left", fontsize=12)
    save(fig, f"s2f_{cond}_fields.png")


def bars(allres):
    if not allres:
        return
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 3.6), sharey=True)
    for ax, (c, lbl) in zip(axs, CONDS):
        for k, nz in enumerate(NZ):
            s = allres.get(f"{nz}_{c}")
            yk = len(NZ) - 1 - k
            ax.barh(yk, 100, height=0.62, color=MUTED, alpha=0.22, zorder=2)
            if s is None:
                ax.text(3, yk, "計算中", va="center", fontsize=9, color=MUTED)
                continue
            v = s["mean"] * 100
            ax.barh(yk, v, height=0.62, color=COLOR[nz], zorder=3)
            ax.plot([s["p10"] * 100] * 2, [yk - 0.36, yk + 0.36], color=TEXT1, lw=1.6, zorder=4)
            ax.text(min(v, 100) + 2.5, yk, f"{v:.0f}%", va="center", fontsize=10.5, color=TEXT1, zorder=5)
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100%"])
        ax.set_title(lbl, loc="left", fontsize=11)
        ax.grid(axis="y", visible=False)
    axs[0].set_yticks(range(len(NZ)), [LABEL[n].split("（")[0] for n in reversed(NZ)])
    fig.suptitle("臉在扶手斜上方時，吸到的空氣有幾成來自出風口（彩色＝平均，黑線＝最差 10% 的時刻）", x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    save(fig, "s2f_saf_bars.png")


def video(cond, fname):
    frames = {nz: sorted(glob.glob(os.path.join(RUNS, f"{nz}_{cond}", "frames", "f*.u8"))) for nz in NZ}
    n = min(len(v) for v in frames.values())
    if n == 0:
        return None
    metas = {nz: json.load(open(os.path.join(RUNS, f"{nz}_{cond}", "meta.json"))) for nz in NZ}
    tmpd = os.path.join(OUT, "_vid_" + fname)
    os.makedirs(tmpd, exist_ok=True)
    for k in range(n):
        fig, axs = plt.subplots(1, 4, figsize=(12, 4.2))
        for ax, nz in zip(axs, NZ):
            m = metas[nz]
            a = np.fromfile(frames[nz][k], np.uint8).reshape(m["ny"], m["nx"]).astype(float)
            ext = [0, m["nx"] * m["dx"] * 100, 0, m["ny"] * m["dx"] * 100]
            ax.imshow(np.ma.masked_where(a == 255, a / 254.0), origin="lower", extent=ext, cmap=SEQ, vmin=0, vmax=1)
            ax.imshow(np.ma.masked_where(a != 255, np.ones_like(a)), origin="lower", extent=ext, cmap=SOLID_CMAP, vmin=0, vmax=1)
            mx, my = np.array(m["mouth"]) * 100
            ax.plot(mx, my, "o", ms=6, mfc="none", mec=CRIT, mew=1.4)
            ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            ax.set_title(LABEL[nz].split("（")[0], loc="left", fontsize=9.5)
        fig.suptitle(f"臉在斜上方、側風 0.15 m/s    t = {k*0.08:.2f} s", x=0.02, ha="left", fontsize=11)
        fig.tight_layout()
        fig.savefig(os.path.join(tmpd, f"{k:04d}.png"), dpi=90)
        plt.close(fig)
    out = os.path.join(OUT, fname)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "12", "-i", os.path.join(tmpd, "%04d.png"),
                    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "28", out], check=True)
    for f in glob.glob(os.path.join(tmpd, "*.png")):
        os.remove(f)
    os.rmdir(tmpd)
    return out


def main():
    allres, loaded = {}, {}
    for nz in NZ:
        for c, _ in CONDS:
            r = load(f"{nz}_{c}")
            if r is None:
                continue
            loaded[f"{nz}_{c}"] = r
            allres[f"{nz}_{c}"] = r["res"]
            s = r["res"]
            print(f"{nz}_{c}: 口鼻 {s['mean']*100:5.1f}%  最差10% {s['p10']*100:5.1f}%  前/後半 {s['first_half']*100:.1f}/{s['second_half']*100:.1f}")
    for c, lbl in CONDS:
        field_panel(loaded, c, lbl)
    bars(allres)
    json.dump(allres, open(os.path.join(OUT, "s2f_results.json"), "w"), indent=1)
    if "--video" in sys.argv:
        print("video:", video("vc15", "s2f_vc15.mp4"))


if __name__ == "__main__":
    main()
