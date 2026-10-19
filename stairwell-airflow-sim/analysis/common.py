"""共用：圖表樣式（中文字型、配色）與空氣物性。"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)

_font = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
if os.path.exists(_font):
    font_manager.fontManager.addfont(_font)
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=_font).get_name()
DARK = os.environ.get("THEME") == "dark"
SURFACE, TEXT1, TEXT2, MUTED, EDGE, GRID = (
    ("#1a1a19", "#f0efec", "#c3c2b7", "#8f8e87", "#4a4a46", "#2e2e2c") if DARK else
    ("#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#c9c8c2", "#e6e5e0"))
plt.rcParams.update({
    "axes.unicode_minus": False,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": EDGE,
    "axes.labelcolor": TEXT2,
    "xtick.color": TEXT2,
    "ytick.color": TEXT2,
    "text.color": TEXT1,
    "axes.titlecolor": TEXT1,
    "legend.labelcolor": TEXT1,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "lines.linewidth": 2.0,
    "font.size": 11,
    "legend.frameon": False,
})

# 類別色（固定順序，不循環）；深色模式用同色相、為深底重新取階的版本
SERIES = (["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"] if DARK else
          ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"])
CRIT = SERIES[7]
# 連續色階（單一藍色相）：淺色模式 低=淺；深色模式 低=深
SEQ_STOPS = (["#1a1a19", "#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"] if DARK else
             ["#fcfcfb", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])

NOZZLE_LABEL = {
    "plain": "A 一般定向噴嘴（基準）",
    "coanda": "B 康達曲面導流",
    "coax": "C 低混合率同軸噴嘴",
    "amp": "D 氣流倍增式",
}
NOZZLE_COLOR = {"plain": SERIES[0], "coanda": SERIES[1], "coax": SERIES[2], "amp": SERIES[3]}

# 20 °C 空氣
RHO = 1.204
NU = 1.51e-5
MU = RHO * NU


def save(fig, name):
    if DARK:
        root, ext = os.path.splitext(name)
        name = f"{root}_dark{ext}"
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return p
