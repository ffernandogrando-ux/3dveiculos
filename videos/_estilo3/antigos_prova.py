"""Prova dos carros populares ANTIGOS (motor3d/veiculos_antigos.py) no estúdio cinza de populares_real.png.

Uso:  ~/.venv-video/bin/python videos/_estilo3/antigos_prova.py [lineup] [perfis] [close] [--amostras 48] [--escala 1.0]
Saídas nesta pasta:
- antigos_real.png: lineup 3/4 frente (quadradinho branco, bolinha vermelho, anos2000 prata, quadradinho "gasto"
  verde-escuro, bolinha azul-escuro, sedan90 vinho);
- antigos_perfis.png: os mesmos de perfil (câmera ortográfica, 2 fileiras), para conferir a silhueta;
- antigos_close.png (opcional): close 3/4 traseira, para conferir lanternas, calotas e a pintura gasta.
O estúdio (nova_cena, estudio, luzes, so_nos_veiculos, camera, render, checar_rodas) é cópia fiel do
veiculos_real_prova.py (não importado, para não depender de edições lá).
"""
import sys, os, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "motor3d"))
import bpy, bmesh
from mathutils import Vector
import veiculos3 as v3
import veiculos_antigos as va

LISTA = [("quadradinho", "branco", "ok"), ("bolinha", "vermelho", "ok"), ("anos2000", "prata", "ok"),
         ("quadradinho", "verde_escuro", "gasto"), ("bolinha", "azul_escuro", "ok"), ("sedan90", "vinho", "ok")]


def args():
    a = sys.argv[1:]
    alvo = [x for x in a if not x.startswith("--") and not x.replace(".", "").isdigit()]
    amostras = int(a[a.index("--amostras") + 1]) if "--amostras" in a else 48
    escala = float(a[a.index("--escala") + 1]) if "--escala" in a else 1.0
    return alvo or ["lineup", "perfis"], amostras, escala


