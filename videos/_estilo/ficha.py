"""Ficha de identidade visual do canal de veículos ("Oficina de bolso"): mascote Parafuso, carros e motos.

Uso:  ~/.venv-video/bin/python videos/_estilo/ficha.py [parafuso] [expr] [carros] [motos] [quadro] [ficha]
      (sem argumentos = tudo). Saídas nesta pasta (.png) e _tmp/ (renders crus).
"""
import sys, os, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "motor3d"))
import bpy
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont
import motor as mt
import pecas_habitos as ph
import pecas_veiculos as pv

AMOSTRAS = int(os.environ.get("AMOSTRAS", 24))
TMP = os.path.join(HERE, "_tmp")
os.makedirs(TMP, exist_ok=True)


def camera(pos, alvo, lens=35, orto=None):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.clip_start = 0.01
    if orto:
        cd.type = "ORTHO"
        cd.ortho_scale = orto
    cam = mt.link(bpy.data.objects.new("cam", cd))
    cam.location = pos
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")
    mt.scene.camera = cam
    return cam


def mundo(cor="#2A3038", forca=0.6):
    w = bpy.data.worlds.new("mundo")
    mt.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = mt.lin(cor)
    bg.inputs["Strength"].default_value = forca


def luz_sol(rot, energia=3.0, cor="#FFF6E8", angulo=8):
    d = bpy.data.lights.new("sol", "SUN")
    d.energy = energia
    d.color = mt.lin(cor)[:3]
    d.angle = math.radians(angulo)
    o = mt.link(bpy.data.objects.new("sol", d))
    o.rotation_euler = [math.radians(a) for a in rot]


def luz_area(pos, alvo, energia=80, tam=1.5, cor="#FFFFFF"):
    d = bpy.data.lights.new("area", "AREA")
    d.energy = energia
    d.size = tam
    d.color = mt.lin(cor)[:3]
    o = mt.link(bpy.data.objects.new("area", d))
    o.location = pos
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")


def iluminar(escala=1.0):
    mundo()
    luz_sol((52, 8, -30), energia=2.6)
    luz_area((-2.5 * escala, -3.0 * escala, 2.5 * escala), (0, 0, 0.3), energia=120 * escala ** 2, tam=3 * escala,
             cor="#FFF4E6")
    luz_area((2.5 * escala, 2.0 * escala, 1.5 * escala), (0, 0, 0.4), energia=60 * escala ** 2, tam=2 * escala,
             cor="#FFB27A")   # contraluz laranja (cor da marca)


def render(nome, res):
    sc = mt.scene
    sc.cycles.samples = AMOSTRAS
    sc.cycles.transparent_max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.filepath = os.path.join(TMP, nome)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"render {nome}: {time.time() - t0:.1f} s")
    return sc.render.filepath


# ================================================================ cenas
def cena_parafuso():
    """Parafuso em 4 vistas: frente, 3/4, perfil, costas."""
    mt.setup(1, samples=AMOSTRAS)
    M = {}
    pv.materiais_veiculos(M)
    pv.palco_oficina("palco", M, largura=20, fundo_y=2.0, z_brilho=0.3)
    R = 0.2
    objs = []
    for i, (rot, pose) in enumerate(((0, "lanterna"), (-35, "lanterna"), (-90, "parado"), (180, "parado"))):
        P = pv.parafuso(f"p{i}", M, R=R, pose=pose, boca="aberta" if i < 2 else "sorriso", sobrancelha=12)
        P["raiz"].location = (-1.65 + i * 1.1, 0, 0)
        P["raiz"].rotation_euler = (0, 0, math.radians(rot))
        objs.append(P["raiz"])
    ph.contorno(objs, M, esp=0.008)
    iluminar(1.5)
    camera((0, -6.0, 2.1), (0, 0, 0.5), lens=50)
    return render("parafuso.png", (1600, 760))


