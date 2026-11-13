"""Filtro de desenho + HUD de jogo (nosso) + som → teste_terceira.mp4.  Uso: python montar.py"""
import os, math, subprocess, glob
from PIL import Image, ImageDraw, ImageFont
from desenho import desenho

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
FPS, W, H, D, T_AUDIO = 24, 576, 1024, 10.0, 2.0
T_DIN0, T_DIN1 = 5.76 - 2, 7.2 - 2              # "deixando dinheiro no asfalto"
T_CORTE, T_TUM, T_OMB, T_SAI = 5.74, 7.9, 8.14, 9.1
FB = os.path.join(RAIZ, "assets", "fontes")
fonte = lambda s: ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Black.otf", s)
V2 = os.environ.get("V2") == "1"
SAIDA = os.path.join(AQUI, "_final2" if V2 else "_final")
os.makedirs(SAIDA, exist_ok=True)


def caixa(d, xy, r=10, fill=(15, 18, 24, 190), outline=None, w=2):
    d.rounded_rectangle(xy, r, fill=fill, outline=outline, width=w)


def texto(d, xy, s, tam, cor=(255, 255, 255), contorno=4, anc="la"):
    d.text(xy, s, font=fonte(tam), fill=cor, stroke_width=contorno, stroke_fill=(10, 10, 12), anchor=anc)


def hud(img, t):
    o = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    # --- bolso (barra de dinheiro) no canto de cima, esquerda
    nivel = 1.0 - 0.45 * min(max((t - T_DIN0) / (T_DIN1 - T_DIN0), 0), 1)
    caixa(d, (18, 40, 250, 100))
    texto(d, (32, 50), "BOLSO", 20, (190, 230, 190), 0)
    d.rounded_rectangle((32, 76, 236, 90), 5, fill=(40, 45, 50, 255))
    cor = (70, 200, 90) if nivel > 0.7 else (235, 170, 40)
    d.rounded_rectangle((32, 76, 32 + 204 * nivel, 90), 5, fill=cor)
    # moedinhas "−R$" subindo enquanto o dinheiro vaza
    for k in range(5):
        tk = T_DIN0 + k * 0.3
        if tk < t < tk + 0.8:
            u = (t - tk) / 0.8
            a = int(255 * (1 - u) ** 0.7)
            texto(d, (60 + k * 34, 120 + 40 * u), "−R$", 24, (255, 80, 70, a), 3)
    # --- pneu (pressão) no canto de cima, direita: sempre baixo, pisca
    caixa(d, (W - 200, 40, W - 18, 100))
    texto(d, (W - 186, 50), "PNEU", 20, (230, 230, 230), 0)
    pisca = (int(t * 3) % 2 == 0)
    d.rounded_rectangle((W - 186, 76, W - 32, 90), 5, fill=(40, 45, 50, 255))
    d.rounded_rectangle((W - 186, 76, W - 186 + 154 * 0.32, 90), 5, fill=(235, 60, 50) if pisca else (150, 40, 35))
    if pisca:
        texto(d, (W - 74, 47), "⚠", 26, (255, 200, 40), 0)
    # --- piada: estacionou na calçada
    if V2 and 4.3 < t < 5.7:
        u = min((t - 4.3) / 0.15, 1)
        caixa(d, (60, 300, W - 60, 372), 12, fill=(235, 170, 30, int(235 * u)), outline=(20, 20, 20, int(255 * u)), w=3)
        texto(d, (W / 2, 312), "⚠ ESTACIONOU NA CALÇADA", 27, (20, 20, 20, int(255 * u)), 0, "ma")
        texto(d, (W / 2, 344), "−R$ multa", 20, (120, 20, 20, int(255 * u)), 0, "ma")
    # --- missão
    if T_CORTE + 0.1 < t < T_TUM - 0.2:
        u = min((t - T_CORTE - 0.1) / 0.2, 1)
        caixa(d, (40, 170, W - 40, 250), 14, fill=(15, 18, 24, int(210 * u)), outline=(255, 190, 40, int(255 * u)), w=3)
        texto(d, (W / 2, 186), "MISSÃO", 22, (255, 190, 40, int(255 * u)), 0, "ma")
        texto(d, (W / 2, 212), "CHECAR O PNEU", 30, (255, 255, 255, int(255 * u)), 3, "ma")
    if T_TUM - 0.05 < t < T_TUM + 0.6:
        s = 1 + 0.25 * math.exp(-(t - T_TUM) * 10)
        texto(d, (W * 0.62, 640), "TUM!", int(64 * s), (255, 215, 60), 6, "mm")
    if t > T_SAI + 0.1:
        u = min((t - T_SAI - 0.1) / 0.15, 1)
        caixa(d, (40, 170, W - 40, 262), 14, fill=(120, 20, 20, int(220 * u)), outline=(255, 255, 255, int(255 * u)), w=3)
        texto(d, (W / 2, 184), "✗ MISSÃO FALHOU", 34, (255, 255, 255, int(255 * u)), 3, "ma")
        texto(d, (W / 2, 228), "chute não mede pressão", 22, (255, 220, 220, int(255 * u)), 0, "ma")
    img = img.convert("RGBA")
    img.alpha_composite(o)
    return img.convert("RGB")


