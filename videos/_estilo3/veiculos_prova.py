"""Prova de acabamento dos veículos "brinquedo de vinil" (motor3d/veiculos3.py).

Uso:  ~/.venv-video/bin/python videos/_estilo3/veiculos_prova.py [carros] [motos] [--amostras 48] [--escala 1.0]
Saídas nesta pasta: carros.png (5 carros em 3/4) e motos.png (street, cub com baú, trail).
Estúdio: ciclorama infinito cinza-azulado claro, luz principal de área grande + preenchimento + recorte.
"""
import sys, os, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "motor3d"))
import bpy, bmesh
from mathutils import Vector
import veiculos3 as v3

FUNDO = "#FFE07A"      # parede do ciclorama
CHAO = "#F3F5F9"       # chão (claro: sombras limpas, não vira mostarda)
LUZ = 0.8             # multiplica as 3 luzes (ajuste fino)


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    alvo = [x for x in a if not x.startswith("--") and not x.replace(".", "").isdigit()]
    amostras = int(a[a.index("--amostras") + 1]) if "--amostras" in a else 48
    escala = float(a[a.index("--escala") + 1]) if "--escala" in a else 1.0
    return alvo or ["carros", "motos"], amostras, escala


def nova_cena(res, amostras):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    c = sc.cycles
    c.device = "CPU"
    c.samples = amostras
    c.use_adaptive_sampling = True
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    if hasattr(c, "denoising_quality"):
        c.denoising_quality = "HIGH"
    if hasattr(c, "denoising_prefilter"):
        c.denoising_prefilter = "ACCURATE"
    c.max_bounces = 6
    c.diffuse_bounces = 3
    c.glossy_bounces = 3
    c.caustics_reflective = c.caustics_refractive = False
    sc.view_settings.view_transform = "Standard"      # cores vivas (o AgX deixava pastel)
    w = bpy.data.worlds.new("mundo")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = v3.lin("#FFF8EC")   # ambiente branco-quente: preenche sem amarelar
    bg.inputs["Strength"].default_value = 0.42
    return sc


def ciclorama(larg=40.0, fundo_y=6.0, raio=3.0, altura=12.0):
    """Piso + curva + parede numa malha só (sem quina): o fundo "infinito" de estúdio."""
    bm = bmesh.new()
    perfil = [(-20.0, 0.0), (fundo_y - raio, 0.0)]
    for k in range(1, 16):
        a = math.pi / 2 * k / 16
        perfil.append((fundo_y - raio + raio * math.sin(a), raio - raio * math.cos(a)))
    perfil += [(fundo_y, raio), (fundo_y, altura)]
    nx = 2
    rows = []
    for (y, z) in perfil:
        rows.append([bm.verts.new((-larg / 2 + larg * i / nx, y, z)) for i in range(nx + 1)])
    for r in range(len(rows) - 1):
        for i in range(nx):
            f = bm.faces.new([rows[r][i], rows[r][i + 1], rows[r + 1][i + 1], rows[r + 1][i]])
            # material pela altura: chão claro até a metade da curva, parede amarela dali para cima
            f.material_index = 0 if f.calc_center_median().z < raio * 0.35 else 1
    chao = v3.vinil("ciclorama_chao", CHAO, rough=0.8, coat=0.0)
    parede = v3.vinil("ciclorama_parede", FUNDO, rough=0.9, coat=0.0)
    o = v3._obj("ciclorama", bm, [chao, parede])
    return o


def luz_area(nome, pos, alvo, energia, tam, cor="#FFFFFF"):
    d = bpy.data.lights.new(nome, "AREA")
    d.energy = energia
    d.shape = "DISK"
    d.size = tam
    d.color = v3.lin(cor)[:3]
    o = v3._link(bpy.data.objects.new(nome, d))
    o.location = pos
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")
    return o


def camera(pos, alvo, lens=50):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cam = v3._link(bpy.data.objects.new("cam", cd))
    cam.location = pos
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")
    bpy.context.scene.camera = cam
    return cam


def estudio(centro, dist):
    cx, cy, cz = centro
    ciclorama(fundo_y=cy + 4.5)
    k = LUZ * (dist / 8) ** 2   # mesma iluminação no centro para qualquer distância (carros e motos)
    luz_area("key", (cx - dist * 0.55, cy - dist * 0.75, cz + dist * 0.75), centro, 700 * k, dist * 0.7, "#FFF6EC")
    luz_area("fill", (cx + dist * 0.8, cy - dist * 0.55, cz + dist * 0.25), centro, 260 * k, dist * 0.8, "#EEF3FF")
    luz_area("rim", (cx + dist * 0.2, cy + dist * 0.7, cz + dist * 0.55), centro, 450 * k, dist * 0.35, "#FFFFFF")


def render(caminho):
    t = time.time()
    bpy.context.scene.render.filepath = caminho
    bpy.ops.render.render(write_still=True)
    print(f"render {os.path.basename(caminho)}: {time.time() - t:.1f}s")


def checar_rodas(D):
    """Conta vértices da lata (subdividida) dentro do volume de cada roda (interpenetração)."""
    dg = bpy.context.evaluated_depsgraph_get()
    tot = 0
    for o in D["lataria"]:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        for rd in D["rodas"]:
            inv = rd.matrix_world.inverted()
            R = max(rd.dimensions.x, rd.dimensions.z) / 2
            w = rd.dimensions.y / 2
            for v in me.vertices:
                p = inv @ (mw @ v.co)
                if abs(p.y) < w and p.x * p.x + p.z * p.z < (R * 0.98) ** 2:
                    tot += 1
        ev.to_mesh_clear()
    return tot


def cena_carros(amostras, escala):
    nova_cena((int(2000 * escala), int(720 * escala)), amostras)
    M = v3.materiais({})
    lista = [("picape", "vermelho", False), ("suv", "azul", False), ("hatch", "laranja", True),
             ("popular", "amarelo", False), ("seda", "verde", False)]
    passo = 2.75
    for k, (tipo, cor, rosto) in enumerate(lista):
        D = v3.carro(f"car_{tipo}", M, tipo, cor, rosto=rosto, humor="feliz")
        D["raiz"].location = ((k - 2) * passo, 0, 0)
        D["raiz"].rotation_euler = (0, 0, math.radians(-32))
        bpy.context.view_layer.update()
        print(tipo, "interpenetração (vértices):", checar_rodas(D))
    alvo = (0, 0, 0.62)
    camera((0.0, -19.5, 5.2), alvo, lens=50)
    estudio(alvo, 9.0)
    render(os.path.join(HERE, "carros.png"))


def cena_motos(amostras, escala):
    nova_cena((int(1800 * escala), int(720 * escala)), amostras)
    M = v3.materiais({})
    lista = [("street", "vermelho", False), ("cub", "branco", True), ("trail", "azul", False)]
    passo = 1.75
    for k, (tipo, cor, bau) in enumerate(lista):
        D = v3.moto(f"moto_{tipo}", M, tipo, cor, bau=bau)
        D["raiz"].location = ((k - 1) * passo, 0, 0)
        D["raiz"].rotation_euler = (0, 0, math.radians(-30))
        bpy.context.view_layer.update()
        print(tipo, "interpenetração (vértices):", checar_rodas(D))
    alvo = (0, 0, 0.55)
    camera((0.0, -10.5, 2.6), alvo, lens=50)
    estudio(alvo, 5.0)
    render(os.path.join(HERE, "motos.png"))


if __name__ == "__main__":
    alvo, amostras, escala = args()
    if "carros" in alvo:
        cena_carros(amostras, escala)
    if "motos" in alvo:
        cena_motos(amostras, escala)
