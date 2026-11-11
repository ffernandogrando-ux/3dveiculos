"""Efeitos sonoros do motor: sons gravados da biblioteca CC0 (com fallback sintetizado) + mixador.

Uso em cada vídeo (efeitos.py):
    from sons import Mix, pop, thud, ...
    mx = Mix(duracao)
    mx.put(1.2, pop(), 0.6)
    mx.save("efeitos.wav")
"""
import os, wave, subprocess
import numpy as np
from scipy import signal

SR = 44100
LIB = os.environ.get("SFX_LIB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "biblioteca_sons"))
HAS_LIB = os.path.isdir(LIB)
rng = np.random.default_rng(3)


# ================================================================ utilidades
def tt(d):
    return np.arange(int(d * SR)) / SR


def env(n, a=0.005, r=None):
    t = np.arange(n) / SR
    e = np.minimum(t / a, 1.0)
    if r:
        e *= np.exp(-t / r)
    return e


def fades(x, a=0.05, r=0.1):
    x = x.copy()
    na, nr = min(int(a * SR), len(x) // 2), min(int(r * SR), len(x) // 2)
    if na:
        x[:na] *= np.linspace(0, 1, na)
    if nr:
        x[-nr:] *= np.linspace(1, 0, nr)
    return x


def bandnoise(n, lo, hi):
    b, a = signal.butter(2, [lo / (SR / 2), hi / (SR / 2)], "band")
    return signal.lfilter(b, a, rng.standard_normal(n))


def lownoise(n, hi):
    b, a = signal.butter(2, hi / (SR / 2), "low")
    return signal.lfilter(b, a, rng.standard_normal(n))


def lowpass(x, f):
    b, a = signal.butter(2, f / (SR / 2), "low")
    return signal.lfilter(b, a, x)


def norm(x, peak):
    return peak * x / (np.abs(x).max() + 1e-9)


def mixdown(*parts):
    n = max(len(p) for p in parts)
    return sum(np.pad(p, (0, n - len(p))) for p in parts)


_cache = {}


def sample(rel, start=0.0, dur=None, pitch=1.0, lp=None, peak=0.7, fade=0.01):
    """Trecho de um arquivo da biblioteca. pitch < 1 = mais grave e mais longo."""
    path = os.path.join(LIB, rel)
    if path not in _cache:
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                           capture_output=True, check=True)
        _cache[path] = np.frombuffer(r.stdout, np.float32).astype(np.float64)
    x = _cache[path]
    i0 = int(start * SR)
    n = int(dur * SR * pitch) if dur else len(x) - i0
    x = x[i0:i0 + n].copy()
    if pitch != 1.0:
        x = np.interp(np.arange(0, len(x), pitch), np.arange(len(x)), x)
    if lp:
        x = lowpass(x, lp)
    return fades(norm(x, peak), fade, fade)


def loop_sample(rel, d, start=0.0, **kw):
    """Repete um loop até cobrir d segundos."""
    x = sample(rel, start, None, **{**kw, "fade": 0.002})
    reps = int(np.ceil(d * SR / len(x)))
    return fades(np.tile(x, reps)[: int(d * SR)], 0.15, 0.25)


# ================================================================ sons sintetizados
def s_pop(pitch=1.0):
    t = tt(0.12)
    f = 380 * pitch * (1 + 1.6 * (1 - np.exp(-t / 0.02)))
    return 0.55 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.002, 0.035)


def ding(f=1320, vol=0.25):
    t = tt(0.9)
    s = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.01 * t) + 0.2 * np.sin(2 * np.pi * f * 3.02 * t)
    return vol * s * env(len(t), 0.003, 0.28)


def chime(notes=(523.25, 659.25, 783.99, 1046.5), gap=0.11):
    out = np.zeros(int((1.0 + gap * len(notes)) * SR))
    for i, f in enumerate(notes):
        d = ding(f)
        st = int(i * gap * SR)
        out[st:st + len(d)] += d[: len(out) - st]
    return 0.9 * out


def s_thud(heavy=1.0, metal=True):
    t = tt(0.55)
    f = 75 * (1 + np.exp(-t / 0.03))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.001, 0.12)
    s += bandnoise(len(t), 800, 5000) * env(len(t), 0.0005, 0.012) * 0.25
    if metal:
        for fr, a in ((620, 0.25), (1187, 0.15), (1893, 0.1)):
            s += a * np.sin(2 * np.pi * fr * t) * env(len(t), 0.001, 0.09)
    return 0.8 * heavy * s


def s_rumble(d, lvl=0.6):
    n = int(d * SR)
    s = lownoise(n, 180) / 4 + 0.3 * bandnoise(n, 200, 900) / 3
    return lvl * fades(s, 0.3, 0.3)


