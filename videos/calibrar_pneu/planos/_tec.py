"""Apoio dos planos TÉCNICOS (estúdio escuro de montadora) do vídeo 02: cena, câmera e HUD em pós.

O HUD (callouts, contadores, mostradores) é desenhado com PIL DEPOIS de cada quadro ser gravado
(handler render_write), projetando os pontos 3D com a câmera daquele quadro: acompanha a câmera e a animação
e funciona igual em `teste t1 t2` e no render completo do comum.renderizar.

    import _tec as T
    sc = T.setup(P)                         # comum.setup + estúdio técnico
    T.hud(lambda h, t: ...)                 # desenho do HUD por quadro (t = tempo local em s)
"""
import os, sys, math
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, ".."))
import comum as C
import bpy
import numpy as np
from mathutils import Vector
import tecnico as tc
from PIL import Image, ImageDraw, ImageFont

FONTE = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FONTE_MED = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
FONTE_BLACK = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp(a, b, t):
    return a + (b - a) * t


def suave(t, t0, t1):
    x = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    return x * x * (3 - 2 * x)


# ------------------------------------------------------------ cena
def setup(P, luz=1.0, alvo=(0, 0, 0.32)):
    sc = C.setup(P)
    tc._MATS.clear()
    c = sc.cycles
    c.glossy_bounces = 2
    c.diffuse_bounces = 1
    c.transparent_max_bounces = 8
    c.adaptive_threshold = 0.04
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    w = sc.world or bpy.data.worlds.new("mundo")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = tc.lin(tc.GRAFITE_ESC)
    bg.inputs[1].default_value = 0.12
    tc.estudio_tecnico(alvo=alvo, luz=luz)
    return sc


def camera(loc, alvo, lente=70):
    cam = tc.camera(loc, alvo, lente=lente)
    return cam


def cam_key(cam, t, loc, alvo, lente=None):
    """Keyframe de câmera (posição + mira + lente) no tempo local t."""
    cam.location = loc
    tc.mirar(cam, alvo)
    cam.keyframe_insert("location", frame=C.F(t))
    cam.keyframe_insert("rotation_euler", frame=C.F(t))
    if lente:
        cam.data.lens = lente
        cam.data.keyframe_insert("lens", frame=C.F(t))


def key_no(socket, t, v):
    socket.default_value = v
    socket.keyframe_insert("default_value", frame=C.F(t))


