"""Prova do estilo "EXPLICATIVO TÉCNICO 3D" (direção B): cena de mecanismo invisível.

Gera 2 quadros 9:16 nesta pasta:
  tecnico_pneu.png  -> dois pneus em corte, CALIBRADO x MURCHO, com callouts
  tecnico_motor.png -> motor monocilíndrico em corte, pistão no meio do curso, óleo âmbar no cárter

Uso:  ~/.venv-video/bin/python videos/_estilo4/mecanismo_prova.py [pneu|motor|tudo] [escala] [amostras]
      escala 0.5 = prévia em 540x960.
Os textos (callouts, títulos) são desenhados em pós com PIL sobre o render.
"""
import os, sys, time, math
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "motor3d"))
import bpy
import tecnico as tc
from PIL import Image, ImageDraw, ImageFont

FONTE = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FONTE_MED = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
FONTE_BLACK = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
CALLOUTS = os.environ.get("SEM_CALLOUTS") is None


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ------------------------------------------------------------ texto em pós (HUD técnico)
class HUD:
    def __init__(self, caminho):
        self.img = Image.open(caminho).convert("RGBA")
        self.W, self.H = self.img.size
        self.k = self.W / 1080
        self.camada = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.camada)

    def fonte(self, tam, arq=FONTE):
        return ImageFont.truetype(arq, int(tam * self.k))

    def texto(self, xy, txt, tam=34, cor="#FFFFFF", ancora="ls", espaco=0.06, arq=FONTE, alpha=255):
        """Texto com espaçamento entre letras (tracking)."""
        f = self.fonte(tam, arq)
        trk = tam * espaco * self.k
        larg = sum(f.getlength(c) for c in txt) + trk * (len(txt) - 1)
        x, y = xy
        if ancora[0] == "r":
            x -= larg
        elif ancora[0] == "m":
            x -= larg / 2
        for c in txt:
            self.d.text((x, y), c, font=f, fill=rgb(cor) + (alpha,), anchor="l" + ancora[1])
            x += f.getlength(c) + trk
        return larg

    def etiqueta(self, ini, fim, titulo, sub=None, cor=tc.CIANO, tam=36):
        """Texto em cima do trecho horizontal do callout (ini = cotovelo, fim = ponta)."""
        (x0, y0), (x1, y1) = ini, fim
        x = min(x0, x1) + 5 * self.k
        anc = "l"
        self.texto((x, y1 - 14 * self.k), titulo, tam, "#FFFFFF", anc + "s")
        if sub:
            self.texto((x, y1 + 30 * self.k), sub, tam * 0.58, cor, anc + "s", espaco=0.10, arq=FONTE_MED)

    def caixa_tag(self, xy, txt, cor, tam=30, ancora="m"):
        f = self.fonte(tam, FONTE_BLACK)
        trk = tam * 0.12 * self.k
        larg = sum(f.getlength(c) for c in txt) + trk * (len(txt) - 1)
        px, py = 18 * self.k, 12 * self.k
        x, y = xy
        if ancora == "m":
            x -= larg / 2
        hgt = tam * self.k * 0.74
        self.d.rectangle([x - px, y - hgt - py, x + larg + px, y + py], fill=rgb(cor) + (255,))
        xx = x
        for c in txt:
            self.d.text((xx, y), c, font=f, fill=rgb("#0E1115") + (255,), anchor="ls")
            xx += f.getlength(c) + trk

    def cantos(self, margem=54, comp=46, cor="#3A4452", esp=3):
        k = self.k
        m, c, e = margem * k, comp * k, max(1, int(esp * k))
        W, H = self.W, self.H
        for (x, y, sx, sy) in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
            self.d.line([(x, y), (x + sx * c, y)], fill=rgb(cor) + (255,), width=e)
            self.d.line([(x, y), (x, y + sy * c)], fill=rgb(cor) + (255,), width=e)

    def cabecalho(self, rotulo, indice):
        k = self.k
        y = 150 * k
        self.texto((84 * k, y), indice, 24, tc.CIANO, "ls", espaco=0.18, arq=FONTE_MED)
        self.d.line([(84 * k, y + 18 * k), (84 * k + 60 * k, y + 18 * k)], fill=rgb(tc.CIANO) + (255,), width=max(1, int(3 * k)))
        self.texto((84 * k, y + 70 * k), rotulo, 30, "#DDE3EA", "ls", espaco=0.16, arq=FONTE)

    def salvar(self, caminho):
        Image.alpha_composite(self.img, self.camada).convert("RGB").save(caminho, optimize=True)


def p2(p):
    return tc.projetar(p)


# ------------------------------------------------------------ (a) pneu
def larg_txt(txt, tam, arq=FONTE, espaco=0.06):
    f = ImageFont.truetype(arq, tam)
    return sum(f.getlength(c) for c in txt) + tam * espaco * (len(txt) - 1)


def chamada(ancora, cam, cot, titulo, sub, cor, escala, tam=34):
    """Callout diagramado em px (base 1080): cotovelo 'cot'; o trecho horizontal tem a largura do texto e vai
    para o lado do sinal de cot[2] (-1 = esquerda, +1 = direita)."""
    w = max(larg_txt(titulo, tam), larg_txt(sub or "", int(tam * 0.58), FONTE_MED, 0.10)) + 10
    x, y, lado = cot
    c = tc.callout_tela(ancora, cam, (x * escala, y * escala), (x + lado * w) * escala, cor=cor,
                        espessura=0.0022, bolinha=0.0075, nome="c_" + titulo[:6])
    c.update(titulo=titulo, sub=sub, cor=cor, tam=tam)
    return c