PASTA = "_quadros2" if V2 else "_quadros"
n = int(D * FPS)
ult = None
for i in range(n):
    p = os.path.join(AQUI, PASTA, f"{i + 1:04d}.png")
    if os.path.exists(p):
        ult = p
    im = Image.open(ult).convert("RGB") if V2 else desenho(Image.open(ult))
    hud(im, i / FPS).save(os.path.join(SAIDA, f"{i:04d}.png"))

S = lambda *p: os.path.join(RAIZ, *p)
sons = [  # (arquivo, início local, volume, duração máx)
    (S("assets/sons/carro/Car_Engine_Loop.ogg"), 0.0, 0.35, 4.6),
    (S("assets/sons/carro/Car_Engine_Turning_Off.ogg"), 4.4, 0.4, 2.0),
    (S("assets/sons/carro/Car_Door_Close.ogg"), 5.55, 0.6, 1.5),
    (S("biblioteca_sons/impacto_grave/hit.wav"), 3.9, 0.45, 0.6),
    (S("biblioteca_sons/aparecer/pop.ogg"), T_CORTE + 0.1, 0.5, 1.0),
    (S("biblioteca_sons/impacto_grave/hit.wav"), T_TUM - 0.02, 0.9, 1.0),
    (S("biblioteca_sons/aparecer/pop.ogg"), T_SAI + 0.1, 0.6, 1.0),
]
cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(SAIDA, "%04d.png"),
       "-ss", str(T_AUDIO), "-t", str(D), "-i", S("videos/calibrar_pneu/narracao.wav")]
fc = []
for k, (f, t0, v, dur) in enumerate(sons):
    cmd += ["-i", f]
    ms = int(t0 * 1000)
    fc.append(f"[{k + 2}:a]atrim=0:{dur},afade=t=out:st={max(dur - 0.3, 0)}:d=0.3,volume={v},adelay={ms}|{ms}[s{k}]")
# voz na frente: efeitos somados num bus, mais baixos, e "ducking" (abaixam sozinhos quando a voz fala)
fc.append("[1:a]volume=1.0,asplit=2[nar][chave]")
fc.append("".join(f"[s{k}]" for k in range(len(sons))) + f"amix=inputs={len(sons)}:normalize=0,volume=0.6[sfx]")
fc.append("[sfx][chave]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=250[sfxd]")
fc.append(f"[nar][sfxd]amix=inputs=2:normalize=0,atrim=0:{D},loudnorm=I=-14:TP=-1.5:LRA=11[a]")
cmd += ["-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "19", "-c:a", "aac", "-b:a", "192k", os.path.join(AQUI, "teste_terceira_v2.mp4" if V2 else "teste_terceira.mp4")]
subprocess.run(cmd, check=True)
print("ok")
