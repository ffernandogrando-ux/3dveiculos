"""Prova do Zé ADULTO (direção A "estilizado adulto"): poses lado a lado + retrato 9:16 na oficina.

Uso:  ~/.venv-video/bin/python videos/_estilo4/ze_adulto_prova.py [lineup] [retrato]
"""
import sys, os, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "motor3d"))
import bpy
from mathutils import Vector
import motor as mt
import boneco_adulto as ba

AMOSTRAS = int(os.environ.get("AMOSTRAS", 32))


def preparar():
    mt.setup(1, samples=AMOSTRAS)
    sc = mt.scene
    c = sc.cycles
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 6, 3, 3
    if hasattr(c, "denoising_quality"):
        c.denoising_quality = "HIGH"
        c.denoising_prefilter = "ACCURATE"
    sc.view_settings.view_transform = "Standard"        # cor viva (pedido do dono); contraste vem da luz 3:1
    sc.view_settings.exposure = -1.0
    w = bpy.data.worlds.new("mundo")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = mt.lin("#2A2F36")
    bg.inputs["Strength"].default_value = 0.4
    return sc


def luzes(alvo=(0, 0, 1.2), k=1.0):
    def area(pos, energia, tam, cor):
        d = bpy.data.lights.new("a", "AREA")
        d.energy, d.size = energia * k, tam
        d.color = mt.lin(cor)[:3]
        o = mt.link(bpy.data.objects.new("a", d))
        o.location = pos
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")
    area((-2.4, -3.0, 3.2), 900, 2.5, "#FFF3E6")      # key 5000 K
    area((3.0, -2.2, 1.8), 300, 3.0, "#DCE6FF")       # fill 1/3
    area((1.2, 2.0, 2.8), 900, 1.0, "#FFB070")        # rim quente


def camera(pos, alvo, lens=45, dof=None):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    if dof:
        cd.dof.use_dof = True
        cd.dof.focus_distance, cd.dof.aperture_fstop = dof
    cam = mt.link(bpy.data.objects.new("cam", cd))
    cam.location = pos
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")
    mt.scene.camera = cam


def render(nome, res):
    sc = mt.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 50 if os.environ.get("RASCUNHO") else 100
    sc.render.filepath = os.path.join(HERE, nome)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"render {nome}: {time.time() - t:.1f} s")


def lineup():
    preparar()
    M = {}
    ba.oficina(M, largura=12, fundo_y=2.0)
    cfg = [(0, "parado", "neutro"), (-30, "aponta", "fala"), (0, "explica", "sorriso"),
           (15, "bracos_cruzados", "preocupado"), (25, "conta", "surpreso")]
    for i, (rot, pose, ex) in enumerate(cfg):
        Z = ba.ze_adulto(f"ze{i}", M, pose=pose, expressao=ex)
        Z["raiz"].location = (-2.4 + i * 1.2, 0, 0)
        Z["raiz"].rotation_euler = (0, 0, math.radians(rot))
    luzes(alvo=(0, 0, 1.1), k=1.6)
    camera((0, -8.2, 1.5), (0, 0, 1.0), lens=45)
    render("ze_adulto_lineup.png", (2000, 900))


def retrato():
    preparar()
    M = {}
    ba.oficina(M, largura=8, fundo_y=1.8)
    Z = ba.ze_adulto("ze", M, pose="explica", expressao="fala", olhar=(0.2, 0.0))
    Z["raiz"].rotation_euler = (0, 0, math.radians(-15))
    luzes(alvo=(0, 0, 1.3))
    camera((-0.45, -2.3, 1.5), (0, 0, 1.3), lens=50, dof=(2.35, 2.8))
    render("ze_adulto_retrato.png", (1080, 1920))


def rosto():
    preparar()
    M = {}
    ba.oficina(M, largura=8, fundo_y=1.8)
    for i, ex in enumerate(("neutro", "sorriso", "fala", "preocupado", "surpreso")):
        Z = ba.ze_adulto(f"ze{i}", M, pose="parado", expressao=ex)
        Z["raiz"].location = (-1.0 + i * 0.5, 0, 0)
    luzes(alvo=(0, 0, 1.6))
    camera((0, -3.4, 1.68), (0, 0, 1.64), lens=85)
    render("ze_adulto_rostos.png", (2000, 600))


if __name__ == "__main__":
    a = sys.argv[1:] or ["lineup", "retrato"]
    if "lineup" in a:
        lineup()
    if "retrato" in a:
        retrato()
    if "rosto" in a:
        rosto()
