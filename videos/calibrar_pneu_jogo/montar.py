"""Monta o vídeo 02 no estilo jogo: quadros de rua (_quadros) + raio-X (../calibrar_pneu/quadros), HUD de jogo,
transição "whip" nas trocas rua ↔ raio-X e som (voz na frente: efeitos com ducking, -14 LUFS).
    ~/.venv-video/bin/python montar.py
"""
import os, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
S = lambda *p: os.path.join(RAIZ, *p)
FPS, W, H, D = 24, 576, 1024, 66.2
RUA = [(0.0, 11.92), (33.0, 40.6), (53.16, 66.2)]
CORTES = [11.92, 33.0, 40.6, 53.16]
F_BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
_f = {}
fonte = lambda s: _f.setdefault(s, ImageFont.truetype(F_BLACK, s))
SAIDA = os.path.join(AQUI, "_final")
os.makedirs(SAIDA, exist_ok=True)


def na_rua(t):
    return any(a <= t < b for a, b in RUA)


def lerp(a, b, u):
    u = min(max(u, 0.0), 1.0)
    return a + (b - a) * u


def caixa(d, xy, r=10, fill=(15, 18, 24, 190), outline=None, w=2):
    d.rounded_rectangle(xy, r, fill=fill, outline=outline, width=w)


def texto(d, xy, s, tam, cor=(255, 255, 255), contorno=4, anc="la"):
    d.text(xy, s, font=fonte(tam), fill=cor, stroke_width=contorno, stroke_fill=(10, 10, 12), anchor=anc)


def aparece(t, t0, t1, ent=0.15):
    """0..1 de opacidade de um elemento que vive de t0 a t1 (entra e sai rápido)."""
    if t < t0 or t > t1:
        return 0.0
    return min(1.0, (t - t0) / ent, (t1 - t) / ent)


def pop(t, t0):
    """Escala de 'carimbo' (cresce e assenta)."""
    return 1 + 0.35 * math.exp(-max(t - t0, 0) * 12)


def selo(d, t, t0, t1, txt, y, cor_fundo, cor_txt=(20, 20, 20), tam=34, sub=None):
    a = aparece(t, t0, t1)
    if a <= 0:
        return
    A = int(255 * a)
    s = pop(t, t0)
    tt = int(tam * s)
    larg = fonte(tt).getlength(txt) + 44
    if sub:
        larg = max(larg, fonte(22).getlength(sub) + 44)
    hh = tt + 26 + (32 if sub else 0)
    caixa(d, (W / 2 - larg / 2, y, W / 2 + larg / 2, y + hh), 14, fill=(*cor_fundo, int(235 * a)),
          outline=(15, 15, 15, A), w=3)
    texto(d, (W / 2, y + 12), txt, tt, (*cor_txt, A), 0, "ma")
    if sub:
        texto(d, (W / 2, y + tt + 18), sub, 22, (*cor_txt, A), 0, "ma")


def nivel_bolso(t):
    v = 1.0
    v -= 0.4 * min(max((t - 4.56) / 2.6, 0), 1)       # "deixando dinheiro no asfalto"
    v -= 0.15 * min(max((t - 32.1) / 0.5, 0), 1)      # "o carro bebe mais"
    v -= 0.33 * min(max((t - 33.6) / 0.4, 0), 1)      # "troca o jogo de pneu"
    return max(v, 0.04)


def nivel_pneu(t):
    v = 0.34 - 0.12 * min(max((t - 13.0) / 6.0, 0), 1)   # "perde ar sozinho, todo mês"
    v = lerp(v, 1.0, (t - 57.7) / 0.8)                  # "calibra no número da plaquinha"
    return v


