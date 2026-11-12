"""3 quadros 9:16 de teste do estilo final (3D vinil, cores vivas): gancho, explicação e final.

Uso:  ~/.venv-video/bin/python videos/_estilo3/quadros_teste.py [1] [2] [3]   (sem argumentos = todos)
Saídas: quadro1_gancho.png, quadro2_explica.png, quadro3_final.png nesta pasta (renders crus em _tmp/).
Tema de exemplo: esquentar o carro parado (roteiro 01).
"""
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "motor3d"))
sys.path.insert(0, os.path.join(HERE, "..", "_estilo"))
sys.path.insert(0, HERE)
import bpy
from PIL import Image, ImageDraw
import motor as mt
import boneco as bc
import veiculos3 as v3
import personagem_prova as pp
import ficha as fi          # losango() e placa_oficina() (gráficos 2D)

AMOSTRAS = int(os.environ.get("AMOSTRAS", 32))
TMP = os.path.join(HERE, "_tmp")
os.makedirs(TMP, exist_ok=True)
W, H = 1080, 1920


def base():
    pp.preparar("vinil")
    mt.scene.cycles.samples = AMOSTRAS
    mt.scene.view_settings.exposure = -0.2
    M = {}
    bc.oficina_clara(M, "vinil", largura=10, fundo_y=1.8)
    return M


def render(nome):
    sc = mt.scene
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 50 if os.environ.get("RASCUNHO") else 100
    sc.render.filepath = os.path.join(TMP, nome)
    bpy.ops.render.render(write_still=True)
    return sc.render.filepath


def quadro1():
    """Gancho: Zé apontando para o hatch laranja (preocupado) — 'Você conhece alguém que...?'."""
    M = base()
    V = v3.carro("carro", v3.materiais({}), "hatch", "laranja", rosto=True, humor="preocupado")
    V["raiz"].location = (0.55, 0.75, 0)
    V["raiz"].rotation_euler = (0, 0, math.radians(-150))
    V["raiz"].scale = (0.72, 0.72, 0.72)
    Z = bc.mecanico("ze", M, "vinil", pose="aponta", expressao="fala", olhar=(0.7, 0.0))
    Z["raiz"].location = (-0.3, -0.45, 0)
    Z["raiz"].rotation_euler = (0, 0, math.radians(-25))
    pp.luzes(alvo=(0, 0, 0.55), escala=1.0)
    pp.camera((-0.1, -5.0, 0.6), (0.05, 0.1, 0.85), lens=50, dof=(5.0, 5.6))
    img = Image.open(render("q1.png")).convert("RGBA")
    L = fi.losango("VOCÊ\nFAZ\nISSO?", int(img.width * 0.44))
    img.alpha_composite(L, (int(img.width / 2 - L.width / 2), int(img.width * 0.05)))
    img.convert("RGB").save(os.path.join(HERE, "quadro1_gancho.png"))


def quadro2():
    """Explicação: close no carro (cara preocupada) com o Zé explicando ao lado + etiqueta de problema."""
    M = base()
    V = v3.carro("carro", v3.materiais({}), "hatch", "laranja", rosto=True, humor="assustado")
    V["raiz"].location = (-0.1, 0.5, 0)
    V["raiz"].rotation_euler = (0, 0, math.radians(-108))
    V["raiz"].scale = (0.8, 0.8, 0.8)
    Z = bc.mecanico("ze", M, "vinil", pose="explica", expressao="preocupado", olhar=(-0.4, 0.0))
    Z["raiz"].location = (0.55, -0.5, 0)
    Z["raiz"].rotation_euler = (0, 0, math.radians(28))
    pp.luzes(alvo=(0.2, 0, 0.5), escala=1.0)
    pp.camera((0.15, -4.3, 0.7), (0.15, 0.0, 0.72), lens=46, dof=(4.3, 5.6))
    img = Image.open(render("q2.png")).convert("RGBA")
    e = fi.placa_oficina("MOTOR SEM ÓLEO", "#E5484D", img.width, px=img.width * 0.055)
    img.alpha_composite(e, (int(img.width / 2 - e.width / 2), int(img.height * 0.17)))
    img.convert("RGB").save(os.path.join(HERE, "quadro2_explica.png"))


def quadro3():
    """Final: close do Zé com '?' — 'E aí, você faz isso?'."""
    M = base()
    Z = bc.mecanico("ze", M, "vinil", pose="explica", expressao="sorriso", olhar=(0.0, 0.0))
    Z["raiz"].rotation_euler = (0, 0, math.radians(-12))
    pp.luzes(alvo=(0, 0, 0.9), escala=1.0)
    pp.camera((-0.25, -1.9, 1.05), (0, 0, 0.92), lens=55, dof=(1.95, 3.0))
    img = Image.open(render("q3.png")).convert("RGBA")
    d = ImageDraw.Draw(img)
    f = fi.fonte(img.width * 0.42)
    x, y = img.width * 0.68, img.height * 0.06
    for dx, dy, cor in ((10, 12, (0, 0, 0, 90)), (0, 0, "#FFC400")):
        d.text((x + dx, y + dy), "?", font=f, fill=cor, stroke_width=int(img.width * 0.012), stroke_fill="#1E2329")
    img.convert("RGB").save(os.path.join(HERE, "quadro3_final.png"))


if __name__ == "__main__":
    a = sys.argv[1:] or ["1", "2", "3"]
    if "1" in a:
        quadro1()
    if "2" in a:
        quadro2()
    if "3" in a:
        quadro3()
