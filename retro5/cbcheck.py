"""cbcheck.py - simulate colour-blindness on the dashboard palette (Machado 2009 matrices, full severity) and report the closest pair in CIELAB deltaE.
Run: python cbcheck.py"""
import itertools
import numpy as np

M_DEUT = np.array([[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]])
M_PROT = np.array([[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]])


def _lin(c):
    c = np.array(c, float) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _srgb(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, l * 12.92, 1.055 * l ** (1 / 2.4) - 0.055) * 255


def _rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def _lab(rgb):
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = M @ _lin(rgb) / np.array([0.95047, 1, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def closest(pal, M=None):
    best = (1e9, None)
    for a, b in itertools.combinations(pal, 2):
        ca = _srgb(M @ _lin(_rgb(pal[a]))) if M is not None else _rgb(pal[a])
        cb = _srgb(M @ _lin(_rgb(pal[b]))) if M is not None else _rgb(pal[b])
        d = float(np.linalg.norm(_lab(ca) - _lab(cb)))
        if d < best[0]:
            best = (d, (a, b))
    return best


if __name__ == "__main__":
    import charts as C
    for nm, M in [("normal vision", None), ("deuteranopia", M_DEUT), ("protanopia", M_PROT)]:
        d, pair = closest(C.TYPE_COL, M)
        print(f"{nm:14s} closest pair: {pair[0]} / {pair[1]}  deltaE = {d:.1f}")
