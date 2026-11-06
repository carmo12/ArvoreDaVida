"""
Árvore da Vida — animação de partículas
=======================================

Uma semente de luz cai do céu, cria raízes, cresce como uma árvore e
atravessa as quatro estações até se dissolver em luz e renascer.

Dia e noite se alternam o tempo todo (sol, lua com fases, nuvens, estrelas,
aurora) e cada estação traz detalhes próprios:

  primavera  borboletas, chuva fina, arco-íris, flores no chão, pétalas ao vento
  verão      raios de sol, pássaros, frutos, tempestade com relâmpagos, vaga-lumes
  outono     ventania, redemoinho de folhas, cogumelos, névoa, gansos, lua da colheita
  inverno    neve acumulada, pingentes de gelo, flocos de cristal, nevasca, halo da lua

Requisitos:
    pip install pygame numpy

Executar:
    python arvore_da_vida.py

Controles:
    ESPAÇO      pausar / continuar
    ← / →       voltar / avançar 4 segundos
    D           ir para a próxima parte do dia (amanhecer, dia, entardecer, noite)
    1 … 8       pular para uma fase
    R           nova árvore
    S           salvar imagem (png)
    ESC         sair
"""

import math
import random
import sys
import time
from types import SimpleNamespace

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
DAY_LEN = CYCLE / 6.0         # um dia completo (noite + dia) a cada ~10 s
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
ICE = C(0.55, 0.85, 1.00)
SPRING_P = [C(1.0, 0.42, 0.72), C(1.0, 0.78, 0.90), C(0.90, 0.35, 0.95), C(1.0, 0.60, 0.80)]
SUMMER_P = [C(0.15, 1.0, 0.60), C(0.10, 0.85, 0.95), C(0.55, 1.0, 0.35), C(0.20, 0.95, 0.80)]
AUTUMN_P = [C(1.0, 0.55, 0.12), C(1.0, 0.32, 0.08), C(0.95, 0.15, 0.25), C(1.0, 0.80, 0.25)]
SOIL_P = [C(0.70, 0.45, 0.28), C(0.85, 0.74, 0.58), C(0.55, 0.45, 0.75)]
GRASS_SP, GRASS_SU, GRASS_AU = C(0.45, 1.0, 0.50), C(0.12, 0.90, 0.75), C(1.0, 0.70, 0.22)
AUR_A, AUR_B = C(0.10, 0.95, 0.65), C(0.65, 0.25, 0.95)
BUTTER_P = [C(1.0, 0.45, 0.80), C(0.45, 0.90, 1.0), C(1.0, 0.86, 0.30), C(0.85, 0.80, 1.0)]
WILD_P = [C(1.0, 0.45, 0.70), C(1.0, 0.95, 0.90), C(1.0, 0.85, 0.30), C(0.75, 0.60, 1.0), C(0.50, 0.80, 1.0)]
FRUIT_P = [C(1.0, 0.20, 0.15), C(1.0, 0.45, 0.12), C(1.0, 0.72, 0.18)]
MUSH_P = [C(0.25, 0.95, 0.80), C(1.0, 0.45, 0.25), C(0.75, 0.45, 1.0)]
WIND_AU, WIND_WI = C(1.0, 0.78, 0.50), C(0.80, 0.92, 1.0)
BIRD_COL = (16, 18, 32)

# céu noturno: (tempo, topo RGB, horizonte RGB)
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

# céu diurno por estação
SKY_DAY_KEYS = [
    (0.0,  (34, 78, 170),  (176, 200, 238)),
    (17.0, (34, 78, 170),  (176, 200, 238)),
    (21.0, (70, 118, 214), (250, 190, 214)),   # primavera: horizonte rosado
    (29.0, (70, 118, 214), (250, 190, 214)),
    (33.0, (14, 100, 210), (132, 220, 242)),   # verão: azul vivo
    (39.0, (14, 100, 210), (132, 220, 242)),
    (43.0, (74, 98, 168),  (252, 186, 118)),   # outono: dourado
    (49.0, (74, 98, 168),  (252, 186, 118)),
    (52.0, (104, 134, 176), (218, 228, 240)),  # inverno: pálido
    (56.0, (104, 134, 176), (218, 228, 240)),
    (60.0, (34, 78, 170),  (176, 200, 238)),
]
SKY_DAY_KEYS = [(t, np.array(a + b, np.float32)) for t, a, b in SKY_DAY_KEYS]

# cor do chão de dia: primavera, verão, outono, inverno
GROUND_DAY = [C(70, 104, 66), C(52, 112, 74), C(118, 80, 44), C(176, 190, 220)]
WARM = C(255, 128, 84)
DUSK_TOP = C(88, 56, 128)

# fases da lua em cada noite: (ângulo de fase, lado iluminado)
MOON_PHASES = [(2.3, 1), (1.7, 1), (0.9, 1), (0.45, 1), (0.0, 1), (1.9, -1)]

# ventanias (tempo, força, largura) e tempestade
GUSTS = [(41.8, 1.0, 0.9), (44.4, 1.3, 0.8), (47.2, 1.0, 0.9), (50.7, 1.1, 1.0), (52.3, 0.9, 0.9)]
BOLTS = [(31.55, 0.22), (32.25, 0.78), (32.9, 0.45)]      # (tempo, posição x)

# bandos de pássaros: (início, duração, altura, direção, formação, escala, quantidade)
FLOCKS = [
    (24.3, 6.5, 230, +1, "pair", 0.80, 2),
    (34.3, 6.0, 190, +1, "loose", 0.75, 6),
    (36.2, 6.0, 300, -1, "loose", 0.65, 5),
    (44.2, 6.5, 170, -1, "V", 1.00, 9),
    (46.0, 6.0, 260, +1, "V", 0.80, 7),
]


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


def bump(t, c, w):
    return math.exp(-((t - c) / w) ** 2)


def sky_clock(t):
    """Luz do dia, crepúsculo e posição do sol e da lua no instante t."""
    d = (t / DAY_LEN) % 1.0
    a = (d - 0.25) * 2 * math.pi            # 0 = nascer do sol, π = pôr do sol
    e = math.sin(a)                         # elevação do sol (-1 … 1)
    light = float(sstep(-0.20, 0.30, e))
    twi = math.exp(-(e / 0.28) ** 2)
    sun = (W * 0.5 - math.cos(a) * W * 0.47, GROUND_Y - math.sin(a) * GROUND_Y * 0.82)
    moon = (W * 0.5 + math.cos(a) * W * 0.47, GROUND_Y + math.sin(a) * GROUND_Y * 0.82)
    return light, twi, e, sun, moon


def season_w(t):
    """Peso de cada estação (primavera, verão, outono, inverno), com transição suave."""
    sp = sstep(16.0, 21.0, t) * (1 - sstep(SUM0 - 1, SUM1 - 1, t))
    su = sstep(SUM0 - 1, SUM1 - 1, t) * (1 - sstep(AUT0 - 1, AUT1 - 1, t))
    au = sstep(AUT0 - 1, AUT1 - 1, t) * (1 - sstep(WIN0 - 1, WIN1 - 0.5, t))
    wi = sstep(WIN0 - 1, WIN1 - 0.5, t) * (1 - sstep(56.0, 59.0, t))
    return float(sp), float(su), float(au), float(wi)


def gust(t):
    return sum(a * bump(t, c, w) for c, a, w in GUSTS)


