"""
profile_geom.py — 使用者提供的扶手斷面（2026-10 草圖）在模擬裡的幾何。2D 與 3D 共用。

草圖：圓角方形的空心鋁擠型；右側（樓梯側）有一道凹槽，燈條藏在凹槽底部；
右上角是「噴氣區域」，風往右上方（約 40°）吹出。草圖沒有標尺寸，以下尺寸是依草圖比例
假設的（整體寬 110 mm、高 104 mm），全部集中在 P 這個字典，量到真尺寸後只改這裡。

座標：斷面左下角為原點，x 往樓梯側、y 往上，單位 mm。
"""
import numpy as np

P = dict(
    W=110.0, H=104.0,          # 整體寬、高（假設）
    body_right=38.0,           # 左側主體的右緣（凹槽左壁）
    lip_right=65.0,            # 上方握持唇的右緣
    lip_bottom=65.0,           # 握持唇的下緣（凹槽頂）
    pocket_right=71.0,         # 凹槽右壁（下方平台左緣）
    pocket_bottom=28.0,        # 凹槽底（燈條所在）
    lower_top=40.0,            # 右下平台頂面
    corner_r=6.0,              # 外圓角
    aim=40.0,                  # 噴氣方向（草圖箭頭約 40°，由水平量起）
    chamfer=38.0,              # 右上角斜切面長度：出風口就開在這個面上
    slot_depth=30.0,           # 出風通道（整流段）深度
)


def chamfer_geometry(p=P):
    """斜切面：法線方向 = 噴氣方向。回傳 (出風口中心 xy, 單位法線 n, 單位切線 t, 斜切距離 d)。"""
    a = np.deg2rad(p["aim"])
    n = np.array([np.cos(a), np.sin(a)])
    t = np.array([-np.sin(a), np.cos(a)])
    d = p["chamfer"] * np.sin(a) * np.cos(a)          # 直角轉角被切掉的深度
    corner = np.array([p["lip_right"], p["H"]])
    return corner - d * n, n, t, d


def _rounded_rect(X, Y, x0, x1, y0, y1, r, corners):
    """長方形 + 指定角的圓角（corners: 'bl','br','tl','tr' 的子集）。"""
    m = (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)
    for c in corners:
        cx = x0 + r if c[1] == "l" else x1 - r
        cy = y0 + r if c[0] == "b" else y1 - r
        inx = (X < cx) if c[1] == "l" else (X > cx)
        iny = (Y < cy) if c[0] == "b" else (Y > cy)
        m &= ~(inx & iny & ((X - cx) ** 2 + (Y - cy) ** 2 > r * r))
    return m


def solid_mask(X, Y, p=P):
    """斷面實心範圍（X、Y 為 mm，原點在斷面左下）。2D 模擬只需要外形，內部空腔不影響外部氣流。"""
    r = p["corner_r"]
    body = _rounded_rect(X, Y, 0, p["body_right"] + 1e-9, 0, p["H"], r, ["tl", "bl"])
    lip = (X >= p["body_right"] - 1) & (X < p["lip_right"]) & (Y >= p["lip_bottom"]) & (Y < p["H"])
    bottom = _rounded_rect(X, Y, 0, p["W"], 0, p["pocket_bottom"], r, ["bl", "br"])
    lower = _rounded_rect(X, Y, p["pocket_right"], p["W"], 0, p["lower_top"], r, ["tr", "br"])
    m = body | lip | bottom | lower
    c, n, t, d = chamfer_geometry(p)
    s = (X - c[0]) * n[0] + (Y - c[1]) * n[1]
    m &= ~(s > 0)                                     # 右上角斜切
    return m


def led_region(X, Y, p=P):
    """燈條（凹槽底部）：只用來畫圖，不影響氣流。"""
    return (X >= p["body_right"] + 2) & (X < p["pocket_right"] - 6) & (Y >= p["pocket_bottom"]) & (Y < p["pocket_bottom"] + 5)


def outlet_streams(kind, q, p=P):
    """出風口的分流：回傳 [(n0, n1, U), ...]（沿斜切面切線方向的範圍 mm，與出口風速 m/s）以及總寬 mm。
    kind 'C'：低混合同軸，中央 15 mm + 兩側 7.5 mm 伴流（風速一半），中間 1.5 mm 隔板，總寬 33 mm。
    kind 'W'：空氣牆，同一個斜切面上整片均勻出風，寬 33 mm（斷面放得下的最寬）。
    q：每公尺出風口的送風量（m³/s/m）。"""
    if kind == "C":
        bc, bs, g = 15.0, 7.5, 1.5
        U1 = q / ((bc + 2 * bs * 0.5) * 1e-3)
        h = bc / 2 + g + bs
        return [(-bc / 2, bc / 2, U1), (bc / 2 + g, h, 0.5 * U1), (-h, -bc / 2 - g, 0.5 * U1)], 2 * h
    if kind == "W":
        w = 33.0
        return [(-w / 2, w / 2, q / (w * 1e-3))], w
    raise ValueError(kind)