def hud(img, t):
    o = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    # barras fixas
    b = nivel_bolso(t)
    caixa(d, (18, 40, 250, 100))
    texto(d, (32, 50), "BOLSO", 20, (190, 230, 190), 0)
    d.rounded_rectangle((32, 76, 236, 90), 5, fill=(40, 45, 50, 255))
    d.rounded_rectangle((32, 76, 32 + 204 * b, 90), 5,
                        fill=(70, 200, 90) if b > 0.7 else ((235, 170, 40) if b > 0.3 else (230, 60, 50)))
    p = nivel_pneu(t)
    caixa(d, (W - 200, 40, W - 18, 100))
    texto(d, (W - 186, 50), "PNEU", 20, (230, 230, 230), 0)
    d.rounded_rectangle((W - 186, 76, W - 32, 90), 5, fill=(40, 45, 50, 255))
    ok = p > 0.9
    pisca = ok or (int(t * 3) % 2 == 0)
    d.rounded_rectangle((W - 186, 76, W - 186 + 154 * p, 90), 5,
                        fill=(70, 200, 90) if ok else ((235, 60, 50) if pisca else (150, 40, 35)))
    if ok:
        texto(d, (W - 74, 47), "✓", 26, (90, 220, 110), 0)
    elif pisca:
        texto(d, (W - 74, 47), "⚠", 26, (255, 200, 40), 0)
    # −R$ escorrendo do bolso
    for t0, n in ((4.56, 6), (32.1, 3), (33.6, 5)):
        for k in range(n):
            tk = t0 + k * 0.28
            if tk < t < tk + 0.8:
                u = (t - tk) / 0.8
                texto(d, (50 + (k % 5) * 36, 112 + 46 * u), "−R$", 24, (255, 80, 70, int(255 * (1 - u) ** 0.7)), 3)
    # modo raio-X
    if not na_rua(t):
        a = int(255 * min(1.0, (t - max(c for c in CORTES if c <= t)) / 0.2))
        caixa(d, (W / 2 - 92, 112, W / 2 + 92, 146), 8, fill=(10, 60, 70, int(a * 0.85)), outline=(80, 230, 230, a), w=2)
        texto(d, (W / 2, 118), "VISÃO RAIO-X", 20, (120, 245, 245, a), 0, "ma")
    # título
    a = aparece(t, 0.0, 4.2, ent=0.1)
    if a > 0:
        tt = int(62 * pop(t, 0.05))
        texto(d, (W / 2, 190), "VOCÊ FAZ ISSO?", tt, (255, 215, 60, int(255 * a)), 7, "ma")
    # piada do meio-fio
    selo(d, t, 5.8, 7.4, "⚠ ESTACIONOU NA CALÇADA", 300, (235, 170, 30), tam=27, sub="−R$ multa")
    # missão do chute
    a = aparece(t, 7.84, 9.6)
    if a > 0:
        A = int(255 * a)
        caixa(d, (40, 170, W - 40, 250), 14, fill=(15, 18, 24, int(210 * a)), outline=(255, 190, 40, A), w=3)
        texto(d, (W / 2, 186), "MISSÃO", 22, (255, 190, 40, A), 0, "ma")
        texto(d, (W / 2, 212), "CHECAR O PNEU", 30, (255, 255, 255, A), 3, "ma")
    if 9.85 < t < 10.5:
        texto(d, (W * 0.62, 640), "TUM!", int(64 * pop(t, 9.88)), (255, 215, 60), 6, "mm")
    selo(d, t, 11.2, 11.92, "✗ MISSÃO FALHOU", 170, (190, 30, 30), (255, 255, 255), sub="chute não mede pressão")
    # H: resultado / culpa
    selo(d, t, 33.6, 35.4, "−R$ JOGO DE PNEU", 170, (190, 30, 30), (255, 255, 255), sub="trocado antes da hora")
    selo(d, t, 36.4, 37.6, "CULPA DO PNEU BARATO?", 170, (245, 245, 245), sub="✗ não")
    # objeções
    selo(d, t, 37.7, 40.5, "AH, MAS…", 170, (255, 205, 50), tam=40, sub="calibro no posto depois de rodar")
    selo(d, t, 46.8, 49.4, "AH, MAS…", 760, (255, 205, 50), tam=40, sub="encho até o número do pneu")
    # L: missão certa com checklist
    a = aparece(t, 53.3, 61.0)
    if a > 0:
        A = int(255 * a)
        itens = [(54.6, "1 vez por mês"), (56.0, "com o pneu frio"), (57.7, "número da porta ou do manual"),
                 (60.0, "e o estepe!")]
        caixa(d, (36, 640, W - 36, 640 + 64 + 46 * 4), 14, fill=(15, 18, 24, int(215 * a)), outline=(90, 220, 110, A), w=3)
        texto(d, (60, 654), "MISSÃO: CALIBRAR CERTO", 26, (120, 235, 140, A), 0)
        for k, (tk, s) in enumerate(itens):
            if t >= tk:
                y = 700 + 46 * k
                texto(d, (60, y), "✓", int(30 * pop(t, tk)), (90, 220, 110, A), 0)
                texto(d, (100, y + 2), s, 24, (255, 255, 255, A), 0)
    # M / N
    selo(d, t, 61.1, 63.5, "MANDA PRA QUEM", 170, (255, 255, 255), sub="só calibra no chutinho 👟".replace(" 👟", ""))
    a = aparece(t, 63.6, 66.3, ent=0.1)
    if a > 0:
        texto(d, (W * 0.8, 300), "?", int(150 * pop(t, 63.65)), (255, 215, 60, int(255 * a)), 8, "mm")
        texto(d, (W / 2, 820), "QUANDO FOI A ÚLTIMA VEZ?", 28, (255, 255, 255, int(255 * a)), 4, "ma")
    img = img.convert("RGBA")
    img.alpha_composite(o)
    return img.convert("RGB")