def gust_drift(t):
    """Deslocamento acumulado das ventanias do outono (empurra as folhas)."""
    return sum(a * w * 0.886 * (1 + np.tanh(1.2 * (t - c) / w)) for c, a, w in GUSTS[:3])


def flash_at(t):
    f = 0.0
    for te, _ in BOLTS:
        dt = t - te
        if dt >= 0:
            f += math.exp(-dt / 0.06)
            if dt > 0.16:
                f += 0.8 * math.exp(-(dt - 0.16) / 0.07)
    return min(f, 1.6)


def rain_amounts(t):
    shower = 0.80 * float(sstep(23.0, 24.0, t) * (1 - sstep(26.4, 27.4, t)))
    storm = float(sstep(30.3, 30.9, t) * (1 - sstep(33.0, 33.6, t)))
    return shower, storm


def value_noise(h, w, gh, gw, rng):
    """Ruído suave que se repete na horizontal (para nuvens em loop)."""
    g = rng.random((gh + 1, gw))
    ys = np.linspace(0, gh, h, endpoint=False)
    xs = np.linspace(0, gw, w, endpoint=False)
    y0 = ys.astype(int); x0 = xs.astype(int)
    fy = ys - y0; fx = xs - x0
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    x1 = (x0 + 1) % gw
    top = g[y0][:, x0] * (1 - fx) + g[y0][:, x1] * fx
    bot = g[y0 + 1][:, x0] * (1 - fx) + g[y0 + 1][:, x1] * fx
    return top * (1 - fy[:, None]) + bot * fy[:, None]


def fbm(h, w, gh, gw, rng, octaves=4):
    n = np.zeros((h, w)); amp = 1.0; tot = 0.0
    for _ in range(octaves):
        n += amp * value_noise(h, w, gh, gw, rng)
        tot += amp; gh *= 2; gw *= 2; amp *= 0.5
    return n / tot


def radial_surface(size, fn):
    r = (np.arange(size) - size / 2 + 0.5) / (size / 2)
    xx, yy = np.meshgrid(r, r, indexing="ij")
    v = (np.clip(fn(np.hypot(xx, yy)), 0, 1) * 255).astype(np.uint8)
    return pygame.surfarray.make_surface(np.ascontiguousarray(np.stack([v, v, v], -1)))


def make_moon(phase, flip, r=40):
    n = 2 * r + 4
    xx, yy = np.mgrid[-r - 2:r + 2, -r - 2:r + 2].astype(np.float32)
    rho2 = (xx ** 2 + yy ** 2) / (r * r)
    z = np.sqrt(np.clip(1 - rho2, 0, 1))
    lx, lz = math.sin(phase), math.cos(phase)
    lit = np.clip(((xx / r) * flip * lx + z * lz) * 2.4 + 0.15, 0, 1)
    rng = np.random.default_rng(5)
    maria = 0.80 + 0.20 * value_noise(n, n, 3, 3, rng)
    edge = np.clip((1 - np.sqrt(rho2)) * r / 1.6, 0, 1)
    v = (0.06 + 0.94 * lit) * maria * edge * 255
    arr = np.stack([v * 0.96, v * 0.97, v], -1).astype(np.uint8)
    return pygame.surfarray.make_surface(np.ascontiguousarray(arr))


