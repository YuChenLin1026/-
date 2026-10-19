"""
build_face.py — S2 改版：臉在扶手「斜上方」。

人扶著內側扶手下樓時，口鼻在扶手的斜上方。這裡把口鼻放在出風口往樓梯側 28 cm、往上 35 cm
（距離約 45 cm、仰角約 51°），頭部以直徑 16 cm 圓柱近似，口鼻量測框在頭部朝出風口那一側。
出風口：
  A 一般定向：6 mm 窄縫，朝向口鼻。
  B 康達往上（Ku）：出風縫藏在導風腔底面，經下緣圓角 R30 轉向上（不另外對準口鼻，這就是它的設計）。
  C 低混合同軸：中央 15 mm＋兩側 7.5 mm 伴流，朝向口鼻。
  D 氣流倍增：開口 40 mm、內壁兩道 4.5 mm 縫、背面開放，朝向口鼻。
  W 空氣牆（第 05 章的最佳設計）：寬 80 mm、整流段 60 mm、水平往樓梯側吹，送風量 20 或 40 L/s/m。
A–D 每公尺出風口送風量都是 5 L/s（與舊 S2 相同）；網格 1.5 mm。
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

DX = 1.5e-3
LX, LY = 0.68, 0.82
X0, Y0 = 0.16, 0.20                  # 出風口出口中心（左側留空間給 B 的導風腔）
MOUTH = (X0 + 0.28, Y0 + 0.35)
HEAD_R = 0.08
AIM = np.degrees(np.arctan2(MOUTH[1] - Y0, MOUTH[0] - X0))
Q = 5e-3
RAIL_R = 0.025
NU, D_MOL, U_LAT_MAX, TAU_MIN = 1.5e-5, 2.0e-5, 0.1, 0.504
T_TOTAL, T_WARM = 10.0, 3.0
T_TOTAL0, T_WARM0 = 24.0, 8.0         # 無側風：氣流慢、要更久才穩定，平均後 16 秒
NX, NY = int(round(LX / DX)), int(round(LY / DX))
FLUID, SOLID, INLET = 0, 1, 2


def grid():
    x = (np.arange(NX) + 0.5) * DX
    y = (np.arange(NY) + 0.5) * DX
    return np.meshgrid(x, y)


def local(X, Y, ang):
    a = np.deg2rad(ang)
    s = (X - X0) * np.cos(a) + (Y - Y0) * np.sin(a)
    n = -(X - X0) * np.sin(a) + (Y - Y0) * np.cos(a)
    return s, n, np.cos(a), np.sin(a)


def rect(X, Y, x0, x1, y0, y1):
    return (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)


def rail_behind(X, Y, t, ang, L, keep):
    a = np.deg2rad(ang)
    rx, ry = X0 - (L + RAIL_R - 0.008) * np.cos(a), Y0 - (L + RAIL_R - 0.008) * np.sin(a)
    t[((X - rx) ** 2 + (Y - ry) ** 2 <= RAIL_R ** 2) & ~keep] = SOLID


def outlet_channels(X, Y, t, ux, uy, half_w, L, streams, ang):
    s, n, cs, sn = local(X, Y, ang)
    wall = 3 * DX
    t[(s >= -L - 3 * DX) & (s < 0) & (np.abs(n) < half_w + wall)] = SOLID
    keep = np.zeros_like(t, bool)
    for n0, n1, U in streams:
        ch = (s >= -L) & (s < 0) & (n >= n0) & (n < n1)
        t[ch] = FLUID
        keep |= ch
        inl = ch & (s < -L + 2 * DX)
        t[inl] = INLET
        ux[inl] = U * cs
        uy[inl] = U * sn
    rail_behind(X, Y, t, ang, L, keep | ((s >= -L - 3 * DX) & (s < 0) & (np.abs(n) < half_w + wall)))


def nozzle_A(X, Y, t, ux, uy):
    b = 6e-3
    outlet_channels(X, Y, t, ux, uy, b / 2, 25e-3, [(-b / 2, b / 2, Q / b)], AIM)
    return dict(U_exit=Q / b)


def nozzle_C(X, Y, t, ux, uy):
    bc, bs = 15e-3, 7.5e-3
    U1 = Q / (bc + 2 * bs * 0.5)
    h = bc / 2 + DX + bs
    outlet_channels(X, Y, t, ux, uy, h, 30e-3,
                    [(-bc / 2, bc / 2, U1), (bc / 2 + DX, h, 0.5 * U1), (-h, -bc / 2 - DX, 0.5 * U1)], AIM)
    return dict(U_exit=U1)


def nozzle_D(X, Y, t, ux, uy):
    W, b, th, L = 40e-3, 4.5e-3, 6e-3, 30e-3
    U = Q / (2 * b)
    s, n, cs, sn = local(X, Y, AIM)
    for sg in (+1, -1):
        n_in = sg * W / 2
        lo, hi = sorted((n_in, n_in + sg * th))
        t[(s >= -L) & (s < 0) & (n >= lo) & (n < hi)] = SOLID
        slo, shi = (n_in - b, n_in) if sg > 0 else (n_in, n_in + b)
        plo, phi = (slo - 2 * DX, slo) if sg > 0 else (shi, shi + 2 * DX)
        t[(s >= -L) & (s < -L + 10e-3) & (n >= plo) & (n < phi)] = SOLID          # 縫與開口的隔板
        t[(s >= -L) & (s < -L + 2 * DX) & (n >= slo) & (n < shi)] = SOLID          # 縫的背板
        inl = (s >= -L + 2 * DX) & (s < -L + 4 * DX) & (n >= slo) & (n < shi)
        t[inl] = INLET
        ux[inl] = U * cs
        uy[inl] = U * sn
    a = np.deg2rad(AIM)
    rx, ry = X0 - (L + 0.015 + RAIL_R) * np.cos(a), Y0 - (L + 0.015 + RAIL_R) * np.sin(a)
    t[(X - rx) ** 2 + (Y - ry) ** 2 <= RAIL_R ** 2] = SOLID
    return dict(U_exit=U)


def nozzle_B(X, Y, t, ux, uy):
    """康達往上：導風腔底面出風縫往樓梯側吹，經下緣圓角 R30 轉向上。導風腔正面中點在 (X0, Y0)。"""
    b, R, Wc, Hc = 6e-3, 30e-3, 0.15, 0.06
    U = Q / b
    xr, xl, yb, yt = X0, X0 - Wc, Y0 - Hc / 2, Y0 + Hc / 2
    cx, cy = xr - R, yb + R
    body = rect(X, Y, xl, xr, yb, yt)
    body &= ~((X > cx) & (Y < cy)) | ((X - cx) ** 2 + (Y - cy) ** 2 <= R * R)
    t[body] = SOLID
    L = 0.04
    t[rect(X, Y, cx - L, cx, yb - b - 3 * DX, yb - b)] = SOLID
    t[rect(X, Y, cx - L - 3 * DX, cx - L, yb - b - 3 * DX, yb)] = SOLID
    ch = rect(X, Y, cx - L, cx, yb - b, yb)
    t[ch] = FLUID
    inl = ch & (X < cx - L + 2 * DX)
    t[inl] = INLET
    ux[inl] = U
    gx = X0 - Wc / 2
    t[rect(X, Y, gx - 8e-3, gx + 8e-3, yt, yt + 38e-3)] = SOLID
    t[(X - gx) ** 2 + (Y - (yt + 38e-3 + 24e-3)) ** 2 <= 24e-3 ** 2] = SOLID
    return dict(U_exit=U)


def nozzle_W(X, Y, t, ux, uy, q):
    W = 80e-3
    outlet_channels(X, Y, t, ux, uy, W / 2, 60e-3, [(-W / 2, W / 2, q / W)], 0.0)
    return dict(U_exit=q / W)


NOZZLES = dict(A=nozzle_A, B=nozzle_B, C=nozzle_C, D=nozzle_D)


def build(name, nz, vc, q=Q):
    X, Y = grid()
    t = np.zeros((NY, NX), np.uint8)
    ux = np.zeros((NY, NX), np.float32)
    uy = np.zeros((NY, NX), np.float32)
    info = nozzle_W(X, Y, t, ux, uy, q) if nz == "W" else NOZZLES[nz](X, Y, t, ux, uy)
    # 頭：口鼻在 MOUTH，頭中心再沿出風口→口鼻方向往外 HEAD_R + 1.5 cm
    d = np.array([MOUTH[0] - X0, MOUTH[1] - Y0])
    d /= np.linalg.norm(d)
    hc = np.array(MOUTH) + d * (HEAD_R + 0.015)
    t[(X - hc[0]) ** 2 + (Y - hc[1]) ** 2 <= HEAD_R ** 2] = SOLID
    # 口鼻量測框：頭部朝出風口一側、離頭表面 0.5–2.5 cm、寬 ±1.2 cm
    s = (X - hc[0]) * (-d[0]) + (Y - hc[1]) * (-d[1])
    n = (X - hc[0]) * (-d[1]) + (Y - hc[1]) * d[0]
    probe = (s >= HEAD_R + 0.005) & (s <= HEAD_R + 0.025) & (np.abs(n) <= 0.012) & (t != SOLID)
    u_ref = max(float(np.abs(ux).max()), float(np.abs(uy).max()), 2.5 * vc)
    vel_scale = u_ref / U_LAT_MAX
    dt = DX / vel_scale
    t_total, t_warm = (T_TOTAL0, T_WARM0) if vc == 0 else (T_TOTAL, T_WARM)
    cfg = dict(nx=NX, ny=NY, steps=int(round(t_total / dt)), warmup=int(round(t_warm / dt)),
               tau0=max(0.5 + 3 * NU * dt / DX ** 2, TAU_MIN), cs=0.17, dlat=D_MOL * dt / DX ** 2, sct=0.7,
               vc=vc / vel_scale, sponge=25, probe_every=max(1, int(round(0.01 / dt))),
               frame_every=max(1, int(round(0.08 / dt))) if vc == 0.15 and nz != "W" else 0)
    dd = os.path.join(ROOT, "runs_face", name)
    os.makedirs(os.path.join(dd, "frames"), exist_ok=True)
    with open(os.path.join(dd, "case.cfg"), "w") as f:
        for k, v in cfg.items():
            f.write(f"{k} {v:.10g}\n")
    with open(os.path.join(dd, "geom.bin"), "wb") as f:
        f.write(t.tobytes())
        f.write((ux / vel_scale).astype(np.float32).tobytes())
        f.write((uy / vel_scale).astype(np.float32).tobytes())
        f.write(probe.astype(np.uint8).tobytes())
    meta = dict(name=name, nozzle=nz, vc_ms=vc, dx=DX, dt=dt, vel_scale=vel_scale, x0=X0, y0=Y0,
                mouth=MOUTH, head_c=hc.tolist(), head_r=HEAD_R, aim_deg=AIM, q=q, t_total=t_total,
                t_warm=t_warm, **info, **cfg)
    json.dump(meta, open(os.path.join(dd, "meta.json"), "w"), indent=1)
    np.save(os.path.join(dd, "type.npy"), t)
    return meta


CASES = [(f"{nz}_vc{int(vc*100):02d}", nz, vc, Q) for vc in (0.0, 0.15, 0.30) for nz in "ABCD"]
CASES += [(f"W{qq}_vc{int(vc*100):02d}", "W", vc, qq * 1e-3) for qq in (20, 40) for vc in (0.0, 0.15, 0.30)]

if __name__ == "__main__":
    sel = sys.argv[1:]
    for name, nz, vc, q in CASES:
        if sel and name not in sel:
            continue
        m = build(name, nz, vc, q)
        print(f"{name:8s} steps={m['steps']:6d} tau0={m['tau0']:.4f} U={m['U_exit']:.2f} aim={m['aim_deg']:.0f}°")
