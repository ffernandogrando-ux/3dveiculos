"""Teste de estilo "animação em papel recortado" (cutout / stop-motion de papel), 100 % 2D em PIL: rápido.

Cena: o motorista (personagem original) chega no carro, olha o pneu, dá o chutinho (TUM), "tá bom ainda" e vai embora.
Áudio: trecho 8,18–11,92 s da narração do vídeo 02. 12 qps "on twos" + tremidinho por quadro (feito à mão).
Uso: python videos/_papel/teste_papel.py  →  videos/_papel/teste_papel.mp4
"""
import os, math, random, subprocess, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(HERE, "..", "..")
W, H, FPS = 576, 1024, 12
T0, T1 = 8.18, 11.92
DUR = T1 - T0
TMP = os.path.join(HERE, "_quadros")
os.makedirs(TMP, exist_ok=True)
PAL = json.load(open(os.path.join(RAIZ, "videos", "calibrar_pneu", "palavras.json")))


def tw(p, depois=0.0):
    for w, a, b in PAL:
        if a >= depois - 0.01 and w.lower().strip(",.?!").startswith(p):
            return a - T0
    raise KeyError(p)


T_CHUTE, T_TA, T_SEGUE = tw("chutinho"), tw("tá", 10.0), tw("segue")

# ---------------------------------------------------------------- textura de papel
rng = np.random.default_rng(1)
GRAO = (rng.normal(0, 1, (H, W)) * 6).astype(np.float32)
GRAO = np.asarray(Image.fromarray(np.clip(GRAO + 128, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)),
                  np.float32) - 128
