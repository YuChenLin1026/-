"""
驗證 1：二維泊肅葉管流（平行板通道）——檢查壁面 bounce-back、黏度與入口條件。
平行板間距 H=40 格，均勻入口速度 U，充分發展後應為拋物線分布 u(y)=1.5U·(1-(2y/H-1)^2)。
以 L2 相對誤差與流量守恆評估。
"""
import json, os, subprocess, sys
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
from common import plt, save, SERIES, TEXT2

nx, ny, H = 600, 42, 40
U = 0.05
d = os.path.join(ROOT, "runs", "_val_poiseuille")
os.makedirs(os.path.join(d, "frames"), exist_ok=True)
t = np.zeros((ny, nx), np.uint8)
t[0, :] = 1; t[-1, :] = 1
ux = np.zeros((ny, nx), np.float32); uy = np.zeros_like(ux)
t[1:-1, 0] = 2; ux[1:-1, 0] = U
probe = np.zeros((ny, nx), np.uint8)
tau = 0.56
cfg = dict(nx=nx, ny=ny, steps=30000, warmup=28000, tau0=tau, cs=0.0, dlat=0.01, sct=0.7, vc=0, sponge=1,
           probe_every=1000, frame_every=0)
with open(os.path.join(d, "case.cfg"), "w") as f:
    for k, v in cfg.items(): f.write(f"{k} {v}\n")
with open(os.path.join(d, "geom.bin"), "wb") as f:
    f.write(t.tobytes()); f.write(ux.tobytes()); f.write(uy.tobytes()); f.write(probe.tobytes())
if not os.path.exists(os.path.join(d, "mean_ux.f32")):
  subprocess.run([os.path.join(ROOT, "solver", "lbm2d"), d], check=True, env=dict(os.environ, OMP_NUM_THREADS="1"),
                 stderr=subprocess.DEVNULL)
mu = np.fromfile(os.path.join(d, "mean_ux.f32"), np.float32).reshape(ny, nx)
x = 450
y = np.arange(1, ny - 1) - 0.5          # halfway bounce-back: wall at y=0.5 → 局部座標
prof = mu[1:-1, x]
ana = 1.5 * U * (1 - (2 * (y + 0.0) / H - 1) ** 2)
# 以格心位置 (k+0.5) 計算解析解
yc = np.arange(H) + 0.5
ana = 1.5 * U * (1 - (2 * yc / H - 1) ** 2)
l2 = np.sqrt(np.sum((prof - ana) ** 2) / np.sum(ana ** 2))
flux_in = U * H
flux_x = prof.sum()
res = dict(L2_rel_error=float(l2), flux_ratio=float(flux_x / flux_in), umax_ratio=float(prof.max() / (1.5 * U)))
print(res)
fig, ax = plt.subplots(figsize=(5.6, 4))
ax.plot(ana / U, yc / H, color=TEXT2, lw=1.5, ls="--", label="解析解（拋物線）")
ax.plot(prof / U, yc / H, "o", color=SERIES[0], ms=4, label="本求解器")
ax.set_xlabel("u / U（入口平均速度）"); ax.set_ylabel("y / H")
ax.set_title(f"驗證｜平行板管流  L2 誤差 {l2*100:.2f}%", loc="left", fontsize=11)
ax.legend(fontsize=9)
save(fig, "val_poiseuille.png")
json.dump(res, open(os.path.join(ROOT, "out", "val_poiseuille.json"), "w"), indent=1)