def cena_pneu(escala, amostras):
    tc.nova_cena(res=(int(1080 * escala), int(1920 * escala)), amostras=amostras)
    tc.estudio_tecnico(alvo=(0, 0, 0.32), luz=1.0)
    yaw = -24
    cal = tc.pneu_corte("calibrado", loc=(-0.31, 0.0, 0.0), yaw=yaw, pressao=1.0, cor_pegada=tc.VERDE)
    mur = tc.pneu_corte("murcho", loc=(0.31, 0.0, 0.0), yaw=yaw, pressao=0.40, cor_pegada=tc.VERMELHO)
    alvo = (0.0, 0.0, 0.40)
    cam = tc.camera((0, -5.4, 1.6), alvo, lente=70)
    tc.orbita(cam, alvo, 5.4, 0.0, 1.6)
    bpy.context.view_layer.update()
    co = []
    if CALLOUTS:
        co.append(chamada(cal["ancoras"]["cintas"], cam, (300, 655, 1), "CINTAS DE AÇO", None, tc.CIANO, escala, 30))
        co.append(chamada(cal["ancoras"]["ar"], cam, (470, 745, 1), "AR", "SEGURA O PESO", tc.CIANO, escala, 30))
        co.append(chamada(cal["ancoras"]["pegada"], cam, (300, 1500, -1), "PEGADA CERTA", "APOIO POR INTEIRO", tc.VERDE, escala))
        co.append(chamada(mur["ancoras"]["flanco"], cam, (1000, 1385, -1), "FLANCO DOBRADO", "ESQUENTA", tc.LARANJA, escala))
        co.append(chamada(mur["ancoras"]["pegada"], cam, (765, 1530, 1), "PEGADA LARGA", "GASTA OS OMBROS", tc.VERMELHO, escala))
    return cal, mur, co


def pos_pneu(caminho, cal, mur, co):
    h = HUD(caminho)
    h.cantos()
    h.cabecalho("PNEU EM CORTE", "01 / PRESSÃO")
    for p, txt, cor, sub in ((cal, "CALIBRADO", tc.VERDE, "PRESSÃO DO MANUAL"),
                             (mur, "MURCHO", tc.VERMELHO, "PRESSÃO BAIXA")):
        x, _ = p2(p["ancoras"]["topo"])
        y = 470 * h.k
        h.caixa_tag((x, y), txt, cor, 34)
        h.texto((x, y + 50 * h.k), sub, 20, "#9AA6B4", "ms", espaco=0.14, arq=FONTE_MED)
    for c in co:
        h.etiqueta(p2(c["cotovelo"]), p2(c["fim"]), c["titulo"], c["sub"], c["cor"], tam=c["tam"])
    h.salvar(caminho)


# ------------------------------------------------------------ (b) motor
def cena_motor(escala, amostras):
    tc.nova_cena(res=(int(1080 * escala), int(1920 * escala)), amostras=amostras)
    tc.estudio_tecnico(alvo=(0, 0, 0.25), luz=0.55)
    mt = tc.motor_corte("motor", loc=(0, 0, 0), yaw=-24, ang_vira=80)
    alvo = (0.0, 0.0, 0.245)
    cam = tc.camera((0, -2.2, 0.6), alvo, lente=85)
    tc.orbita(cam, alvo, 2.25, 0.0, 0.62)
    bpy.context.view_layer.update()
    co = {}
    co["aneis"] = tc.callout(mt["ancoras"]["aneis"], cam, dx=-0.11, dy=0.10, compr=0.09, espessura=0.0009,
                             bolinha=0.0035, nome="c_aneis")
    co["oleo"] = tc.callout(mt["ancoras"]["oleo"], cam, dx=0.09, dy=-0.07, compr=0.08, cor=tc.CIANO,
                            espessura=0.0009, bolinha=0.0035, nome="c_oleo")
    return mt, co


def pos_motor(caminho, mt, co):
    h = HUD(caminho)
    h.cantos()
    h.cabecalho("MOTOR EM CORTE", "02 / LUBRIFICAÇÃO")
    rot = {"aneis": ("ANÉIS", "VEDAM O CILINDRO"), "oleo": ("ÓLEO", "LUBRIFICA E ESFRIA")}
    for k, c in co.items():
        t, s = rot[k]
        h.etiqueta(p2(c["cotovelo"]), p2(c["fim"]), t, s, tc.CIANO, tam=40)
    h.salvar(caminho)


if __name__ == "__main__":
    args = [a for a in sys.argv[sys.argv.index("--") + 1:]] if "--" in sys.argv else sys.argv[1:]
    qual = args[0] if args else "tudo"
    escala = float(args[1]) if len(args) > 1 else 1.0
    amostras = int(args[2]) if len(args) > 2 else 48
    if qual in ("pneu", "tudo"):
        t0 = time.time()
        cal, mur, co = cena_pneu(escala, amostras)
        t1 = time.time()
        out = os.path.join(AQUI, "tecnico_pneu.png")
        tc.render(out)
        t2 = time.time()
        pos_pneu(out, cal, mur, co)
        print(f"PNEU: montagem {t1 - t0:.1f}s, render {t2 - t1:.1f}s; pegada calibrado {cal['pegada']}, murcho {mur['pegada']}")
    if qual in ("motor", "tudo"):
        t0 = time.time()
        mt, co = cena_motor(escala, amostras)
        t1 = time.time()
        out = os.path.join(AQUI, "tecnico_motor.png")
        tc.render(out)
        t2 = time.time()
        pos_motor(out, mt, co)
        print(f"MOTOR: montagem {t1 - t0:.1f}s, render {t2 - t1:.1f}s")