FIBRA = np.asarray(Image.fromarray(np.clip(rng.normal(128, 30, (H // 8, W // 8)), 0, 255).astype(np.uint8))
                   .resize((W, H), Image.BICUBIC), np.float32) - 128


def papel(cor):
    """Folha de papel colorido do tamanho do quadro (cor + grão + fibra)."""
    c = np.array(Image.new("RGB", (1, 1), cor).getpixel((0, 0)), np.float32)
    a = c[None, None, :] + GRAO[..., None] * 0.9 + FIBRA[..., None] * 0.08
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


_folhas = {}


def folha(cor):
    if cor not in _folhas:
        _folhas[cor] = papel(cor)
    return _folhas[cor]


def borda_rasgada(pts, amp=1.6, seed=0, passo=6):
    """Subdivide o polígono e treme a borda (corte à mão com tesoura)."""
    r = random.Random(seed)
    out = []
    for i in range(len(pts)):
        a, b = np.array(pts[i], float), np.array(pts[(i + 1) % len(pts)], float)
        n = max(1, int(np.linalg.norm(b - a) / passo))
        for k in range(n):
            p = a + (b - a) * k / n
            out.append((p[0] + r.uniform(-amp, amp), p[1] + r.uniform(-amp, amp)))
    return out


def colar(img, pts, cor, sombra=(5, 6), seed=0, contorno=None):
    """Recorte de papel: sombra projetada suave + papel colorido + borda levemente mais clara."""
    pts = borda_rasgada(pts, seed=seed)
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    if sombra:
        s = Image.new("L", (W, H), 0)
        ImageDraw.Draw(s).polygon([(x + sombra[0], y + sombra[1]) for x, y in pts], fill=110)
        s = s.filter(ImageFilter.GaussianBlur(4))
        img.paste((20, 14, 10), (0, 0), s)
    img.paste(folha(cor), (0, 0), m)
    if contorno:
        ImageDraw.Draw(img).line(pts + [pts[0]], fill=contorno, width=1)


def circulo(c, r, n=28):
    return [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def elipse(c, rx, ry, n=28, rot=0.0):
    ca, sa = math.cos(rot), math.sin(rot)
    return [(c[0] + rx * math.cos(t) * ca - ry * math.sin(t) * sa, c[1] + rx * math.cos(t) * sa + ry * math.sin(t) * ca)
            for t in (2 * math.pi * k / n for k in range(n))]


def girar(pts, piv, ang):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(piv[0] + (x - piv[0]) * ca - (y - piv[1]) * sa, piv[1] + (x - piv[0]) * sa + (y - piv[1]) * ca)
            for x, y in pts]


def mover(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def alfinete(img, p):
    """Bailarina (prendedor de papel) dourada na junta."""
    d = ImageDraw.Draw(img)
    d.ellipse([p[0] - 3.5, p[1] - 3.5, p[0] + 3.5, p[1] + 3.5], fill="#C9A245", outline="#7A5F22")
    d.ellipse([p[0] - 1.2, p[1] - 2, p[0] + 0.8, p[1] - 0.5], fill="#F4E2A0")


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- cenário (camadas)
def cenario(img, j):
    colar(img, [(0, 0), (W, 0), (W, 420), (0, 420)], "#9ED3E8", sombra=None, seed=1)          # céu
    for k, (x, y, r) in enumerate(((90, 140, 34), (130, 128, 44), (175, 142, 30), (420, 90, 30), (460, 80, 38))):
        colar(img, circulo((x + j[0], y + j[1]), r), "#FBFAF6", sombra=(3, 4), seed=10 + k)    # nuvens
    colar(img, [(0, 300), (W, 280), (W, 470), (0, 470)], "#D9B98A", seed=2)                   # muro
    for k in range(6):
        colar(img, [(k * 104 - 4, 300 - k * 4), (k * 104 + 4, 300 - k * 4), (k * 104 + 4, 470), (k * 104 - 4, 470)],
              "#C7A272", sombra=(2, 2), seed=20 + k)
    colar(img, [(470, 120), (482, 120), (482, 470), (470, 470)], "#7E868F", seed=3)           # poste
    colar(img, [(482, 128), (540, 120), (540, 132), (482, 138)], "#7E868F", seed=4)
    colar(img, [(0, 470), (W, 470), (W, 520), (0, 520)], "#B8B4AA", seed=5)                    # calçada
    colar(img, [(0, 515), (W, 515), (W, H), (0, H)], "#4A4E55", seed=6)                         # asfalto
    for k in range(3):
        colar(img, [(40 + k * 200, 860), (150 + k * 200, 858), (150 + k * 200, 872), (40 + k * 200, 874)],
              "#F2EFE6", sombra=(2, 2), seed=30 + k)


def carro(img, j, tremor=0.0):
    """Popular hatch de papel (genérico), vermelho, de lado. tremor: balanço depois do chute."""
    dx, dy = 250 + j[0], 560 + j[1] + tremor * 3
    corpo = [(0, 150), (20, 95), (95, 85), (150, 30), (300, 28), (335, 85), (350, 100), (352, 150), (330, 168),
             (20, 168)]
    corpo = girar(corpo, (180, 150), math.radians(tremor * 0.8))
    colar(img, mover(corpo, dx, dy), "#C9433A", seed=40)
    for k, jan in enumerate(([(160, 40), (225, 38), (225, 85), (110, 87)], [(235, 38), (295, 37), (322, 84), (235, 85)])):
        colar(img, mover(girar(jan, (180, 150), math.radians(tremor * 0.8)), dx, dy), "#2F4C66", sombra=(2, 2),
              seed=41 + k)
    colar(img, mover([(330, 100), (352, 104), (352, 118), (330, 116)], dx, dy), "#FFE6A3", sombra=(1, 2), seed=43)
    colar(img, mover([(0, 112), (16, 110), (16, 126), (0, 128)], dx, dy), "#E05A44", sombra=(1, 2), seed=44)
    for cx in (75, 285):
        r = 38
        c = (dx + cx, dy + 165)
        colar(img, circulo(c, r), "#26282C", seed=50 + cx)
        colar(img, circulo(c, r * 0.55), "#C9CDD2", sombra=(1, 2), seed=51 + cx)
        for k in range(5):
            a = 2 * math.pi * k / 5 + 0.3
            ImageDraw.Draw(img).ellipse([c[0] + r * 0.32 * math.cos(a) - 2, c[1] + r * 0.32 * math.sin(a) - 2,
                                         c[0] + r * 0.32 * math.cos(a) + 2, c[1] + r * 0.32 * math.sin(a) + 2],
                                        fill="#7E848C")
    return (dx + 75, dy + 165)        # centro da roda traseira (a que leva o chute)


# ---------------------------------------------------------------- o motorista (personagem original, de papel)
PELE, PELE_E = "#8A5A3C", "#73482E"
REGATA, JEANS, JEANS_E, TENIS, CABELO = "#F3F1EA", "#3F5F8F", "#34507A", "#2A2C31", "#1E1712"


def boneco(img, x, y, j, perna_chute=0.0, perna_passo=0.0, ombros=0.0, olhar=0.0, expr="neutro", fala=0.0,
           virado=1):
    """Recorte articulado. (x, y) = pé no chão. perna_chute: 0..1 (chute com a perna da frente).
    perna_passo: -1..1 (balanço de caminhada). ombros: 0..1 (dar de ombros). virado: 1 = olha para a direita."""
    x, y = x + j[0], y + j[1]
    s = virado
    quad = (x, y - 205)
    # perna de trás
    a_tras = math.radians(-14 * perna_passo)
    p_tras = girar([(-14, 0), (10, 0), (8, 205 - 30), (-12, 205 - 30)], (0, 0), a_tras)
    colar(img, mover([(s * px, py) for px, py in p_tras], quad[0], quad[1]), JEANS_E, seed=60)
    pe_t = girar([(-10, 170), (30, 170), (34, 190), (-12, 190)], (0, 0), a_tras)
    colar(img, mover([(s * px, py) for px, py in pe_t], quad[0], quad[1]), TENIS, seed=61)
    # braço de trás
    sh = (quad[0] - s * 6, quad[1] - 150 - ombros * 12)
    a_b = math.radians(10 + ombros * 55)
    braco_t = girar([(-8, 0), (8, 0), (6, 120), (-6, 120)], (0, 0), a_b * s)
    colar(img, mover(braco_t, *sh), PELE_E, seed=62)
    # tronco: jeans (quadril) + regata
    colar(img, [(quad[0] - 26, quad[1] - 10), (quad[0] + 26, quad[1] - 10), (quad[0] + 24, quad[1] + 30),
                (quad[0] - 24, quad[1] + 30)], JEANS, seed=63)
    colar(img, [(quad[0] - 34, quad[1] - 6), (quad[0] + 34, quad[1] - 6), (quad[0] + 36, quad[1] + 4),
                (quad[0] - 36, quad[1] + 4)], "#4A3324", sombra=(2, 2), seed=64)           # cinto
    ImageDraw.Draw(img).rectangle([quad[0] - 6, quad[1] - 6, quad[0] + 6, quad[1] + 4], outline="#C9CDD2", width=2)
    yt = quad[1] - 160 - ombros * 10
    tronco = [(quad[0] - 30, quad[1] - 2), (quad[0] + 30, quad[1] - 2), (quad[0] + 34, yt + 40),
              (quad[0] + 22, yt + 4), (quad[0] + 10, yt + 6), (quad[0], yt + 16), (quad[0] - 10, yt + 6),
              (quad[0] - 22, yt + 4), (quad[0] - 34, yt + 40)]
    colar(img, [(px, py) for px, py in tronco], REGATA, seed=65, contorno="#D8D4C8")
    # pescoço e cabeça
    hc = (quad[0] + s * 4, yt - 30)
    colar(img, [(hc[0] - 9, yt - 8), (hc[0] + 9, yt - 8), (hc[0] + 10, yt + 16), (hc[0] - 10, yt + 16)], PELE_E, seed=66)
    colar(img, elipse(hc, 30, 35), PELE, seed=67)
    # cabelo crespo curto com volume (topo arredondado em "nuvem")
    cab = []
    for k in range(13):
        a = math.pi + math.pi * k / 12
        r = 38 + (3 if k % 2 else 0)
        cab.append((hc[0] + r * math.cos(a), hc[1] - 6 + r * 0.95 * math.sin(a)))
    cab += [(hc[0] + 31, hc[1] - 8), (hc[0] - 31, hc[1] - 8)]
    colar(img, cab, CABELO, sombra=(2, 3), seed=68)
    colar(img, elipse((hc[0] - s * 30, hc[1] + 2), 6, 9), PELE_E, sombra=(1, 2), seed=69)    # orelha
    # rosto (desenho simples sobre o papel)
    d = ImageDraw.Draw(img)
    ex = hc[0] + s * 8
    for k, ox in enumerate((-10, 10)):
        cx, cy = ex + ox, hc[1] + 2
        aberto = 6 if expr != "careta" else 3
        d.ellipse([cx - 5, cy - aberto, cx + 5, cy + aberto], fill="#FBFAF4")
        d.ellipse([cx - 2.5 + s * olhar * 2, cy - 2.5 + abs(olhar) * 2, cx + 2.5 + s * olhar * 2,
                   cy + 2.5 + abs(olhar) * 2], fill="#1A1410")
        inc = {"careta": 0.35, "desdem": -0.25, "bravo": 0.45}.get(expr, 0.0) * (1 if ox < 0 else -1)
        bz = cy - 11 - (4 if expr == "desdem" and ox > 0 else 0)
        d.line([(cx - 7, bz + inc * 7), (cx + 7, bz - inc * 7)], fill="#1E1712", width=4)
    my = hc[1] + 20
    if fala > 0.1:
        d.ellipse([ex - 7, my - 3, ex + 7, my + 3 + fala * 7], fill="#4A1E1E")
    elif expr in ("careta", "bravo"):
        d.arc([ex - 9, my, ex + 9, my + 10], 200, 340, fill="#4A1E1E", width=3)
    elif expr == "desdem":
        d.line([(ex - 9, my + 3), (ex + 9, my - 1)], fill="#4A1E1E", width=3)
    else:
        d.arc([ex - 9, my - 6, ex + 9, my + 6], 20, 160, fill="#4A1E1E", width=3)
    # perna da frente (a que chuta) — gira no quadril; canela dobra
    a_f = math.radians(14 * perna_passo - 60 * math.sin(math.pi * min(perna_chute, 1.0)))
    coxa = girar([(-14, 0), (12, 0), (11, 95), (-12, 95)], (0, 0), -a_f * s * -1 if False else a_f)
    coxa = [(s * -px if False else s * px, py) for px, py in coxa]
    joelho = girar([(0, 95)], (0, 0), a_f)[0]
    joelho = (s * joelho[0], joelho[1])
    dob = math.radians(30 * math.sin(math.pi * min(perna_chute * 1.3, 1.0)))
    canela = girar([(-12, 0), (11, 0), (10, 82), (-11, 82)], (0, 0), a_f + dob)
    canela = [(s * px + joelho[0], py + joelho[1]) for px, py in canela]
    pe = girar([(-10, 72), (32, 72), (36, 92), (-12, 92)], (0, 0), a_f + dob)
    pe = [(s * px + joelho[0], py + joelho[1]) for px, py in pe]
    colar(img, mover(canela, *quad), JEANS, seed=70)
    colar(img, mover(pe, *quad), TENIS, seed=71)
    colar(img, mover([(px, py) for px, py in coxa], *quad), JEANS, seed=72)
    alfinete(img, (quad[0] + joelho[0], quad[1] + joelho[1]))
    alfinete(img, quad)
    # braço da frente
    sh2 = (quad[0] + s * 26, quad[1] - 150 - ombros * 12)
    a_b2 = math.radians(-12 - ombros * 60)
    braco = girar([(-8, 0), (8, 0), (6, 62), (-6, 62)], (0, 0), a_b2 * s)
    cot = girar([(0, 62)], (0, 0), a_b2 * s)[0]
    ante = girar([(-7, 0), (7, 0), (6, 58), (-6, 58)], (0, 0), (a_b2 + math.radians(-40 * ombros)) * s)
    mao = (cot[0] + girar([(0, 62)], (0, 0), (a_b2 + math.radians(-40 * ombros)) * s)[0][0],
           cot[1] + girar([(0, 62)], (0, 0), (a_b2 + math.radians(-40 * ombros)) * s)[0][1])
    colar(img, mover(braco, *sh2), PELE, seed=73)
    colar(img, mover(mover(ante, *cot), *sh2), PELE, seed=74)
    colar(img, circulo((sh2[0] + mao[0], sh2[1] + mao[1]), 9), PELE, sombra=(2, 2), seed=75)
    alfinete(img, sh2)
    alfinete(img, (sh2[0] + cot[0], sh2[1] + cot[1]))


def adesivo(img, txt, c, rot, s=1.0, fundo="#FFD23F"):
    f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Black.otf", int(64 * s))
    x0, y0, x1, y1 = f.getbbox(txt)
    w, h = x1 - x0 + 40, y1 - y0 + 30
    lay = Image.new("RGBA", (w + 20, h + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([10, 10, 10 + w, 10 + h], 14, fill=fundo, outline="#1A1A1A", width=4)
    d.text((30 - x0, 25 - y0), txt, font=f, fill="#1A1A1A")
    lay = lay.rotate(rot, expand=True, resample=Image.BICUBIC)
    sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    sh.putalpha(lay.getchannel("A").point(lambda v: int(v * 0.45)))
    img.paste((20, 14, 10), (int(c[0] - lay.width / 2) + 6, int(c[1] - lay.height / 2) + 8), sh)
    img.paste(lay, (int(c[0] - lay.width / 2), int(c[1] - lay.height / 2)), lay)


def quadro(i):
    t = i / FPS
    r = random.Random(i // 2)                            # "on twos": treme a cada 2 quadros
    j = (r.uniform(-1.2, 1.2), r.uniform(-1.2, 1.2))
    img = Image.new("RGB", (W, H), "#000")
    cenario(img, j)
    # andar até o carro (0 → T_CHUTE - 0.5), chute, depois sai andando para a esquerda
    chegada = T_CHUTE - 0.45
    if t < chegada:
        x = -60 + (175 - -60) * ease(t / chegada)
        passo = math.sin(t * 9)
        virado, expr, olhar = 1, "neutro", 0.6
    elif t < T_SEGUE:
        x, passo, virado = 175, 0.0, 1
        expr, olhar = ("careta", 1.0) if t < T_CHUTE + 0.6 else ("desdem", 0.2)
    else:
        u = (t - T_SEGUE) / (DUR - T_SEGUE)
        x = 175 - 260 * ease(u)
        passo, virado, expr, olhar = math.sin(t * 9), -1, "desdem", 0.0
    chute = (t - T_CHUTE + 0.1) / 0.45 if T_CHUTE - 0.1 < t < T_CHUTE + 0.35 else 0.0
    tremor = math.sin((t - T_CHUTE - 0.2) * 30) * math.exp(-(t - T_CHUTE - 0.2) * 5) if t > T_CHUTE + 0.2 else 0.0
    ombros = math.sin(math.pi * min(max((t - T_TA) / 0.8, 0), 1)) if T_TA < t < T_TA + 0.8 else 0.0
    fala = abs(math.sin(t * 22)) if T_TA - 0.05 < t < T_TA + 0.75 else 0.0
    carro(img, j, tremor)
    boneco(img, x, 930, j, perna_chute=chute, perna_passo=passo, ombros=ombros, olhar=olhar, expr=expr, fala=fala,
           virado=virado)
    if T_CHUTE + 0.15 < t < T_CHUTE + 1.0:
        adesivo(img, "TUM!", (400, 520), r.uniform(-8, -4), s=0.9 + 0.1 * math.exp(-(t - T_CHUTE) * 6))
    if T_TA < t < T_SEGUE + 0.3:
        adesivo(img, "\"TÁ BOM AINDA\"", (W / 2, 220), 3, s=0.55, fundo="#FFFFFF")
    # vinheta de papel (bordas mais escuras)
    return img


if __name__ == "__main__":
    n = int(DUR * FPS)
    for i in range(n):
        quadro(i).save(os.path.join(TMP, f"{i:04d}.png"))
    wav = os.path.join(RAIZ, "videos", "calibrar_pneu", "narracao.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(TMP, "%04d.png"),
                    "-ss", str(T0), "-t", str(DUR), "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "24",
                    "-c:a", "aac", "-shortest", os.path.join(HERE, "teste_papel.mp4")], check=True)
    quadro(int((T_CHUTE + 0.2) * FPS)).save(os.path.join(HERE, "teste_papel_chute.png"))
    print("ok", n)