def make_bolt(rng, x0, y0, x1, y1):
    def jag(a, b, spread, depth):
        pts = [np.array(a, float), np.array(b, float)]
        for _ in range(depth):
            new = [pts[0]]
            for p, q in zip(pts, pts[1:]):
                d = q - p
                ln = np.hypot(d[0], d[1]) + 1e-6
                nrm = np.array([-d[1], d[0]]) / ln
                new += [(p + q) / 2 + nrm * rng.normal(0, spread * ln), q]
            pts = new
        return np.array(pts)

    main = jag((x0, y0), (x1, y1), 0.20, 5)
    out = [main]
    for idx in rng.choice(np.arange(len(main) // 4, len(main) * 3 // 4), 3, replace=False):
        p = main[idx]
        ang = math.pi / 2 + rng.choice([-1, 1]) * rng.uniform(0.4, 0.9)
        ln = rng.uniform(80, 170)
        out.append(jag(p, p + ln * np.array([math.cos(ang), math.sin(ang)]), 0.22, 4))
    return out


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
        self._gen_extras(rng)

        # copa estática → centro do mandala
        _, _, _, _, ex, ey = self.transform(1000.0, sway=0.0)
        tx, ty = ex[self.l_cseg], ey[self.l_cseg]
        self.crown = np.array([np.median(tx), np.mean(ty) - 10])
        d = np.hypot(tx - self.crown[0], ty - self.crown[1])
        self.crown_r = float(min(np.percentile(d, 90) + 40, W * 0.46))
        self.cache = None

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

    def _gen_extras(self, rng):
        # frutos: nascem no verão e caem no outono
        nf = min(70, len(self.l_cseg))
        self.fr_seg = self.l_cseg[rng.choice(len(self.l_cseg), nf, replace=False)]
        self.fr_dx = rng.normal(0, 5, nf)
        self.fr_dy = rng.uniform(4, 12, nf)
        self.fr_t0 = rng.uniform(33.0, 38.5, nf)
        self.fr_fall = rng.uniform(43.0, 48.0, nf)
        self.fr_rest = rng.uniform(0, 5, nf)
        self.fr_col = pick(rng, FRUIT_P, nf)
        # pingentes de gelo: pendem dos galhos no inverno
        cand = np.nonzero((self.kind == 0) & (self.order >= 2) & (self.order <= 6))[0]
        ni = min(120, len(cand))
        self.ic_seg = rng.choice(cand, ni, replace=False)
        self.ic_len = rng.uniform(8, 22, ni)
        self.ic_t0 = rng.uniform(WIN0 + 0.3, WIN0 + 4.0, ni)
        self.ic_ph = rng.uniform(0, 6.28, ni)

    # -- animação -----------------------------------------------------------
    def transform(self, t, sway=1.0):
        n = len(self.parent)
        f = np.clip((t - self.t0) / (self.t1 - self.t0), 0.0, 1.0)
        ang = np.zeros(n); sx = np.zeros(n); sy = np.zeros(n); ex = np.zeros(n); ey = np.zeros(n)
        g = 0.6 + 0.4 * math.sin(t * 0.31) + 0.25 * math.sin(t * 0.83) + 1.3 * gust(t)
        rel = self.rel + sway * g * self.sway_amp * np.sin(t * 1.3 + self.sway_ph)
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
        self.cache = self.transform(t)
        f, ang, sx, sy, ex, ey = self.cache
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
                # a ventania empurra as folhas enquanto caem
                push = 55 * (gust_drift(self.l_ft[fall] + dm) - gust_drift(self.l_ft[fall]))
                xf = (x0 + 16 * dm + push
                      + self.l_sw[fall] * np.sin(2.0 * dm + self.l_ph[fall]) * np.minimum(dm, 1))
                yf = np.minimum(y0 + vy * d + 0.3 * self.l_sw[fall] * np.sin(3.1 * d), gy)
                x[fall] = xf; y[fall] = yf
                inten[fall] = np.where(d > dl, 0.6 * np.exp(-(d - dl) / 2.5), 1.0 + 0.4 * np.sin(d * 4 + self.l_ph[fall]))
            inten *= 1 - sstep(57.0, 60.0, t)
            m = vis & (inten > 0.01)
            cv.add(x[m], y[m], col[m] * inten[m, None])

    def draw_extras(self, cv, t):
        """Frutos (verão → outono) e pingentes de gelo (inverno)."""
        f, ang, sx, sy, ex, ey = self.cache

        seg = self.fr_seg
        grow = ease_out_back((t - self.fr_t0) / 1.6)
        d = np.clip(t - self.fr_fall, 0, None)
        x = ex[seg] + self.fr_dx
        y = ey[seg] + self.fr_dy
        gy = ground_at(x) - self.fr_rest
        y = np.minimum(y + 0.5 * 320 * d * d, gy)
        vis = (grow > 0.04) & (t < 56.0)
        if vis.any():
            fade = (1 - sstep(50.0, 53.0, t)) * (1 - sstep(56.0, 58.0, t))
            col = self.fr_col[vis] * (0.9 * grow[vis] * fade)[:, None]
            cv.glow(x[vis], y[vis], col, r=2.2, n=6)
            cv.add(x[vis], y[vis] - 1.0, col * 0.9)

        seg = self.ic_seg
        lg = self.ic_len * sstep(self.ic_t0, self.ic_t0 + 2.2, t) * (1 - sstep(56.0, 58.5, t))
        m = lg > 0.5
        if m.any():
            k = 6
            s = np.linspace(0, 1, k)[None, :]
            X = np.repeat(ex[seg][m][:, None], k, axis=1) + 0.0 * s
            Y = ey[seg][m][:, None] + s * lg[m][:, None]
            glint = 1 + 2.5 * np.maximum(0, np.sin(t * 2.2 + self.ic_ph[m])) ** 12
            col = ICE[None, None, :] * (0.45 + 0.75 * s)[..., None]
            col = col * np.where(s == 1.0, glint[:, None], 1.0)[..., None]
            cv.add(X.ravel(), Y.ravel(), col.reshape(-1, 3))


# ──────────────────────────────────────────────────────────────── mundo ──
class World:
    def __init__(self, seed):
        self.cv = Canvas()
        rng = np.random.default_rng(12345)
        self._ys = np.arange(H, dtype=np.float32)

        # estrelas
        n = 650
        self.st_x = rng.uniform(0, W, n)
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
        n = 1400
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

        self._init_sky(rng)
        self._init_props(rng)
        self.new_tree(seed)

    # -- recursos do céu, chão e clima ---------------------------------------
    def _init_sky(self, rng):
        # nuvens (textura que se repete na horizontal)
        ch = 430
        n = fbm(215, 450, 3, 6, rng, 5)
        dens = np.clip((n - 0.48) * 3.6, 0, 1) ** 1.25
        yy = np.linspace(0, 1, 215)[:, None]
        env = np.exp(-((yy - 0.38) / 0.34) ** 2)
        img = (dens * env * (1.0 - 0.30 * yy) * 255).astype(np.uint8)
        tile = pygame.surfarray.make_surface(np.ascontiguousarray(np.stack([img] * 3, -1).transpose(1, 0, 2)))
        self.cloud_tile = pygame.transform.smoothscale(tile, (W, ch))
        self.cloud_tmp = pygame.Surface((W, ch))

        # névoa rasteira
        n = fbm(60, 450, 2, 6, rng, 4)
        d = np.clip((n - 0.40) * 3.2, 0, 1)
        yy = np.linspace(0, 1, 60)[:, None]
        img = (d * (yy ** 1.5) * np.clip((1 - yy) * 5.0, 0, 1) * 1.6 * 255).clip(0, 255).astype(np.uint8)
        tile = pygame.surfarray.make_surface(np.ascontiguousarray(np.stack([img] * 3, -1).transpose(1, 0, 2)))
        self.fog_tile = pygame.transform.smoothscale(tile, (W, 150))
        self.fog_tmp = pygame.Surface((W, 150))

        # sol e lua
        self.sun_glow = radial_surface(
            640, lambda d: 0.95 * np.exp(-(d / 0.07) ** 2) + 0.50 * np.exp(-(d / 0.20) ** 1.4) * np.clip(1 - d, 0, 1)
            + 0.24 * np.clip(1 - d, 0, 1) ** 3)
        self.sun_disc = radial_surface(96, lambda d: np.clip((0.46 - d) / 0.05, 0, 1))
        self.moon_glow = radial_surface(440, lambda d: 0.55 * np.exp(-(d / 0.12) ** 1.6) + 0.20 * np.clip(1 - d, 0, 1) ** 2.5)
        self.moons = [make_moon(p, f) for p, f in MOON_PHASES]
        self.flare_discs = [radial_surface(s, lambda d: np.clip(1 - d, 0, 1) ** 0.8 * 0.55) for s in (46, 74, 30, 110)]

        # raios de sol (superfície pequena, ampliada)
        self.ray_small = pygame.Surface((W // 3, H // 3))
        self.ray_big = pygame.Surface((W, H))

        # chão (silhueta com borda suave) e arco-íris
        self.g_y0 = int(GROUND_Y - 30)
        self.g_h = H - self.g_y0
        gy = ground_at(np.arange(W)) - self.g_y0
        a = np.clip((np.arange(self.g_h)[None, :] - gy[:, None] + 1.0) / 2.0, 0, 1) * 255
        self.g_mask = pygame.Surface((W, self.g_h), pygame.SRCALPHA)
        px = pygame.surfarray.pixels3d(self.g_mask); px[:] = 255; del px
        pa = pygame.surfarray.pixels_alpha(self.g_mask); pa[:] = a.astype(np.uint8); del pa
        self.g_tmp = pygame.Surface((W, self.g_h), pygame.SRCALPHA)

        rh = 640
        big = pygame.Surface((W * 2, rh * 2))
        cols = [(255, 60, 60), (255, 150, 40), (255, 230, 70), (70, 230, 100), (60, 200, 255), (70, 90, 255), (160, 70, 230)]
        for i, col in enumerate(cols):
            pygame.draw.circle(big, tuple(int(v * 0.8) for v in col), (W + 60, int((GROUND_Y + 70) * 2)),
                               (440 - i * 8) * 2, 14)
        self.rb_surf = pygame.transform.smoothscale(big, (W, rh))
        self.rb_tmp = pygame.Surface((W, rh))

        # máscara que escurece o céu atrás das partículas durante o dia
        self.mask8 = pygame.Surface((W // 4, H // 4), 0, 8)
        self.mask8.set_palette([(i, i, i) for i in range(256)])

        # raios da tempestade
        brng = np.random.default_rng(31)
        self.bolts = [make_bolt(brng, xr * W, -10, xr * W + brng.uniform(-40, 40), GROUND_Y - 10) for _, xr in BOLTS]

    def _init_props(self, rng):
        # borboletas
        nb = 16
        self.bf_cx = rng.uniform(W * 0.18, W * 0.82, nb)
        self.bf_cy = rng.uniform(H * 0.32, GROUND_Y - 60, nb)
        self.bf_ax = rng.uniform(60, 180, nb)
        self.bf_ay = rng.uniform(30, 90, nb)
        self.bf_f = rng.uniform(0.18, 0.40, (3, nb))
        self.bf_p = rng.uniform(0, 6.28, (5, nb))
        self.bf_s = rng.uniform(9.0, 13.0, nb)
        self.bf_col = pick(rng, BUTTER_P, nb)
        ang = rng.random(14) * 2 * np.pi; rad = np.sqrt(rng.random(14))
        ux, uy = 0.55 + 0.55 * rad * np.cos(ang), -0.30 + 0.38 * rad * np.sin(ang)
        ang = rng.random(8) * 2 * np.pi; rad = np.sqrt(rng.random(8))
        lx, ly = 0.38 + 0.30 * rad * np.cos(ang), 0.32 + 0.26 * rad * np.sin(ang)
        wx = np.concatenate([ux, lx]); wy = np.concatenate([uy, ly])
        wb = 0.45 + 0.9 * np.hypot(wx - 0.5, wy) / 1.2
        self.bf_wx = np.concatenate([wx, -wx]); self.bf_wy = np.concatenate([wy, wy])
        self.bf_wb = np.concatenate([wb, wb])

        # pétalas ao vento
        npt = 260
        self.pt_rx = rng.uniform(-1, 1, npt); self.pt_ry = rng.uniform(-1, 0.7, npt)
        self.pt_vy = rng.uniform(24, 44, npt); self.pt_vx = rng.uniform(10, 34, npt)
        self.pt_off = rng.uniform(0, 14, npt); self.pt_sp = rng.uniform(0.8, 1.2, npt)
        self.pt_ph = rng.uniform(0, 6.28, npt)
        self.pt_col = pick(rng, SPRING_P + [C(1.0, 0.95, 0.95)], npt)

        # flores silvestres
        nf = 170
        self.wf_x = rng.uniform(0, W, nf); self.wf_h = rng.uniform(7, 19, nf)
        self.wf_t0 = rng.uniform(18.8, 24.5, nf); self.wf_lean = rng.normal(0, 0.3, nf)
        self.wf_col = pick(rng, WILD_P, nf); self.wf_ph = rng.uniform(0, 6.28, nf)

        # chuva
        nr = 1400
        self.rd_x = rng.uniform(-200, W + 200, nr); self.rd_y0 = rng.uniform(0, H + 60, nr)
        self.rd_len = rng.uniform(18, 32, nr); self.rd_v = rng.uniform(0.85, 1.15, nr)

        # cogumelos
        nm = 26
        self.mu_x = np.clip(rng.normal(W / 2, 170, nm), 40, W - 40)
        self.mu_h = rng.uniform(5, 12, nm); self.mu_r = rng.uniform(4, 9, nm)
        self.mu_t0 = AUT0 + 0.8 + rng.random(nm) * 3.6
        self.mu_col = pick(rng, MUSH_P, nm)
        a = rng.uniform(np.pi, 2 * np.pi, (nm, 16)); r = np.sqrt(rng.random((nm, 16)))
        self.mu_cx = r * np.cos(a); self.mu_cy = r * np.sin(a) * 0.7
        self.mu_sp = rng.uniform(-0.6, 0.6, (nm, 3))

        # redemoinho de folhas e riscos de vento
        nw = 240
        self.wh_h = rng.random(nw); self.wh_ph = rng.uniform(0, 6.28, nw)
        self.wh_col = pick(rng, AUTUMN_P, nw)
        nv = 16
        self.wd_y = rng.uniform(120, GROUND_Y - 40, nv); self.wd_len = rng.uniform(160, 280, nv)
        self.wd_v = rng.uniform(380, 560, nv); self.wd_o = rng.uniform(0, W + 520, nv)
        self.wd_ph = rng.uniform(0, 6.28, nv); self.wd_dy = rng.uniform(-30, 40, nv)
        self.wd_i = rng.uniform(0.5, 1.0, nv)

        # neve no chão e flocos grandes
        ns = 4200
        self.sg_x = rng.uniform(0, W, ns)
        prof = 6 + 5 * np.sin(self.sg_x * 0.013 + 1.0) + 3 * np.sin(self.sg_x * 0.041)
        self.sg_h = rng.random(ns) ** 1.5 * prof
        self.sg_c = 0.20 + 0.45 * rng.random(ns)
        self.sg_tw = rng.random(ns) < 0.10
        self.sg_ph = rng.uniform(0, 6.28, ns)
        nfl = 20
        self.fl_x = rng.uniform(0, W, nfl); self.fl_y = rng.uniform(0, H, nfl)
        self.fl_v = rng.uniform(22, 46, nfl); self.fl_r = rng.uniform(9, 16, nfl)
        self.fl_ph = rng.uniform(0, 6.28, nfl); self.fl_w = rng.uniform(-1, 1, nfl)
        s = np.array([0.25, 0.45, 0.65, 0.85, 1.0])
        arm = [(v, 0.0) for v in s]
        for sv in (0.55, 0.8):
            for sg in (-1, 1):
                for b in (1, 2):
                    arm.append((sv + 0.12 * b, sg * 0.16 * b))
        arm = np.array(arm)
        k = np.arange(6) * np.pi / 3
        self.fl_ax = np.concatenate([arm[:, 0] * np.cos(a) - arm[:, 1] * np.sin(a) for a in k])
        self.fl_ay = np.concatenate([arm[:, 0] * np.sin(a) + arm[:, 1] * np.cos(a) for a in k])

        # bandos de pássaros: deslocamentos de cada ave
        self.flock_off = []
        for (_, _, _, dn, form, sc, n) in FLOCKS:
            offs = []
            for i in range(n):
                if form == "V":
                    row = (i + 1) // 2; side = 1 if i % 2 else -1
                    offs.append((-dn * row * 24 * sc, side * row * 11 * sc))
                elif form == "pair":
                    offs.append((-dn * 26 * i, 14 * i))
                else:
                    offs.append((rng.uniform(-90, 90), rng.uniform(-45, 45)))
            self.flock_off.append(offs)

    def new_tree(self, seed=None):
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        self.tree = Tree(self.seed)

    # -- contexto de cada quadro ---------------------------------------------
    def context(self, t):
        c = SimpleNamespace(t=t)
        c.L, c.twi, c.e, c.sun, c.moon = sky_clock(t)
        c.night = 1.0 - c.L
        c.sp, c.su, c.au, c.wi = season_w(t)
        c.shower, c.storm = rain_amounts(t)
        c.rain = max(c.shower, c.storm)
        c.flash = flash_at(t)
        c.gust = gust(t)
        c.sun_a = float(sstep(-0.22, 0.02, c.e)) * (1 - 0.85 * c.rain)
        c.moon_a = float(sstep(0.12, -0.14, c.e)) * (1 - 0.9 * c.storm)
        c.moon_k = int(t / DAY_LEN + 0.5) % len(MOON_PHASES)
        c.snow = float(sstep(WIN0 + 0.2, WIN1 + 3.5, t) * (1 - sstep(56.5, 60.0, t)))
        return c

    # -- partículas: céu e chão ----------------------------------------------
    def draw_stars(self, t, T):
        c = self.c
        cv = self.cv
        n = c.night ** 2 * (1 - 0.9 * c.storm)
        tw = 0.55 + 0.45 * np.sin(T * self.st_tw + self.st_ph)
        cv.add(self.st_x, self.st_y, self.st_c * (tw * n)[:, None])
        # estrela cadente
        k = int(T // 13.0)
        loc = T - k * 13.0
        if loc < 1.1 and n > 0.2:
            r = np.random.default_rng(k + 777)
            x0, y0 = r.uniform(0.15 * W, 0.85 * W), r.uniform(40, 260)
            a = r.choice([0.45, math.pi - 0.45]) + r.normal(0, 0.1)
            d = np.array([math.cos(a), math.sin(a)])
            hx, hy = x0 + d[0] * loc * 650, y0 + d[1] * loc * 650
            j = np.arange(45)
            env = math.sin(math.pi * loc / 1.1) * n
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
        inten = tw * (vis + flash * (1 - burst * 0.7)) * (0.40 + 0.60 * self.c.night)
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
        sway = 3.0 * np.sin(t * 1.5 + self.gr_bx * 0.02) + 1.5 * np.sin(t * 2.7 + self.gr_bx * 0.05) + 5.0 * self.c.gust
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
        c = self.c
        vis = float(sstep(29.0, 32.0, t) * (1 - sstep(41.0, 44.0, t))) * c.night ** 2 * (1 - c.storm)
        if vis <= 0.01:
            return
        f, p = self.ff_f, self.ff_p
        x = self.ff_bx + 45 * np.sin(t * 0.30 * f[0] + p[0]) + 20 * np.sin(t * 0.71 * f[1] + p[1])
        y = self.ff_by + 28 * np.sin(t * 0.40 * f[2] + p[2]) + 12 * np.sin(t * 0.93 * f[3] + p[3])
        blink = np.maximum(0, np.sin(t * self.ff_w + p[4])) ** 6
        col = C(0.85, 1.0, 0.45)[None] * (1.6 * blink * vis)[:, None]
        self.cv.glow(x, y, col, r=1.6, n=8)

    def draw_snow(self, t):
        c = self.c
        vis = float(sstep(WIN0, WIN1 - 0.5, t) * (1 - sstep(57.0, 60.0, t)))
        if vis <= 0:
            return
        nv = int(len(self.sn_x) * (0.50 + 0.50 * min(c.gust, 1.0)) * (0.6 + 0.4 * vis))
        drift = 70 * sum(a * w * 0.886 * (1 + math.tanh(1.2 * (t - cc) / w)) for cc, a, w in GUSTS[3:])
        x = (self.sn_x + 14 * t + drift + 16 * np.sin(t * 0.9 + self.sn_ph)) % W
        y = (self.sn_y + self.sn_v * t) % H
        m = (y < ground_at(x)) & (np.arange(len(x)) < nv)
        self.cv.add(x[m], y[m], SNOW[None] * (self.sn_i[m] * vis)[:, None])

    # -- partículas: primavera -----------------------------------------------
    def draw_butterflies(self, c):
        amt = (c.sp + 0.6 * c.su) * float(sstep(19.5, 21.0, c.t))
        if amt < 0.03:
            return
        t = c.t
        inten = amt * (0.55 + 0.75 * c.L) * (1 - 0.8 * c.rain)
        x = (self.bf_cx + self.bf_ax * np.sin(t * self.bf_f[0] + self.bf_p[0])
             + 0.35 * self.bf_ax * np.sin(t * self.bf_f[1] * 2.7 + self.bf_p[1]))
        y = (self.bf_cy + self.bf_ay * np.sin(t * self.bf_f[2] + self.bf_p[2]) + 7 * np.sin(t * 3.1 + self.bf_p[3]))
        flap = 0.22 + 0.78 * np.abs(np.sin(t * 10.5 + self.bf_p[4]))
        S = self.bf_s
        X = x[:, None] + self.bf_wx[None, :] * (S * flap)[:, None]
        Y = y[:, None] + self.bf_wy[None, :] * S[:, None]
        col = self.bf_col[:, None, :] * self.bf_wb[None, :, None] * inten
        self.cv.add(X.ravel(), Y.ravel(), col.reshape(-1, 3))
        self.cv.glow(x, y, self.bf_col * inten * 0.8, r=1.8, n=6)

    def draw_petals(self, c):
        amt = c.sp * float(sstep(21.0, 24.0, c.t)) + 0.25 * c.su
        if amt < 0.03:
            return
        tr = self.tree
        n = len(self.pt_rx)
        ox = tr.crown[0] + self.pt_rx * tr.crown_r * 0.95
        oy = tr.crown[1] + self.pt_ry * tr.crown_r * 0.5
        gnd = ground_at(ox) - 2
        life = np.maximum((gnd - oy) / self.pt_vy, 3.0)
        tt = (c.t * self.pt_sp + self.pt_off) % life
        x = ox + self.pt_vx * tt + 14 * np.sin(1.7 * tt + self.pt_ph)
        y = np.minimum(oy + self.pt_vy * tt + 5 * np.sin(2.9 * tt + self.pt_ph), gnd)
        fade = np.minimum(tt / 0.8, 1) * np.minimum((life - tt) / 0.8, 1)
        vis = np.arange(n) < int(n * min(amt, 1.0))
        self.cv.add(x[vis], y[vis], self.pt_col[vis] * (fade * 0.6)[vis, None])

    def draw_wildflowers(self, c):
        t = c.t
        vis = 1 - float(sstep(AUT0, AUT1 + 3.0, t))
        grow = ease_out_back((t - self.wf_t0) / 1.4) * vis
        m = grow > 0.03
        if not m.any():
            return
        x0 = self.wf_x[m]
        gnd = ground_at(x0) + 1
        h = (self.wf_h * grow)[m]
        sway = (2.2 * np.sin(t * 1.6 + self.wf_ph) + 1.2 * np.sin(t * 2.9 + self.wf_ph * 1.7) + 3.0 * c.gust)[m]
        s = np.linspace(0, 1, 5)[None, :]
        X = x0[:, None] + (self.wf_lean[m] * h)[:, None] * s + sway[:, None] * s * s
        Y = gnd[:, None] - h[:, None] * s
        self.cv.add(X.ravel(), Y.ravel(), GRASS_SP * 0.32)
        hx, hy = X[:, -1], Y[:, -1]
        ang = np.arange(6) * np.pi / 3 + t * 0.4
        r = 2.4 * grow[m]
        HX = hx[:, None] + r[:, None] * np.cos(ang)[None]
        HY = hy[:, None] + r[:, None] * np.sin(ang)[None]
        self.cv.add(HX.ravel(), HY.ravel(), np.repeat(self.wf_col[m] * 0.8, 6, axis=0))
        self.cv.glow(hx, hy, GOLD * 0.55, r=1.2, n=4)

    # -- partículas: chuva e tempestade ----------------------------------------
    def draw_rain(self, c):
        amt = c.rain
        if amt < 0.03:
            return
        t = c.t
        nv = int(len(self.rd_x) * min(amt, 1.0))
        slant = 0.10 + 0.30 * c.storm
        speed = 520 + 420 * c.storm
        y = (self.rd_y0[:nv] + speed * self.rd_v[:nv] * t) % (H + 60) - 30
        x = self.rd_x[:nv] + slant * y
        gnd = ground_at(x)
        up = y < gnd
        col = C(0.55, 0.72, 1.0) * (0.42 + 0.2 * c.storm) * (1 + 1.1 * c.L)
        norm = math.hypot(slant, 1.0)
        ln = self.rd_len[:nv]
        for k, kw in ((0, 1.0), (1, 0.7), (2, 0.5), (3, 0.3), (4, 0.15)):
            px = x - slant / norm * ln * k * 0.5
            py = y - 1 / norm * ln * k * 0.5
            self.cv.add(px[up], py[up], col * kw)
        s = y - gnd
        sp = (s >= 0) & (s < 16)
        if sp.any():
            ss = s[sp]; fx = x[sp]; gy = gnd[sp]
            k = (1 - ss / 16)[:, None]
            self.cv.add(fx - ss * 1.3, gy - 4 * ss * (1 - ss / 16), col * k)
            self.cv.add(fx + ss * 1.3, gy - 4 * ss * (1 - ss / 16), col * k)

    def draw_lightning(self, c):
        for (te, _), bolt in zip(BOLTS, self.bolts):
            dt = c.t - te
            if not 0 <= dt < 0.45:
                continue
            f = math.exp(-dt / 0.06) + (0.8 * math.exp(-(dt - 0.16) / 0.07) if dt > 0.16 else 0.0)
            seg = np.linspace(0, 1, 14, endpoint=False)
            for i, poly in enumerate(bolt):
                X = (poly[:-1, 0, None] + (poly[1:, 0] - poly[:-1, 0])[:, None] * seg[None]).ravel()
                Y = (poly[:-1, 1, None] + (poly[1:, 1] - poly[:-1, 1])[:, None] * seg[None]).ravel()
                self.cv.glow(X, Y, C(0.75, 0.88, 1.0) * f * (1.3 if i == 0 else 0.55), r=1.2, n=4)

    # -- partículas: outono -------------------------------------------------------
    def draw_mushrooms(self, c):
        t = c.t
        grow = ease_out_back((t - self.mu_t0) / 1.0) * (1 - float(sstep(WIN0, WIN0 + 2.0, t)))
        m = grow > 0.03
        if not m.any():
            return
        g = grow[m]
        x = self.mu_x[m]
        y = ground_at(x) + 2
        h = self.mu_h[m] * g
        col = self.mu_col[m] * (0.45 + 0.9 * c.night)
        stem = np.linspace(0, 1, 4)[None, :]
        self.cv.add((x[:, None] + 0 * stem).ravel(), (y[:, None] - h[:, None] * stem).ravel(),
                    np.repeat(col * 0.45, 4, axis=0))
        top = y - h
        cx = x[:, None] + self.mu_cx[m] * (self.mu_r[m] * g)[:, None]
        cy = top[:, None] + self.mu_cy[m] * (self.mu_r[m] * g)[:, None]
        self.cv.add(cx.ravel(), cy.ravel(), np.repeat(col * 0.9, cx.shape[1], axis=0))
        sx = x[:, None] + self.mu_sp[m] * (self.mu_r[m] * g * 0.7)[:, None]
        sy = top[:, None] - (self.mu_r[m] * g * 0.25)[:, None] + 0 * sx
        self.cv.add(sx.ravel(), sy.ravel(), C(1.0, 0.95, 0.85) * (0.5 + 0.5 * c.night))
        if c.night > 0.2:
            self.cv.glow(x, top, col * 0.4 * c.night, r=3.2, n=8)

    def draw_whirl(self, c):
        g = bump(c.t, 45.2, 1.15)
        if g < 0.05:
            return
        t = c.t
        h = self.wh_h
        r = 14 + 90 * h * (0.6 + 0.4 * np.sin(t * 1.3 + h * 5))
        ang = t * 6.0 * (1.25 - 0.5 * h) + self.wh_ph
        cx = W * 0.74 + 26 * math.sin(t * 1.1) + 18 * h
        x = cx + r * np.cos(ang)
        y = GROUND_Y - 4 - 230 * h + r * 0.25 * np.sin(ang)
        self.cv.add(x, y, self.wh_col * (1.5 * g))

    def draw_wind(self, c):
        g = c.gust
        if g < 0.12:
            return
        t = c.t
        w = c.au + c.wi
        col = (WIND_AU * c.au + WIND_WI * c.wi) / max(w, 1e-3)
        u = np.linspace(0, 1, 64)[None, :]
        x0 = (-260 + ((t * self.wd_v + self.wd_o) % (W + 520)))[:, None]
        X = x0 + u * self.wd_len[:, None]
        Y = self.wd_y[:, None] + 18 * np.sin(u * 5.0 + self.wd_ph[:, None] + t * 2.0) + u * self.wd_dy[:, None]
        inten = (np.sin(np.pi * u) ** 1.5) * 0.30 * min(g, 1.4) * self.wd_i[:, None] * (0.7 + 0.8 * c.L)
        self.cv.add(X.ravel(), Y.ravel(), (col[None, None, :] * inten[..., None]).reshape(-1, 3))

    # -- partículas: inverno -------------------------------------------------------
    def draw_snowground(self, c):
        if c.snow < 0.02:
            return
        t = c.t
        x = self.sg_x
        y = ground_at(x) - self.sg_h * c.snow + 1
        tw = np.where(self.sg_tw, 1 + 5 * np.maximum(0, np.sin(t * 2.1 + self.sg_ph)) ** 14, 1.0)
        self.cv.add(x, y, SNOW[None] * (self.sg_c * tw * c.snow)[:, None])

    def draw_flakes(self, c):
        vis = float(sstep(WIN0, WIN1 - 0.5, c.t) * (1 - sstep(57.0, 60.0, c.t)))
        if vis < 0.02:
            return
        t = c.t
        cx = (self.fl_x + 14 * t + 30 * np.sin(t * 0.5 + self.fl_ph)) % W
        cy = (self.fl_y + self.fl_v * t) % H
        ok = cy < ground_at(cx) - 6
        rot = t * self.fl_w * 0.8 + self.fl_ph
        cr, sr = np.cos(rot)[:, None], np.sin(rot)[:, None]
        R = self.fl_r[:, None]
        X = cx[:, None] + R * (cr * self.fl_ax[None] - sr * self.fl_ay[None])
        Y = cy[:, None] + R * (sr * self.fl_ax[None] + cr * self.fl_ay[None])
        k = X.shape[1]
        self.cv.add(X[ok].ravel(), Y[ok].ravel(), C(0.75, 0.92, 1.0) * (0.55 + 1.3 * c.L) * vis)

    def draw_halo(self, c):
        if c.wi < 0.05 or c.moon_a < 0.1:
            return
        mx, my = c.moon
        if my > GROUND_Y - 40:
            return
        t = c.t
        a = c.wi * c.moon_a
        for R, n, k in ((78, 260, 0.22), (140, 380, 0.12)):
            ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
            tw = 0.7 + 0.3 * np.sin(t * 1.5 + ang * 7)
            self.cv.add(mx + R * np.cos(ang), my + R * np.sin(ang), C(0.75, 0.88, 1.0) * (k * a) * tw[:, None])
        self.cv.glow(np.array([mx - 78, mx + 78]), np.array([my, my]), C(0.8, 0.9, 1.0) * 0.5 * a, r=2.0, n=8)

    # -- fundo: céu, astros, nuvens -------------------------------------------------
    def sky(self, c):
        t, L, twi = c.t, c.L, c.twi
        v = keyinterp(t, SKY_KEYS) * (1 - L) + keyinterp(t, SKY_DAY_KEYS) * L
        top, hor = v[:3].copy(), v[3:].copy()
        k = 0.6 * twi
        hor = hor * (1 - k) + WARM * k
        top = top * (1 - 0.2 * twi) + DUSK_TOP * 0.2 * twi
        dark = 1 - 0.32 * c.rain
        top *= dark; hor *= dark
        if c.flash:
            fc = C(120, 150, 255) * min(c.flash, 1.5)
            top = top + fc * 0.35; hor = hor + fc * 0.5
        y = self._ys
        u = (np.clip(y / GROUND_Y, 0, 1) ** (1.8 - 0.6 * L))[:, None]
        col = top[None] * (1 - u) + hor[None] * u
        s = pygame.surfarray.make_surface(np.clip(col, 0, 255).astype(np.uint8).reshape(1, H, 3))
        return pygame.transform.scale(s, (W, H))

    def aurora(self, t, strength):
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

    def draw_aurora(self, screen, T, c):
        strength = (0.20 + 0.14 * c.wi) * c.night ** 1.5 * (1 - c.storm)
        if strength > 0.01:
            screen.blit(self.aurora(T, strength), (0, 0), special_flags=pygame.BLEND_ADD)

    @staticmethod
    def _rgb(col, k=1.0):
        return tuple(int(max(0, min(255, v * k * 255))) for v in col)

    def sun_color(self, c):
        cols = [C(1.0, 0.92, 0.80), C(1.0, 0.97, 0.86), C(1.0, 0.76, 0.48), C(0.88, 0.94, 1.0)]
        w = [c.sp, c.su, c.au, c.wi]
        s = sum(w)
        col = cols[0] if s < 1e-3 else sum(wi * ci for wi, ci in zip(w, cols)) / s
        return col * (1 - 0.65 * c.twi) + C(1.0, 0.50, 0.28) * 0.65 * c.twi

    def draw_sun(self, screen, c):
        a = c.sun_a
        if a < 0.02:
            return
        col = self.sun_color(c)
        sx, sy = c.sun
        k = a * (0.55 + 0.45 * c.twi)
        g = self.sun_glow.copy()
        g.fill(self._rgb(col, k), special_flags=pygame.BLEND_RGB_MULT)
        screen.blit(g, (sx - 320, sy - 320), special_flags=pygame.BLEND_ADD)
        size = int(70 * (0.85 + 0.55 * c.twi + 0.2 * c.su))
        d = pygame.transform.smoothscale(self.sun_disc, (size, size))
        d.fill(self._rgb(col, a), special_flags=pygame.BLEND_RGB_MULT)
        screen.blit(d, (sx - size / 2, sy - size / 2), special_flags=pygame.BLEND_ADD)

    def draw_moon(self, screen, c):
        a = c.moon_a
        if a < 0.02:
            return
        mx, my = c.moon
        phase = MOON_PHASES[c.moon_k][0]
        full = 1 - phase / math.pi
        col = C(0.86, 0.92, 1.0) * (1 - c.au) + C(1.0, 0.72, 0.45) * c.au
        gl = self.moon_glow.copy()
        gl.fill(self._rgb(col, a * (0.35 + 0.55 * full)), special_flags=pygame.BLEND_RGB_MULT)
        screen.blit(gl, (mx - 220, my - 220), special_flags=pygame.BLEND_ADD)
        size = int(84 * (1 + 0.40 * c.au))
        m = pygame.transform.smoothscale(self.moons[c.moon_k], (size, size))
        m.fill(self._rgb(col, a), special_flags=pygame.BLEND_RGB_MULT)
        screen.blit(m, (mx - size / 2, my - size / 2), special_flags=pygame.BLEND_ADD)

    def draw_clouds(self, screen, c):
        cover = 0.55 * c.sp + 0.95 * c.su + 0.8 * c.au + 0.9 * c.wi
        cover = max(cover, 0.45) * (1 + 0.9 * c.rain)
        day = C(0.80, 0.82, 0.86)
        night = C(0.30, 0.36, 0.58) * (0.22 + 0.78 * c.moon_a)
        col = night * (1 - c.L) + day * c.L
        tw = 0.7 * c.twi
        col = col * (1 - tw) + C(1.0, 0.55, 0.38) * tw
        col = col * cover * (1 - 0.35 * c.rain)
        if c.flash:
            col = col + C(0.7, 0.8, 1.0) * min(c.flash, 1.5) * 0.7
        off = int((c.t / CYCLE) * W) % W
        tmp = self.cloud_tmp
        tmp.blit(self.cloud_tile, (-off, 0))
        tmp.blit(self.cloud_tile, (W - off, 0))
        tmp.fill(self._rgb(col), special_flags=pygame.BLEND_RGB_MULT)
        screen.blit(tmp, (0, 0), special_flags=pygame.BLEND_ADD)

    def draw_birds(self, screen, c):
        if c.L < 0.12:
            return
        t = c.t
        for (t0, dur, y0, dn, form, sc, n), offs in zip(FLOCKS, self.flock_off):
            u = (t - t0) / dur
            if not 0 < u < 1:
                continue
            lx = (-60 + u * (W + 120)) if dn > 0 else (W + 60 - u * (W + 120))
            ly = y0 + 20 * math.sin(u * 3.4 + y0)
            for i, (ox, oy) in enumerate(offs):
                x, y = lx + ox, ly + oy + 4 * math.sin(t * 1.3 + i)
                f = math.sin(t * 9.0 + i * 0.9)
                s = sc
                pts = [(x - 13 * s, y - (9 * f + 1) * s), (x - 6.5 * s, y - (4.5 * f + 2.5) * s), (x, y + 1.5 * s),
                       (x + 6.5 * s, y - (4.5 * f + 2.5) * s), (x + 13 * s, y - (9 * f + 1) * s)]
                pygame.draw.lines(screen, BIRD_COL, False, pts, max(1, int(2 * s)))

    def draw_rainbow(self, screen, c):
        reveal = float(sstep(26.2, 27.8, c.t))
        fade = 1 - float(sstep(28.0, 29.2, c.t))
        k = 0.55 * fade * c.L ** 2 * reveal
        if k < 0.02:
            return
        tmp = self.rb_tmp
        tmp.blit(self.rb_surf, (0, 0))
        tmp.fill(self._rgb(C(1, 1, 1), k), special_flags=pygame.BLEND_RGB_MULT)
        screen.blit(tmp, (0, 0), (0, 0, int(W * reveal), tmp.get_height()), special_flags=pygame.BLEND_ADD)

    def draw_ground(self, screen, c):
        w = np.array([c.sp, c.su, c.au, c.wi], np.float32)
        s = float(w.sum())
        day = GROUND_DAY[0] if s < 1e-3 else sum(wi * g for wi, g in zip(w, GROUND_DAY)) / s
        night = day * 0.10 + C(3, 3, 7)
        col = night * (1 - c.L) + day * c.L
        snow = c.snow
        snow_col = C(24, 32, 56) * (1 - c.L) + C(176, 190, 220) * c.L
        col = col * (1 - snow) + snow_col * snow
        col = col + WARM * 0.10 * c.twi * c.sun_a
        if c.flash:
            col = col + C(40, 50, 80) * min(c.flash, 1.5)
        grad = np.linspace(1.0, 0.38, self.g_h)[:, None] * np.clip(col, 0, 255)[None]
        g = pygame.surfarray.make_surface(grad.astype(np.uint8).reshape(1, self.g_h, 3))
        g = pygame.transform.scale(g, (W, self.g_h))
        self.g_tmp.blit(g, (0, 0))
        self.g_tmp.blit(self.g_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(self.g_tmp, (0, self.g_y0))

    def draw_fog(self, screen, c):
        mist = 0.4 + 0.9 * c.twi
        k = 0.85 * c.au * mist + 0.30 * c.sp * mist + 0.45 * c.wi * (0.4 + 0.7 * c.twi) + 0.35 * c.rain
        k = min(k, 1.0)
        if k < 0.04:
            return
        day = C(0.82, 0.84, 0.90)
        night = C(0.22, 0.26, 0.42)
        col = night * (1 - c.L) + day * c.L
        col = col * (1 - 0.45 * c.au) + C(1.0, 0.72, 0.50) * 0.45 * c.au * (0.4 + 0.6 * c.L)
        col = col * k * 0.55
        off = int(-(c.t / CYCLE) * W) % W
        tmp = self.fog_tmp
        tmp.blit(self.fog_tile, (-off, 0))
        tmp.blit(self.fog_tile, (W - off, 0))
        tmp.fill(self._rgb(col), special_flags=pygame.BLEND_RGB_MULT)
        screen.blit(tmp, (0, int(GROUND_Y - 120)), special_flags=pygame.BLEND_ADD)

    def draw_rays(self, screen, c):
        base = 0.5 * c.sp + 1.0 * c.su + 0.8 * c.au + 0.3 * c.wi
        k = base * float(sstep(-0.05, 0.14, c.e)) * c.sun_a * (0.6 + 0.4 * c.twi)
        if k < 0.04:
            return
        t = c.t
        col = self.sun_color(c)
        sx, sy = c.sun
        surf = self.ray_small
        surf.fill((0, 0, 0))
        cx, cy = self.tree.crown
        a0 = math.atan2(cy - sy, cx - sx)
        p0 = (sx / 3, sy / 3)
        for i in range(11):
            ang = a0 + (i - 5) * 0.085 + 0.02 * math.sin(t * 0.4 + i * 1.7)
            hw = 0.018 + 0.012 * math.sin(t * 0.3 + i * 2.1)
            ii = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(t * 0.6 + i * 1.3))
            p1 = (p0[0] + 340 * math.cos(ang - hw), p0[1] + 340 * math.sin(ang - hw))
            p2 = (p0[0] + 340 * math.cos(ang + hw), p0[1] + 340 * math.sin(ang + hw))
            pygame.draw.polygon(surf, self._rgb(col, k * 0.085 * ii), [p0, p1, p2])
        pygame.transform.smoothscale(surf, (W, H), self.ray_big)
        screen.blit(self.ray_big, (0, 0), special_flags=pygame.BLEND_ADD)

    def draw_flares(self, screen, c):
        k = (0.6 * c.su + 0.2 * c.sp + 0.3 * c.au) * c.L ** 3 * c.sun_a * float(sstep(0.25, 0.6, c.e))
        if k < 0.03:
            return
        sx, sy = c.sun
        tints = [C(0.4, 1.0, 0.7), C(0.5, 0.6, 1.0), C(1.0, 0.6, 0.8), C(1.0, 0.85, 0.5)]
        for ghost, kk, tint in zip(self.flare_discs, (0.35, 0.8, 1.3, 1.7), tints):
            x = sx + (W / 2 - sx) * kk
            y = sy + (GROUND_Y * 0.55 - sy) * kk
            d = ghost.copy()
            d.fill(self._rgb(tint, k * 0.35), special_flags=pygame.BLEND_RGB_MULT)
            screen.blit(d, (x - d.get_width() / 2, y - d.get_height() / 2), special_flags=pygame.BLEND_ADD)

    # -- composição final -----------------------------------------------------------
    def composite(self, screen, ps, c):
        L = c.L
        s1 = pygame.transform.smoothscale(ps, (W // 4, H // 4))
        if L > 0.03:
            # de dia, escurece suavemente o céu atrás da copa e dos galhos para as cores aparecerem
            a = pygame.surfarray.pixels3d(s1)
            m = a.max(axis=2)
            del a
            lut = (255 - np.clip(np.arange(256) * 5.0, 0, 255) * 0.78 * L).astype(np.uint8)
            pygame.surfarray.blit_array(self.mask8, lut[m])
            big = pygame.transform.smoothscale(self.mask8.convert(32), (W, H))
            screen.blit(big, (0, 0), special_flags=pygame.BLEND_MULT)
        screen.blit(ps, (0, 0), special_flags=pygame.BLEND_ADD)
        # bloom em duas escalas (mais fraco de dia)
        s2 = pygame.transform.smoothscale(s1, (W // 14, H // 14))
        bl = 1 - 0.55 * L
        if bl < 0.99:
            q = (int(255 * bl),) * 3
            s1.fill(q, special_flags=pygame.BLEND_RGB_MULT)
            s2.fill(q, special_flags=pygame.BLEND_RGB_MULT)
        screen.blit(pygame.transform.smoothscale(s1, (W, H)), (0, 0), special_flags=pygame.BLEND_ADD)
        screen.blit(pygame.transform.smoothscale(s2, (W, H)), (0, 0), special_flags=pygame.BLEND_ADD)

    # -- interface -----------------------------------------------------------
    def label(self, text, font, color):
        key = (text, id(font), color)
        if key not in self.label_cache:
            self.label_cache[key] = font.render(text, True, color)
        return self.label_cache[key]

    def draw_ui(self, screen, c, show_hint):
        t = c.t
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

        # parte do dia, com ícone de sol ou lua
        d = (t / DAY_LEN) % 1.0
        if c.twi > 0.45:
            name = "amanhecer" if d < 0.5 else "entardecer"
        else:
            name = "dia" if c.L > 0.5 else "noite"
        ts = self.label(name, self.small, (200, 190, 235))
        ts.set_alpha(int(200 * alpha))
        tx = W // 2 - ts.get_width() // 2
        ty = H - 84
        screen.blit(ts, (tx + 8, ty))
        ix, iy = tx - 8, ty + 9
        if c.L > 0.5:
            pygame.draw.circle(screen, (255, 214, 130), (ix, iy), 4)
        else:
            pygame.draw.circle(screen, (220, 228, 250), (ix, iy), 4)
            pygame.draw.circle(screen, (14, 10, 24), (ix + 2, iy - 1), 4)

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
            h = self.label("espaço pausar  ·  ←/→ navegar  ·  D dia/noite  ·  1–8 fases  ·  R nova árvore  ·  S salvar  ·  ESC sair",
                           self.small, (150, 140, 190))
            screen.blit(h, (W // 2 - h.get_width() // 2, 16))

    # -- quadro ----------------------------------------------------------------
    def render(self, screen, t, T, show_hint=False):
        c = self.c = self.context(t)
        cv = self.cv
        cv.begin()
        self.draw_stars(t, T)
        self.draw_mandala(t)
        self.draw_soil(t)
        self.draw_snowground(c)
        self.draw_grass(t)
        self.draw_wildflowers(c)
        self.draw_mushrooms(c)
        self.tree.draw(cv, t)
        self.tree.draw_extras(cv, t)
        self.draw_seed(t)
        self.draw_fireflies(t)
        self.draw_butterflies(c)
        self.draw_petals(c)
        self.draw_rain(c)
        self.draw_lightning(c)
        self.draw_snow(t)
        self.draw_flakes(c)
        self.draw_wind(c)
        self.draw_whirl(c)
        self.draw_halo(c)
        cv.flush()
        ps = cv.surface()

        screen.blit(self.sky(c), (0, 0))
        self.draw_aurora(screen, T, c)
        self.draw_sun(screen, c)
        self.draw_moon(screen, c)
        self.draw_clouds(screen, c)
        self.draw_birds(screen, c)
        self.draw_rainbow(screen, c)
        self.draw_ground(screen, c)
        self.draw_fog(screen, c)
        self.draw_rays(screen, c)
        self.draw_flares(screen, c)
        self.composite(screen, ps, c)
        screen.blit(self.vignette, (0, 0), special_flags=pygame.BLEND_MULT)
        self.draw_ui(screen, c, show_hint)


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
    quarter = DAY_LEN / 4
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
                elif e.key == pygame.K_d:
                    t = min((math.floor(t / quarter + 1e-6) + 1) * quarter + 0.05, CYCLE - 0.01)
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
