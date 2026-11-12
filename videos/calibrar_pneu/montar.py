"""Montagem final do vídeo 02 (calibrar o pneu): textos HUD do estilo adulto + efeitos + narração + transições.

Uso:  ~/.venv-video/bin/python videos/calibrar_pneu/montar.py [previa]
  1) gera efeitos.wav (efeitos sincronizados com palavras.json) e audio_final.wav (narração + efeitos);
  2) copia quadros/ → quadros_txt/ desenhando o título, os carimbos HUD e o "?" final;
  3) chama motor3d/transicoes.py (whip só na troca rua/oficina ↔ estúdio técnico) e gera o MP4 em saida/.
'previa' monta só com os quadros que já existem (os que faltam viram tela preta) — para acompanhar o render.
"""
import os, sys, json, shutil, subprocess, math
HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(RAIZ, "motor3d"))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sons as S

FPS = 24
T = json.load(open(os.path.join(HERE, "tempos.json")))
DUR = T["duracao"]
PL = T["planos"]
W = json.load(open(os.path.join(HERE, "palavras.json")))
FB = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
FM = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"


def tw(p, depois=0.0):
    for w, a, b in W:
        if a >= depois - 0.01 and w.lower().strip(",.?!").startswith(p):
            return a
    raise KeyError(p)


# ---------------------------------------------------------------- textos (só nos planos de encenação: os técnicos
# já têm o HUD próprio desenhado pelos seus scripts)
COR = {"problema": "#FF3B3B", "solucao": "#2BD576", "tempo": "#19C3E6", "objecao": "#9AA3AD"}
CARIMBOS = [
    {"t": tw("dinheiro"), "fim": PL["B_dinheiro"][1] - 0.1, "texto": "R$ NO ASFALTO", "tipo": "problema"},
    {"t": tw("chutinho") + 0.15, "fim": tw("chutinho") + 1.0, "texto": "TUM!", "tipo": "tempo"},
    {"t": tw("tá", 10.0), "fim": tw("segue") + 0.2, "texto": "\"TÁ BOM AINDA\"", "tipo": "objecao"},
    {"t": tw("troca", 33), "fim": tw("barato") - 0.4, "texto": "PNEU ANTES DA HORA", "tipo": "problema"},
    {"t": tw("barato") - 0.3, "fim": PL["H_resultado"][1] - 0.1, "texto": "PNEU RUIM?", "tipo": "objecao"},
    {"t": tw("ah", 37), "fim": PL["I_posto"][1] - 0.1, "texto": "AH, MAS…", "tipo": "objecao"},
    {"t": tw("certo", 53), "fim": tw("vez", 54) - 0.05, "texto": "O CERTO", "tipo": "solucao"},
    {"t": tw("vez", 54), "fim": tw("calibra", 56) - 0.1, "texto": "1x POR MÊS · FRIO", "tipo": "solucao"},
    {"t": tw("plaquinha"), "fim": tw("não", 59) - 0.1, "texto": "PLAQUINHA DA PORTA", "tipo": "solucao"},
    {"t": tw("step") - 0.2, "fim": PL["L_certo"][1] - 0.05, "texto": "+ ESTEPE", "tipo": "solucao"},
    {"t": tw("manda"), "fim": PL["M_manda"][1] - 0.05, "texto": "MANDA PRA QUEM CALIBRA NO CHUTINHO", "tipo": "tempo",
     "px": 0.042},
]
TITULO = (0.15, PL["A_gancho"][1] - 0.05)
INTERROG = (PL["N_final"][0] + 0.25, DUR)


def _f(px, f=FB):
    return ImageFont.truetype(f, int(px))


def _entrada(t, t0, t1, d=0.18):
    """0..1: entra deslizando em d s, sai em 0,12 s."""
    if t < t0 or t > t1:
        return 0.0
    a = min(1.0, (t - t0) / d)
    b = min(1.0, (t1 - t) / 0.12)
    e = 1 - (1 - a) ** 3
    return max(0.0, min(e, b))


def _pilula(txt, tipo, Wimg, px=0.052):
    f = _f(Wimg * px)
    x0, y0, x1, y1 = f.getbbox(txt)
    padx, pady, barra = int(Wimg * 0.035), int(Wimg * 0.022), int(Wimg * 0.014)
    w, h = x1 - x0 + 2 * padx + barra, y1 - y0 + 2 * pady
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(h * 0.18), fill=(14, 17, 22, 215))
    d.rectangle([0, 0, barra, h - 1], fill=COR[tipo])
    d.text((barra + padx - x0, pady - y0), txt, font=f, fill="#FFFFFF")
    return im


