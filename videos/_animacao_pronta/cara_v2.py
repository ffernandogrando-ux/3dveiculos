"""Prova do "cara" v2 (motor3d/personagem_q.py): frente, 3/4, costas, close da gola/regata e do cinto/jeans.
Saída: cara_v2.png.   AMOSTRAS=10 ~/.venv-video/bin/python cara_v2.py"""
import os, sys, time
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "motor3d"))
import bpy
from mathutils import Vector
import motor as mt
import personagem_q as pq
import animacao_pronta as ap
from PIL import Image, ImageDraw

A = int(os.environ.get("AMOSTRAS", 10))
sc = mt.setup(1, samples=A, res=(576, 1024))
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = -0.7
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = mt.lin("#B9C4CE")
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.5
chao = mt.box("chao", -6, 6, -6, 6, -0.01, 0, None)
m = bpy.data.materials.new("chao"); m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = mt.lin("#6E7378")
chao.data.materials.append(m)
for pos, e, cor in (((-2.2, -3.0, 3.2), 330, "#FFE8D0"), ((2.6, -2.0, 2.2), 120, "#DCE6FF"),
                    ((0.5, 2.8, 3.0), 260, "#FFFFFF")):
    d = bpy.data.lights.new("a", "AREA"); d.energy, d.size = e, 2.0; d.color = mt.lin(cor)[:3]
    o = mt.link(bpy.data.objects.new("a", d)); o.location = pos
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (Vector((0, 0, 1.0)) - Vector(pos)).to_track_quat("-Z", "Y")
t0 = time.time()
Q = pq.personagem("cara")
pq._acoes_ual(Q)
ap.aplicar_acao(Q, "Idle_Loop")
print("montagem: %.1fs" % (time.time() - t0))
cd = bpy.data.cameras.new("c"); cam = mt.link(bpy.data.objects.new("c", cd)); sc.camera = cam
al = mt.empty("al", (0, 0, 1)); ct = cam.constraints.new("TRACK_TO"); ct.target = al
ct.track_axis, ct.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
tomadas = [("frente", (0, -3.6, 1.0), (0, 0, 0.9), 40),
           ("tres_quartos", (2.3, -2.8, 1.15), (0, 0, 0.9), 40),
           ("costas", (-0.6, 3.6, 1.0), (0, 0, 0.9), 40),
           ("gola", (0.25, -1.15, 1.5), (0, 0, 1.42), 50),
           ("cinto", (0.3, -0.95, 0.95), (0, 0, 0.84), 50)]
sc.frame_set(10)
ims = []
for nome, c, a, lens in tomadas:
    cam.location, al.location, cd.lens = c, a, lens
    sc.render.filepath = os.path.join(AQUI, f"_v2_{nome}.png")
    t = time.time(); bpy.ops.render.render(write_still=True); print(nome, "%.1fs" % (time.time() - t), flush=True)
    im = Image.open(sc.render.filepath).convert("RGB").resize((288, 512))
    ImageDraw.Draw(im).text((6, 4), nome, fill=(255, 255, 255))
    ims.append(im)
    os.remove(sc.render.filepath)
folha = Image.new("RGB", (288 * 5, 512))
for k, im in enumerate(ims):
    folha.paste(im, (k * 288, 0))
folha.save(os.path.join(AQUI, "cara_v2.png"))
print("ok")