def rise_tone(d, f0=120, f1=380):
    t = tt(d)
    tone = np.sin(2 * np.pi * np.cumsum(f0 + (f1 - f0) * t / d) / SR)
    return fades(0.15 * tone + 0.3 * lownoise(len(t), 500) / 3, 0.08, 0.12)


def rain(d, lvl=0.35):
    n = int(d * SR)
    s = bandnoise(n, 900, 7000) / 3
    for _ in range(int(d * 40)):
        i = rng.integers(0, max(1, n - 800))
        s[i:i + 600] += 0.5 * bandnoise(600, 2000, 6000) / 3 * env(600, 0.0005, 0.003)
    return lvl * fades(s, 0.4, 0.5)


def crackle(d, lvl=0.4):
    """Fogo: ruído grave + estalos aleatórios."""
    n = int(d * SR)
    s = 0.5 * lownoise(n, 400) / 3
    for _ in range(int(d * 25)):
        i = rng.integers(0, max(1, n - 1500))
        L = int(rng.integers(200, 1500))
        s[i:i + L] += rng.uniform(0.3, 1.0) * bandnoise(L, 1500, 8000) / 3 * env(L, 0.0003, 0.004)
    return lvl * fades(s, 0.2, 0.4)


def squeak():
    t = tt(0.16)
    f = 2600 + 900 * np.sin(np.pi * t / 0.16) + 120 * np.sin(2 * np.pi * 38 * t)
    return 0.22 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.16) ** 0.5


def buzz_fly(d, lvl=0.06):
    t = tt(d)
    f = 210 + 25 * np.sin(2 * np.pi * 3.1 * t) + 12 * np.sin(2 * np.pi * 7.3 * t)
    s = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR)
    return lvl * fades(lowpass(s, 1800) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * t)), 0.4, 0.6)


def beeps(d, f=1050, every=0.55):
    out = np.zeros(int(d * SR))
    t = 0.0
    while t + 0.25 < d:
        b = np.sin(2 * np.pi * f * tt(0.22)) * fades(np.ones(int(0.22 * SR)), 0.005, 0.02)
        i = int(t * SR)
        out[i:i + len(b)] += 0.12 * b
        t += every
    return out


def drone(d, f=55, lvl=0.18):
    """Tensão: zumbido grave (perigo, contaminação)."""
    t = tt(d)
    s = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.5 * t + 0.3) + 0.3 * np.sin(2 * np.pi * f * 2.02 * t)
    return lvl * fades(s * (0.8 + 0.2 * np.sin(2 * np.pi * 0.5 * t)), 0.6, 0.8)


def zap():
    n = int(0.35 * SR)
    s = bandnoise(n, 2000, 9000) / 3 * (0.5 + 0.5 * signal.square(2 * np.pi * 60 * tt(0.35)))
    return 0.35 * s * env(n, 0.002, 0.12)


def hum_elec(d):
    t = tt(d)
    s = np.sin(2 * np.pi * 60 * t) + 0.6 * np.sin(2 * np.pi * 120 * t) + 0.3 * np.sin(2 * np.pi * 180 * t)
    return 0.07 * fades(s, 0.2, 0.3)


def flap():
    n = int(0.22 * SR)
    return 0.3 * lowpass(rng.standard_normal(n), 700) / 3 * np.sin(np.pi * np.arange(n) / n) ** 2


def sad(f0=330, f1=220, d=0.7):
    t = tt(d)
    f = f0 + (f1 - f0) * t / d
    return 0.16 * np.sin(2 * np.pi * np.cumsum(f) / SR) * fades(np.ones(len(t)), 0.02, 0.25)