def cena_expressoes():
    """Expressões do Parafuso (as que o roteiro pede): curioso, explicando, espanto, joinha (solução)."""
    mt.setup(1, samples=AMOSTRAS)
    M = {}
    pv.materiais_veiculos(M)
    pv.palco_oficina("palco", M, largura=20, fundo_y=2.0, z_brilho=0.3)
    R = 0.2
    objs = []
    cfg = (dict(pose="lanterna", boca="sorriso", sobrancelha=16, olhar=(0.6, 0.3), luz=True),
           dict(pose="aponta", boca="aberta", sobrancelha=8, olhar=(-0.7, 0.0)),
           dict(pose="parado", boca="o", sobrancelha=-14, olhar=(0, 0.2)),
           dict(pose="joinha", boca="sorriso", sobrancelha=0, olhar=(0, 0)))
    for i, c in enumerate(cfg):
        P = pv.parafuso(f"e{i}", M, R=R, **c)
        P["raiz"].location = (-1.65 + i * 1.1, 0, 0)
        P["raiz"].rotation_euler = (0, 0, math.radians(-12))
        objs.append(P["raiz"])
    ph.contorno(objs, M, esp=0.008)
    iluminar(1.5)
    camera((0, -6.0, 2.1), (0, 0, 0.5), lens=50)
    return render("expressoes.png", (1600, 760))


CARROS = (("picape", "branco"), ("hatch", "vermelho"), ("suv", "prata"), ("popular", "azul"))


def cena_carros():
    mt.setup(1, samples=AMOSTRAS)
    M = {}
    pv.materiais_veiculos(M)
    pv.palco_oficina("palco", M, largura=30, fundo_y=4.0, z_brilho=0.4)
    objs = []
    xs = (-4.05, -1.3, 1.45, 4.1)
    for i, ((tipo, cor), x) in enumerate(zip(CARROS, xs)):
        V = pv.carro_chibi(f"c{i}", M, tipo=tipo, cor=cor, rosto=(i == 1), humor="feliz")
        V["raiz"].location = (x, 0, 0)
        V["raiz"].rotation_euler = (0, 0, math.radians(215 if tipo == "picape" else -30))
        objs.append(V["raiz"])
    ph.contorno(objs, M, esp=0.012)
    iluminar(3.0)
    camera((0, -14.5, 3.8), (0, 0, 0.5), lens=50)
    return render("carros.png", (1800, 700))


MOTOS = (("street", "vermelho", False), ("cub", "branco", True), ("trail", "azul", False))


def cena_motos():
    mt.setup(1, samples=AMOSTRAS)
    M = {}
    pv.materiais_veiculos(M)
    pv.palco_oficina("palco", M, largura=20, fundo_y=2.5, z_brilho=0.35)
    objs = []
    for i, (tipo, cor, bau) in enumerate(MOTOS):
        V = pv.moto_chibi(f"m{i}", M, tipo=tipo, cor=cor, bau=bau)
        V["raiz"].location = (-1.75 + i * 1.75, 0, 0)
        V["raiz"].rotation_euler = (0, 0, math.radians(-28))
        objs.append(V["raiz"])
    ph.contorno(objs, M, esp=0.008)
    iluminar(2.0)
    camera((0, -6.8, 1.7), (0, 0, 0.45), lens=50)
    return render("motos.png", (1800, 700))


def cena_quadro():
    """Quadro 9:16 de teste do estilo: Parafuso com a lanterna acesa olhando o hatch com cara de cansado."""
    mt.setup(1, samples=AMOSTRAS)
    M = {}
    pv.materiais_veiculos(M)
    pv.palco_oficina("palco", M, largura=14, fundo_y=2.6, z_brilho=0.5)
    V = pv.carro_chibi("carro", M, tipo="hatch", cor="vermelho", rosto=True, humor="cansado", olhar=(0.7, 0.3))
    V["raiz"].location = (0.45, 0.75, 0)
    V["raiz"].rotation_euler = (0, 0, math.radians(-118))
    P = pv.parafuso("par", M, R=0.15, pose="lanterna", boca="aberta", sobrancelha=16, olhar=(0.6, 0.3), luz=True,
                    mira=(0.8, -0.35, -0.12))
    P["raiz"].location = (-0.55, -0.35, 0)
    P["raiz"].rotation_euler = (0, 0, math.radians(55))
    ph.contorno([V["raiz"], P["raiz"]], M, esp=0.01)
    iluminar(1.6)
    camera((-0.2, -2.75, 1.05), (0.0, 0.25, 0.42), lens=36)
    return render("quadro_base.png", (576, 1024))


