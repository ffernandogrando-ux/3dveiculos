"""Modelos 3D prontos da NVIDIA (SimReady Assets, Hugging Face) dentro das cenas do Blender.

Coleção aberta com ~2.700 objetos reais (peças de motor, freio, suspensão, ferramentas, cozinha, banheiro,
hospital, armazém...), em OpenUSD, com materiais PBR. Licença CC BY 4.0: pode usar em vídeo monetizado, mas o
crédito é obrigatório na descrição do post (use `creditos()`).

Uso dentro de uma cena (bpy):
    import simready as sr
    motor = sr.importar("engineAssembly_v8_engine_a01", estilo="lowpoly", altura=1.2, loc=(0, 0, 0))
    freio = sr.importar("brakeSystem_brakes_assembly_a01", estilo="realista", altura=0.6, cores={"orange": "#E53935"})
    print(sr.creditos())

Linha de comando (com o Python do venv do Blender):
    $PY simready.py buscar freio brake         # procura nomes no catálogo
    $PY simready.py baixar <nome>              # só baixa para o cache
    $PY simready.py previa <nome> saida.png [lowpoly|realista]
    $PY simready.py glb <nome> saida.glb [tris]   # GLB leve para Three.js / React Three Fiber

Estilos:
- "lowpoly": simplifica a malha (padrão 40 mil triângulos), troca as texturas por cores chapadas (paleta por
  palavra do nome do material: orange, black, chrome, steel...) e sombreamento facetado. Combina com o motor3d.
- "realista": mantém os materiais da NVIDIA (texturas reduzidas para 1024 px para poupar memória).

Cada asset pesa de 0,3 a 2 GB no original (texturas 4K); o download já pula miniaturas, materiais MDL e as cópias
para outros simuladores, e fica em ~/.cache/simready (ou $SIMREADY_CACHE). Não vai para o git.
"""
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

DATASET = "nvidia/simready-assets"
HF = "https://huggingface.co"
CACHE = os.path.expanduser(os.environ.get("SIMREADY_CACHE", "~/.cache/simready"))
CREDITO = "Modelos 3D: NVIDIA SimReady Assets (huggingface.co/datasets/nvidia/simready-assets), licença CC BY 4.0"

# arquivos que o Blender não usa (miniaturas, materiais MDL, variantes de outros simuladores)
_PULAR = ("/.thumbs/", "instances_mujoco", "instances_newton", ".mdl", "/source_assets/")


# ================================================================ catálogo e download
def _json(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r), r.headers.get("Link", "")


def catalogo(atualizar=False):
    """Lista com o nome de todos os assets (guardada em cache)."""
    arq = os.path.join(CACHE, "catalogo.json")
    if os.path.exists(arq) and not atualizar:
        return json.load(open(arq))
    nomes, url = [], f"{HF}/api/datasets/{DATASET}/tree/main"
    while url:
        dados, link = _json(url)
        nomes += [d["path"] for d in dados if d["type"] == "directory"]
        prox = [p.split(";")[0].strip("<> ") for p in link.split(",") if 'rel="next"' in p]
        url = prox[0] if prox else None
    os.makedirs(CACHE, exist_ok=True)
    json.dump(sorted(nomes), open(arq, "w"))
    return sorted(nomes)


def buscar(*termos):
    """Nomes que contêm todos os termos (sem diferenciar maiúsculas)."""
    t = [x.lower() for x in termos]
    return [n for n in catalogo() if all(x in n.lower() for x in t)]


def _baixar_arquivo(caminho):
    destino = os.path.join(CACHE, caminho)
    if os.path.exists(destino):
        return
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    url = f"{HF}/datasets/{DATASET}/resolve/main/{urllib.parse.quote(caminho)}"
    tmp = destino + ".part"
    urllib.request.urlretrieve(url, tmp)
    os.replace(tmp, destino)


def baixar(nome):
    """Baixa o asset para o cache (só o que o Blender usa) e devolve o caminho do .usd principal."""
    pasta = os.path.join(CACHE, nome, "simready_usd")
    pronto = os.path.join(CACHE, nome, ".completo")
    if not os.path.exists(pronto):
        dados, _ = _json(f"{HF}/api/datasets/{DATASET}/tree/main/{urllib.parse.quote(nome)}?recursive=true")
        arquivos = [d["path"] for d in dados if d["type"] == "file"
                    and not any(p in "/" + d["path"] for p in _PULAR)]
        if not arquivos:
            raise ValueError(f"asset não encontrado: {nome} (tente simready.buscar)")
        mb = sum(d.get("size", 0) for d in dados if d["path"] in arquivos) / 1e6
        print(f"simready: baixando {nome} ({len(arquivos)} arquivos, {mb:.0f} MB)...")
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(_baixar_arquivo, arquivos))
        open(pronto, "w").close()
    usds = sorted(f for f in os.listdir(pasta) if f.endswith(".usd") and f.startswith("sm_"))
    return os.path.join(pasta, usds[0])


