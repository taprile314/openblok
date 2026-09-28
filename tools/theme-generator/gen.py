import os, sys, wave, colorsys
import numpy as np
from PIL import Image, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
DEF = os.path.join(BASE, "../../data/themes/default/graphics")
OUT = os.path.join(BASE, "out")
W, H = 1920, 1080
rng = np.random.default_rng(7)


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in range(0, len(h), 2)], dtype=float)


def save(arr, path, jpg=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if jpg:
        im.convert("RGB").save(path, quality=92)
    else:
        im.save(path)


def blur(arr, r):
    chans = [np.array(Image.fromarray(np.clip(arr[..., c], 0, 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(r)), dtype=float) for c in range(arr.shape[2])]
    return np.stack(chans, -1)


def grid(h, w):
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    return yy, xx


def rrect_sdf(u, v, inset, r):
    # rounded rect in unit tile
    hx = 0.5 - inset
    qx = np.abs(u - 0.5) - (hx - r)
    qy = np.abs(v - 0.5) - (hx - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def downsample(arr, size=32):
    # premultiplied downsample to avoid dark fringes
    a = arr[..., 3:4] / 255
    pm = np.concatenate([arr[..., :3] * a, arr[..., 3:4]], -1)
    f = arr.shape[0] // size
    pm = pm.reshape(size, f, size, f, 4).mean((1, 3))
    a = np.maximum(pm[..., 3:4] / 255, 1e-6)
    return np.concatenate([pm[..., :3] / a, pm[..., 3:4]], -1)


def nearest(arr, f):
    return arr.repeat(f, 0).repeat(f, 1)


# ---------------------------------------------------------------- minos
S = 128


def mino_neon(col):
    yy, xx = grid(S, S)
    u, v = (xx + .5) / S, (yy + .5) / S
    d = rrect_sdf(u, v, 0.07, 0.12)
    out = np.zeros((S, S, 4))
    inner = np.exp(-np.maximum(-d, 0) / 0.10)
    fill = col * (0.38 + 0.5 * inner)[..., None]
    edge = sstep(-0.075, -0.045, d) * (1 - sstep(-0.005, 0.005, d))
    fill = fill * (1 - edge[..., None]) + np.minimum(col * 0.75 + 110, 255) * edge[..., None]
    hl = np.exp(-(((u - 0.3) / 0.12) ** 2 + ((v - 0.24) / 0.035) ** 2))
    fill = fill + 200 * hl[..., None]
    alpha = np.where(d < 0, 255, 170 * np.exp(-d / 0.025))
    out[..., :3] = np.where((d < 0)[..., None], fill, col)
    out[..., 3] = alpha
    return downsample(out)


def mino_nes(col, hollow):
    p = np.zeros((8, 8, 4))
    p[..., 3] = 255
    p[..., :3] = col
    if hollow:
        p[1:6, 1:6, :3] = 255
    p[0, 0, :3] = 255
    p[1, 1, :3] = 255; p[1, 2, :3] = 255; p[2, 1, :3] = 255
    p[7, :, :3] = 0
    p[:, 7, :3] = 0
    return nearest(p, 4)


CRT_PATTERNS = {
    "i": lambda x, y: np.ones_like(x),
    "j": lambda x, y: ((x + y) % 2 == 0) * 0.6 + 0.4,
    "l": lambda x, y: (y % 2 == 0) * 0.55 + 0.45,
    "o": lambda x, y: np.where((x == 0) | (y == 0) | (x == 6) | (y == 6) | ((x == 3) & (y == 3)), 1, 0.3),
    "s": lambda x, y: ((x + y) % 3 == 0) * 0.6 + 0.4,
    "t": lambda x, y: ((x % 2 == 0) | (y % 2 == 0)) * 0.5 + 0.5,
    "z": lambda x, y: (x % 2 == 0) * 0.55 + 0.45,
    "garbage": lambda x, y: ((x % 3 == 1) & (y % 3 == 1)) * 0.6 + 0.25,
}


def mino_crt(col, kind):
    yy, xx = grid(8, 8)
    k = CRT_PATTERNS[kind](xx, yy)
    p = np.zeros((8, 8, 4))
    p[..., :3] = col * k[..., None]
    p[..., 3] = 255
    p[7, :, :3] = col * 0.08
    p[:, 7, :3] = col * 0.08
    big = nearest(p, 4)
    glow = blur(big, 1.2)
    big[..., :3] = np.maximum(big[..., :3], glow[..., :3] * 0.9)
    big[1::2, :, :3] *= 0.72  # scanlines
    return big


def mino_soft(col):
    yy, xx = grid(S, S)
    u, v = (xx + .5) / S, (yy + .5) / S
    d = rrect_sdf(u, v, 0.05, 0.18)
    top = col + (255 - col) * 0.28
    bot = col * 0.78
    g = v[..., None]
    fill = np.where(g < 0.5, top + (col - top) * (g / 0.5), col + (bot - col) * ((g - 0.5) / 0.5))
    border = sstep(-0.045, -0.03, d)[..., None]
    fill = fill * (1 - border) + col * 0.55 * border
    hl = np.exp(-(((v - 0.16) / 0.025) ** 2)) * sstep(0.15, 0.3, u) * (1 - sstep(0.7, 0.85, u))
    fill = fill + (255 - fill) * 0.45 * hl[..., None]
    out = np.zeros((S, S, 4))
    out[..., :3] = fill
    out[..., 3] = 255 * (1 - sstep(-0.006, 0.006, d))
    return downsample(out)


def mino_glass(col):
    yy, xx = grid(S, S)
    u, v = (xx + .5) / S, (yy + .5) / S
    d = rrect_sdf(u, v, 0.04, 0.12)
    t = ((u + v) / 2)[..., None]
    fill = (col * 1.15) * (1 - t) + col * 0.55 * t
    gloss = (v < 0.48 - 0.12 * u) * 0.32
    gloss = blur(np.repeat(gloss[..., None] * 255, 1, -1), 1.5)[..., 0] / 255
    fill = fill + (255 - fill) * gloss[..., None]
    rim = sstep(-0.05, -0.025, d)[..., None]
    fill = fill * (1 - rim) + (col + (255 - col) * 0.6) * rim
    out = np.zeros((S, S, 4))
    out[..., :3] = fill
    out[..., 3] = 235 * (1 - sstep(-0.006, 0.006, d))
    return downsample(out)


def ghost_rounded(col, inset=0.07, r=0.12, fill_a=40):
    yy, xx = grid(S, S)
    u, v = (xx + .5) / S, (yy + .5) / S
    d = rrect_sdf(u, v, inset, r)
    line = sstep(-0.07, -0.05, d) * (1 - sstep(-0.006, 0.006, d))
    out = np.zeros((S, S, 4))
    out[..., :3] = col
    out[..., 3] = np.maximum(line * 230, (d < 0) * fill_a)
    return downsample(out)


def ghost_pixel(col, dotted=False):
    p = np.zeros((8, 8, 4))
    p[..., :3] = col
    edge = np.zeros((8, 8), bool)
    edge[0, :7] = edge[6, :7] = edge[:7, 0] = edge[:7, 6] = True
    if dotted:
        yy, xx = grid(8, 8)
        edge &= ((xx + yy) % 2 == 0)
    p[..., 3] = edge * 220
    return nearest(p, 4)


def matrix_cell(fill, fill_a, line, line_a):
    c = np.zeros((32, 32, 4))
    c[..., :3] = fill
    c[..., 3] = fill_a
    c[31, :, :3] = line; c[31, :, 3] = line_a
    c[:, 31, :3] = line; c[:, 31, 3] = line_a
    return c


# ---------------------------------------------------------------- UI pieces
def recolor_well(src, panel, panel_a, border, border_a, edge, edge_a):
    a = np.array(Image.open(src).convert("RGBA"), dtype=float)
    out = np.zeros_like(a)
    is_border = (a[..., 2] > 200) & (a[..., 3] > 0)
    is_edge = (a[..., 2] < 50) & (a[..., 3] == 153)
    is_panel = (a[..., 2] < 50) & (a[..., 3] == 76)
    out[is_panel, :3] = panel; out[is_panel, 3] = panel_a
    out[is_border, :3] = border; out[is_border, 3] = border_a
    out[is_edge, :3] = edge; out[is_edge, 3] = edge_a
    return out


def vgrad(stops, h=720, w=32):
    y = np.linspace(0, 1, h)
    cols = np.stack([np.interp(y, [s[0] for s in stops], [hexc(s[1])[c] for s in stops]) for c in range(3)], -1)
    return np.repeat(cols[:, None, :], w, 1)


def recolor_logo(hue=None, sat=1.0, mono=None):
    im = Image.open(os.path.join(DEF, "logo.png")).convert("RGBA")
    a = np.array(im, dtype=float)
    rgb = a[..., :3] / 255
    out = rgb.copy()
    flat = rgb.reshape(-1, 3)
    res = out.reshape(-1, 3)
    for i, (r, g, b) in enumerate(flat):
        hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
        if mono is not None:
            lum = 0.3 * r + 0.59 * g + 0.11 * b
            res[i] = np.array(mono) / 255 * lum * 1.15
        elif ss > 0.2:
            res[i] = colorsys.hsv_to_rgb(hue, min(1, ss * sat), vv)
    a[..., :3] = np.clip(res.reshape(rgb.shape), 0, 1) * 255
    return a


# ---------------------------------------------------------------- backgrounds
def add_stars(img, n, region_h, seed, bright=255):
    r = np.random.default_rng(seed)
    ys = r.integers(0, int(region_h), n)
    xs = r.integers(0, W, n)
    b = r.random(n) ** 3 * bright
    layer = np.zeros((H, W, 3))
    layer[ys, xs] = b[:, None]
    big = r.random(n) > 0.96
    glow = np.zeros((H, W, 3))
    glow[ys[big], xs[big]] = 255 * 6
    return img + layer + blur(np.clip(glow, 0, 255), 2.5) * 0.9


def dither(img, amt=2.0):
    return img + rng.normal(0, amt, img.shape)


def bg_synthwave():
    yy, xx = grid(H, W)
    hz = 0.60 * H
    y = yy / hz
    sky = np.zeros((H, W, 3))
    stops = [(0, "#07021A"), (0.45, "#1A0638"), (0.8, "#5B0F6B"), (1.0, "#FF3D8B")]
    for c in range(3):
        sky[..., c] = np.interp(y, [s[0] for s in stops], [hexc(s[1])[c] for s in stops])
    sky = add_stars(sky, 900, hz * 0.7, 1)
    # sun
    cx, cy, R = W / 2, hz - 0.02 * H, 0.21 * H
    dist = np.hypot(xx - cx, yy - cy)
    sv = np.clip((yy - (cy - R)) / (2 * R), 0, 1)[..., None]
    suncol = hexc("#FFE45E") * (1 - sv) + hexc("#FF2E88") * sv
    rel = (yy - cy) / R
    k = np.clip(rel, 0, 1)
    period = 0.16
    stripe = ((rel > 0.05) & (((rel + 1) % period) < period * (0.2 + 0.6 * k)))
    inside = (dist < R) & ~stripe
    glow = np.exp(-np.maximum(dist - R, 0) / (0.12 * H))[..., None] * hexc("#FF3D8B") * 0.55
    img = sky + glow * (yy < hz)[..., None]
    img = np.where(inside[..., None], suncol, img)
    # ground + grid
    t = np.clip((yy - hz) / (H - hz), 1e-4, 1)
    ground = yy >= hz
    z = 1.6 / t
    fz = np.abs(z - np.round(z))
    dpx = fz * t ** 2 * (H - hz) / 1.6
    hline = np.exp(-(dpx / 1.3) ** 2)
    sc = W * 0.055
    xp = (xx - W / 2) / t / sc
    vd = np.abs(xp - np.round(xp)) * t * sc
    vline = np.exp(-(vd / (1.0 + 1.4 * t)) ** 2)
    lines = np.maximum(hline, vline) * np.clip(t * 3, 0, 1)
    gcol = hexc("#FF2BD6")
    gr = hexc("#12032A") * (1 - t[..., None]) + hexc("#05010D") * t[..., None]
    gl = gr + lines[..., None] * gcol
    gl = gl + blur(np.clip(lines[..., None] * gcol, 0, 255), 4) * 0.8
    img = np.where(ground[..., None], gl, img)
    hglow = np.exp(-np.abs(yy - hz) / 6)[..., None] * hexc("#FF7AE6")
    img = img + hglow
    return dither(img)


def bg_nes():
    w, h = W // 8, H // 8
    yy, xx = grid(h, w)
    img = np.zeros((h, w, 3))
    chk = ((xx // 2 + yy // 2) % 2 == 0)
    img[chk] = hexc("#08081C")
    img[~chk] = hexc("#000008")
    shapes = [[(0, 0), (1, 0), (2, 0), (3, 0)], [(0, 0), (0, 1), (1, 1), (2, 1)], [(2, 0), (0, 1), (1, 1), (2, 1)],
              [(0, 0), (1, 0), (0, 1), (1, 1)], [(1, 0), (2, 0), (0, 1), (1, 1)], [(1, 0), (0, 1), (1, 1), (2, 1)],
              [(0, 0), (1, 0), (1, 1), (2, 1)]]
    cols = ["#3CBCFC", "#0058F8", "#F87858", "#F8B800", "#58D854", "#D800CC", "#F83800"]
    r = np.random.default_rng(3)
    for _ in range(70):
        k = r.integers(0, 7)
        cs = 4
        ox, oy = r.integers(0, w - 16), r.integers(0, h - 10)
        if w * 0.33 < ox < w * 0.62:
            continue
        col = hexc(cols[k]) * 0.28
        for (bx, by) in shapes[k]:
            x0, y0 = ox + bx * cs, oy + by * cs
            img[y0:y0 + cs - 1, x0:x0 + cs - 1] = col
            img[y0, x0] = col * 2
    return nearest(img, 8)


def bg_crt():
    yy, xx = grid(H, W)
    img = np.zeros((H, W, 3)) + hexc("#020A05")
    gridl = ((xx % 60) < 1.5) | ((yy % 60) < 1.5)
    img[gridl] = hexc("#062012")
    r = np.random.default_rng(5)
    # fake terminal text columns on the sides
    for side in (0, 1):
        x0 = 60 if side == 0 else int(W * 0.66)
        for row in range(38):
            y0 = 60 + row * 26
            x = x0
            n = r.integers(5, 40)
            for _ in range(n):
                wch = 12
                if r.random() < 0.8:
                    img[y0:y0 + 14, x:x + wch - 3] = hexc("#0F4A22") * (0.6 + 0.4 * r.random())
                x += wch
                if x > x0 + 560:
                    break
    img = img + blur(img, 3) * 0.6
    img[(yy % 3) == 0] *= 0.45
    vig = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
    img *= (1 - 0.55 * np.clip(vig - 0.3, 0, 1))[..., None]
    img += np.random.default_rng(9).normal(0, 3, img.shape) * np.array([0.3, 1, 0.5])
    return img


def bg_dracula():
    yy, xx = grid(H, W)
    t = ((xx / W + yy / H) / 2)[..., None]
    img = hexc("#23242F") * (1 - t) + hexc("#14151B") * t
    blobs = np.zeros((H, W, 3))
    for (bx, by, rad, col, s) in [(0.15, 0.25, 0.35, "#BD93F9", 0.20), (0.85, 0.75, 0.4, "#FF79C6", 0.16),
                                  (0.8, 0.15, 0.25, "#8BE9FD", 0.12), (0.2, 0.9, 0.3, "#50FA7B", 0.06)]:
        d = np.hypot(xx / W - bx, (yy / H - by) * H / W)
        blobs += np.exp(-(d / rad) ** 2)[..., None] * hexc(col) * s
    img = img + blobs
    dots = ((xx % 40) < 2) & ((yy % 40) < 2)
    img[dots] = img[dots] * 0.6 + hexc("#6272A4") * 0.4
    return dither(img, 1.5)


def bg_aurora():
    yy, xx = grid(H, W)
    y = yy / H
    img = np.zeros((H, W, 3))
    stops = [(0, "#01020A"), (0.55, "#06122A"), (1, "#0C2238")]
    for c in range(3):
        img[..., c] = np.interp(y, [s[0] for s in stops], [hexc(s[1])[c] for s in stops])
    img = add_stars(img, 1400, H * 0.8, 2)
    xn = xx / W
    aur = np.zeros((H, W, 3))
    r = np.random.default_rng(11)
    for i, (base, amp, h, cA, cB, s) in enumerate([
            (0.42, 0.07, 0.22, "#3CFFA0", "#7A5CFF", 1.0),
            (0.30, 0.05, 0.18, "#2EE6D6", "#B45CFF", 0.7),
            (0.52, 0.04, 0.12, "#6CFF7A", "#3CFFA0", 0.5)]):
        p1, p2, p3 = r.random(3) * 6
        yc = H * (base + amp * np.sin(xn * 5.2 + p1) + amp * 0.5 * np.sin(xn * 11.7 + p2))
        above = np.clip((yc - yy) / (h * H), 0, None)
        prof = np.where(yy < yc, np.exp(-above * 2.2), np.exp(-((yy - yc) / 10) ** 2))
        rays = 0.55 + 0.45 * np.sin(xx * 0.045 + np.sin(xx * 0.007 + p3) * 6) ** 2
        rays *= 0.6 + 0.4 * np.sin(xn * 17 + p3) ** 2
        k = np.clip(above / 1.2, 0, 1)[..., None]
        col = hexc(cA) * (1 - k) + hexc(cB) * k
        aur += (prof * rays)[..., None] * col * s
    img = img + blur(np.clip(aur, 0, 255), 3) * 0.75
    # mountains
    ridge = H * (0.80 - 0.07 * np.sin(xn * 3.1 + 1) - 0.04 * np.sin(xn * 9.3) - 0.015 * np.sin(xn * 31))
    ridge2 = H * (0.88 - 0.04 * np.sin(xn * 4.7 + 2) - 0.02 * np.sin(xn * 17))
    img = np.where((yy > ridge)[..., None], hexc("#070B18") + np.exp(-(yy - ridge) / 4)[..., None] * 40, img)
    img = np.where((yy > ridge2)[..., None], hexc("#03050C"), img)
    return dither(img, 1.5)


# ---------------------------------------------------------------- audio
SR = 44100


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


def lowpass(x, a):
    y = np.zeros_like(x)
    acc = 0.0
    if np.isscalar(a):
        a = np.full(len(x), a)
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def wave_of(kind, freq, n, duty=0.5):
    f = np.full(n, freq) if np.isscalar(freq) else freq
    ph = np.cumsum(f) / SR
    fr = ph % 1
    if kind == "sine": return np.sin(2 * np.pi * ph)
    if kind == "square": return np.where(fr < duty, 1.0, -1.0)
    if kind == "saw": return 2 * fr - 1
    if kind == "tri": return 2 * np.abs(2 * fr - 1) - 1


def env(n, a=0.004, tau=0.2, release=0.02):
    t = np.arange(n) / SR
    e = np.minimum(t / a, 1) * np.exp(-np.maximum(t - a, 0) / tau)
    rl = int(release * SR)
    if rl and rl < n:
        e[-rl:] *= np.linspace(1, 0, rl)
    return e


def voice(style, f, dur):
    n = int(dur * SR)
    if style == "synthwave":
        x = sum(wave_of("saw", f * d, n) for d in (0.993, 1.0, 1.007)) / 3
        x = lowpass(x, 0.35) + 0.4 * wave_of("sine", f / 2, n)
        return x * env(n, 0.005, dur * 0.55)
    if style == "nes":
        x = wave_of("square", f, n, 0.25)
        e = np.round(env(n, 0.002, dur * 0.7) * 15) / 15
        return x * e * 0.8
    if style == "crt":
        x = wave_of("square", f, n) * env(n, 0.002, dur * 0.5)
        return np.round(x * 12) / 12 * 0.7
    if style == "dracula":
        x = wave_of("sine", f, n) + 0.3 * wave_of("sine", f * 2.01, n) + 0.25 * wave_of("tri", f, n)
        return x * env(n, 0.006, dur * 0.45) * 0.8
    if style == "aurora":
        x = wave_of("sine", f, n) + 0.22 * wave_of("sine", f * 2.76, n) * env(n, 0.002, dur * 0.15) \
            + 0.08 * wave_of("sine", f * 5.4, n) * env(n, 0.002, dur * 0.07)
        return x * env(n, 0.004, dur * 0.5) * 0.9


def noise_sweep(dur, a0, a1, tau=None):
    n = int(dur * SR)
    x = np.random.default_rng(1).uniform(-1, 1, n)
    a = np.linspace(a0, a1, n)
    return lowpass(x, a) * env(n, dur * 0.35 if tau is None else 0.003, dur * 0.4 if tau is None else tau)


def place(parts, total=None):
    end = max(s + len(x) / SR for s, x in parts)
    n = int(((total or end) + 0.01) * SR)
    out = np.zeros(n)
    for s, x in parts:
        i = int(s * SR)
        out[i:i + len(x)] += x[:n - i]
    return out


def seq(style, root, notes, gap, dur, vel=1.0):
    return [(i * gap, voice(style, midi(root + m), dur) * vel) for i, m in enumerate(notes)]


def fx(style, x):
    """returns stereo"""
    if style == "synthwave":
        d = int(0.19 * SR)
        L = np.concatenate([x, np.zeros(d * 4)]); R = L.copy()
        for k in range(1, 4):
            tap = np.zeros_like(L); tap[d * k:] = L[:len(L) - d * k] * (0.38 ** k)
            if k % 2: R = R + tap
            else: L = L + tap
        return np.stack([L, R], 1)
    if style in ("aurora", "dracula"):
        wet = 0.35 if style == "aurora" else 0.18
        tail = int(0.8 * SR)
        y = np.concatenate([x, np.zeros(tail)])
        rev = np.zeros_like(y)
        for dl, g in [(0.0297, .77), (0.0371, .75), (0.0411, .73), (0.0437, .71)]:
            dd = int(dl * SR)
            c = y.copy()
            for i in range(dd, len(c), dd):
                c[i:i + dd] += c[i - dd:i][:len(c[i:i + dd])] * g
            rev += c
        rev = lowpass(rev / 4, 0.3)
        L = y + wet * rev
        R = y + wet * np.roll(rev, 331)
        return np.stack([L, R], 1)
    return np.stack([x, x], 1)


def write_wav(path, st, peak=0.85):
    st = st / max(1e-9, np.abs(st).max()) * peak
    # trim trailing silence
    nz = np.where(np.abs(st).max(1) > 1e-3)[0]
    st = st[:nz[-1] + 1] if len(nz) else st
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())


def make_sfx(style, root, minor, outdir):
    third = 3 if minor else 4
    tri = [0, third, 7]
    V = lambda f, d: voice(style, f, d)
    thump = V(np.linspace(midi(root - 12), midi(root - 24), int(0.1 * SR)), 0.1) if style != "aurora" else V(midi(root - 12), 0.09)
    sounds = {}
    click = noise_sweep(0.03, 0.9, 0.2, tau=0.006) * 0.4
    sounds["lock"] = (place([(0, thump * 0.8), (0, click)]), 0.55)
    sounds["rotate"] = (V(midi(root + 24), 0.04), 0.3)
    sounds["hold"] = (place(seq(style, root + 12, [0, 7], 0.045, 0.06)), 0.4)
    sounds["garbage"] = (place([(0, noise_sweep(0.22, 0.25, 0.03, tau=0.08)), (0, V(np.linspace(midi(root - 5), midi(root - 17), int(.2 * SR)), 0.2) * 0.6)]), 0.6)
    for i, m in ((3, 12), (2, 12), (1, 19)):
        sounds[f"countdown{i}"] = (V(midi(root + m), 0.16 if i > 1 else 0.3), 0.6)
    sounds["levelup"] = (place(seq(style, root + 12, [0, third, 7, 12, 12 + third, 19, 24], 0.05, 0.14)), 0.7)
    # line clears: richer the more lines
    lc = {
        1: [0, 7, 12],
        2: [0, third, 7, 12],
        3: [0, third, 7, 12, 12 + third, 19],
    }
    for k, notes in lc.items():
        parts = seq(style, root + 12, notes, 0.05 - k * 0.005, 0.16 + 0.04 * k)
        parts.append((0, noise_sweep(0.25 + 0.08 * k, 0.05, 0.5) * (0.25 + 0.05 * k)))
        sounds[f"lineclear{k}"] = (place(parts), 0.75 + 0.03 * k)
    arp = seq(style, root + 12, [0, third, 7, 12, 12 + third, 19, 24, 24 + third, 31], 0.034, 0.18)
    t0 = 9 * 0.034
    chord = [(t0, voice(style, midi(root + 24 + m), 0.9) * 0.55) for m in tri + [12]]
    bass = [(t0, voice(style, midi(root - 12), 0.7) * 0.8)]
    sweep = [(0, noise_sweep(0.6, 0.02, 0.8) * 0.45)]
    sounds["lineclear4"] = (place(arp + chord + bass + sweep), 0.9)
    fan = seq(style, root + 12, [0, third, 7], 0.09, 0.2) + [(0.3 + i * 0.0, voice(style, midi(root + 12 + m), 0.2)) for i, m in enumerate([5, 9, 12])] \
        + [(0.55, voice(style, midi(root + 12 + m), 0.2)) for m in [7, 11, 14]] \
        + [(0.8, voice(style, midi(root + 24 + m), 1.1) * 0.7) for m in tri + [12]]
    sounds["finish"] = (place(fan), 0.85)
    go = seq(style, root, [12, 10 if minor else 11, 7, 3, 0], 0.18, 0.3) + [(0.95, voice(style, midi(root - 12), 1.2))]
    sounds["gameover"] = (place(go), 0.8)
    for name, (x, peak) in sounds.items():
        write_wav(os.path.join(outdir, name + ".wav"), fx(style, x), peak)


# ---------------------------------------------------------------- themes
ORDER = ["i", "j", "l", "o", "s", "t", "z", "garbage"]

THEMES = {
    "synthwave": dict(
        desc="Neon retro sunset", style="synthwave", root=57, minor=True,
        pal=["#00F0FF", "#3D5AFE", "#FF8A00", "#FFE600", "#39FF14", "#B026FF", "#FF1F6D", "#6B5B95"],
        mino=lambda c, k: mino_neon(c), ghost=lambda: ghost_rounded(hexc("#FF6BF0")),
        bg=bg_synthwave, matrix=("#1A0433", 110, "#FF2BD6", 60),
        well=("#12022A", 150, "#4A0A5E", 190, "#FF2BD6", 90),
        fill=[(0, "#1A0638"), (1, "#050110")], menu=[(0, "#2B0A4A"), (0.7, "#12032A"), (1, "#05010D")],
        logo=dict(hue=0.87, sat=1.2), gauge="#FF2BD6",
        colors=dict(label_normal="#F0E6FF", label_highlight="#FF2BD6", pause_normal="#F0E6FF", pause_highlight="#00F0FF",
                    mainmenu_normal="#C49BFF", mainmenu_highlight="#FFFFFF", mainmenu_panel="#C0189E",
                    countdown="#00F0FF", game_end="#FF2BD6", popup="#00F0FF", line_clear="#FF6BF0D8")),
    "nes": dict(
        desc="8-bit NES style", style="nes", root=60, minor=False,
        pal=["#3CBCFC", "#0058F8", "#F87858", "#F8B800", "#58D854", "#D800CC", "#F83800", "#BCBCBC"],
        mino=lambda c, k: mino_nes(c, k in ("i", "o", "t")), ghost=lambda: ghost_pixel(hexc("#FCFCFC")),
        bg=bg_nes, matrix=("#000000", 200, "#1C1C3C", 255),
        well=("#000000", 215, "#0000A8", 235, "#7C7C7C", 255),
        fill=[(0, "#000010"), (1, "#000000")], menu=[(0, "#000030"), (1, "#000000")],
        logo=dict(hue=0.0, sat=1.3), gauge="#F83800",
        colors=dict(label_normal="#FCFCFC", label_highlight="#F8B800", pause_normal="#FCFCFC", pause_highlight="#F8B800",
                    mainmenu_normal="#7C7CFC", mainmenu_highlight="#FCFCFC", mainmenu_panel="#D82800",
                    countdown="#FCFCFC", game_end="#F83800", popup="#F8B800", line_clear="#FCFCFCF0")),
    "crt_verde": dict(
        desc="Green phosphor terminal", style="crt", root=64, minor=True,
        pal=["#66FF99", "#22CC55", "#99FFAA", "#44FF77", "#18B84A", "#77EE88", "#33DD66", "#1C7A3C"],
        mino=lambda c, k: mino_crt(c, k), ghost=lambda: ghost_pixel(hexc("#33FF66"), dotted=True),
        bg=bg_crt, matrix=("#000000", 90, "#0E3A1C", 200),
        well=("#010603", 200, "#0B3A18", 215, "#0E3A1C", 255),
        fill=[(0, "#031208"), (1, "#000000")], menu=[(0, "#04200D"), (1, "#000200")],
        logo=dict(mono=(80, 255, 130)), gauge="#33FF66",
        colors=dict(label_normal="#66FF99", label_highlight="#CCFFDD", pause_normal="#66FF99", pause_highlight="#CCFFDD",
                    mainmenu_normal="#2E9E55", mainmenu_highlight="#000000", mainmenu_panel="#33FF66",
                    countdown="#66FF99", game_end="#66FF99", popup="#CCFFDD", line_clear="#66FF99C8")),
    "dracula": dict(
        desc="Dracula palette, soft and clean", style="dracula", root=62, minor=True,
        pal=["#8BE9FD", "#6C7EE1", "#FFB86C", "#F1FA8C", "#50FA7B", "#BD93F9", "#FF5555", "#6272A4"],
        mino=lambda c, k: mino_soft(c), ghost=lambda: ghost_rounded(hexc("#BD93F9"), 0.05, 0.18, 30),
        bg=bg_dracula, matrix=("#282A36", 120, "#44475A", 150),
        well=("#1E1F29", 170, "#44475A", 215, "#44475A", 200),
        fill=[(0, "#2B2D3A"), (1, "#191A21")], menu=[(0, "#343746"), (1, "#191A21")],
        logo=dict(hue=0.75, sat=0.8), gauge="#FF79C6",
        colors=dict(label_normal="#F8F8F2", label_highlight="#FF79C6", pause_normal="#F8F8F2", pause_highlight="#BD93F9",
                    mainmenu_normal="#8D96C4", mainmenu_highlight="#F8F8F2", mainmenu_panel="#6A4FB0",
                    countdown="#BD93F9", game_end="#FF79C6", popup="#8BE9FD", line_clear="#BD93F9B8")),
    "aurora": dict(
        desc="Northern lights, glassy blocks", style="aurora", root=65, minor=False,
        pal=["#7FFFD4", "#4D8CFF", "#FFB47A", "#FFF08A", "#6CFF9E", "#C38BFF", "#FF7A9C", "#5A6B8C"],
        mino=lambda c, k: mino_glass(c), ghost=lambda: ghost_rounded(hexc("#9FFFE0"), 0.04, 0.12, 35),
        bg=bg_aurora, matrix=("#04101F", 110, "#1E4A5A", 110),
        well=("#030A18", 165, "#0F3A4A", 190, "#1E4A5A", 180),
        fill=[(0, "#06122A"), (1, "#01020A")], menu=[(0, "#0C2238"), (0.6, "#06122A"), (1, "#01020A")],
        logo=dict(hue=0.45, sat=1.0), gauge="#7FFFD4",
        colors=dict(label_normal="#E6FFF6", label_highlight="#7FFFD4", pause_normal="#E6FFF6", pause_highlight="#7FFFD4",
                    mainmenu_normal="#6FB7B0", mainmenu_highlight="#FFFFFF", mainmenu_panel="#1F7F74",
                    countdown="#7FFFD4", game_end="#C38BFF", popup="#7FFFD4", line_clear="#B8FFF0C0")),
}


def build(name, T):
    d = os.path.join(OUT, name)
    g = os.path.join(d, "graphics")
    for k, c in zip(ORDER, T["pal"]):
        save(T["mino"](hexc(c), k), os.path.join(g, f"mino_{k}.png"))
    save(T["mino"](hexc("#C8C8C8"), "i"), os.path.join(g, "mino.png"))
    save(T["ghost"](), os.path.join(g, "ghost.png"))
    f, fa, l, la = T["matrix"]
    save(matrix_cell(hexc(f), fa, hexc(l), la), os.path.join(g, "matrix.png"))
    p, pa, b, ba, e, ea = T["well"]
    for wf in ["narrow", "wide", "narrow_battle", "wide_battle"]:
        save(recolor_well(os.path.join(DEF, "well", wf + ".png"), hexc(p), pa, hexc(b), ba, hexc(e), ea),
             os.path.join(g, "well", wf + ".png"))
    save(vgrad(T["fill"]), os.path.join(g, "game_fill.png"))
    save(vgrad(T["menu"]), os.path.join(g, "menu_fill.png"))
    save(np.zeros((2, 2, 3)) + hexc(T["gauge"]), os.path.join(g, "garbage.png"))
    save(recolor_logo(**T["logo"]), os.path.join(g, "logo.png"))
    save(T["bg"](), os.path.join(d, "backgrounds", "gameplay", f"{name}.jpg"), jpg=True)
    make_sfx(T["style"], T["root"], T["minor"], os.path.join(d, "sfx"))
    cfg = [f"[meta]", f'name = {name}', f'author = "Claude for Tomás"', f'description = "{T["desc"]}"', 'version = "v1.0"', "",
           "[colors]"] + [f"{k} = {v}" for k, v in T["colors"].items()] + ["", "[gameplay]", "draw_labels = yes",
                                                                         "custom_minos = yes", "tint_ghost = no", ""]
    with open(os.path.join(d, "theme.cfg"), "w") as fh:
        fh.write("\n".join(cfg))
    print("built", name, flush=True)


if __name__ == "__main__":
    names = sys.argv[1:] or list(THEMES)
    for n in names:
        build(n, THEMES[n])
