"""Prova da biblioteca de assets: a MESMA rua (mesmo carro, mesma câmera) feita de dois jeitos, lado a lado.

  A) a rua atual por código (videos/calibrar_pneu/planos/_rua.py: R.rua + R.dia)
  B) a rua com a biblioteca (motor3d/biblioteca.py): HDRI de dia, asfalto PBR, calçada de concreto PBR, muro de
     reboco pintado PBR, poste/hidrante/caixa de luz do Poly Haven e cones do Kenney.

    ~/.venv-video/bin/python videos/_assets/prova_rua.py            # 360x640, 16 amostras (econômico)
    RES=576 AMOSTRAS=24 ~/.venv-video/bin/python videos/_assets/prova_rua.py
Saída: videos/_assets/prova_rua.png (as duas lado a lado, com rótulo).
"""
import os, sys, math, time
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "videos", "calibrar_pneu", "planos"))
sys.path.insert(0, os.path.join(RAIZ, "motor3d"))
import _rua as R            # traz comum (C), motor (mt), veiculos_antigos...
import bpy
import motor as mt
import biblioteca as bib

W = int(os.environ.get("RES", 360))
H = int(W * 16 / 9)
AMOSTRAS = int(os.environ.get("AMOSTRAS", 16))
TMP = os.path.join(AQUI, "_tmp")
os.makedirs(TMP, exist_ok=True)
CAM = dict(pos=(5.2, -4.6, 1.25), alvo=(0.2, 3.2, 0.95), lens=30)


def base():
    sc = mt.setup(1.0, samples=AMOSTRAS, res=(W, H))
    sc.cycles.max_bounces, sc.cycles.diffuse_bounces = 4, 2
    sc.render.threads_mode = "FIXED"          # econômico: há renders de vídeo rodando junto
    sc.render.threads = int(os.environ.get("THREADS", 2))
    return sc


def carro(M):
    c = R.carro(M, cor="vermelho")
    c["raiz"].location = (0, 2.95, 0)
    return c


def render(nome):
    sc = mt.scene
    sc.render.filepath = os.path.join(TMP, nome + ".png")
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"{nome}: {time.time() - t0:.1f}s", flush=True)
    return sc.render.filepath


# ------------------------------------------------------------- A) rua por código
def rua_codigo():
    sc = base()
    R.dia(sc, sol=(50, 0, -35))
    M = {}
    R.rua(M)
    carro(M)
    R.camera(CAM["pos"], CAM["alvo"], lens=CAM["lens"])
    return render("A_codigo")