# ================================================================ 2D
FONTE = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
FONTE_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
GRAF, CREME, LAR, GEMA = "#1E2329", "#FFF4E0", "#FF7A1A", "#FFC928"


def fonte(px, f=FONTE):
    return ImageFont.truetype(f, int(px))


def placa_oficina(texto, cor, larg_img, px=None):
    """Etiqueta 'plaquinha de oficina': retângulo com 2 parafusos nos cantos, faixa de cor à esquerda."""
    f = fonte(px or larg_img * 0.06)
    x0, y0, x1, y1 = f.getbbox(texto)
    tw, th = x1 - x0, y1 - y0
    pad, faixa = int(th * 0.6), int(th * 0.55)
    w, h = faixa + tw + pad * 3, th + pad * 2
    im = Image.new("RGBA", (w + 14, h + 14), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([8, 10, w + 8, h + 10], radius=int(h * 0.18), fill=(0, 0, 0, 90))
    d.rounded_rectangle([2, 2, w + 2, h + 2], radius=int(h * 0.18), fill=CREME, outline=GRAF, width=4)
    d.rounded_rectangle([2, 2, faixa + 2, h + 2], radius=int(h * 0.18), fill=cor, outline=GRAF, width=4)
    d.rectangle([faixa - 6, 4, faixa + 2, h], fill=cor)
    for cy in (pad * 0.9, h - pad * 0.9):    # parafusinhos
        cx = faixa + tw + pad * 2.4
        r = max(4, th * 0.13)
        d.ellipse([cx - r, cy - r + 2, cx + r, cy + r + 2], fill="#B9C1C9", outline=GRAF, width=2)
        d.line([cx - r * 0.6, cy + 2, cx + r * 0.6, cy + 2], fill=GRAF, width=2)
    d.text((faixa + pad - x0 + 2, pad - y0 + 2), texto, font=f, fill=GRAF)
    return im


def losango(texto, lado):
    """Placa de trânsito amarela (losango) com o gancho."""
    im = Image.new("RGBA", (lado + 20, lado + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = lado / 2 + 6
    pts = [(c, 6), (lado + 6, c), (c, lado + 6), (6, c)]
    d.polygon([(x + 6, y + 8) for x, y in pts], fill=(0, 0, 0, 100))
    d.polygon(pts, fill=GEMA, outline=GRAF)
    d.line(pts + [pts[0]], fill=GRAF, width=int(lado * 0.035), joint="curve")
    k = 0.8
    pi = [(c, 6 + lado * 0.1), (lado + 6 - lado * 0.1, c), (c, lado + 6 - lado * 0.1), (6 + lado * 0.1, c)]
    d.line(pi + [pi[0]], fill=GRAF, width=int(lado * 0.012))
    linhas = texto.split("\n")
    f = fonte(lado * 0.13)
    hh = sum(f.getbbox(l)[3] - f.getbbox(l)[1] for l in linhas) + (len(linhas) - 1) * lado * 0.03
    y = c - hh / 2
    for l in linhas:
        b = f.getbbox(l)
        d.text((c - (b[2] - b[0]) / 2 - b[0], y - b[1]), l, font=f, fill=GRAF)
        y += b[3] - b[1] + lado * 0.03
    return im


def pos_quadro(src):
    img = Image.open(src).convert("RGBA")
    W = img.width
    L = losango("VOCÊ\nFAZ\nISSO?", int(W * 0.46))
    img.alpha_composite(L, (int(W / 2 - L.width / 2), int(W * 0.06)))
    e = placa_oficina("MOTOR SOFRE", "#E5484D", W)
    img.alpha_composite(e, (int(W / 2 - e.width / 2), int(img.height * 0.78)))
    img.convert("RGB").save(os.path.join(HERE, "quadro_teste.png"))


def ficha():
    """Prancha única: título, paleta, Parafuso (vistas + expressões), carros, motos, etiquetas e quadro de teste."""
    par = Image.open(os.path.join(TMP, "parafuso.png")).convert("RGB")
    exp = Image.open(os.path.join(TMP, "expressoes.png")).convert("RGB")
    car = Image.open(os.path.join(TMP, "carros.png")).convert("RGB")
    mot = Image.open(os.path.join(TMP, "motos.png")).convert("RGB")
    qd = Image.open(os.path.join(HERE, "quadro_teste.png")).convert("RGB")
    Wt = 2400
    mx = 40
    colw = Wt - mx * 3 - 560
    blocos = []

    def esc(im, w):
        return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)

    par, exp, car, mot = (esc(i, colw) for i in (par, exp, car, mot))
    qd = esc(qd, 560)
    cab = 170
    lb = 64
    Ht = cab + 4 * (lb + 10) + par.height + exp.height + car.height + mot.height + mx * 2 + 260
    out = Image.new("RGB", (Wt, Ht), GRAF)
    d = ImageDraw.Draw(out)
    d.text((mx, 40), "OFICINA DE BOLSO", font=fonte(84), fill=CREME)
    d.text((mx, 128), "identidade visual do canal de veículos  ·  proposta para aprovação", font=fonte(34, FONTE_B),
           fill=LAR)
    y = cab + 20
    for titulo, im in (("PARAFUSO  ·  mascote (frente, 3/4, perfil, costas)", par),
                       ("PARAFUSO  ·  expressões (lanterna acesa, explicando, espanto, joinha)", exp),
                       ("CARROS  ·  picape compacta, hatch, SUV compacto, hatch de entrada", car),
                       ("MOTOS  ·  street 160, motoneta com baú de entrega, trail 160", mot)):
        d.text((mx, y), titulo, font=fonte(36, FONTE_B), fill=GEMA)
        y += lb
        out.paste(im, (mx, y))
        d.rounded_rectangle([mx - 3, y - 3, mx + im.width + 2, y + im.height + 2], radius=6, outline="#3A414A",
                            width=4)
        y += im.height + 10
    # coluna da direita: quadro de teste + paleta + etiquetas
    xr = mx * 2 + colw
    d.text((xr, cab + 20), "QUADRO DE TESTE 9:16", font=fonte(36, FONTE_B), fill=GEMA)
    out.paste(qd, (xr, cab + 20 + lb))
    yp = cab + 20 + lb + qd.height + 50
    d.text((xr, yp), "PALETA", font=fonte(36, FONTE_B), fill=GEMA)
    yp += lb
    pal = (("grafite", "#1E2329"), ("laranja-segurança", "#FF7A1A"), ("amarelo-gema", "#FFC928"),
           ("azul-macacão", "#2F6FB3"), ("vermelho-freio", "#E5484D"), ("creme", "#FFF4E0"))
    for i, (n, c) in enumerate(pal):
        yy = yp + i * 78
        d.rounded_rectangle([xr, yy, xr + 66, yy + 66], radius=10, fill=c, outline="#5A636D", width=3)
        d.text((xr + 86, yy + 6), n, font=fonte(30, FONTE_B), fill=CREME)
        d.text((xr + 86, yy + 38), c, font=fonte(22, FONTE_B), fill="#9AA3AD")
    yp += len(pal) * 78 + 40
    d.text((xr, yp), "ETIQUETAS", font=fonte(36, FONTE_B), fill=GEMA)
    yp += lb
    for t, c in (("PROBLEMA", "#E5484D"), ("SOLUÇÃO", "#FFC928"), ("TEMPO", "#3A414A"), ("OBJEÇÃO", "#9AA3AD"),
                 ("R$ NO BOLSO", "#FF7A1A")):
        e = placa_oficina(t, c, 560, px=34)
        out.paste(e, (xr, yp), e)
        yp += e.height + 12
    out = out.crop((0, 0, Wt, max(y, yp) + mx))
    out.save(os.path.join(HERE, "ficha_identidade.jpg"), quality=90)
    print("ficha:", out.size)


if __name__ == "__main__":
    alvo = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    alvo = alvo or ["parafuso", "expr", "carros", "motos", "quadro", "ficha"]
    if "parafuso" in alvo:
        cena_parafuso()
    if "expr" in alvo:
        cena_expressoes()
    if "carros" in alvo:
        cena_carros()
    if "motos" in alvo:
        cena_motos()
    if "quadro" in alvo:
        pos_quadro(cena_quadro())
    if "ficha" in alvo:
        ficha()