def linear(idblocks):
    """Interpolação linear em todas as curvas dos datablocks dados (objetos, materiais, shape keys)."""
    for idb in idblocks:
        for ad in (getattr(idb, "animation_data", None),):
            if not ad or not ad.action:
                continue
            for fc in _fcurves(ad.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"


def _fcurves(action):
    if hasattr(action, "fcurves") and len(action.fcurves):
        return list(action.fcurves)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for cb in getattr(strip, "channelbags", []):
                out += list(cb.fcurves)
    return out


def mat_mix_emissivo(c1, c2, forca=4.0, alpha=1.0, nome="emis_mix"):
    """Emissivo com nó Value 'mix' (0 = c1, 1 = c2) animável."""
    m = tc.mat_emissivo(c1, forca, nome, alpha)
    nt = m.node_tree
    em = [n for n in nt.nodes if n.type == "EMISSION"][0]
    v = nt.nodes.new("ShaderNodeValue"); v.name = v.label = "mix"
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"
    tc._sock(mx, "A").default_value = tc.lin(c1)
    tc._sock(mx, "B").default_value = tc.lin(c2)
    nt.links.new(v.outputs[0], tc._sock(mx, "Factor", "VALUE"))
    nt.links.new([o for o in mx.outputs if o.type == "RGBA"][0], em.inputs["Color"])
    return m


# ------------------------------------------------------------ HUD em pós
class HUD:
    def __init__(self, caminho):
        self.img = Image.open(caminho).convert("RGBA")
        self.W, self.H = self.img.size
        self.k = self.W / 1080
        self.camada = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.camada)

    def px(self, p3):
        return tc.projetar(p3)

    def fonte(self, tam, arq=FONTE):
        return ImageFont.truetype(arq, max(6, int(tam * self.k)))

    def largura(self, txt, tam, arq=FONTE, espaco=0.06):
        f = self.fonte(tam, arq)
        return sum(f.getlength(c) for c in txt) + tam * self.k * espaco * (len(txt) - 1)

    def texto(self, xy, txt, tam=34, cor="#FFFFFF", ancora="ls", espaco=0.06, arq=FONTE, alpha=255):
        f = self.fonte(tam, arq)
        trk = tam * espaco * self.k
        larg = self.largura(txt, tam, arq, espaco)
        x, y = xy
        if ancora[0] == "r":
            x -= larg
        elif ancora[0] == "m":
            x -= larg / 2
        for ch in txt:
            self.d.text((x, y), ch, font=f, fill=rgb(cor) + (int(alpha),), anchor="l" + ancora[1])
            x += f.getlength(ch) + trk
        return larg

    def linha(self, pts, cor, esp=2.4, alpha=255):
        self.d.line(pts, fill=rgb(cor) + (int(alpha),), width=max(1, int(round(esp * self.k))), joint="curve")

    def callout(self, ancora3d, cot, titulo, sub=None, cor=tc.CIANO, lado=-1, tam=34, alpha=1.0, crescer=1.0):
        """Callout 2D: bolinha na âncora projetada -> cotovelo (px base 1080) -> trecho horizontal do tamanho do
        texto (lado -1 = esquerda, +1 = direita). crescer (0..1) desenha a linha aos poucos (entrada)."""
        if alpha <= 0.01 or crescer <= 0.0:
            return
        k = self.k
        ax, ay = self.px(ancora3d)
        cx, cy = cot[0] * k, cot[1] * k
        w = max(self.largura(titulo, tam), self.largura(sub or "", tam * 0.62, FONTE_MED, 0.10)) + 40 * k
        fx = cx + lado * w
        A = int(255 * alpha)
        r = 7 * k
        self.d.ellipse([ax - r, ay - r, ax + r, ay + r], fill=rgb(cor) + (A,))
        r2 = 14 * k
        self.d.ellipse([ax - r2, ay - r2, ax + r2, ay + r2], outline=rgb(cor) + (A,), width=max(1, int(2 * k)))
        c1 = min(1.0, crescer * 2)
        c2 = max(0.0, crescer * 2 - 1)
        mx, my = ax + (cx - ax) * c1, ay + (cy - ay) * c1
        self.linha([(ax, ay), (mx, my)], cor, alpha=A)
        if c2 > 0:
            self.linha([(cx, cy), (cx + (fx - cx) * c2, cy)], cor, alpha=A)
        if crescer >= 0.999:
            x = fx + 2 * k if lado < 0 else cx + 30 * k
            self.texto((x, cy - 13 * k), titulo, tam, "#FFFFFF", "ls", alpha=A)
            if sub:
                self.texto((x, cy + 32 * k), sub, tam * 0.62, cor, "ls", espaco=0.10, arq=FONTE_MED, alpha=A)

    def tag(self, xy, txt, cor, tam=30, ancora="m", alpha=1.0, cor_txt="#0E1115"):
        if alpha <= 0.01:
            return
        f = self.fonte(tam, FONTE_BLACK)
        k = self.k
        trk = tam * 0.12 * k
        larg = sum(f.getlength(c) for c in txt) + trk * (len(txt) - 1)
        px_, py_ = 18 * k, 12 * k
        x, y = xy[0] * k, xy[1] * k
        if ancora == "m":
            x -= larg / 2
        elif ancora == "r":
            x -= larg
        hgt = tam * k * 0.74
        A = int(255 * alpha)
        self.d.rectangle([x - px_, y - hgt - py_, x + larg + px_, y + py_], fill=rgb(cor) + (A,))
        for ch in txt:
            self.d.text((x, y), ch, font=f, fill=rgb(cor_txt) + (A,), anchor="ls")
            x += f.getlength(ch) + trk

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
        self.d.line([(84 * k, y + 18 * k), (144 * k, y + 18 * k)], fill=rgb(tc.CIANO) + (255,), width=max(1, int(3 * k)))
        self.texto((84 * k, y + 70 * k), rotulo, 30, "#DDE3EA", "ls", espaco=0.16)

    def vinheta(self, forca=0.38):
        W, H = self.W, self.H
        y, x = np.mgrid[0:H, 0:W]
        r = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H * 0.55) / (H * 0.62)) ** 2)
        a = (np.clip((r - 0.55) / 0.6, 0, 1) ** 1.6 * forca * 255).astype("uint8")
        v = Image.new("RGBA", (W, H), (6, 8, 11, 0))
        v.putalpha(Image.fromarray(a))
        self.img = Image.alpha_composite(self.img, v)

    def salvar(self, caminho):
        self.vinheta()
        Image.alpha_composite(self.img, self.camada).convert("RGB").save(caminho)


