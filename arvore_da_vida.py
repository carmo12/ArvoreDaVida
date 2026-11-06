"""
Árvore da Vida — animação de partículas
=======================================

Uma semente de luz cai do céu, cria raízes, cresce como uma árvore
e atravessa as quatro estações (primavera, verão, outono, inverno)
até se dissolver em luz e renascer — cada ciclo gera uma árvore nova.

Requisitos:
    pip install pygame numpy

Executar:
    python arvore_da_vida.py

Controles:
    ESPAÇO      pausar / continuar
    ← / →       voltar / avançar 4 segundos
    1 … 8       pular para uma fase
    R           nova árvore
    S           salvar imagem (png)
    ESC         sair
"""

import math
import random
import sys
import time

import numpy as np
import pygame

# ─────────────────────────────────────────────────────────── configuração ──
W, H = 900, 900
FPS = 60
GROUND_Y = H * 0.80
TRAIL = 0.45          # rastro das partículas (0 = sem rastro)
EXPOSURE = 1.15

# linha do tempo de um ciclo (segundos)
CYCLE = 62.0
SEED_LAND = 3.2
ROOT0, ROOT1 = 3.3, 9.5
GROW0, GROW1 = 5.0, 19.0
SPRING0 = 18.5
SUM0, SUM1 = 30.0, 34.0
AUT0, AUT1 = 40.0, 44.0
FALL0, FALL1 = 42.0, 48.0
WIN0, WIN1 = 49.5, 52.5
DIS0 = 56.0

STAGES = [
    (0.0, "a semente"),
    (SEED_LAND, "raízes"),
    (GROW0 + 1.0, "crescimento"),
    (SPRING0, "primavera"),
    (SUM0, "verão"),
    (AUT0, "outono"),
    (WIN0, "inverno"),
    (DIS0, "renascimento"),
]


def C(*rgb):
    return np.array(rgb, dtype=np.float32)


# paleta
BARK_A = C(1.00, 0.50, 0.30)     # tronco: cobre rosado
BARK_B = C(0.78, 0.55, 1.00)     # galhos finos: lilás
ROOT_C = C(0.20, 0.80, 1.00)     # raízes: ciano
SPARK = C(1.00, 0.92, 0.75)
GOLD = C(1.00, 0.78, 0.32)
SNOW = C(0.82, 0.90, 1.00)
SPRING_P = [C(1.0, 0.42, 0.72), C(1.0, 0.78, 0.90), C(0.90, 0.35, 0.95), C(1.0, 0.60, 0.80)]
SUMMER_P = [C(0.15, 1.0, 0.60), C(0.10, 0.85, 0.95), C(0.55, 1.0, 0.35), C(0.20, 0.95, 0.80)]
AUTUMN_P = [C(1.0, 0.55, 0.12), C(1.0, 0.32, 0.08), C(0.95, 0.15, 0.25), C(1.0, 0.80, 0.25)]
SOIL_P = [C(0.70, 0.45, 0.28), C(0.85, 0.74, 0.58), C(0.55, 0.45, 0.75)]
GRASS_SP, GRASS_SU, GRASS_AU = C(0.45, 1.0, 0.50), C(0.12, 0.90, 0.75), C(1.0, 0.70, 0.22)
AUR_A, AUR_B = C(0.10, 0.95, 0.65), C(0.65, 0.25, 0.95)

# céu: (tempo, topo RGB, horizonte RGB)
SKY_KEYS = [
    (0.0,  (3, 3, 14),  (16, 10, 34)),
    (17.0, (3, 3, 14),  (16, 10, 34)),
    (21.0, (7, 4, 22),  (46, 16, 52)),   # primavera: crepúsculo rosado
    (29.0, (7, 4, 22),  (46, 16, 52)),
    (33.0, (2, 8, 24),  (8, 36, 52)),    # verão: turquesa
    (39.0, (2, 8, 24),  (8, 36, 52)),
    (43.0, (9, 4, 10),  (54, 24, 12)),   # outono: âmbar
    (49.0, (9, 4, 10),  (54, 24, 12)),
    (52.0, (3, 5, 18),  (20, 30, 60)),   # inverno: gelo
    (56.0, (3, 5, 18),  (20, 30, 60)),
    (60.0, (3, 3, 14),  (16, 10, 34)),
]
SKY_KEYS = [(t, np.array(a + b, np.float32)) for t, a, b in SKY_KEYS]
EARTH = C(4, 3, 5)


# ───────────────────────────────────────────────────────────── utilidades ──
def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ease_out_back(x):
    x = np.clip(x, 0.0, 1.0)
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * (x - 1.0) ** 3 + c1 * (x - 1.0) ** 2


def keyinterp(t, keys):
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = float(sstep(t0, t1, t))
            return v0 * (1 - u) + v1 * u
    return keys[-1][1]


def ground_at(x):
    return GROUND_Y + 10 * np.sin(x * 0.009 + 0.7) + 5 * np.sin(x * 0.023 + 2.1) + 2.5 * np.sin(x * 0.061)


def angdiff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def pick(rng, palette, n):
    p = np.stack(palette)
    return p[rng.integers(0, len(palette), n)]