def desenhar(img, t):
    Wi, Hi = img.size
    out = img.convert("RGBA")
    # título "VOCÊ FAZ ISSO?" (barra laranja + etiqueta técnica)
    e = _entrada(t, *TITULO, d=0.25)
    if e > 0:
        f, fs = _f(Wi * 0.11), _f(Wi * 0.03, FM)
        lay = Image.new("RGBA", out.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        x = int(Wi * 0.07 - (1 - e) * Wi * 0.2)
        y = int(Hi * 0.085)
        d.text((x, y), "01 / PNEU", font=fs, fill=(25, 195, 230, int(255 * e)))
        for k, linha in enumerate(("VOCÊ FAZ", "ISSO?")):
            yy = y + int(Wi * 0.05) + k * int(Wi * 0.12)
            d.text((x + 3, yy + 4), linha, font=f, fill=(0, 0, 0, int(110 * e)))
            d.text((x, yy), linha, font=f, fill=(255, 255, 255, int(255 * e)))
        d.rectangle([x, y + int(Wi * 0.31), x + int(Wi * 0.3 * e), y + int(Wi * 0.322)], fill=(232, 89, 12, 255))
        out.alpha_composite(lay)
    # carimbos HUD
    for c in CARIMBOS:
        e = _entrada(t, c["t"], c["fim"])
        if e <= 0:
            continue
        p = _pilula(c["texto"], c["tipo"], Wi, c.get("px", 0.052))
        p.putalpha(p.getchannel("A").point(lambda v: int(v * e)))
        x = int(Wi / 2 - p.width / 2 + (1 - e) * Wi * 0.08)
        out.alpha_composite(p, (x, int(Hi * 0.17)))
    # "?" final
    e = _entrada(t, *INTERROG, d=0.22)
    if e > 0:
        f = _f(Wi * 0.36 * (0.85 + 0.15 * e))
        lay = Image.new("RGBA", out.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        x, y = int(Wi * 0.66), int(Hi * 0.04)
        d.text((x + 6, y + 8), "?", font=f, fill=(0, 0, 0, int(120 * e)))
        d.text((x, y), "?", font=f, fill=(232, 89, 12, int(255 * e)), stroke_width=int(Wi * 0.008),
               stroke_fill=(255, 255, 255, int(255 * e)))
        out.alpha_composite(lay)
    return out.convert("RGB")


# ---------------------------------------------------------------- efeitos (volumes moderados: a narração manda)
def efeitos(path):
    mx = S.Mix(DUR)
    sw = lambda: S.sample("transicao/wind1.wav", 0.0, 0.5, peak=0.6, fade=0.08)
    for t in (PL["C_olha_so"][0], PL["H_resultado"][0], PL["J_quente"][0], PL["L_certo"][0]):
        mx.put(t - 0.18, sw(), 0.35)
    for k in range(5):                                   # moedinhas tilintando
        mx.put(tw("dinheiro") + 0.15 + k * 0.17, S.ding(f=2400 + 300 * (k % 3), vol=0.2), 0.35)
    mx.put(tw("chutinho") + 0.12, S.sample("impacto_grave/hit.wav", 0, 0.6, peak=0.8), 0.7)       # TUM
    mx.put(tw("perde"), S.fades(S.norm(S.bandnoise(int(3.0 * S.SR), 2500, 7000), 0.25), 0.4, 0.8), 0.25)  # ar
    mx.put(tw("achata"), S.sample("arrasto/scrape2.wav", 0, 0.9, pitch=0.8, peak=0.5), 0.3)
    mx.put(tw("esquenta"), S.s_rumble(2.0, 0.4), 0.35)
    mx.put(tw("bebe"), S.sad(440, 300, 0.5), 0.3)
    mx.put(tw("barato"), S.sad(330, 220, 0.6), 0.35)
    mx.put(tw("estufa"), S.rise_tone(0.8, 160, 420), 0.25)
    mx.put(tw("esfria"), S.sad(420, 200, 0.7), 0.3)
    mx.put(tw("máximo"), S.beeps(0.9, 1050, 0.3), 0.18)
    mx.put(tw("plaquinha") + 0.1, S.chime(), 0.35)
    mx.put(tw("step") + 0.05, S.ding(1320, 0.3), 0.4)
    mx.put(INTERROG[0], S.s_pop(1.0), 0.5)
    mx.save(path, peak=0.5)


def mix_final(efx, narr, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", narr, "-i", efx, "-filter_complex",
                    "[0:a]aresample=44100,pan=stereo|c0=c0|c1=c0,volume=1.0[n];[1:a]volume=0.55[e];"
                    "[n][e]amix=inputs=2:normalize=0:duration=longest,alimiter=limit=0.95,"
                    f"atrim=0:{DUR}", "-ar", "44100", out], check=True)


if __name__ == "__main__":
    previa = "previa" in sys.argv
    efx, aud = os.path.join(HERE, "efeitos.wav"), os.path.join(HERE, "audio_final.wav")
    efeitos(efx)
    mix_final(efx, os.path.join(HERE, "narracao.wav"), aud)
    src, dst = os.path.join(HERE, "quadros"), os.path.join(HERE, "quadros_txt")
    os.makedirs(dst, exist_ok=True)
    n = int(round(DUR * FPS))
    preto = None
    for g in range(1, n + 1):
        p = os.path.join(src, f"{g:04d}.png")
        if os.path.exists(p):
            img = Image.open(p).convert("RGB")
        elif previa:
            preto = preto or Image.new("RGB", (576, 1024), (12, 14, 18))
            img = preto
        else:
            raise SystemExit(f"falta o quadro {g} — rode os planos ou use 'previa'")
        desenhar(img, (g - 1) / FPS).save(os.path.join(dst, f"{g:04d}.png"))
    cortes = {"fps": FPS, "duracao": DUR, "transicoes": [PL["H_resultado"][0], PL["J_quente"][0], PL["L_certo"][0]]}
    cj = os.path.join(HERE, "cortes.json")
    json.dump(cortes, open(cj, "w"), indent=1)
    saida = os.path.join(HERE, "saida")
    subprocess.run([sys.executable, os.path.join(RAIZ, "motor3d", "transicoes.py"), dst, cj, saida, "calibrar_pneu",
                    aud], check=True)
    print("pronto:", saida)