# ================================================================ sons com biblioteca (fallback sintetizado)
if HAS_LIB:
    _wind_starts = None

    def whoosh(d=1.1):
        """Transição suave: rajada curta de vento, filtrada."""
        global _wind_starts
        if _wind_starts is None:
            x = sample("transicao/wind1.wav", peak=1.0)
            w = int(d * SR)
            e = np.convolve(np.abs(x), np.ones(2048) / 2048, "same")
            cands = sorted(range(0, len(x) - w, SR // 2), key=lambda i: -e[i + w // 2])
            _wind_starts = []
            for c in cands:
                if all(abs(c - o) > 3 * SR for o in _wind_starts):
                    _wind_starts.append(c)
                if len(_wind_starts) == 8:
                    break
            _wind_starts = [s / SR for s in _wind_starts] * 4
        s = _wind_starts.pop(0)
        x = sample("transicao/wind1.wav", s, d, lp=2200, peak=0.35)
        return x * np.sin(np.pi * np.linspace(0, 1, len(x))) ** 2

    def wind(d, lvl=0.5):
        return fades(sample("transicao/wind2.wav", 5.0, d, lp=3000, peak=lvl), 0.4, 0.5)

    def pop(pitch=1.0):
        return sample("aparecer/pop.ogg", pitch=pitch, peak=0.5, fade=0.003)

    def thud(heavy=1.0, metal=True):
        hit = sample("impacto_metal/sfx100v2_metal_hit_01.ogg" if metal else "impacto_madeira/sfx100v2_wood_hit_01.ogg",
                     pitch=0.8 if metal else 0.6, peak=0.7 * heavy, fade=0.003)
        return mixdown(0.6 * s_thud(heavy, metal=False), hit)

    def clank(pitch=1.0):
        return sample("impacto_metal/sfx100v2_metal_hit_01.ogg", pitch=pitch, peak=0.45, fade=0.003)

    def rumble(d, lvl=0.6):
        return sample("tremor/earthquake.wav", 5.0 + 3.1 * (d * 7 % 9), d, lp=900, peak=lvl, fade=0.25)

    def thunder(lvl=0.6):
        return sample("tremor/sfx100v2_thunder_01.ogg", peak=lvl, fade=0.05)

    def stones(n=3, lvl=0.6):
        return np.concatenate([sample(f"terra_pedras/sfx100v2_stones_0{1 + i % 3}.ogg", peak=lvl, fade=0.003) for i in range(n)])

    def scrape(pitch=0.55, lvl=0.35):
        return sample("arrasto/scrape2.wav", pitch=pitch, peak=lvl, fade=0.05)

    def engine(d, lvl=0.3, pitch=0.8):
        return loop_sample("maquina_broca/sfx100v2_loop_machine_04.ogg", d, pitch=pitch, lp=2500, peak=lvl)

    def drill(d, lvl=0.45):
        return fades(sample("maquina_broca/sfx100v2_loop_machine_01.ogg", 0.5, d, pitch=0.9, peak=lvl), 0.12, 0.12)

    def water(d, lvl=0.5):
        return loop_sample("agua/sfx100v2_loop_water_01.ogg", d, peak=lvl)

    def bubbling(d, lvl=0.35):
        return fades(sample("borbulhar/kettle-boil.wav", 100.0, d, lp=5000, peak=lvl), 0.3, 0.4)

    def crumple(lvl=0.3):
        return sample(f"sacola/crumples{rng.integers(1, 3)}.wav", peak=lvl, fade=0.02)

    def paper(lvl=0.5):
        return sample("papel/pageturn1.wav", peak=lvl, fade=0.01)
else:
    def whoosh(d=1.1):
        return 0.15 * fades(bandnoise(int(d * SR), 300, 1500) / 3, d / 2, d / 2)

    def wind(d, lvl=0.5):
        return lvl * fades(bandnoise(int(d * SR), 200, 1200) / 3, 0.4, 0.5)

    pop, thud, rumble = s_pop, s_thud, s_rumble

    def clank(pitch=1.0):
        return s_thud(0.5, True)

    def thunder(lvl=0.6):
        return s_rumble(3.0, lvl)

    def stones(n=3, lvl=0.6):
        return s_rumble(0.5 * n, lvl)

    def scrape(pitch=0.55, lvl=0.35):
        return lvl * fades(bandnoise(int(1.5 * SR), 300, 2000) / 3, 0.1, 0.3)

    def engine(d, lvl=0.3, pitch=0.8):
        t = tt(d)
        return lvl * fades(lowpass(signal.sawtooth(2 * np.pi * 70 * t), 900), 0.2, 0.3)

    def drill(d, lvl=0.45):
        return engine(d, lvl)

    def water(d, lvl=0.5):
        return lvl * fades(bandnoise(int(d * SR), 250, 2200) / 3, 0.25, 0.3)

    bubbling = water

    def crumple(lvl=0.3):
        return lvl * fades(bandnoise(int(1.0 * SR), 2000, 8000) / 3, 0.05, 0.3)

    def paper(lvl=0.5):
        return crumple(lvl)


# ================================================================ mixador
class Mix:
    def __init__(self, duration):
        self.d = duration
        self.buf = np.zeros((int(duration * SR) + SR * 4, 2))

    def put(self, t, s, vol=1.0, pan=0.0):
        i = int(max(0.0, t) * SR)
        l, r = np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))
        n = min(len(s), len(self.buf) - i)
        if n <= 0:
            return
        self.buf[i:i + n, 0] += s[:n] * vol * l * 1.414
        self.buf[i:i + n, 1] += s[:n] * vol * r * 1.414

    def save(self, path, peak=0.89):
        x = self.buf[: int(self.d * SR)]
        x = x / (np.abs(x).max() / peak + 1e-9)
        with wave.open(path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((x * 32767).astype("<i2").tobytes())
        print("salvo:", path)