# ────────────────────────────────────────────────────── canvas de partículas ──
class Canvas:
    """Acumula partículas com mistura aditiva (splat bilinear) num buffer HDR."""

    def __init__(self):
        self.acc = np.zeros(W * H * 3, np.float32)
        self.surf = pygame.Surface((W, H))
        self.xs, self.ys, self.cs = [], [], []

    def clear(self):
        self.acc[:] = 0

    def begin(self):
        self.acc *= TRAIL
        self.xs.clear(); self.ys.clear(); self.cs.clear()

    def add(self, x, y, col):
        x = np.asarray(x, np.float32).ravel()
        y = np.asarray(y, np.float32).ravel()
        if len(x) == 0:
            return
        col = np.broadcast_to(np.asarray(col, np.float32), (len(x), 3))
        self.xs.append(x); self.ys.append(y); self.cs.append(col)

    def glow(self, x, y, col, r=1.3, n=6):
        x = np.asarray(x, np.float32).ravel()
        y = np.asarray(y, np.float32).ravel()
        col = np.broadcast_to(np.asarray(col, np.float32), (len(x), 3))
        a = np.linspace(0, 2 * np.pi, n, endpoint=False)
        X = (x[:, None] + r * np.cos(a)[None]).ravel()
        Y = (y[:, None] + r * np.sin(a)[None]).ravel()
        self.add(X, Y, np.repeat(col, n, axis=0) * 0.45)
        self.add(x, y, col)

    def flush(self):
        if not self.xs:
            return
        x = np.concatenate(self.xs); y = np.concatenate(self.ys); c = np.concatenate(self.cs)
        m = (x >= 0) & (x < W - 1.01) & (y >= 0) & (y < H - 1.01)
        x, y, c = x[m], y[m], c[m]
        x0 = x.astype(np.int32); y0 = y.astype(np.int32)
        fx = x - x0; fy = y - y0
        w = np.concatenate([(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy])
        b = x0 * H + y0
        idx = np.concatenate([b, b + H, b + 1, b + H + 1]) * 3
        idx3 = np.concatenate([idx, idx + 1, idx + 2])
        cw = np.concatenate([np.tile(c[:, k], 4) * w for k in range(3)])
        np.add(self.acc, np.bincount(idx3, weights=cw, minlength=W * H * 3), out=self.acc, casting="unsafe")

    def surface(self):
        a = self.acc.reshape(W, H, 3) * EXPOSURE
        img = a / (1.0 + a) * 255.0
        pygame.surfarray.blit_array(self.surf, img.astype(np.uint8))
        return self.surf


# ───────────────────────────────────────────────────────────────── árvore ──
class Tree:
    MAX_ORDER = 7

    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        bx = W / 2 + rng.uniform(-25, 25)
        self.base = np.array([bx, float(ground_at(bx)) + 2.0])
        self.segs = []
        self.tips = []
        self._gen_tree(rng)
        self._gen_roots(rng)

        a = np.array(self.segs, dtype=np.float64)
        self.parent = a[:, 0].astype(int)
        self.rel = a[:, 1]; self.length = a[:, 2]
        self.w0 = a[:, 3]; self.w1 = a[:, 4]
        self.order = a[:, 5].astype(int)
        t0, t1 = a[:, 6], a[:, 7]
        self.kind = a[:, 8].astype(int)
        self.level = a[:, 9].astype(int)
        n = len(self.parent)

        # normaliza tempos para a linha do tempo
        self.t0 = np.empty(n); self.t1 = np.empty(n)
        for k, (A, B) in ((0, (GROW0, GROW1)), (1, (ROOT0, ROOT1))):
            m = self.kind == k
            lo, hi = t0[m].min(), t1[m].max()
            self.t0[m] = A + (t0[m] - lo) / (hi - lo) * (B - A)
            self.t1[m] = A + (t1[m] - lo) / (hi - lo) * (B - A)
        self.levels = [np.nonzero(self.level == L)[0] for L in range(self.level.max() + 1)]
        self.sway_amp = np.where(self.kind == 0, 0.008 + 0.006 * self.order, 0.0)
        self.sway_ph = self.level * 0.45 + rng.uniform(0, 0.6, n)

        self._gen_bark(rng)
        self._gen_leaves(rng)

        # copa estática → centro do mandala
        _, _, _, _, ex, ey = self.transform(1000.0, sway=0.0)
        tx, ty = ex[self.l_cseg], ey[self.l_cseg]
        self.crown = np.array([np.median(tx), np.mean(ty) - 10])
        d = np.hypot(tx - self.crown[0], ty - self.crown[1])
        self.crown_r = float(min(np.percentile(d, 90) + 40, W * 0.46))

    # -- geração ------------------------------------------------------------
    def _add(self, parent, rel, length, w0, w1, order, t0, t1, kind):
        level = self.segs[parent][9] + 1 if parent >= 0 else 0
        self.segs.append((parent, rel, length, w0, w1, order, t0, t1, kind, level))
        return len(self.segs) - 1

    def _gen_tree(self, rng):
        speed = 46.0

        def branch(parent, parent_abs, rel, length, width, order, t):
            if len(self.segs) > 4200:
                self.tips.append(parent)
                return
            n = 4 if order < 2 else (3 if order < 5 else 2)
            sl = length / n
            a = parent_abs
            w = width
            wend = width * 0.7
            seg = parent
            for i in range(n):
                if i == 0:
                    r = rel
                else:
                    r = rng.normal(0, 0.09 + 0.02 * order)
                    pull = 0.18 if order == 0 else (0.08 if order < 3 else 0.02)
                    r += pull * angdiff(-math.pi / 2, a)
                a += r
                w2 = width + (wend - width) * (i + 1) / n
                dur = sl / speed
                seg = self._add(seg, r, sl, w, w2, order, t, t + dur, 0)
                t += dur
                w = w2
                if 1 <= order <= self.MAX_ORDER - 2 and i == n - 2 and rng.random() < 0.5:
                    side = rng.choice([-1, 1]) * rng.uniform(0.55, 0.95)
                    branch(seg, a, side, length * rng.uniform(0.45, 0.6), w * 0.55, order + 1, t)
            if order < self.MAX_ORDER:
                k = 3 if rng.random() < (0.45 if order < 2 else 0.22) else 2
                spread = rng.uniform(0.32, 0.55) * (1.15 if order == 0 else 1.0)
                angs = [-spread, spread] if k == 2 else [-spread * 1.1, rng.normal(0, 0.1), spread * 1.1]
                for ca in angs:
                    branch(seg, a, ca + rng.normal(0, 0.08), length * rng.uniform(0.70, 0.84),
                           w * rng.uniform(0.72, 0.86), order + 1, t)
            else:
                self.tips.append(seg)

        branch(-1, 0.0, -math.pi / 2 + rng.normal(0, 0.04), rng.uniform(122, 140), 22.0, 0, 0.0)

    def _gen_roots(self, rng):
        speed = 50.0

        def root(parent, parent_abs, rel, length, width, order, t):
            n = 3
            sl = length / n
            a = parent_abs
            seg = parent
            w = width
            for i in range(n):
                r = rel if i == 0 else rng.normal(0, 0.25)
                r += 0.08 * angdiff(math.pi / 2, a + r)
                a += r
                w2 = width * (1 - 0.35 * (i + 1) / n)
                seg = self._add(seg, r, sl, w, w2, order, t, t + sl / speed, 1)
                t += sl / speed
                w = w2
            if order < 4:
                for ca in (-rng.uniform(0.3, 0.7), rng.uniform(0.3, 0.7)):
                    root(seg, a, ca, length * rng.uniform(0.6, 0.8), w * 0.8, order + 1, t)

        for ang in np.linspace(0.18, 0.82, 4) * math.pi + rng.normal(0, 0.08, 4):
            root(-1, 0.0, ang, rng.uniform(55, 85), 6.0, 0, rng.uniform(0, 0.3))

    def _gen_bark(self, rng):
        n = len(self.parent)
        wavg = (self.w0 + self.w1) * 0.5
        dens = np.where(self.kind == 0, 0.38, 0.40)
        cnt = (self.length * np.maximum(wavg, 1.2) * dens).astype(int) + 3
        seg = np.repeat(np.arange(n), cnt)
        N = len(seg)
        self.b_seg = seg
        self.b_s = rng.random(N)
        r = rng.random(N) * 2 - 1
        self.b_u = np.sign(r) * np.abs(r) ** 0.7
        rim = 0.55 + 0.9 * np.abs(self.b_u) ** 5
        bright = (0.24 + 0.38 * rng.random(N)) * rim
        o = (self.order[seg] / self.MAX_ORDER)[:, None]
        col = BARK_A[None] * (1 - o) + BARK_B[None] * o
        col = np.where((self.kind[seg] == 1)[:, None], ROOT_C[None] * 0.75, col)
        self.b_col = (col * bright[:, None]).astype(np.float32)
        self.b_ph = rng.uniform(0, 2 * np.pi, N)
        # dissolve: as pontas evaporam primeiro, o tronco por último
        self.b_rd = (1 - self.order[seg] / self.MAX_ORDER) * 2.2 + rng.random(N) * 0.9

    def _gen_leaves(self, rng):
        extra = np.nonzero((self.kind == 0) & (self.order >= self.MAX_ORDER - 1))[0]
        extra = extra[rng.random(len(extra)) < 0.5]
        cl_seg = np.unique(np.concatenate([np.array(self.tips, int), extra]))
        nc = len(cl_seg)
        per = 15
        cl = np.repeat(np.arange(nc), per)
        N = nc * per
        self.l_cseg = cl_seg
        self.l_seg = cl_seg[cl]

        R = rng.uniform(7, 12, nc)[cl]
        # forma de flor (5 pétalas)
        th = rng.random(N) * 2 * np.pi
        rot = (rng.random(nc) * 2 * np.pi)[cl]
        rr = np.sqrt(rng.random(N))
        petal = 0.3 + 0.7 * np.abs(np.cos(2.5 * (th - rot)))
        fr = R * rr * petal
        self.l_fx = np.cos(th) * fr
        self.l_fy = np.sin(th) * fr
        # forma de folhagem (elipses orientadas)
        la = (rng.random(nc) * np.pi)[cl]
        gx = rng.normal(0, R * 0.85)
        gy = rng.normal(0, R * 0.5)
        self.l_lx = gx * np.cos(la) - gy * np.sin(la)
        self.l_ly = gx * np.sin(la) + gy * np.cos(la) - R * 0.3

        center = rr < 0.28
        sp = pick(rng, SPRING_P, N)
        sp[center] = GOLD
        sp *= ((0.38 + 0.30 * rng.random(N)) * (0.7 + 0.6 * petal * rr))[:, None]
        su = pick(rng, SUMMER_P, N) * (0.30 + 0.28 * rng.random(N))[:, None]
        au = pick(rng, AUTUMN_P, N) * (0.38 + 0.34 * rng.random(N))[:, None]
        self.l_sp, self.l_su, self.l_au = sp.astype(np.float32), su.astype(np.float32), au.astype(np.float32)

        self.l_tb = (np.maximum(self.t1[cl_seg], SPRING0 - 1.0) + rng.uniform(0, 3.5, nc))[cl]
        ft = rng.uniform(FALL0, FALL1, N)
        petals = rng.random(N) < 0.06
        ft[petals] = rng.uniform(22.0, 29.0, petals.sum())
        self.l_ft = ft
        self.l_vy = rng.uniform(55, 95, N)
        self.l_ph = rng.uniform(0, 2 * np.pi, N)
        self.l_sw = rng.uniform(8, 24, N)
        self.l_rest = rng.uniform(0, 4, N)

    # -- animação -----------------------------------------------------------
    def transform(self, t, sway=1.0):
        n = len(self.parent)
        f = np.clip((t - self.t0) / (self.t1 - self.t0), 0.0, 1.0)
        ang = np.zeros(n); sx = np.zeros(n); sy = np.zeros(n); ex = np.zeros(n); ey = np.zeros(n)
        gust = 0.6 + 0.4 * math.sin(t * 0.31) + 0.25 * math.sin(t * 0.83)
        rel = self.rel + sway * gust * self.sway_amp * np.sin(t * 1.3 + self.sway_ph)
        bx0, by0 = self.base
        for idx in self.levels:
            p = self.parent[idx]
            has = p >= 0
            a = np.where(has, ang[p], 0.0) + rel[idx]
            ang[idx] = a
            bx = np.where(has, ex[p], bx0)
            by = np.where(has, ey[p], by0)
            sx[idx] = bx; sy[idx] = by
            L = self.length[idx] * f[idx]
            ex[idx] = bx + np.cos(a) * L
            ey[idx] = by + np.sin(a) * L
        return f, ang, sx, sy, ex, ey

    @staticmethod
    def dissolve(x, y, col, rd, ph, t):
        dd = np.clip(t - (DIS0 + rd), 0, None)
        if not dd.any():
            return x, y, col
        y = y - (22 * dd + 20 * dd * dd)
        x = x + 10 * np.sin(dd * 2.5 + ph) * dd
        mix = sstep(0.0, 0.8, dd)[:, None]
        fade = (np.exp(-dd * 0.85) * (1 + 2.2 * np.exp(-dd * 2.5) * (dd > 0)))[:, None]
        col = (col * (1 - mix) + SPARK[None] * 0.35 * mix) * fade
        return x, y, col

    def draw(self, cv, t):
        f, ang, sx, sy, ex, ey = self.transform(t)
        frost = float(sstep(WIN0, WIN1, t))

        # casca + raízes
        i = np.nonzero(self.b_s <= f[self.b_seg])[0]
        if len(i):
            seg = self.b_seg[i]; s = self.b_s[i]; u = self.b_u[i]
            a = ang[seg]
            ca, sa = np.cos(a), np.sin(a)
            w = self.w0[seg] + (self.w1[seg] - self.w0[seg]) * s
            along = s * self.length[seg]
            half = u * w * 0.5
            x = sx[seg] + ca * along - sa * half
            y = sy[seg] + sa * along + ca * half
            col = self.b_col[i] * (0.85 + 0.15 * np.sin(t * 3.0 + self.b_ph[i]))[:, None]
            if frost > 0:
                top = np.clip(-u * ca, 0, 1) ** 0.5 * (self.kind[seg] == 0)
                k = (frost * top * 0.85)[:, None]
                col = col * (1 - k) + SNOW[None] * 0.42 * k
            x, y, col = self.dissolve(x, y, col, self.b_rd[i], self.b_ph[i], t)
            cv.add(x, y, col)

        # brotos crescendo: faíscas na ponta
        g = np.nonzero((f > 0) & (f < 1))[0]
        if len(g):
            j = np.repeat(g, 4)
            jx = ex[j] + np.random.normal(0, 1.6, len(j))
            jy = ey[j] + np.random.normal(0, 1.6, len(j))
            c = np.where((self.kind[j] == 1)[:, None], ROOT_C[None] * 0.9, SPARK[None] * 0.9)
            cv.glow(jx, jy, c, r=1.5)

        # folhas / flores
        seg = self.l_seg
        bud = sstep(self.t1[seg], self.t1[seg] + 0.6, t) * 0.2
        grow = bud + 0.8 * ease_out_back((t - self.l_tb) / 1.4)
        vis = grow > 0.01
        if vis.any():
            m_su = float(sstep(SUM0, SUM1, t))
            m_au = float(sstep(AUT0, AUT1, t))
            ox = (self.l_fx * (1 - m_su) + self.l_lx * m_su) * grow + 0.8 * np.sin(t * 2.3 + self.l_ph)
            oy = (self.l_fy * (1 - m_su) + self.l_ly * m_su) * grow + 0.6 * np.cos(t * 1.9 + self.l_ph)
            x = ex[seg] + ox
            y = ey[seg] + oy
            col = (self.l_sp * (1 - m_su) + self.l_su * m_su) * (1 - m_au) + self.l_au * m_au
            inten = np.ones(len(x))

            fd = t - self.l_ft
            fall = fd > 0
            if fall.any():
                d = fd[fall]
                x0, y0 = x[fall], y[fall]
                vy = self.l_vy[fall]
                gy = ground_at(x0) - self.l_rest[fall]
                dl = np.maximum((gy - y0) / vy, 0)
                dm = np.minimum(d, dl)
                xf = x0 + 16 * dm + self.l_sw[fall] * np.sin(2.0 * dm + self.l_ph[fall]) * np.minimum(dm, 1)
                yf = np.minimum(y0 + vy * d + 0.3 * self.l_sw[fall] * np.sin(3.1 * d), gy)
                x[fall] = xf; y[fall] = yf
                inten[fall] = np.where(d > dl, 0.6 * np.exp(-(d - dl) / 2.5), 1.0 + 0.4 * np.sin(d * 4 + self.l_ph[fall]))
            inten *= 1 - sstep(57.0, 60.0, t)
            m = vis & (inten > 0.01)
            cv.add(x[m], y[m], col[m] * inten[m, None])


# ──────────────────────────────────────────────────────────────── mundo ──
class World:
    def __init__(self, seed):
        self.cv = Canvas()
        rng = np.random.default_rng(12345)
        self._ys = np.arange(H, dtype=np.float32)

        # estrelas
        n = 650
        self.st_x = rng.uniform(0, W, n)
        self.st_y = rng.uniform(0, GROUND_Y - 30, n) ** 1.0
        self.st_y = (rng.random(n) ** 1.4) * (GROUND_Y - 30)
        b = rng.random(n) ** 3
        warm = rng.random(n) < 0.2
        c = np.where(warm[:, None], C(1.0, 0.85, 0.7)[None], C(0.75, 0.85, 1.0)[None])
        self.st_c = c * (0.05 + 0.5 * b)[:, None] * (1 - self.st_y / GROUND_Y * 0.6)[:, None]
        self.st_tw = rng.uniform(0.5, 3.0, n)
        self.st_ph = rng.uniform(0, 2 * np.pi, n)

        # solo
        n = 11000
        sx = rng.uniform(0, W, n)
        d = rng.random(n) ** 2.2 * (H - GROUND_Y + 20)
        self.so_x = sx
        self.so_y = ground_at(sx) + d - 2
        self.so_d = d
        fall = (1 - d / (H - GROUND_Y + 20)) ** 1.6
        self.so_c = pick(rng, SOIL_P, n) * ((0.10 + 0.30 * rng.random(n)) * fall)[:, None]
        self.so_tw = rng.random(n) < 0.07
        self.so_ph = rng.uniform(0, 2 * np.pi, n)

        # grama
        nb, k = 340, 8
        bx = rng.uniform(0, W, nb)
        self.gr_bx = np.repeat(bx, k)
        self.gr_by = np.repeat(ground_at(bx) + 1, k)
        self.gr_s = np.tile(np.linspace(0, 1, k), nb)
        self.gr_h = np.repeat(rng.uniform(5, 20, nb), k)
        self.gr_lean = np.repeat(rng.normal(0, 0.35, nb), k)
        self.gr_i = np.repeat(0.12 + 0.12 * rng.random(nb), k) * (0.5 + 0.5 * self.gr_s)

        # vaga-lumes
        n = 80
        self.ff_bx = rng.uniform(W * 0.08, W * 0.92, n)
        self.ff_by = rng.uniform(H * 0.25, GROUND_Y - 15, n)
        self.ff_f = rng.uniform(0.5, 1.5, (4, n))
        self.ff_p = rng.uniform(0, 2 * np.pi, (5, n))
        self.ff_w = rng.uniform(1.0, 2.5, n)

        # neve
        n = 900
        self.sn_x = rng.uniform(0, W, n)
        self.sn_y = rng.uniform(0, H, n)
        self.sn_v = rng.uniform(18, 55, n)
        self.sn_ph = rng.uniform(0, 2 * np.pi, n)
        self.sn_i = 0.15 + 0.45 * rng.random(n) ** 2

        # mandala (semente da vida)
        pts, qs = [], []
        def circle(cx, cy, r, npts):
            q = np.linspace(0, 1, npts, endpoint=False)
            a = q * 2 * np.pi + math.atan2(cy, cx)
            pts.append(np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], 1)); qs.append(q)
        circle(0, 0, 1.0, 700)
        circle(0, 0, 1.06, 500)
        circle(0, 0, 0.5, 300)
        for kk in range(6):
            a = kk * math.pi / 3
            circle(0.5 * math.cos(a), 0.5 * math.sin(a), 0.5, 300)
        for kk in range(12):
            a = kk * math.pi / 6
            circle(1.03 * math.cos(a), 1.03 * math.sin(a), 0.035, 20)
        self.md_p = np.concatenate(pts)
        self.md_q = np.concatenate(qs)
        nm = len(self.md_p)
        self.md_ph = rng.uniform(0, 2 * np.pi, nm)
        ang = np.arctan2(self.md_p[:, 1], self.md_p[:, 0])
        mix = (0.5 + 0.5 * np.sin(ang * 3))[:, None]
        self.md_c = GOLD[None] * (1 - mix) + C(0.70, 0.60, 1.0)[None] * mix

        # vinheta
        xx, yy = np.meshgrid(np.arange(W), np.arange(H), indexing="ij")
        r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)) / 1.414
        v = np.clip(1 - 0.7 * r ** 2.4, 0, 1)
        self.vignette = pygame.surfarray.make_surface((v[..., None].repeat(3, 2) * 255).astype(np.uint8))

        # aurora (grade de baixa resolução)
        self.au_x = np.linspace(0, W, 240)[:, None]
        self.au_y = np.linspace(0, H * 0.7, 110)[None, :]

        try:
            self.font = pygame.font.SysFont("georgia,palatino,timesnewroman,dejavuserif", 30, italic=True)
            self.small = pygame.font.SysFont("georgia,palatino,timesnewroman,dejavuserif", 15, italic=True)
        except Exception:
            self.font = pygame.font.Font(None, 34); self.small = pygame.font.Font(None, 18)
        self.label_cache = {}

        self.new_tree(seed)

    def new_tree(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        self.tree = Tree(self.seed)

    # -- camadas -------------------------------------------------------------
    def draw_stars(self, t, T):
        cv = self.cv
        tw = 0.55 + 0.45 * np.sin(T * self.st_tw + self.st_ph)
        cv.add(self.st_x, self.st_y, self.st_c * tw[:, None])
        # estrela cadente
        k = int(T // 13.0)
        loc = T - k * 13.0
        if loc < 1.1:
            r = np.random.default_rng(k + 777)
            x0, y0 = r.uniform(0.15 * W, 0.85 * W), r.uniform(40, 260)
            a = r.choice([0.45, math.pi - 0.45]) + r.normal(0, 0.1)
            d = np.array([math.cos(a), math.sin(a)])
            hx, hy = x0 + d[0] * loc * 650, y0 + d[1] * loc * 650
            j = np.arange(45)
            env = math.sin(math.pi * loc / 1.1)
            cv.add(hx - d[0] * j * 3.5, hy - d[1] * j * 3.5,
                   (C(0.9, 0.95, 1.0)[None] * ((1 - j / 45) ** 2 * 0.9 * env)[:, None]))

    def draw_mandala(self, t):
        tr = self.tree
        draw = float(sstep(16.5, 23.0, t))
        if draw <= 0:
            return
        vis = 1 - float(sstep(53.0, 57.0, t))
        burst = float(sstep(DIS0, DIS0 + 4, t))
        flash = math.exp(-((t - DIS0 - 0.6) / 0.8) ** 2) * 1.5
        R = tr.crown_r * (1 + 0.6 * burst)
        rot = t * 0.04
        cr, sr = math.cos(rot), math.sin(rot)
        p = self.md_p
        x = tr.crown[0] + R * (cr * p[:, 0] - sr * p[:, 1])
        y = tr.crown[1] + R * (sr * p[:, 0] + cr * p[:, 1])
        m = self.md_q < draw
        tw = 0.20 + 0.55 * np.maximum(0, np.sin(t * 2 + self.md_ph)) ** 8
        inten = tw * (vis + flash * (1 - burst * 0.7))
        self.cv.add(x[m], y[m], self.md_c[m] * inten[m, None])

    def draw_soil(self, t):
        col = self.so_c
        tw = np.where(self.so_tw, 1 + 3 * np.maximum(0, np.sin(t * 1.7 + self.so_ph)) ** 12, 1.0)
        col = col * tw[:, None]
        if SEED_LAND < t < SEED_LAND + 3.5:
            lx, ly = self.tree.base
            r = (t - SEED_LAND) * 240
            d = np.abs(np.hypot(self.so_x - lx, (self.so_y - ly) * 3.0) - r)
            boost = np.exp(-(d / 14) ** 2) * math.exp(-(t - SEED_LAND) * 1.1) * 5.0
            col = col * (1 + boost)[:, None] + (GOLD * 0.05)[None] * boost[:, None]
        frost = float(sstep(WIN0, WIN1, t) * (1 - sstep(57, 60, t)))
        if frost > 0:
            k = (frost * np.exp(-self.so_d / 6.0) * 0.9)[:, None]
            col = col * (1 - k) + SNOW[None] * 0.28 * k
        self.cv.add(self.so_x, self.so_y, col)

    def draw_grass(self, t):
        h = float(sstep(17.0, 23.0, t) * (1 - sstep(50.0, 54.0, t)))
        if h <= 0:
            return
        s = self.gr_s
        sway = 3.0 * np.sin(t * 1.5 + self.gr_bx * 0.02) + 1.5 * np.sin(t * 2.7 + self.gr_bx * 0.05)
        hh = self.gr_h * h
        x = self.gr_bx + (np.sin(self.gr_lean) * hh * s + sway * s * s)
        y = self.gr_by - hh * s
        m_su = float(sstep(SUM0, SUM1, t)); m_au = float(sstep(AUT0, AUT1, t))
        c = (GRASS_SP * (1 - m_su) + GRASS_SU * m_su) * (1 - m_au) + GRASS_AU * m_au
        self.cv.add(x, y, c[None] * self.gr_i[:, None])

    def draw_seed(self, t):
        if t > GROW0 + 1.5:
            return
        lx, ly = self.tree.base
        cv = self.cv

        def pos(tt):
            p = sstep(0.0, SEED_LAND, tt)
            return lx + 35 * np.sin(tt * 1.8) * (1 - p), -20 + (ly - 4 + 20) * p

        if t < SEED_LAND:
            k = np.arange(90)
            tau = t - k * 0.022
            ok = tau > 0
            px, py = pos(tau)
            a = tau * 9 + k * 0.25
            r = 3 + k * 0.09
            col = (GOLD[None] * (1 - k / 90)[:, None] + C(1.0, 0.4, 0.8)[None] * (k / 90)[:, None])
            col = col * (0.6 * np.exp(-k / 28))[:, None]
            cv.add((px + r * np.cos(a))[ok], (py + r * np.sin(a))[ok], col[ok])
            cv.add((px - r * np.cos(a))[ok], (py - r * np.sin(a))[ok], col[ok] * 0.6)
        sx, sy = pos(min(t, SEED_LAND))
        pulse = 1.0 if t < SEED_LAND else 0.75 + 0.25 * math.sin(t * 6)
        fade = 1 - float(sstep(GROW0, GROW0 + 1.5, t))
        cx = sx + np.random.normal(0, 1.8, 18)
        cy = sy + np.random.normal(0, 1.8, 18)
        cv.glow(cx, cy, SPARK * 0.55 * pulse * fade, r=1.6)

        dt = t - SEED_LAND
        if 0 < dt < 2.5:
            # onda de choque elíptica
            a = np.linspace(0, 2 * np.pi, 360, endpoint=False)
            r = dt * 240
            cv.add(lx + r * np.cos(a), ly + r * 0.12 * np.sin(a),
                   C(0.6, 0.9, 1.0) * 0.5 * math.exp(-dt * 1.6))
            # faíscas subindo
            rr = np.random.default_rng(self.seed)
            n = 90
            va = -math.pi / 2 + rr.normal(0, 0.55, n)
            sp = rr.uniform(60, 220, n)
            life = rr.uniform(0.8, 2.0, n)
            x = lx + np.cos(va) * sp * dt
            y = ly + np.sin(va) * sp * dt + 0.5 * 140 * dt * dt
            fade = np.clip(1 - dt / life, 0, 1)
            cv.add(x, y, GOLD[None] * (0.8 * fade)[:, None])

    def draw_fireflies(self, t):
        vis = float(sstep(29.0, 32.0, t) * (1 - sstep(41.0, 44.0, t)))
        if vis <= 0:
            return
        f, p = self.ff_f, self.ff_p
        x = self.ff_bx + 45 * np.sin(t * 0.30 * f[0] + p[0]) + 20 * np.sin(t * 0.71 * f[1] + p[1])
        y = self.ff_by + 28 * np.sin(t * 0.40 * f[2] + p[2]) + 12 * np.sin(t * 0.93 * f[3] + p[3])
        blink = np.maximum(0, np.sin(t * self.ff_w + p[4])) ** 6
        col = C(0.85, 1.0, 0.45)[None] * (1.6 * blink * vis)[:, None]
        self.cv.glow(x, y, col, r=1.6, n=8)

    def draw_snow(self, t):
        vis = float(sstep(WIN0, WIN1 - 0.5, t) * (1 - sstep(57.0, 60.0, t)))
        if vis <= 0:
            return
        x = (self.sn_x + 14 * t + 16 * np.sin(t * 0.9 + self.sn_ph)) % W
        y = (self.sn_y + self.sn_v * t) % H
        m = y < ground_at(x)
        self.cv.add(x[m], y[m], SNOW[None] * (self.sn_i[m] * vis)[:, None])

    # -- fundo ---------------------------------------------------------------
    def sky(self, t):
        v = keyinterp(t, SKY_KEYS)
        top, hor = v[:3], v[3:]
        y = self._ys
        u = (np.clip(y / GROUND_Y, 0, 1) ** 1.7)[:, None]
        col = top[None] * (1 - u) + hor[None] * u
        below = y > GROUND_Y
        d = np.clip((y - GROUND_Y) / (H - GROUND_Y), 0, 1)[below][:, None] ** 0.5
        col[below] = (hor * 0.35)[None] * (1 - d) + EARTH[None] * d
        s = pygame.surfarray.make_surface(col.astype(np.uint8).reshape(1, H, 3))
        return pygame.transform.scale(s, (W, H))

    def aurora(self, t):
        strength = 0.20 + 0.10 * float(sstep(WIN0, WIN1, t) * (1 - sstep(57, 60, t)))
        ax, ay = self.au_x, self.au_y
        yc = H * 0.20 + 45 * np.sin(ax * 0.006 + t * 0.12) + 22 * np.sin(ax * 0.017 - t * 0.21)
        th = 22 + 10 * np.sin(ax * 0.011 + t * 0.27)
        dy = ay - yc
        band = np.exp(-(dy / th) ** 2)
        up = np.exp(-np.clip(-dy, 0, None) / 130.0) * (dy < 0)
        curtain = (0.55 + 0.25 * np.sin(ax * 0.021 + t * 0.35 + 2.0 * np.sin(ax * 0.005 - t * 0.08))
                   + 0.20 * np.sin(ax * 0.067 - t * 0.6)) * sstep(0, W * 0.15, ax) * sstep(W, W * 0.85, ax)
        i = (band * 0.7 + up * 0.45) * np.clip(curtain, 0, None) ** 1.3 * strength
        hm = np.clip(-dy / 120, 0, 1)[..., None]
        col = AUR_A * (1 - hm) + AUR_B * hm
        arr = np.clip(col * i[..., None] * 255, 0, 255).astype(np.uint8)
        return pygame.transform.smoothscale(pygame.surfarray.make_surface(arr), (W, int(H * 0.7)))

    # -- interface -----------------------------------------------------------
    def label(self, text, font, color):
        key = (text, id(font), color)
        if key not in self.label_cache:
            self.label_cache[key] = font.render(text, True, color)
        return self.label_cache[key]

    def draw_ui(self, screen, t, show_hint):
        cur = 0
        for i, (st, _) in enumerate(STAGES):
            if t >= st:
                cur = i
        st = STAGES[cur][0]
        nxt = STAGES[cur + 1][0] if cur + 1 < len(STAGES) else CYCLE
        alpha = float(sstep(st, st + 1.2, t) * (1 - sstep(nxt - 1.0, nxt, t)))
        surf = self.label(STAGES[cur][1], self.font, (235, 225, 255))
        surf.set_alpha(int(220 * alpha))
        screen.blit(surf, (W // 2 - surf.get_width() // 2, H - 62))

        # linha de progresso com marcos
        x0, x1, yl = W * 0.28, W * 0.72, H - 22
        pygame.draw.line(screen, (55, 50, 80), (x0, yl), (x1, yl), 1)
        px = x0 + (x1 - x0) * t / CYCLE
        pygame.draw.line(screen, (170, 150, 230), (x0, yl), (px, yl), 1)
        for i, (s, _) in enumerate(STAGES):
            sx = x0 + (x1 - x0) * s / CYCLE
            on = i <= cur
            pygame.draw.circle(screen, (220, 200, 255) if on else (70, 65, 100), (int(sx), yl), 3 if i == cur else 2)

        if show_hint:
            h = self.label("espaço pausar  ·  ←/→ navegar  ·  1–8 fases  ·  R nova árvore  ·  S salvar  ·  ESC sair",
                           self.small, (150, 140, 190))
            screen.blit(h, (W // 2 - h.get_width() // 2, 16))

    # -- quadro ----------------------------------------------------------------
    def render(self, screen, t, T, show_hint=False):
        cv = self.cv
        cv.begin()
        self.draw_stars(t, T)
        self.draw_mandala(t)
        self.draw_soil(t)
        self.draw_grass(t)
        self.tree.draw(cv, t)
        self.draw_seed(t)
        self.draw_fireflies(t)
        self.draw_snow(t)
        cv.flush()

        screen.blit(self.sky(t), (0, 0))
        screen.blit(self.aurora(T), (0, 0), special_flags=pygame.BLEND_ADD)
        ps = cv.surface()
        screen.blit(ps, (0, 0), special_flags=pygame.BLEND_ADD)
        # bloom em duas escalas
        s1 = pygame.transform.smoothscale(ps, (W // 4, H // 4))
        s2 = pygame.transform.smoothscale(s1, (W // 14, H // 14))
        screen.blit(pygame.transform.smoothscale(s1, (W, H)), (0, 0), special_flags=pygame.BLEND_ADD)
        screen.blit(pygame.transform.smoothscale(s2, (W, H)), (0, 0), special_flags=pygame.BLEND_ADD)
        screen.blit(self.vignette, (0, 0), special_flags=pygame.BLEND_MULT)
        self.draw_ui(screen, t, show_hint)


# ──────────────────────────────────────────────────────────────── principal ──
def main():
    pygame.init()
    args = sys.argv[1:]
    seed = None
    if "--seed" in args:
        seed = int(args[args.index("--seed") + 1])

    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Árvore da Vida")
    world = World(seed if seed is not None else random.randrange(1 << 30))

    # modo de captura: python arvore_da_vida.py --snap 10 25 ...
    if "--snap" in args:
        times = [float(a) for a in args[args.index("--snap") + 1:] if a.replace(".", "").isdigit()]
        for ts in times:
            world.cv.clear()
            for k in range(20):
                tt = max(0.0, ts - (19 - k) / FPS)
                world.render(screen, tt, tt)
            pygame.image.save(screen, f"snap_{ts:05.1f}.png")
            print("salvo", ts)
        return

    clock = pygame.time.Clock()
    t, T = 0.0, 0.0
    paused = False
    start = time.time()
    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit(); return
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    paused = not paused
                elif e.key == pygame.K_RIGHT:
                    t = min(t + 4.0, CYCLE - 0.01)
                elif e.key == pygame.K_LEFT:
                    t = max(t - 4.0, 0.0)
                elif e.key == pygame.K_r:
                    world.new_tree(); t = 0.0; world.cv.clear()
                elif e.key == pygame.K_s:
                    name = f"arvore_{int(time.time())}.png"
                    pygame.image.save(screen, name); print("imagem salva:", name)
                elif pygame.K_1 <= e.key <= pygame.K_8:
                    t = STAGES[e.key - pygame.K_1][0] + 0.01
        if not paused:
            t += dt
            T += dt
            if t >= CYCLE:
                t -= CYCLE
                world.new_tree()
        world.render(screen, t, T, show_hint=paused or time.time() - start < 8)
        pygame.display.flip()


if __name__ == "__main__":
    main()
