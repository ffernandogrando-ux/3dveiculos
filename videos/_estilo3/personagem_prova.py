"""Prova do mascote humano (mecânico "Zé") nas duas direções: A) 3D vinil liso  B) 2D toon com contorno.

Uso:  ~/.venv-video/bin/python videos/_estilo3/personagem_prova.py [vinil|toon] [lineup|quadro]
Saídas nesta pasta: ze_<estilo>_lineup.png (frente, 3/4, poses) e ze_<estilo>_quadro.png (9:16).
"""
import sys, os, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "motor3d"))
import bpy
from mathutils import Vector
import motor as mt
import boneco as bc

AMOSTRAS = int(os.environ.get("AMOSTRAS", 32))


def preparar(estilo):
    mt.setup(1, samples=AMOSTRAS)
    sc = mt.scene
    c = sc.cycles
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 6, 3, 2
    if hasattr(c, "denoising_quality"):
        c.denoising_quality = "HIGH"
        c.denoising_prefilter = "ACCURATE"
    sc.render.filter_size = 1.2
    w = bpy.data.worlds.new("mundo")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    if estilo == "vinil":
        sc.view_settings.view_transform = "Standard"     # AgX deixava tudo pastel (boné salmão, macacão bebê)
        sc.view_settings.exposure = 0.0
        bg.inputs["Color"].default_value = mt.lin("#DDE6EE")
        bg.inputs["Strength"].default_value = 0.12
    else:
        sc.view_settings.view_transform = "Standard"
        bg.inputs["Color"].default_value = mt.lin("#DCE6F2")
        bg.inputs["Strength"].default_value = 1.0
        sc.cycles.samples = 8
        sc.render.use_freestyle = True
        sc.render.line_thickness_mode = "ABSOLUTE"
        vl = sc.view_layers[0]
        vl.use_freestyle = True
        ls = vl.freestyle_settings.linesets.new("contorno")
        ls.select_by_visibility = True
        ls.select_silhouette = ls.select_border = True
        ls.select_crease = False
        ls.linestyle.color = mt.lin("#2A1E1A")[:3]
        ls.linestyle.thickness = 2.5 * 1024 / 1024
        ls.linestyle.chaining = "PLAIN"
    return sc


def luzes(alvo=(0, 0, 0.6), escala=1.0):
    def area(pos, energia, tam, cor):
        d = bpy.data.lights.new("a", "AREA")
        d.energy, d.size = energia * escala ** 2 * 0.3, tam * escala
        d.color = mt.lin(cor)[:3]
        o = mt.link(bpy.data.objects.new("a", d))
        o.location = [p * escala for p in pos]
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = (Vector(alvo) - o.location).to_track_quat("-Z", "Y")
    area((-2.2, -2.6, 2.6), 420, 2.5, "#FFF1E0")     # key (5200 K, quente)
    area((2.6, -2.0, 1.4), 300, 2.5, "#E6EEFF")      # fill frio (key ~40 % mais forte)
    area((0.6, 1.2, 2.2), 840, 1.2, "#FFFFFF")       # rim forte atrás/acima (descola da parede clara)


def camera(pos, alvo, lens=50, dof=None):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    if dof:
        cd.dof.use_dof = True
        cd.dof.focus_distance = dof[0]
        cd.dof.aperture_fstop = dof[1]
    cam = mt.link(bpy.data.objects.new("cam", cd))
    cam.location = pos
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")
    mt.scene.camera = cam
    return cam


def render(nome, res):
    sc = mt.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.filepath = os.path.join(HERE, nome)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"render {nome}: {time.time() - t0:.1f} s")


def lineup(estilo):
    preparar(estilo)
    M = {}
    bc.oficina_clara(M, estilo, largura=12, fundo_y=1.4)
    cfg = [(0, "parado", "sorriso", (0, 0)), (-35, "aponta", "fala", (0.6, 0)), (-15, "joinha", "sorriso", (0, 0)),
           (0, "espanto", "espanto", (0, 0.3)), (20, "explica", "preocupado", (0, 0))]
    for i, (rot, pose, expr, olhar) in enumerate(cfg):
        Z = bc.mecanico(f"ze{i}", M, estilo=estilo, pose=pose, expressao=expr, olhar=olhar, chave=(i != 3))
        Z["raiz"].location = (-2.0 + i * 1.0, 0, 0)
        Z["raiz"].rotation_euler = (0, 0, math.radians(rot))
    luzes(alvo=(0, 0, 0.6), escala=1.6)
    camera((0, -6.4, 1.15), (0, 0, 0.62), lens=50)
    render(f"ze_{estilo}_lineup.png", (1800, 760))


def quadro(estilo):
    preparar(estilo)
    M = {}
    bc.oficina_clara(M, estilo, largura=6, fundo_y=1.2)
    Z = bc.mecanico("ze", M, estilo=estilo, pose="aponta", expressao="fala", olhar=(0.5, 0.1))
    Z["raiz"].rotation_euler = (0, 0, math.radians(-20))
    luzes(alvo=(0, 0, 0.7))
    camera((-1.05, -2.75, 0.72), (0, 0, 0.64), lens=70, dof=(2.95, 4.0) if estilo == "vinil" else None)
    render(f"ze_{estilo}_quadro.png", (576, 1024))


if __name__ == "__main__":
    a = sys.argv[1:]
    estilos = [e for e in ("vinil", "toon") if e in a] or ["vinil", "toon"]
    cenas = [c for c in ("lineup", "quadro") if c in a] or ["lineup", "quadro"]
    for e in estilos:
        if "lineup" in cenas:
            lineup(e)
        if "quadro" in cenas:
            quadro(e)