# ================================================================ importação no Blender
_PALETA = [  # palavra no nome do material -> cor chapada (hex, sRGB)
    ("orange", "#F07A1A"), ("red", "#D8312A"), ("yellow", "#F2C230"), ("blue", "#3C78D8"), ("green", "#3FA34D"),
    ("white", "#E8E8E4"), ("black", "#2A2B30"), ("rubber", "#1F2023"), ("tire", "#1F2023"), ("leather", "#3A2E28"),
    ("copper", "#C8743A"), ("bronze", "#C8743A"), ("brass", "#C9A13B"), ("gold", "#D4AF37"),
    ("chrome", "#C9CDD3"), ("alumin", "#B5BAC2"), ("stainless", "#A9AEB5"), ("steel", "#8E949C"),
    ("iron", "#6E737A"), ("metal", "#9AA0A8"), ("wood", "#A87B4F"), ("glass", "#BFE3F2"),
    ("plastic", "#4A4D55"), ("fabric", "#6F7A8C"), ("paper", "#EDE6D6"), ("cardboard", "#C9A16B"),
]


def _lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]


def _cor(nome_mat, cores):
    n = nome_mat.lower()
    for chave, hexcol in list((cores or {}).items()) + _PALETA:
        if chave.lower() in n:
            return hexcol
    return "#A3A6AB"


def _mat_chapado(bpy, nome, hexcol, transparente=False):
    m = bpy.data.materials.get(nome)
    if m:
        return m
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = _lin(hexcol)
    b.inputs["Roughness"].default_value = 0.85
    if transparente:
        b.inputs["Alpha"].default_value = 0.35
    return m


def _caixa_limite(objs):
    from mathutils import Vector
    mn, mx = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mn = Vector(map(min, mn, w))
            mx = Vector(map(max, mx, w))
    return mn, mx