_DESENHOS = []


def hud(func):
    """Registra o desenho do HUD (func(h, t_local)) para todo quadro gravado."""
    _DESENHOS.append(func)
    if _ao_gravar not in bpy.app.handlers.render_write:
        bpy.app.handlers.render_write.append(_ao_gravar)
    return func


def _ao_gravar(scene, *_):
    caminho = bpy.path.abspath(scene.render.filepath)
    if not os.path.exists(caminho):
        return
    t = (scene.frame_current - 1) / C.FPS
    h = HUD(caminho)
    for f in _DESENHOS:
        f(h, t)
    h.salvar(caminho)


def a_cada_quadro(func):
    """func(t_local) chamada antes de cada quadro (posições procedurais: moléculas, bolinhas)."""
    def _h(scene, *_):
        func((scene.frame_current - 1) / C.FPS)
    bpy.app.handlers.frame_change_pre.append(_h)
    return func


def vert_mundo(ob, idx):
    """Posição de mundo do vértice idx considerando shape keys (valor atual)."""
    me = ob.data
    co = Vector(me.vertices[idx].co)
    if me.shape_keys:
        base = me.shape_keys.key_blocks[0]
        co = Vector(base.data[idx].co)
        for kb in me.shape_keys.key_blocks[1:]:
            co += (Vector(kb.data[idx].co) - Vector(base.data[idx].co)) * kb.value
    return ob.matrix_world @ co


def idx_pneu(D, k_anel, i_perfil):
    """Índice do vértice na malha da borracha: anel k (ângulo), ponto i do perfil EXTERNO."""
    n = D["perfil"]["n"]
    return k_anel * 2 * n + i_perfil


def i_perfil(D, a_alvo=None, tn_alvo=None, lado=1):
    pf = D["perfil"]
    a0, r0 = pf["a0"], pf["r0"]
    tn = (r0 - pf["rb"]) / (pf["R"] - pf["rb"])
    ids = np.where(a0 * lado > 0)[0]
    if a_alvo is not None:
        return int(ids[np.argmin(np.abs(a0[ids] - a_alvo))])
    return int(ids[np.argmin(np.abs(tn[ids] - tn_alvo))])


def seta(h, p0, p1, cor, esp=4, cab=22, alpha=255):
    """Seta 2D de p0 até p1 (px)."""
    k = h.k
    x0, y0 = p0; x1, y1 = p1
    h.linha([(x0, y0), (x1, y1)], cor, esp, alpha)
    ang = math.atan2(y1 - y0, x1 - x0)
    c = cab * k
    pts = [(x1, y1), (x1 - c * math.cos(ang - 0.45), y1 - c * math.sin(ang - 0.45)),
           (x1 - c * math.cos(ang + 0.45), y1 - c * math.sin(ang + 0.45))]
    h.d.polygon(pts, fill=rgb(cor) + (int(alpha),))


# ------------------------------------------------------------ sincronia com a narração (palavras.json)
def _norm(w):
    import unicodedata
    w = unicodedata.normalize("NFD", w.lower())
    return "".join(c for c in w if c.isalnum())


def palavra(P, frase, fim=False, padrao=None):
    """Tempo LOCAL (s) em que 'frase' começa (ou termina, fim=True) dentro do plano, lido de palavras.json.
    Procura a sequência de palavras na janela do plano (com 0,6 s de folga). Sem achar: 'padrao' (fração da
    duração) ou None."""
    import json
    with open(os.path.join(C.HERE, "palavras.json")) as f:
        W = json.load(f)
    alvo = [_norm(x) for x in frase.split()]
    for i in range(len(W) - len(alvo) + 1):
        if W[i][1] < P["ini"] - 0.6 or W[i][1] > P["fim"] + 0.6:
            continue
        if all(_norm(W[i + j][0]) == alvo[j] for j in range(len(alvo))):
            t = W[i + len(alvo) - 1][2] if fim else W[i][1]
            return max(0.0, min(P["dur"], t - P["ini"]))
    print(f"[aviso] '{frase}' não achada em {P['nome']}", flush=True)
    return None if padrao is None else padrao * P["dur"]
