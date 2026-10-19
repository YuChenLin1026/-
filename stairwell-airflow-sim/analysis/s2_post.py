"""
S2 CFD 後處理：呼吸區供氣比例（SAF）、噴流捲吸、驗證檢查、圖與動畫。

量測定義：
  SAF（Supply Air Fraction，供氣比例）＝示蹤劑濃度 c 的時間平均。
    c=1 為出風口送出的空氣，c=0 為環境空氣，所以 SAF 就是「吸進去的空氣裡有多少比例來自出風口」。
  呼吸區＝臉前 5–25 mm、上下 ±12 mm 的方框（2D 斷面上的口鼻位置，臉距出風口 35 cm）。
  每 0.01 s 記錄一次方框平均 c，暖機期（前 3–4 s）後取平均、標準差與第 10 百分位（最差時刻）。
  捲吸比＝某斷面上順流方向的總體積通量 ÷ 出風口送出的體積通量。
  驗證：出口緊鄰處（+1 mm）斷面的示蹤劑通量 ∫c·u dy 應等於設定供氣量 q（質量守恆）。
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np

from common import NOZZLE_COLOR, NOZZLE_LABEL, OUT, ROOT, SERIES, SEQ_STOPS, SURFACE, TEXT1, TEXT2, MUTED, CRIT, DARK, plt, save

RUNS = os.path.join(ROOT, "runs")
NOZZLES = ["plain", "coanda", "coax", "amp"]
CONDS = [("head_vc00", "無側風"), ("head_vc15", "側風 0.15 m/s"), ("head_vc30", "側風 0.30 m/s")]

from matplotlib.colors import LinearSegmentedColormap

SEQ = LinearSegmentedColormap.from_list("seq", SEQ_STOPS)
SOLID_CMAP = LinearSegmentedColormap.from_list("solid", ["#6b6a66", "#6b6a66"])


def load(name):
    d = os.path.join(RUNS, name)
    if not os.path.exists(os.path.join(d, "mean_c.f32")):
        return None
    m = json.load(open(os.path.join(d, "meta.json")))
    ny, nx = m["ny"], m["nx"]
    rd = lambda f: np.fromfile(os.path.join(d, f), np.float32).reshape(ny, nx)
    r = dict(meta=m, type=np.load(os.path.join(d, "type.npy")), c=rd("mean_c.f32"),
             ux=rd("mean_ux.f32") * m["vel_scale"], uy=rd("mean_uy.f32") * m["vel_scale"])
    p = np.loadtxt(os.path.join(d, "probe.txt"))
    tsec = p[:, 0] * m["dt"]
    r["probe_t"], r["probe_c"] = tsec, p[:, 1]
    w = tsec >= m["t_warm"]
    pc = p[w, 1]
    half = len(pc) // 2
    r["saf"] = dict(mean=float(pc.mean()), std=float(pc.std()), p10=float(np.percentile(pc, 10)),
                    p90=float(np.percentile(pc, 90)),
                    first_half=float(pc[:half].mean()), second_half=float(pc[half:].mean()))
    return r


def section(r, xpos, half=0.12):
    m = r["meta"]
    i = int(round(xpos / m["dx"]))
    fluid = r["type"][:, i] != 1
    ux, c = r["ux"][:, i] * fluid, r["c"][:, i] * fluid
    y = (np.arange(m["ny"]) + 0.5) * m["dx"]
    band = np.abs(y - m["y0"]) < half
    q_supply = float(np.sum(c * ux * band) * m["dx"])
    q_total = float(np.sum(np.clip(ux, 0, None) * band) * m["dx"])
    return q_supply, q_total


def metrics(r):
    m = r["meta"]
    out = dict(r["saf"])
    # 出口緊鄰處（+1 mm、±25 mm）的示蹤劑通量：此處擺動小，平均場乘積≈真實通量
    qs1, _ = section(r, m["x0"] + 0.001, half=0.025)
    out["supply_flux_ratio"] = qs1 / m["q"]
    out["entrain"] = {}
    for dxp in (0.03, 0.10, 0.20, 0.30):
        qs, qt = section(r, m["x0"] + dxp)
        out["entrain"][f"{int(dxp*100)}cm"] = qt / m["q"]
    return out


def field_panel(cases, title, fname, xr=(0.0, 0.62)):
    fig, axs = plt.subplots(2, 2, figsize=(12, 7.4), sharex=True, sharey=True)
    im = None
    for ax, nz in zip(axs.flat, NOZZLES):
        r = cases.get(nz)
        ax.set_title(NOZZLE_LABEL[nz], loc="left", fontsize=11)
        ax.grid(False)
        if r is None:
            ax.text(0.5, 0.5, "（計算中）", transform=ax.transAxes, ha="center", color=MUTED)
            continue
        m = r["meta"]
        ext = [0, m["nx"] * m["dx"] * 100, 0, m["ny"] * m["dx"] * 100]
        c = np.ma.masked_where(r["type"] == 1, r["c"])
        im = ax.imshow(c, origin="lower", extent=ext, cmap=SEQ, vmin=0, vmax=1, interpolation="bilinear")
        solid = np.ma.masked_where(r["type"] != 1, np.ones_like(r["c"]))
        ax.imshow(solid, origin="lower", extent=ext, cmap=SOLID_CMAP, vmin=0, vmax=1, interpolation="nearest")
        X, Y = np.meshgrid((np.arange(m["nx"]) + 0.5) * m["dx"] * 100, (np.arange(m["ny"]) + 0.5) * m["dx"] * 100)
        sk = 6
        ax.streamplot(X[::sk, ::sk], Y[::sk, ::sk], r["ux"][::sk, ::sk], r["uy"][::sk, ::sk],
                      color=(0.75, 0.75, 0.72, 0.35) if DARK else (0.32, 0.32, 0.30, 0.35), density=1.1, linewidth=0.5, arrowsize=0.6)
        if m["head"]:
            fx = (m["x0"] + m["face_l"]) * 100
            ax.add_patch(plt.Rectangle((fx - 2.5, m["y0"] * 100 - 1.2), 2.0, 2.4, fill=False, ec=CRIT, lw=1.2))
            ax.text(fx - 3, m["y0"] * 100 + 2.2, f"口鼻 {r['saf']['mean']*100:.0f}%", ha="right", fontsize=10,
                    color=TEXT1, bbox=dict(fc=SURFACE + "cc", ec="none", pad=1.5))
        ax.set_xlim(xr[0] * 100, xr[1] * 100)
        ax.set_ylim(5, 35)
    for ax in axs[1]:
        ax.set_xlabel("沿噴流方向（cm）")
    for ax in axs[:, 0]:
        ax.set_ylabel("cm")
    if not any(v is not None for v in cases.values()):
        plt.close(fig)
        return None
    cb = fig.colorbar(im, ax=axs, shrink=0.75, pad=0.015)
    cb.set_label("乾淨空氣比例（1 = 全是出風口送的空氣）")
    fig.suptitle(title, x=0.06, ha="left", fontsize=13)
    return save(fig, fname)


def make_video(cases_names, fname, title):
    """四個 case 同步（每格 0.08 s）組成 2×2 動畫。"""
    import matplotlib.animation  # noqa: F401  (確認可用)
    frames = {nz: sorted(glob.glob(os.path.join(RUNS, n, "frames", "f*.u8"))) for nz, n in cases_names.items()}
    nmin = min(len(v) for v in frames.values())
    if nmin == 0:
        return None
    tmpd = os.path.join(OUT, "_vid_" + fname)
    os.makedirs(tmpd, exist_ok=True)
    metas = {nz: json.load(open(os.path.join(RUNS, n, "meta.json"))) for nz, n in cases_names.items()}
    for k in range(nmin):
        fig, axs = plt.subplots(2, 2, figsize=(10, 6.4))
        for ax, nz in zip(axs.flat, NOZZLES):
            m = metas[nz]
            a = np.fromfile(frames[nz][k], np.uint8).reshape(m["ny"], m["nx"]).astype(float)
            solid = a == 255
            c = np.ma.masked_where(solid, a / 254.0)
            ext = [0, m["nx"] * m["dx"] * 100, 0, m["ny"] * m["dx"] * 100]
            ax.imshow(c, origin="lower", extent=ext, cmap=SEQ, vmin=0, vmax=1)
            ax.imshow(np.ma.masked_where(~solid, np.ones_like(a)), origin="lower", extent=ext, cmap=SOLID_CMAP, vmin=0, vmax=1)
            ax.set_xlim(0, 62)
            ax.set_ylim(5, 35)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.grid(False)
            ax.set_title(NOZZLE_LABEL[nz], loc="left", fontsize=10)
        fig.suptitle(f"{title}    t = {k*0.08:.2f} s", x=0.04, ha="left", fontsize=12)
        fig.tight_layout()
        fig.savefig(os.path.join(tmpd, f"{k:04d}.png"), dpi=90)
        plt.close(fig)
    out = os.path.join(OUT, fname)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "12", "-i", os.path.join(tmpd, "%04d.png"),
                    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "28", out],
                   check=True)
    for f in glob.glob(os.path.join(tmpd, "*.png")):
        os.remove(f)
    os.rmdir(tmpd)
    return out


def coanda_compare():
    """康達第一版（R15）與修正版（R45）的平均場對照。"""
    pairs = [("coanda_r15_head_vc00", "第一版 R15 mm（縫寬 2.5 倍）"), ("coanda_head_vc00", "修正版 R45 mm（縫寬 7.5 倍）")]
    loaded = [(load(n), t) for n, t in pairs]
    if loaded[0][0] is None:
        return None
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    im = None
    for ax, (r, t) in zip(axs, loaded):
        ax.set_title(t, loc="left", fontsize=11)
        ax.grid(False)
        if r is None:
            ax.text(0.5, 0.5, "（計算中）", transform=ax.transAxes, ha="center", color=MUTED)
            continue
        m = r["meta"]
        ext = [0, m["nx"] * m["dx"] * 100, 0, m["ny"] * m["dx"] * 100]
        im = ax.imshow(np.ma.masked_where(r["type"] == 1, r["c"]), origin="lower", extent=ext, cmap=SEQ, vmin=0, vmax=1)
        ax.imshow(np.ma.masked_where(r["type"] != 1, np.ones_like(r["c"])), origin="lower", extent=ext, cmap=SOLID_CMAP, vmin=0, vmax=1)
        X, Y = np.meshgrid((np.arange(m["nx"]) + 0.5) * m["dx"] * 100, (np.arange(m["ny"]) + 0.5) * m["dx"] * 100)
        sk = 6
        ax.streamplot(X[::sk, ::sk], Y[::sk, ::sk], r["ux"][::sk, ::sk], r["uy"][::sk, ::sk],
                      color=(0.75, 0.75, 0.72, 0.35) if DARK else (0.32, 0.32, 0.30, 0.35), density=1.0, linewidth=0.5, arrowsize=0.6)
        fx = (m["x0"] + m["face_l"]) * 100
        ax.add_patch(plt.Rectangle((fx - 2.5, m["y0"] * 100 - 1.2), 2.0, 2.4, fill=False, ec=CRIT, lw=1.2))
        ax.text(fx - 3, m["y0"] * 100 + 2.2, f"口鼻 {r['saf']['mean']*100:.0f}%", ha="right", fontsize=10,
                color=TEXT1, bbox=dict(fc=SURFACE + "cc", ec="none", pad=1.5))
        ax.set_xlim(0, 62)
        ax.set_ylim(0, 40)
        ax.set_xlabel("cm")
    axs[0].set_ylabel("cm")
    if im is not None:
        fig.colorbar(im, ax=axs, shrink=0.85, pad=0.015).set_label("乾淨空氣比例")
    fig.suptitle("康達曲面：兩種半徑的氣流都沒有沿曲面轉彎，直接往下衝（無側風）", x=0.01, ha="left", fontsize=12)
    return save(fig, "s2_coanda_lesson.png")


def main():
    coanda_compare()
    allres = {}
    loaded = {}
    for nz in NOZZLES:
        for suffix in ["free"] + [c for c, _ in CONDS]:
            name = f"{nz}_{suffix}"
            r = load(name)
            if r is None:
                continue
            loaded[name] = r
            allres[name] = metrics(r)
            s = allres[name]
            print(f"{name:20s} SAF={s['mean']*100:5.1f}% p10={s['p10']*100:5.1f}% "
                  f"halves={s['first_half']*100:.1f}/{s['second_half']*100:.1f}  flux={s['supply_flux_ratio']:.2f} "
                  f"entrain30={s['entrain']['30cm']:.1f}")

    field_panel({nz: loaded.get(f"{nz}_free") for nz in NOZZLES},
                "沒有人擋、沒有風時，乾淨空氣能走多遠", "s2_free_fields.png")
    for c, lbl in CONDS:
        field_panel({nz: loaded.get(f"{nz}_{c}") for nz in NOZZLES},
                    f"臉在出風口前 35 cm、{lbl}：顏色越深＝越多出風口的乾淨空氣", f"s2_{c}_fields.png")

    # ---- 口鼻區乾淨空氣比例：三種側風條件的橫條小圖（補滿到 100%）----
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 3.6), sharey=True)
    for ax, (c, lbl) in zip(axs, CONDS):
        for k, nz in enumerate(NOZZLES):
            s = allres.get(f"{nz}_{c}")
            yk = len(NOZZLES) - 1 - k
            ax.barh(yk, 100, height=0.62, color=MUTED, alpha=0.22, zorder=2)
            if s is None:
                ax.text(3, yk, "計算中", va="center", fontsize=9, color=MUTED)
                continue
            v = s["mean"] * 100
            ax.barh(yk, v, height=0.62, color=NOZZLE_COLOR[nz], zorder=3)
            ax.plot([s["p10"] * 100] * 2, [yk - 0.36, yk + 0.36], color=TEXT1, lw=1.6, zorder=4)
            ax.text(min(v, 100) + 2.5, yk, f"{v:.0f}%", va="center", fontsize=10.5, color=TEXT1, zorder=5)
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100%"])
        ax.set_title(lbl, loc="left", fontsize=11)
        ax.grid(axis="y", visible=False)
    axs[0].set_yticks(range(len(NOZZLES)), [NOZZLE_LABEL[n].split("（")[0] for n in reversed(NOZZLES)])
    fig.suptitle("臉在 35 cm 處，吸到的空氣有幾成來自出風口（彩色＝平均，黑線＝最差 10% 的時刻）",
                 x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    save(fig, "s2_saf_bars.png")

    # ---- 自由噴流：主軸上（含偏移）最大 SAF 隨距離 ----
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    for nz in NOZZLES:
        r = loaded.get(f"{nz}_free")
        if r is None:
            continue
        m = r["meta"]
        xs = np.arange(0.02, 0.50, 0.005)
        band = slice(int((m["y0"] - 0.06) / m["dx"]), int((m["y0"] + 0.06) / m["dx"]))
        best = [r["c"][band, int(round((m["x0"] + x) / m["dx"]))].max() for x in xs]
        ax.plot(xs * 100, np.array(best) * 100, color=NOZZLE_COLOR[nz], label=NOZZLE_LABEL[nz])
    ax.axvline(35, color=CRIT, lw=1, ls="--")
    ax.annotate("低姿勢口鼻位置 35 cm", (35, 96), xytext=(4, 0), textcoords="offset points", fontsize=9, color=CRIT)
    ax.set_xlabel("離出風口距離（cm）")
    ax.set_ylabel("這個距離最乾淨的位置（%）")
    ax.set_ylim(0, 102)
    ax.set_title("離出風口越遠，乾淨空氣被稀釋得越多", loc="left", fontsize=12)
    ax.legend(fontsize=9)
    save(fig, "s2_decay.png")

    # ---- 結合氣源：呼吸區 CO 相對環境濃度 ----
    fig, ax = plt.subplots(figsize=(9.6, 4.4))
    wbar = 0.36
    labels = []
    for k, nz in enumerate(NOZZLES):
        s = allres.get(f"{nz}_head_vc00")
        if s is None:
            continue
        saf = s["mean"]
        labels.append(nz)
        a = 100.0                      # 取樓梯間空氣過濾：CO 穿透 100%
        b = (1 - saf) * 100            # 獨立乾淨氣源
        ax.bar(k - wbar / 2 - 0.01, a, width=wbar, color=SERIES[7], zorder=3, label="取樓梯間空氣＋濾材" if k == 0 else None)
        ax.bar(k + wbar / 2 + 0.01, b, width=wbar, color=SERIES[0], zorder=3, label="獨立乾淨氣源" if k == 0 else None)
        ax.annotate("100", (k - wbar / 2, a), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=9, color=TEXT2)
        ax.annotate(f"{b:.0f}", (k + wbar / 2, b), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=9, color=TEXT2)
    ax.set_xticks(range(len(NOZZLES)), [NOZZLE_LABEL[n].split(" ", 1)[1] for n in NOZZLES], fontsize=9.5)
    ax.set_ylabel("口鼻區 CO ／ 環境 CO（%）")
    ax.set_ylim(0, 115)
    ax.set_title("同一個出風口換氣源：吸樓梯間空氣時，口鼻的 CO 一點都沒少", loc="left", fontsize=11.5)
    ax.legend(fontsize=9, loc="upper right", ncol=2)
    save(fig, "s2_exposure.png")

    with open(os.path.join(OUT, "s2_results.json"), "w") as f:
        json.dump(allres, f, ensure_ascii=False, indent=1)

    if "--video" in sys.argv:
        v1 = make_video({nz: f"{nz}_free" for nz in NOZZLES}, "s2_free.mp4", "自由噴流（供氣比例瞬時場）")
        v2 = make_video({nz: f"{nz}_head_vc15" for nz in NOZZLES}, "s2_head_vc15.mp4", "臉在 35 cm、側風 0.15 m/s")
        print("videos:", v1, v2)


if __name__ == "__main__":
    main()
