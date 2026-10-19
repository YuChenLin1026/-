"""
build.py — 產生四種扶手出風口的 2D 斷面幾何與 case 設定，交給 solver/lbm2d 計算。

斷面定義（垂直於扶手長軸的剖面）：
  x：從扶手指向使用者臉部（噴流主軸）
  y：垂直於噴流（側風方向）
所有噴嘴「每公尺出風口長度的供氣量」相同：q = 5 L/s/m（公平比較條件）。

四組：
  A plain   一般定向噴嘴（基準組）       單一窄縫
  B coanda  康達曲面導流（輔助）         垂直出風縫沿凸曲面轉 90° 後脫離
  C coax    低混合率同軸噴嘴（主要研究） 寬出口、中央核心流 + 兩側低速伴流、整流段
  D amp     氣流倍增式（比較組）         環形開口內壁兩道 3 mm 縫，背面開放吸入環境空氣
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---------------- 物理參數 ----------------
DX = 1.0e-3            # 網格 1 mm
LX, LY = 0.64, 0.40    # 計算域（m）
X0 = 0.08              # 噴嘴出口平面位置
Y0 = LY / 2            # 噴流主軸
Q_SUPPLY = 5.0e-3      # m^2/s：每公尺出風口 5 L/s
NU = 1.5e-5            # 空氣動黏度
D_MOL = 2.0e-5         # 示蹤氣體分子擴散係數（CO 在空氣中約 2e-5 m^2/s）
U_LAT_MAX = 0.1        # 最大格子速度（壓縮性誤差控制）
RAIL_R = 0.025         # 扶手半徑（外徑 50 mm，假設值）
HEAD_R = 0.08          # 頭部以圓柱近似（直徑 160 mm）
FACE_L = 0.35          # 出口到臉部距離（低姿勢）
T_TOTAL = 10.0         # 模擬物理時間（s）
T_WARM = 4.0           # 前 4 s 不列入平均

NX, NY = int(round(LX / DX)), int(round(LY / DX))
FLUID, SOLID, INLET = 0, 1, 2


def grid():
    x = (np.arange(NX) + 0.5) * DX
    y = (np.arange(NY) + 0.5) * DX
    return np.meshgrid(x, y)  # shape (NY, NX)


def disk(X, Y, cx, cy, r):
    return (X - cx) ** 2 + (Y - cy) ** 2 <= r * r


def rect(X, Y, x0, x1, y0, y1):
    return (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)


def handrail(X, Y, cx):
    return disk(X, Y, cx, Y0, RAIL_R)


# ---------------- 四種噴嘴 ----------------
def nozzle_plain(X, Y, t, ux, uy):
    """A：窄縫 6 mm，出口速度 0.833 m/s，整流段 25 mm。"""
    b, L, wall = 6e-3, 25e-3, 2e-3
    U = Q_SUPPLY / b
    t[handrail(X, Y, X0 - L - RAIL_R + 8e-3)] = SOLID
    t[rect(X, Y, X0 - L, X0, Y0 - b / 2 - wall, Y0 + b / 2 + wall)] = SOLID
    ch = rect(X, Y, X0 - L, X0, Y0 - b / 2, Y0 + b / 2)
    t[ch] = FLUID
    inl = ch & rect(X, Y, X0 - L, X0 - L + 2 * DX, -1, 9)
    t[inl] = INLET
    ux[inl] = U
    return dict(U_exit=U, b=b)


def nozzle_coanda(X, Y, t, ux, uy):
    """B：6 mm 出風縫向下吹，沿半徑 15 mm 凸曲面轉 90°，在尖角處脫離後沿 +x 前進。"""
    b, Rc, wall, H = 6e-3, 15e-3, 2e-3, 35e-3
    U = Q_SUPPLY / b
    lcx, lcy = X0, Y0 + Rc + b / 2           # 曲面圓心：轉完 90° 後噴流中心正好在 y=Y0
    # 導流體：上方方塊 + 左下四分之一圓弧；右側垂直面與圓弧底點形成尖角（脫離點）
    t[rect(X, Y, lcx - Rc, lcx, lcy, lcy + H)] = SOLID
    t[disk(X, Y, lcx, lcy, Rc) & (X <= lcx) & (Y <= lcy)] = SOLID
    # 出風縫外壁與頂蓋
    t[rect(X, Y, lcx - Rc - b - wall, lcx - Rc - b, lcy, lcy + H)] = SOLID
    t[rect(X, Y, lcx - Rc - b - wall, lcx, lcy + H, lcy + H + wall)] = SOLID
    ch = rect(X, Y, lcx - Rc - b, lcx - Rc, lcy, lcy + H)
    inl = ch & (Y >= lcy + H - 2 * DX)
    t[inl] = INLET
    uy[inl] = -U
    # 扶手本體在導流體上方
    t[disk(X, Y, lcx - Rc - b / 2, lcy + H + wall + RAIL_R - 2e-3, RAIL_R)] = SOLID
    return dict(U_exit=U, b=b)


def nozzle_coax(X, Y, t, ux, uy):
    """C：總寬 30 mm；中央 14 mm 核心流 U1，兩側各 8 mm 伴流 U2=0.5·U1，整流段 30 mm。"""
    bc, bs, sp, wall, L = 14e-3, 8e-3, 1e-3, 2e-3, 30e-3
    U1 = Q_SUPPLY / (bc + 2 * bs * 0.5)
    U2 = 0.5 * U1
    half = bc / 2 + sp + bs
    t[handrail(X, Y, X0 - L - RAIL_R + 8e-3)] = SOLID
    t[rect(X, Y, X0 - L, X0, Y0 - half - wall, Y0 + half + wall)] = SOLID
    core = rect(X, Y, X0 - L, X0, Y0 - bc / 2, Y0 + bc / 2)
    up = rect(X, Y, X0 - L, X0, Y0 + bc / 2 + sp, Y0 + half)
    dn = rect(X, Y, X0 - L, X0, Y0 - half, Y0 - bc / 2 - sp)
    for m in (core, up, dn):
        t[m] = FLUID
    # 分隔板在出口前 3 mm 結束，減少尾跡
    t[rect(X, Y, X0 - 3e-3, X0, Y0 - half, Y0 + half)] = FLUID
    head = rect(X, Y, X0 - L, X0 - L + 2 * DX, -1, 9)
    for m, U in ((core, U1), (up, U2), (dn, U2)):
        inl = m & head
        t[inl] = INLET
        ux[inl] = U
    return dict(U_exit=U1, U_coflow=U2, b=bc + 2 * bs + 2 * sp)


def nozzle_amp(X, Y, t, ux, uy):
    """D：開口寬 40 mm 的環形導流體，內壁兩道 3 mm 薄縫沿 +x 吹出，背面開放吸入環境空氣。
    （原設計 2 mm 縫只有 2 格網格，縫內壓力堆積並在側風算例出現數值發散，故放寬為 3 mm。）"""
    W, b, th, L = 40e-3, 3e-3, 6e-3, 30e-3
    U = Q_SUPPLY / (2 * b)
    xa = X0 - L
    for s in (+1, -1):
        y_in = Y0 + s * W / 2                 # 內壁
        y_out = y_in + s * th                 # 外壁
        lo, hi = min(y_in, y_out), max(y_in, y_out)
        t[rect(X, Y, xa, X0, lo, hi)] = SOLID
        # 薄縫：內壁上，出口在 xa+8mm，縫內 6 mm 長
        slo, shi = (y_in - b, y_in) if s > 0 else (y_in, y_in + b)
        t[rect(X, Y, xa + 2e-3, xa + 8e-3, slo, shi)] = FLUID
        # 縫與開口之間 1 mm 隔板
        plo, phi = (slo - 1e-3, slo) if s > 0 else (shi, shi + 1e-3)
        t[rect(X, Y, xa, xa + 8e-3, plo, phi)] = SOLID
        t[rect(X, Y, xa, xa + 2e-3, slo, shi)] = SOLID   # 薄縫後端封口
        inl = rect(X, Y, xa + 2e-3, xa + 4e-3, slo, shi)
        t[inl] = INLET
        ux[inl] = U
    # 扶手在導流體後方，留 15 mm 間隙讓環境空氣被吸入
    t[handrail(X, Y, xa - 0.015 - RAIL_R)] = SOLID
    return dict(U_exit=U, b=2 * b, opening=W)


NOZZLES = dict(plain=nozzle_plain, coanda=nozzle_coanda, coax=nozzle_coax, amp=nozzle_amp)


def build_case(name, nozzle, head=True, vc=0.0, frames=False, t_total=T_TOTAL, t_warm=T_WARM):
    X, Y = grid()
    t = np.zeros((NY, NX), np.uint8)
    ux = np.zeros((NY, NX), np.float32)
    uy = np.zeros((NY, NX), np.float32)
    info = NOZZLES[nozzle](X, Y, t, ux, uy)
    hx = X0 + FACE_L + HEAD_R
    if head:
        t[disk(X, Y, hx, Y0, HEAD_R)] = SOLID
    # 口鼻呼吸區：臉前 5–25 mm、上下 ±12 mm
    probe = rect(X, Y, X0 + FACE_L - 0.025, X0 + FACE_L - 0.005, Y0 - 0.012, Y0 + 0.012)
    probe &= t != SOLID

    u_ref = max(float(np.abs(ux).max()), float(np.abs(uy).max()), vc)
    vel_scale = u_ref / U_LAT_MAX            # m/s per lattice velocity
    dt = DX / vel_scale
    nu_lat = NU * dt / DX ** 2
    d_lat = D_MOL * dt / DX ** 2
    steps = int(round(t_total / dt))
    warm = int(round(t_warm / dt))
    cfg = dict(nx=NX, ny=NY, steps=steps, warmup=warm, tau0=0.5 + 3 * nu_lat,
               cs=0.17, dlat=d_lat, sct=0.7, vc=vc / vel_scale, sponge=25,
               probe_every=max(1, int(round(0.01 / dt))),
               frame_every=max(1, int(round(0.08 / dt))) if frames else 0)
    d = os.path.join(ROOT, "runs", name)
    os.makedirs(os.path.join(d, "frames"), exist_ok=True)
    with open(os.path.join(d, "case.cfg"), "w") as f:
        for k, v in cfg.items():
            f.write(f"{k} {v:.10g}\n")
    with open(os.path.join(d, "geom.bin"), "wb") as f:
        f.write(t.tobytes())
        f.write((ux / vel_scale).astype(np.float32).tobytes())
        f.write((uy / vel_scale).astype(np.float32).tobytes())
        f.write(probe.astype(np.uint8).tobytes())
    meta = dict(name=name, nozzle=nozzle, head=head, vc_ms=vc, dx=DX, dt=dt, vel_scale=vel_scale,
                x0=X0, y0=Y0, face_l=FACE_L, head_r=HEAD_R, q=Q_SUPPLY,
                t_total=t_total, t_warm=t_warm, **info, **cfg)
    with open(os.path.join(d, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    np.save(os.path.join(d, "type.npy"), t)
    return d, meta


ALL_CASES = []
for nz in NOZZLES:
    ALL_CASES.append((f"{nz}_free", nz, False, 0.0, True))
    for vc in (0.0, 0.15, 0.30):
        ALL_CASES.append((f"{nz}_head_vc{int(vc * 100):02d}", nz, True, vc, vc == 0.15))

if __name__ == "__main__":
    sel = sys.argv[1:]
    for name, nz, head, vc, fr in ALL_CASES:
        if sel and name not in sel and nz not in sel:
            continue
        tt, tw = (16.0, 4.0) if nz == "coax" else (10.0, 3.0)
        d, m = build_case(name, nz, head, vc, fr, t_total=tt, t_warm=tw)
        print(f"{name:20s} steps={m['steps']:7d} tau0={m['tau0']:.5f} U={m['U_exit']:.3f} m/s dt={m['dt']:.2e}")