# ------------------------------------------------------------- B) rua com a biblioteca
def rua_biblioteca(meio_fio=3.9, x0=-14, x1=14):
    sc = base()
    sc.view_settings.exposure = 0.0
    # HDRI de rua de dia: ilumina e aparece no fundo (prédios/árvores/céu reais)
    bib.hdri("wide_street_01", forca=1.0, rotacao=200)
    # sol de reforço alinhado ao HDRI, para sombra nítida do carro (o HDRI 1k/2k dá sombra mole)
    sol = bpy.data.lights.new("sol", "SUN")
    sol.energy, sol.angle = 1.6, math.radians(1.5)
    sol.color = (1.0, 0.93, 0.84)
    so = mt.link(bpy.data.objects.new("sol", sol))
    so.rotation_euler = (math.radians(50), 0, math.radians(-35))

    M = {}
    asf = bib.textura_pbr("asphalt_02", escala=3.0, tinta="#8C8C8C")     # escurece: asfalto de bairro
    calc = bib.textura_pbr("concrete_pavement", escala=1.6)
    mfio = bib.textura_pbr("concrete_floor_02", escala=1.0)
    muro = bib.textura_pbr("painted_plaster_wall", escala=2.0, tinta="#F1DDB4")
    barrado = bib.textura_pbr("painted_plaster_wall", escala=2.0, tinta="#7FA39F", nome_material="barrado")
    mt.box("asfalto", x0, x1, -30, meio_fio, -0.05, 0.0, asf)
    mt.box("meio_fio", x0, x1, meio_fio, meio_fio + 0.16, -0.05, 0.15, mfio)
    mt.box("calcada", x0, x1, meio_fio + 0.16, meio_fio + 2.2, -0.05, 0.13, calc)
    y = meio_fio + 2.2
    mt.box("muro", x0, x1, y, y + 0.2, 0.0, 2.4, muro)
    mt.box("barrado", x0, x1, y - 0.01, y, 0.0, 0.6, barrado)
    for xp in range(int(x0) + 1, int(x1), 4):
        mt.box(f"pilar{xp}", xp - 0.16, xp + 0.16, y - 0.06, y + 0.22, 0.0, 2.5, muro)
    # faixas pintadas (mesmas do código, para comparar só o material)
    tinta = R._m(M, "faixa", "#E6E2D6", rough=0.6)
    k = x0
    while k < x1:
        mt.box(f"faixa{k:.0f}", k, k + 2.0, -1.6, -1.48, 0.0, 0.003, tinta)
        k += 4.0
    mt.box("borda_am", x0, x1, meio_fio - 0.32, meio_fio - 0.22, 0.0, 0.003, R._m(M, "am", "#D9A21B", rough=0.6))

    # objetos de rua da biblioteca
    # poste de braço curvo (o mais parecido com o de rua brasileira): Kenney City Kit Roads, ~7 m de altura
    kr = os.path.join("kenney", "city_kit_roads", "Models", "GLB format")
    # (o low-poly ganha textura PBR de metal escovado e fica mais fino: escala x/y menor que z)
    metal = bib.textura_pbr("Metal009", escala=0.5, tinta="#9AA0A6", rugosidade=0.45)
    for xp in (-1.6, -11.0):
        p = bib.importar_modelo(os.path.join(kr, "light-curved.glb"), loc=(xp, meio_fio + 0.45, 0.13),
                                material=metal)
        d = bib.dimensoes(p)
        if d[2] > 0:
            s = 7.0 / d[2]
            p.scale = (s * 0.45, s * 0.45, s)
    bib.importar_modelo("fire_hydrant", sem="aged", centralizar=True, loc=(2.4, meio_fio + 0.55, 0.13),
                        rot=(0, 0, 20))
    bib.importar_modelo("utility_box_01", loc=(3.6, y - 0.3, 0.13), rot=(0, 0, 180))
    cone = os.path.join(kr, "construction-cone.glb")
    for i, (cx, cy) in enumerate(((1.9, 1.75), (2.6, 1.4), (3.3, 1.05))):
        c = bib.importar_modelo(cone, loc=(cx, cy, 0.0), rot=(0, 0, 15 * i))
        d = bib.dimensoes(c)
        if d[2] > 0:
            s = 0.55 / d[2]           # cone de trânsito ~55 cm
            c.scale = (s, s, s)
    carro(M)
    R.camera(CAM["pos"], CAM["alvo"], lens=CAM["lens"])
    return render("B_biblioteca")


def lado_a_lado(a, b, saida):
    from PIL import Image, ImageDraw, ImageFont
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    m, faixa = 12, 46
    out = Image.new("RGB", (ia.width * 2 + m * 3, ia.height + faixa + m), "#1b1d21")
    out.paste(ia, (m, faixa))
    out.paste(ib, (ia.width + m * 2, faixa))
    d = ImageDraw.Draw(out)
    try:
        f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 18)
    except OSError:
        f = ImageFont.load_default()
    d.text((m, 12), "A) atual: rua por código (_rua.py)", fill="#e8e8e8", font=f)
    d.text((ia.width + m * 2, 12), "B) biblioteca: HDRI + PBR + modelos CC0", fill="#ffd36b", font=f)
    out.save(saida)
    print("salvo:", saida)


if __name__ == "__main__":
    so = [x for x in sys.argv[1:] if x in ("A", "B")]
    a = os.path.join(TMP, "A_codigo.png") if so == ["B"] else rua_codigo()
    b = os.path.join(TMP, "B_biblioteca.png") if so == ["A"] else rua_biblioteca()
    lado_a_lado(a, b, os.path.join(AQUI, "prova_rua.png"))
