"""Carimbos de texto curtos sobre o vídeo (palavras-chave nos momentos importantes, como nas referências).

Não é título nem legenda: a legenda o usuário faz no CapCut. Use pouco (um carimbo a cada ~5 s no máximo).
Lista em <video>/carimbos.json:  [{"t": 28.97, "fim": 31.4, "texto": "1 MÊS DEPOIS", "tipo": "tempo"}, ...]
Tipos (código de cor do canal): "tempo" (branco sobre escuro, levemente torto), "problema" (branco sobre vermelho),
"solucao" (escuro sobre amarelo). Posição: ~20 % da altura, longe da legenda do CapCut (~70 %).
Aplicado pelo transicoes.py quando recebe o caminho do carimbos.json.
"""
import os, math
from PIL import Image, ImageDraw, ImageFont

FONTES = ["/usr/share/fonts/opentype/inter/Inter-Black.otf", "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
ESTILO = {"tempo": ("#ffffff", "#1d2333", -3), "problema": ("#ffffff", "#e53935", 0), "solucao": ("#1d2333", "#ffc928", 0)}
_cache = {}


def _fonte(px):
    if px not in _cache:
        path = next(f for f in FONTES if os.path.exists(f))
        _cache[px] = ImageFont.truetype(path, px)
    return _cache[px]


def _pilula(texto, tipo, W):
    cor, fundo, rot = ESTILO[tipo]
    f = _fonte(int(W * 0.068))
    x0, y0, x1, y1 = f.getbbox(texto)
    pw, ph = int(W * 0.045), int(W * 0.026)
    w, h = x1 - x0 + 2 * pw, y1 - y0 + 2 * ph
    im = Image.new("RGBA", (w + 12, h + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([6, 10, 6 + w, 10 + h], radius=h // 2, fill=(0, 0, 0, 90))          # sombra
    d.rounded_rectangle([6, 4, 6 + w, 4 + h], radius=h // 2, fill=fundo)
    d.text((6 + pw - x0, 4 + ph - y0), texto, font=f, fill=cor)
    return im.rotate(rot, resample=Image.BICUBIC, expand=True) if rot else im


def _escala(t, t0, t1):
    """Entrada com batida (0 → 1,15 → 1 em 0,22 s), saída encolhendo em 0,14 s."""
    a = t - t0
    if a < 0 or t > t1:
        return 0.0
    if a < 0.13:
        s = 1.15 * a / 0.13
    elif a < 0.22:
        s = 1.15 - 0.15 * (a - 0.13) / 0.09
    else:
        s = 1.0
    b = t1 - t
    if b < 0.14:
        s *= b / 0.14
    return s


def aplicar(img, t, lista):
    """Desenha os carimbos ativos no tempo t sobre a imagem (PIL RGB). Retorna a imagem (nova se mudou)."""
    ativos = [c for c in lista if c["t"] <= t <= c["fim"]]
    if not ativos:
        return img
    W, H = img.size
    out = img.convert("RGBA")
    for c in ativos:
        s = _escala(t, c["t"], c["fim"])
        if s <= 0.01:
            continue
        p = _pilula(c["texto"], c.get("tipo", "tempo"), W)
        p = p.resize((max(1, int(p.width * s)), max(1, int(p.height * s))), Image.BICUBIC)
        y = int(H * c.get("altura", 0.2))
        out.alpha_composite(p, (W // 2 - p.width // 2, y - p.height // 2))
    return out.convert("RGB")
