"""S2 四種噴嘴的斷面幾何圖（報告「量測方法」用）。"""
import os
import sys

import numpy as np
from matplotlib.colors import ListedColormap

from common import NOZZLE_COLOR, NOZZLE_LABEL, ROOT, SURFACE, TEXT1, TEXT2, MUTED, plt, save

sys.path.insert(0, os.path.join(ROOT, "cases"))
import build as B  # noqa: E402

NOTES = {
    "plain": "單一窄縫 6 mm\n出口平均 0.83 m/s\n整流段 25 mm",
    "coanda": "向下吹的 6 mm 縫\n沿 R45 mm 凸面轉 90°\n在尖角脫離，0.83 m/s",
    "coax": "總寬 32 mm\n中央 14 mm：0.23 m/s\n兩側 8 mm：0.11 m/s",
    "amp": "開口 40 mm、背面開放\n內壁兩道 3 mm 縫\n各 0.83 m/s",
}


def main():
    fig, axs = plt.subplots(1, 4, figsize=(14, 4.2))
    X, Y = B.grid()
    for ax, nz in zip(axs, B.NOZZLES):
        t = np.zeros((B.NY, B.NX), np.uint8)
        ux = np.zeros((B.NY, B.NX), np.float32)
        uy = ux.copy()
        B.NOZZLES[nz](X, Y, t, ux, uy)
        ys, xs = slice(int(0.13 / B.DX), int(0.29 / B.DX)), slice(0, int(0.14 / B.DX))
        sub = t[ys, xs]
        img = np.zeros(sub.shape)
        img[sub == 1] = 1
        img[sub == 2] = 2
        cmap = ListedColormap([SURFACE, "#8a8984", NOZZLE_COLOR[nz]])
        ax.imshow(img, origin="lower", cmap=cmap, vmin=0, vmax=2, extent=[0, 14, 13, 29], interpolation="nearest")
        ax.axvline(B.X0 * 100, color=MUTED, lw=0.8, ls=":")
        ax.annotate("出口平面", (B.X0 * 100, 28.4), xytext=(3, 0), textcoords="offset points", fontsize=8, color=TEXT2)
        ax.annotate("", xy=(13.5, B.Y0 * 100), xytext=(B.X0 * 100 + 0.3, B.Y0 * 100),
                    arrowprops=dict(arrowstyle="->", color=NOZZLE_COLOR[nz], lw=1.5))
        ax.text(0.4, 13.6, NOTES[nz], fontsize=8.5, color=TEXT1, va="bottom", linespacing=1.4)
        ax.set_title(NOZZLE_LABEL[nz], loc="left", fontsize=10.5)
        ax.set_xlabel("cm")
        ax.grid(False)
        ax.set_aspect("equal")
    axs[0].set_ylabel("cm")
    fig.suptitle("灰色＝固體（扶手、噴嘴壁）；彩色＝供氣入口格點；箭頭＝噴流方向（朝向使用者臉部）",
                 x=0.01, ha="left", fontsize=10, color=TEXT2)
    fig.tight_layout()
    save(fig, "s2_geometry.png")


if __name__ == "__main__":
    main()