def whip(img, t):
    """Borrão direcional + leve zoom em ±0,12 s de cada troca rua ↔ raio-X."""
    dist = min(abs(t - c) for c in CORTES)
    if dist > 0.13:
        return img
    k = 1 - dist / 0.13
    a = np.asarray(img, np.float32)
    n = int(6 + 34 * k)
    acc = np.zeros_like(a)
    for s in range(0, n, 2):
        acc += np.roll(a, s - n // 2, axis=1)
    a = acc / len(range(0, n, 2))
    im = Image.fromarray(a.astype(np.uint8))
    z = 1 + 0.08 * k
    im = im.resize((int(W * z), int(H * z)), Image.BILINEAR)
    return im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))


if __name__ == "__main__":
    n = int(round(D * FPS))
    ult = None
    for i in range(n):
        f, t = i + 1, i / FPS
        p = os.path.join(AQUI, "_quadros", f"{f:04d}.png") if na_rua(t) else S("videos", "calibrar_pneu", "quadros", f"{f:04d}.png")
        if os.path.exists(p):
            ult = p
        im = Image.open(ult).convert("RGB")
        if im.size != (W, H):
            im = im.resize((W, H), Image.LANCZOS)
        hud(whip(im, t), t).save(os.path.join(SAIDA, f"{i:04d}.png"))
    sons = [  # (arquivo, início, volume, duração máx)
        (S("assets/sons/carro/Car_Engine_Loop.ogg"), 0.0, 0.35, 5.9),
        (S("biblioteca_sons/impacto_grave/hit.wav"), 5.8, 0.45, 0.6),
        (S("assets/sons/carro/Car_Engine_Turning_Off.ogg"), 6.4, 0.4, 1.4),
        (S("assets/sons/carro/Car_Door_Close.ogg"), 7.45, 0.55, 1.2),
        (S("biblioteca_sons/aparecer/pop.ogg"), 7.84, 0.5, 1.0),
        (S("biblioteca_sons/impacto_grave/hit.wav"), 9.86, 0.9, 1.0),
        (S("biblioteca_sons/aparecer/pop.ogg"), 11.2, 0.5, 1.0),
    ]
    for c in CORTES:
        sons.append((S("biblioteca_sons/transicao/wind1.wav"), c - 0.15, 0.35, 0.6))
    for tp in (33.6, 36.4, 37.7, 46.8, 54.6, 56.0, 57.7, 60.0, 61.1, 63.6):
        sons.append((S("biblioteca_sons/aparecer/pop.ogg"), tp, 0.45, 0.8))
    cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(SAIDA, "%04d.png"),
           "-i", S("videos/calibrar_pneu/narracao.wav")]
    fc = []
    for k, (f, t0, v, dur) in enumerate(sons):
        cmd += ["-i", f]
        ms = int(t0 * 1000)
        fc.append(f"[{k + 2}:a]atrim=0:{dur},afade=t=out:st={max(dur - 0.3, 0)}:d=0.3,volume={v},adelay={ms}|{ms}[s{k}]")
    fc.append("[1:a]asplit=2[nar][chave]")
    fc.append("".join(f"[s{k}]" for k in range(len(sons))) + f"amix=inputs={len(sons)}:normalize=0,volume=0.6[sfx]")
    fc.append("[sfx][chave]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=250[sfxd]")
    fc.append(f"[nar][sfxd]amix=inputs=2:normalize=0,atrim=0:{D},loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    os.makedirs(os.path.join(AQUI, "saida"), exist_ok=True)
    cmd += ["-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "19", "-c:a", "aac", "-b:a", "192k", os.path.join(AQUI, "saida", "calibrar_pneu_jogo.mp4")]
    subprocess.run(cmd, check=True)
    print("ok")
