"""
build_zone.py — S6「守住扶手旁 40–60 cm」掃描：送風量 × 出風口 × 側風。

與 S2 的差別：
  - 不放人頭（臉的位置因人、因姿勢而異），改量扶手出風口前方半徑 50 cm 的半圓區域。
  - 網格 2.5 mm（計算量約為 S2 的 1/8，才能在雲端跑完一整組掃描）。
  - 送風量從每公尺 5 L/s 加到 40 L/s。
出風口：
  C 低混合同軸：中央 15 mm 核心流 U1，兩側各 7.5 mm 伴流 U2 = 0.5·U1，總寬約 35 mm，整流段 30 mm。
  W 空氣牆：寬 80 mm、整流段 60 mm 的均勻平直出風（可視為放大的低混合出風口）。
  Wd：同 W，但出風方向向下傾 30°，用來抵銷由下往上的側風（設計探索）。
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

DX = 2.5e-3
LX, LY = 0.90, 1.30
X0, Y0 = 0.12, 0.62            # 出口平面中心
RAIL_R = 0.025
ZONE_R = 0.50                  # 量測區：出口前方半徑 50 cm 的半圓
NU, D_MOL, U_LAT_MAX = 1.5e-5, 2.0e-5, 0.1
T_TOTAL, T_WARM = 8.0, 3.0
TAU_MIN = 0.504
NX, NY = int(round(LX / DX)), int(round(LY / DX))
FLUID, SOLID, INLET = 0, 1, 2


def grid():
    x = (np.arange(NX) + 0.5) * DX
    y = (np.arange(NY) + 0.5) * DX
    return np.meshgrid(x, y)


def rect(X, Y, x0, x1, y0, y1):
    return (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)


def channel_outlet(X, Y, t, ux, uy, half_w, L, streams, angle_deg=0.0):
    """一般化的整流出風口：在出口局部座標 (s 沿出風方向, n 垂直) 畫通道。
    streams: [(n0, n1, U), ...] 各子通道的範圍與速度；子通道之間留 1 格隔板。"""
    a = np.deg2rad(angle_deg)
    cs, sn = np.cos(a), np.sin(a)
    s = (X - X0) * cs + (Y - Y0) * sn          # 沿出風方向，出口在 s=0
    n = -(X - X0) * sn + (Y - Y0) * cs
    wall = 3 * DX                                # 3 格厚，避免斜牆的對角漏風
    body = (s >= -L - 3 * DX) & (s < 0) & (np.abs(n) < half_w + wall)   # 含背板
    t[body] = SOLID
    for n0, n1, U in streams:
        ch = (s >= -L) & (s < 0) & (n >= n0) & (n < n1)
        t[ch] = FLUID
        inl = ch & (s < -L + 2 * DX)
        t[inl] = INLET
        ux[inl] = U * cs
        uy[inl] = U * sn
    # 扶手本體在出風口後方
    rx, ry = X0 - (L + RAIL_R - 0.008) * cs, Y0 - (L + RAIL_R - 0.008) * sn
    rail = (X - rx) ** 2 + (Y - ry) ** 2 <= RAIL_R ** 2
    t[rail & ~((s >= -L) & (s < 0) & (np.abs(n) < half_w))] = SOLID


def nozzle(kind, q, X, Y, t, ux, uy):
    if kind == "C":
        bc, bs = 15e-3, 7.5e-3
        U1 = q / (bc + 2 * bs * 0.5)
        U2 = 0.5 * U1
        h = bc / 2 + DX + bs
        streams = [(-bc / 2, bc / 2, U1), (bc / 2 + DX, h, U2), (-h, -bc / 2 - DX, U2)]
        channel_outlet(X, Y, t, ux, uy, h, 30e-3, streams)
        return dict(U_exit=U1, width=2 * h)
    W = 80e-3
    U = q / W
    channel_outlet(X, Y, t, ux, uy, W / 2, 60e-3, [(-W / 2, W / 2, U)], angle_deg=(-30.0 if kind == "Wd" else 0.0))
    return dict(U_exit=U, width=W)


def build(name, kind, q, vc):
    X, Y = grid()
    t = np.zeros((NY, NX), np.uint8)
    ux = np.zeros((NY, NX), np.float32)
    uy = np.zeros((NY, NX), np.float32)
    info = nozzle(kind, q, X, Y, t, ux, uy)
    zone = ((X - X0) ** 2 + (Y - Y0) ** 2 <= ZONE_R ** 2) & (X > X0 + 0.02) & (t != SOLID)
    u_ref = max(float(np.abs(ux).max()), float(np.abs(uy).max()), 2.5 * vc)
    vel_scale = u_ref / U_LAT_MAX
    dt = DX / vel_scale
    t_total = 20.0 if vc == 0 else T_TOTAL      # 無側風時氣流慢，要算久一點
    # tau0 下限 0.504：大風量時分子黏度換算後太接近穩定邊界，以略放大的黏度換取穩定（報告中註明）
    tau0 = max(0.5 + 3 * NU * dt / DX ** 2, TAU_MIN)
    cfg = dict(nx=NX, ny=NY, steps=int(round(t_total / dt)), warmup=int(round(T_WARM / dt)),
               tau0=tau0, cs=0.17, dlat=D_MOL * dt / DX ** 2, sct=0.7,
               vc=vc / vel_scale, sponge=25, probe_every=max(1, int(round(0.01 / dt))), frame_every=0)
    d = os.path.join(ROOT, "runs_zone", name)
    os.makedirs(os.path.join(d, "frames"), exist_ok=True)
    with open(os.path.join(d, "case.cfg"), "w") as f:
        for k, v in cfg.items():
            f.write(f"{k} {v:.10g}\n")
    with open(os.path.join(d, "geom.bin"), "wb") as f:
        f.write(t.tobytes())
        f.write((ux / vel_scale).astype(np.float32).tobytes())
        f.write((uy / vel_scale).astype(np.float32).tobytes())
        f.write(zone.astype(np.uint8).tobytes())
    meta = dict(name=name, kind=kind, q=q, vc_ms=vc, dx=DX, dt=dt, vel_scale=vel_scale, x0=X0, y0=Y0,
                zone_r=ZONE_R, t_total=t_total, t_warm=T_WARM, **info, **cfg)
    json.dump(meta, open(os.path.join(d, "meta.json"), "w"), indent=1)
    np.save(os.path.join(d, "type.npy"), t)
    return meta


CASES = []
for kind in ("C", "W"):
    CASES.append((f"{kind}_q05_vc00", kind, 5e-3, 0.0))
    for vc in (0.15, 0.30):
        for q in (5e-3, 10e-3, 20e-3, 40e-3):
            CASES.append((f"{kind}_q{int(q*1000):02d}_vc{int(vc*100):02d}", kind, q, vc))
for q in (20e-3, 40e-3):
    CASES.append((f"Wd_q{int(q*1000):02d}_vc30", "Wd", q, 0.30))

if __name__ == "__main__":
    sel = sys.argv[1:]
    for name, kind, q, vc in CASES:
        if sel and name not in sel:
            continue
        m = build(name, kind, q, vc)
        print(f"{name:14s} steps={m['steps']:6d} tau0={m['tau0']:.4f} U={m['U_exit']:.2f} m/s")
