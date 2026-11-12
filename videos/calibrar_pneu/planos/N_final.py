"""Plano N (final): close do Zé na oficina perguntando "E aí, quando foi a última vez que você calibrou?".
Fala animada (boca abre/fecha), sobrancelha sobe na pergunta, piscada, cabeça inclina; push-in leve.
O "?" entra na montagem (carimbos)."""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import comum as C
import bpy
from mathutils import Vector
import motor as mt
import boneco_adulto as ba

P = C.plano("N_final")
D = P["dur"]
sc = C.setup(P)
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = -1.0
w = bpy.data.worlds.new("mundo"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = mt.lin("#2A2F36")
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4
M = {}
ba.oficina(M, largura=8, fundo_y=1.6)
Z = ba.ze_adulto("ze", M, pose="explica", expressao="fala")
Z["raiz"].rotation_euler = (0, 0, math.radians(-12))
arm, R = Z["arm"], Z["rosto"]

# fala: boca abre e fecha (sílabas) até ~75 % do plano, depois sorriso de pergunta
t, k = 0.0, 0
while t < D * 0.75:
    C.key_val(R["boca_aberta"], t, 0.75 if k % 2 == 0 else 0.15)
    t += 0.13 + 0.05 * ((k * 7) % 3)
    k += 1
C.key_val(R["boca_aberta"], D * 0.8, 0.0)
C.key_val(R["sorriso"], 0.0, 0.35)
C.key_val(R["sorriso"], D * 0.8, 0.9)
# sobrancelha sobe na pergunta, piscada no meio
C.key_val(R["sobr_alt"], 0.0, 0.3)
C.key_val(R["sobr_alt"], D * 0.35, 1.2)
C.key_val(R["sobr_alt"], D, 1.0)
for tt, v in ((D * 0.5 - 0.06, 1.0), (D * 0.5, 0.05), (D * 0.5 + 0.08, 1.0)):
    C.key_val(R["abre_olho"], tt, v)
# cabeça inclina na pergunta; mãos abertas sobem um pouco ("e aí?")
C.key_rot(arm, "cabeca", 0.0, 0, 3, 4)
C.key_rot(arm, "cabeca", D * 0.45, -4, 8, 8)
C.key_rot(arm, "cabeca", D, -4, 9, 9)
for t_, f in ((0.0, 0.0), (D * 0.4, 1.0), (D, 1.0)):
    C.key_rot(arm, "ombro_e", t_, -25 - 15 * f, -18 - 6 * f, 0)
    C.key_rot(arm, "ombro_d", t_, -25 - 15 * f, 18 + 6 * f, 0)
    C.key_rot(arm, "cotovelo_e", t_, -60 - 15 * f, 0, 10)
    C.key_rot(arm, "cotovelo_d", t_, -60 - 15 * f, 0, -10)


def luz(pos, energia, tam, cor, alvo=(0, 0, 1.4)):
    d = bpy.data.lights.new("a", "AREA"); d.energy, d.size = energia, tam; d.color = mt.lin(cor)[:3]
    o = mt.link(bpy.data.objects.new("a", d)); o.location = pos
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")


luz((-2.2, -2.2, 1.9), 420, 2.0, "#FFE8D0")
luz((3.0, -2.2, 1.8), 300, 3.0, "#DCE6FF")
luz((1.8, 1.2, 2.2), 900, 1.0, "#CFE0FF")
cd = bpy.data.cameras.new("cam"); cd.lens = 70
cd.dof.use_dof = True; cd.dof.focus_distance = 1.9; cd.dof.aperture_fstop = 2.8
cam = mt.link(bpy.data.objects.new("cam", cd)); sc.camera = cam
alvo = Vector((0.1, 0, 1.42))
for t_, d in ((0.0, 2.6), (D, 2.38)):          # push-in ~9 %
    cam.location = alvo + Vector((-0.32, -1.0, 0.05)).normalized() * d
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (alvo - cam.location).to_track_quat("-Z", "Y")
    cam.keyframe_insert("location", frame=C.F(t_)); cam.keyframe_insert("rotation_quaternion", frame=C.F(t_))
C.renderizar(P, sys.argv)