# ---------------------------------------------------------------- estúdio (cópia de veiculos_real_prova.py)
def nova_cena(res, amostras):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.render.resolution_x, sc.render.resolution_y = res
    c = sc.cycles
    c.device = "CPU"
    c.samples = amostras
    c.use_adaptive_sampling = True
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    if hasattr(c, "denoising_quality"):
        c.denoising_quality = "HIGH"
    c.max_bounces = 8
    c.diffuse_bounces = 3
    c.glossy_bounces = 4
    c.caustics_reflective = c.caustics_refractive = False
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    w = bpy.data.worlds.new("mundo")
    sc.world = w
    w.use_nodes = True
    # ambiente de estúdio: teto claro, horizonte marcado e chão escuro (é o que desenha os reflexos na lataria)
    nt = w.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    els = cr.color_ramp.elements
    # z da direção vai de -1 a 1; abaixo do horizonte tudo fica na cor da posição 0
    els[0].position, els[0].color = 0.0, v3.lin("#24272B")
    els[1].position, els[1].color = 1.0, v3.lin("#D9DEE4")
    for pos, cor in ((0.025, "#9AA0A7"), (0.08, "#7C828A"), (0.35, "#4E535A"), (0.7, "#8E949B")):
        e = els.new(pos)
        e.color = v3.lin(cor)
    nt.links.new(sep.outputs["Z"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.6
    return sc


def estudio(cx=0.0, fundo_y=7.0, raio=3.5):
    """Piso escuro reflexivo + fundo curvo em degradê (escuro embaixo, cinza claro no alto)."""
    bm = bmesh.new()
    perfil = [(-30.0, 0.0), (fundo_y - raio, 0.0)]
    for k in range(1, 20):
        a = math.pi / 2 * k / 20
        perfil.append((fundo_y - raio + raio * math.sin(a), raio - raio * math.cos(a)))
    perfil += [(fundo_y, raio), (fundo_y, 16.0)]
    rows = [[bm.verts.new((cx - 30 + 60 * i / 2, y, z)) for i in range(3)] for (y, z) in perfil]
    for r in range(len(rows) - 1):
        for i in range(2):
            bm.faces.new([rows[r][i], rows[r][i + 1], rows[r + 1][i + 1], rows[r + 1][i]])
    m = bpy.data.materials.new("estudio")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 5.0
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = v3.lin("#1B1D20")
    cr.color_ramp.elements[1].position = 1.0
    cr.color_ramp.elements[1].color = v3.lin("#8C9299")
    nt.links.new(mr.outputs["Result"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    rough = nt.nodes.new("ShaderNodeMapRange")    # piso acetinado (reflexo suave), parede fosca
    rough.inputs["From Min"].default_value = 0.0
    rough.inputs["From Max"].default_value = 0.6
    rough.inputs["To Min"].default_value = 0.38
    rough.inputs["To Max"].default_value = 0.9
    nt.links.new(sep.outputs["Z"], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], b.inputs["Roughness"])
    v3._obj("estudio", bm, m)


def luz(nome, pos, alvo, energia, sx, sy=None, cor="#FFFFFF", spread=None):
    d = bpy.data.lights.new(nome, "AREA")
    d.energy = energia
    if spread:
        d.spread = math.radians(spread)   # luz direcionada: não derrama no piso
    d.shape = "RECTANGLE"
    d.size = sx
    d.size_y = sy if sy else sx
    d.color = v3.lin(cor)[:3]
    o = v3._link(bpy.data.objects.new(nome, d))
    o.location = pos
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")
    return o


def luzes(cx, larg, k=1.0):
    """Softbox grande em cima (faixa longa ao longo da fila), 2 recortes atrás e um preenchimento baixo."""
    luz("softbox", (cx, -0.6, 4.2), (cx, -0.4, 0), 2600 * k * larg / 10, larg, 3.2, "#FFFFFF")
    luz("rim_e", (cx - larg * 0.35, 4.5, 2.6), (cx - larg * 0.15, 0, 0.6), 900 * k, 0.5, 2.5, "#EAF1FF")
    luz("rim_d", (cx + larg * 0.35, 4.5, 2.6), (cx + larg * 0.15, 0, 0.6), 900 * k, 0.5, 2.5, "#EAF1FF")
    luz("fill", (cx, -9.0, 0.9), (cx, 0, 0.5), 260 * k * larg / 10, larg * 0.9, 0.8, "#FFF4E8")
    luz("fundo", (cx, 2.2, 0.4), (cx, 7.0, 2.6), 700 * k, larg * 0.8, 0.6, "#FFFFFF")


def so_nos_veiculos(raizes):
    """Light linking: as luzes de recorte iluminam só os veículos (não fazem poça de luz no piso)."""
    col = bpy.data.collections.new("alvo_recorte")
    for r in raizes:
        for o in [r] + list(r.children_recursive):
            if o.type == "MESH":
                col.objects.link(o)
    for nome in ("rim_e", "rim_d"):
        lo = bpy.data.objects.get(nome)
        if lo is not None and hasattr(lo, "light_linking"):
            lo.light_linking.receiver_collection = col


def camera(pos, alvo, lens=60):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cam = v3._link(bpy.data.objects.new("cam", cd))
    cam.location = pos
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")
    bpy.context.scene.camera = cam
    return cam


def render(caminho):
    t = time.time()
    bpy.context.scene.render.filepath = caminho
    bpy.ops.render.render(write_still=True)
    print(f"render {os.path.basename(caminho)}: {time.time() - t:.1f}s")


def checar_rodas(D):
    dg = bpy.context.evaluated_depsgraph_get()
    tot = 0
    for o in D["lataria"]:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        for rd in D["rodas"]:
            inv = rd.matrix_world.inverted()
            pn = [c for c in rd.children if c.name.endswith("_pneu")][0]
            # medidas do pneu em coordenadas locais (dimensions já vem com a escala da raiz no Blender 5)
            R = max(abs(v[0]) for v in pn.bound_box)
            w = max(abs(v[1]) for v in pn.bound_box)
            for v in me.vertices:
                p = inv @ (mw @ v.co)
                if abs(p.y) < w and p.x * p.x + p.z * p.z < (R * 0.98) ** 2:
                    tot += 1
        ev.to_mesh_clear()
    return tot


# ---------------------------------------------------------------- cenas
def montar(M, passo, rot, dz_fileira=None):
    raizes = []
    for k, (tipo, cor, cons) in enumerate(LISTA):
        D = va.carro_antigo(f"ant_{k}_{tipo}", M, tipo, cor, conservacao=cons, escala=0.5)
        if dz_fileira is None:
            D["raiz"].location = ((k - 2.5) * passo, 0, 0)
        else:   # 2 fileiras de 3 (perfil): a de cima flutua
            D["raiz"].location = (((k % 3) - 1) * passo, 0, dz_fileira * (1 - k // 3))
        D["raiz"].rotation_euler = (0, 0, math.radians(rot))
        bpy.context.view_layer.update()
        print(tipo, cor, cons, "interpenetração (vértices):", checar_rodas(D))
        raizes.append(D["raiz"])
    return raizes


def cena_lineup(amostras, escala):
    nova_cena((int(2400 * escala), int(760 * escala)), amostras)
    raizes = montar({}, 2.30, -30)
    estudio()
    luzes(0, 14)
    so_nos_veiculos(raizes)
    camera((0.0, -19.5, 1.6), (0, 0, 0.34), lens=50)
    render(os.path.join(HERE, "antigos_real.png"))


def cena_perfis(amostras, escala):
    nova_cena((int(2400 * escala), int(1100 * escala)), amostras)
    raizes = montar({}, 2.45, 0, dz_fileira=1.15)
    estudio()
    luzes(0, 8)
    so_nos_veiculos(raizes)
    cam = camera((0.0, -20.0, 0.92), (0.0, 0.0, 0.92), lens=50)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 7.6
    render(os.path.join(HERE, "antigos_perfis.png"))


def cena_close(amostras, escala):
    """Close 3/4 traseira de 3 carros (lanternas, calotas, pintura gasta)."""
    nova_cena((int(1800 * escala), int(800 * escala)), amostras)
    M = {}
    raizes = []
    for k, (tipo, cor, cons) in enumerate([LISTA[3], LISTA[1], LISTA[2]]):
        D = va.carro_antigo(f"close_{k}", M, tipo, cor, conservacao=cons, escala=0.5)
        D["raiz"].location = ((k - 1) * 2.4, 0, 0)
        D["raiz"].rotation_euler = (0, 0, math.radians(-145 if k else -40))
        raizes.append(D["raiz"])
    estudio()
    luzes(0, 8)
    so_nos_veiculos(raizes)
    camera((0.0, -10.5, 1.5), (0, 0, 0.36), lens=50)
    render(os.path.join(HERE, "antigos_close.png"))


if __name__ == "__main__":
    alvo, amostras, escala = args()
    if "lineup" in alvo:
        cena_lineup(amostras, escala)
    if "perfis" in alvo:
        cena_perfis(amostras, escala)
    if "close" in alvo:
        cena_close(amostras, escala)