def importar(nome, estilo="lowpoly", tris=40000, altura=None, loc=(0, 0, 0), rot_z=0.0, cores=None,
             textura_max=1024, nome_obj=None):
    """Importa o asset na cena atual e devolve um Empty pai (base no chão, centrado em `loc`).

    estilo: "lowpoly" (cores chapadas, combina com o motor3d) ou "realista" (materiais da NVIDIA).
    tris: alvo de triângulos depois de simplificar (None = malha original, pode passar de 1 milhão).
    altura: altura final em unidades da cena (None = tamanho real, em metros).
    cores: troca de cor no lowpoly, ex.: {"orange": "#E53935", "caliper": "#E53935"} (palavra do nome do material).
    """
    import bpy
    from mathutils import Vector

    usd = baixar(nome)
    antes = set(bpy.data.objects)
    mats_antes, imgs_antes = set(bpy.data.materials), set(bpy.data.images)
    bpy.ops.wm.usd_import(filepath=usd, import_cameras=False, import_lights=False,
                          support_scene_instancing=False)  # malhas reais (com instâncias, peças somem)
    novos = [o for o in bpy.data.objects if o not in antes]
    malhas = [o for o in novos if o.type == "MESH"]

    # colisores e auxiliares de física não aparecem no vídeo
    for o in malhas[:]:
        if any(p in o.name.lower() for p in ("collision", "collider", "proxy")):
            bpy.data.objects.remove(o)
            malhas.remove(o)
            novos.remove(o)

    total = sum(len(p.vertices) - 2 for o in malhas for p in o.data.polygons)
    if tris and total > tris:
        razao = max(tris / total, 0.005)
        for o in malhas:
            mod = o.modifiers.new("simplificar", "DECIMATE")
            mod.ratio = razao
            mod.use_collapse_triangulate = True
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        for o in malhas:  # aplica o modificador (cena mais leve para o render)
            nova = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
            velha = o.data
            o.modifiers.clear()
            o.data = nova
            if velha.users == 0:
                bpy.data.meshes.remove(velha)

    if estilo == "lowpoly":
        for o in malhas:
            for sl in o.material_slots:
                if sl.material:
                    n = sl.material.name
                    sl.material = _mat_chapado(bpy, f"sr_{_cor(n, cores)}_{'vidro' if 'glass' in n.lower() else 'opaco'}",
                                               _cor(n, cores), "glass" in n.lower())
            for p in o.data.polygons:
                p.use_smooth = False
        for m in set(bpy.data.materials) - mats_antes:
            if m.users == 0 and not m.name.startswith("sr_"):
                bpy.data.materials.remove(m)
        for im in set(bpy.data.images) - imgs_antes:
            if im.users == 0:
                bpy.data.images.remove(im)
    elif textura_max:
        for im in set(bpy.data.images) - imgs_antes:
            if im.size[0] > textura_max:
                im.scale(textura_max, max(1, int(textura_max * im.size[1] / im.size[0])))

    # pai: base no chão, centro em x/y, escala para a altura pedida
    mn, mx = _caixa_limite(malhas)
    pai = bpy.data.objects.new(nome_obj or f"sr_{nome}", None)
    bpy.context.scene.collection.objects.link(pai)
    pai.location = ((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z)
    bpy.context.view_layer.update()
    for o in novos:
        if o.parent is None or o.parent not in novos:
            mw = o.matrix_world.copy()
            o.parent = pai
            o.matrix_world = mw
    esc = (altura / max(mx.z - mn.z, 1e-6)) if altura else 1.0
    pai.location = Vector(loc)
    pai.scale = (esc, esc, esc)
    pai.rotation_euler = (0, 0, rot_z)
    bpy.context.view_layer.update()

    cena = bpy.context.scene
    lista = list(cena.get("simready", []))
    if nome not in lista:
        cena["simready"] = lista + [nome]
    return pai


def creditos(cena=None):
    """Texto de crédito para a descrição do post (obrigatório pela licença CC BY 4.0)."""
    import bpy
    usados = list((cena or bpy.context.scene).get("simready", []))
    return CREDITO + (f". Usados: {', '.join(usados)}." if usados else ".")


# ================================================================ prévia e GLB
def _cena_previa(bpy, pai):
    from mathutils import Vector
    cena = bpy.context.scene
    malhas = [o for o in pai.children_recursive if o.type == "MESH"]
    mn, mx = _caixa_limite(malhas)
    c, r = (mn + mx) / 2, (mx - mn).length / 2
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cena.collection.objects.link(cam)
    cena.camera = cam
    cam.data.lens = 50
    cam.location = c + Vector((r * 2.2, -r * 2.2, r * 1.5))
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    sol = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sol.data.energy, sol.data.angle = 3.5, 0.3
    sol.rotation_euler = (0.8, 0.2, 0.9)
    cena.collection.objects.link(sol)
    w = bpy.data.worlds.new("ceu")
    cena.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = _lin("#CFE3F5")
    bpy.ops.mesh.primitive_plane_add(size=r * 30, location=(c.x, c.y, mn.z))
    bpy.context.object.data.materials.append(_mat_chapado(bpy, "chao", "#6CC36C"))
    cena.render.engine = "CYCLES"
    cena.cycles.samples = 16
    cena.cycles.use_denoising = True
    cena.render.resolution_x = cena.render.resolution_y = 720


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, args = argv[0], argv[1:]
    if cmd == "buscar":
        for n in buscar(*args):
            print(n)
        return
    if cmd == "baixar":
        print(baixar(args[0]))
        return
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if cmd == "previa":
        estilo = args[2] if len(args) > 2 else "lowpoly"
        _cena_previa(bpy, importar(args[0], estilo=estilo))
        bpy.context.scene.render.filepath = os.path.abspath(args[1])
        bpy.ops.render.render(write_still=True)
    elif cmd == "glb":
        tris = int(args[2]) if len(args) > 2 else 60000
        importar(args[0], estilo="realista", tris=tris)
        bpy.ops.export_scene.gltf(filepath=os.path.abspath(args[1]), export_apply=True,
                                  export_image_format="JPEG", export_jpeg_quality=85)
        print(f"GLB: {args[1]} ({os.path.getsize(args[1]) / 1e6:.1f} MB)")
        print("Crédito:", creditos())
    else:
        print("comando desconhecido:", cmd)


if __name__ == "__main__":
    _main(sys.argv[1:])
