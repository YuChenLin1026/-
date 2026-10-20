"""
build_profile.py — 使用者的扶手斷面（profile_geom.py）＋前兩名出風口（C 低混合同軸、W 空氣牆），
放進和 build_face.py 一樣的「臉在斜上方＋有頭」測試（2D、1.5 mm 網格）。

出風口開在握持唇右上角的斜切面上，往右上方約 40° 吹（依草圖）；口鼻在出風口中心往樓梯側 28 cm、往上 35 cm，
和 build_face.py 相同，結果可以直接對照第 04 章。
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_face as BF  # noqa: E402
import profile_geom as PG  # noqa: E402

ROOT = BF.ROOT
DX, NX, NY = BF.DX, BF.NX, BF.NY
X0, Y0 = BF.X0, BF.Y0                       # 出風口中心（m）
MOUTH, HEAD_R = BF.MOUTH, BF.HEAD_R
FLUID, SOLID, INLET = BF.FLUID, BF.SOLID, BF.INLET


def place_profile(X, Y, t, ux, uy, kind, q):
    p = PG.P
    c_mm, n, tt, d = PG.chamfer_geometry(p)
    # 斷面原點（左下角）放在讓出風口中心落在 (X0, Y0) 的位置
    ox, oy = X0 - c_mm[0] * 1e-3, Y0 - c_mm[1] * 1e-3
    Xm, Ym = (X - ox) * 1e3, (Y - oy) * 1e3
    t[PG.solid_mask(Xm, Ym, p)] = SOLID
    # 出風通道：沿 -n 方向深 slot_depth，分流之間 1 格隔板
    s = (Xm - c_mm[0]) * n[0] + (Ym - c_mm[1]) * n[1]          # 沿出風方向（mm），出口在 s=0
    w = (Xm - c_mm[0]) * tt[0] + (Ym - c_mm[1]) * tt[1]        # 沿斜切面（mm）
    streams, width = PG.outlet_streams(kind, q, p)
    L = p["slot_depth"]
    dxm = DX * 1e3
    t[(s >= -L - 3 * dxm) & (s < 0) & (np.abs(w) < width / 2 + 3 * dxm)] = SOLID   # 通道外殼（含背板）
    keep = np.zeros_like(t, bool)
    for w0, w1, U in streams:
        ch = (s >= -L) & (s < 0) & (w >= w0) & (w < w1)
        t[ch] = FLUID
        keep |= ch
        inl = ch & (s < -L + 2 * DX * 1e3)
        t[inl] = INLET
        ux[inl] = U * n[0]
        uy[inl] = U * n[1]
    return dict(U_exit=max(U for _, _, U in streams), width_mm=width, origin=[ox, oy])


def build(name, kind, q, vc):
    X, Y = BF.grid()
    t = np.zeros((NY, NX), np.uint8)
    ux = np.zeros((NY, NX), np.float32)
    uy = np.zeros((NY, NX), np.float32)
    info = place_profile(X, Y, t, ux, uy, kind, q)
    d = np.array([MOUTH[0] - X0, MOUTH[1] - Y0])
    d /= np.linalg.norm(d)
    hc = np.array(MOUTH) + d * (HEAD_R + 0.015)
    t[(X - hc[0]) ** 2 + (Y - hc[1]) ** 2 <= HEAD_R ** 2] = SOLID
    s = (X - hc[0]) * (-d[0]) + (Y - hc[1]) * (-d[1])
    nn = (X - hc[0]) * (-d[1]) + (Y - hc[1]) * d[0]
    probe = (s >= HEAD_R + 0.005) & (s <= HEAD_R + 0.025) & (np.abs(nn) <= 0.012) & (t != SOLID)
    u_ref = max(float(np.abs(ux).max()), float(np.abs(uy).max()), 2.5 * vc)
    vel_scale = u_ref / BF.U_LAT_MAX
    dt = DX / vel_scale
    t_total, t_warm = (BF.T_TOTAL0, BF.T_WARM0) if vc == 0 else (BF.T_TOTAL, BF.T_WARM)
    cfg = dict(nx=NX, ny=NY, steps=int(round(t_total / dt)), warmup=int(round(t_warm / dt)),
               tau0=max(0.5 + 3 * BF.NU * dt / DX ** 2, BF.TAU_MIN), cs=0.17, dlat=BF.D_MOL * dt / DX ** 2, sct=0.7,
               vc=vc / vel_scale, sponge=25, probe_every=max(1, int(round(0.01 / dt))), frame_every=0)
    dd = os.path.join(ROOT, "runs_profile", name)
    os.makedirs(os.path.join(dd, "frames"), exist_ok=True)
    with open(os.path.join(dd, "case.cfg"), "w") as f:
        for k, v in cfg.items():
            f.write(f"{k} {v:.10g}\n")
    with open(os.path.join(dd, "geom.bin"), "wb") as f:
        f.write(t.tobytes())
        f.write((ux / vel_scale).astype(np.float32).tobytes())
        f.write((uy / vel_scale).astype(np.float32).tobytes())
        f.write(probe.astype(np.uint8).tobytes())
    meta = dict(name=name, nozzle=f"P{kind}", kind=kind, vc_ms=vc, dx=DX, dt=dt, vel_scale=vel_scale, x0=X0, y0=Y0,
                mouth=MOUTH, head_c=hc.tolist(), head_r=HEAD_R, aim_deg=PG.P["aim"], q=q, t_total=t_total,
                t_warm=t_warm, profile=PG.P, **info, **cfg)
    json.dump(meta, open(os.path.join(dd, "meta.json"), "w"), indent=1)
    np.save(os.path.join(dd, "type.npy"), t)
    return meta


# 無側風 + 每公尺 40 L/s 會把 2D 模型範圍填滿（第 04 章），所以大風量只算有側風的
CASES = ([(f"PC05_vc{int(vc*100):02d}", "C", 5e-3, vc) for vc in (0.0, 0.15, 0.30)]
         + [(f"PC40_vc{int(vc*100):02d}", "C", 40e-3, vc) for vc in (0.15, 0.30)]
         + [(f"PW40_vc{int(vc*100):02d}", "W", 40e-3, vc) for vc in (0.15, 0.30)])

if __name__ == "__main__":
    sel = sys.argv[1:]
    for name, kind, q, vc in CASES:
        if sel and name not in sel:
            continue
        m = build(name, kind, q, vc)
        print(f"{name:10s} steps={m['steps']:6d} tau0={m['tau0']:.4f} U={m['U_exit']:.2f} width={m['width_mm']:.0f} mm")
