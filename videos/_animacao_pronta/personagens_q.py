"""Prova dos personagens Quaternius (motor3d/personagem_q.py): o cara e o Zé, de frente e 3/4, close da cintura e
do rosto (3 expressões). Saída: personagens_q.png.   AMOSTRAS=10 ~/.venv-video/bin/python personagens_q.py"""
import os, sys, math, time
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "motor3d"))
import bpy
from mathutils import Vector
import motor as mt
import personagem_q as pq

A = int(os.environ.get("AMOSTRAS", 10))
sc = mt.setup(1, samples=A, res=(576, 1024))
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = -0.6
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = mt.lin("#B9C4CE")
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
chao = mt.box("chao", -6, 6, -6, 6, -0.01, 0, None)
m = bpy.data.materials.new("chao"); m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = mt.lin("#8E9399")
chao.data.materials.append(m)
for pos, e, cor in (((-2.2, -3.0, 3.2), 380, "#FFE8D0"), ((2.6, -2.0, 2.2), 140, "#DCE6FF"), ((0.5, 2.5, 3.0), 220, "#FFFFFF")):
    d = bpy.data.lights.new("a", "AREA"); d.energy, d.size = e, 2.0; d.color = mt.lin(cor)[:3]
    o = mt.link(bpy.data.objects.new("a", d)); o.location = pos
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (Vector((0, 0, 1.0)) - Vector(pos)).to_track_quat("-Z", "Y")
t0 = time.time()
Q = pq.personagem("cara"); pq.colocar(Q, (-0.45, 0, 0))
Z = pq.personagem("ze"); pq.colocar(Z, (0.45, 0, 0))
# pose de repouso (T-pose do arquivo) → parado da biblioteca, quadro fixo
for P in (Q, Z):
    pq._acoes_ual(P)
    import animacao_pronta as ap
    ap.aplicar_acao(P, "Idle_Loop")
print("montagem: %.1fs" % (time.time() - t0))
cd = bpy.data.cameras.new("c"); cam = mt.link(bpy.data.objects.new("c", cd)); sc.camera = cam
al = mt.empty("al", (0, 0, 1)); ct = cam.constraints.new("TRACK_TO"); ct.target = al
ct.track_axis, ct.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
V = {"cara": Q, "ze": Z}
tomadas = [("frente", (0, -4.6, 1.05), (0, 0, 0.92), 40),
           ("tres_quartos", (2.9, -3.6, 1.2), (0, 0, 0.92), 40),
           ("cintura", (-0.1, -1.5, 1.05), (-0.45, 0, 0.98), 60),
           ("cintura_ze", (1.05, -1.4, 1.05), (0.45, 0, 0.98), 60)]
out = []
sc.frame_set(10)
for nome, c, a, lens in tomadas:
    cam.location, al.location, cd.lens = c, a, lens
    sc.render.filepath = os.path.join(AQUI, f"_pq_{nome}.png")
    t = time.time(); bpy.ops.render.render(write_still=True); print(nome, "%.1fs" % (time.time() - t))
    out.append(sc.render.filepath)
# rostos: 3 expressões em cada um
for exp in ("sorriso", "bravo", "surpreso"):
    for P, x in ((Q, -0.45), (Z, 0.45)):
        for k, v in dict(abre_olho=1.0, sobr_alt=0.0, sobr_inc=0.0, sorriso=0.15, aperta=0.0, boca_aberta=0.0,
                         boca_larg=0.0, boca_redonda=0.0, **{}).items():
            P["rosto"][k].outputs[0].default_value = v
        for k, v in pq.ba.EXPRESSOES[exp].items():
            P["rosto"][k].outputs[0].default_value = v
    for P, x, nm in ((Q, -0.45, "cara"), (Z, 0.45, "ze")):
        h = P["arm"].matrix_world @ P["arm"].pose.bones["Head"].head
        cam.location, al.location, cd.lens = h + Vector((0.12, -0.75, 0.12)), h + Vector((0, 0, 0.08)), 85
        sc.render.filepath = os.path.join(AQUI, f"_pq_rosto_{nm}_{exp}.png")
        bpy.ops.render.render(write_still=True)
from PIL import Image, ImageDraw
W = 288
def ab(p, crop=None):
    im = Image.open(p).convert("RGB")
    return im.resize((W, 512))
lin1 = [ab(out[0]), ab(out[1]), ab(out[2]), ab(out[3])]
rost = []
for nm in ("cara", "ze"):
    for exp in ("sorriso", "bravo", "surpreso"):
        im = Image.open(os.path.join(AQUI, f"_pq_rosto_{nm}_{exp}.png")).convert("RGB").crop((0, 250, 576, 890)).resize((192, 213))
        ImageDraw.Draw(im).text((6, 4), f"{nm}: {exp}", fill=(255, 255, 255))
        rost.append(im)
folha = Image.new("RGB", (W * 4, 512 + 213), (24, 24, 24))
for k, im in enumerate(lin1):
    folha.paste(im, (k * W, 0))
for k, im in enumerate(rost):
    folha.paste(im, ((k % 6) * 192, 512 + (k // 6) * 213))
folha.save(os.path.join(AQUI, "personagens_q.png"))
for f in os.listdir(AQUI):
    if f.startswith("_pq_"):
        os.remove(os.path.join(AQUI, f))
print("ok")
