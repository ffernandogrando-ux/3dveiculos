"""Plano H: "RESULTADO: TROCA O JOGO DE PNEU antes da hora, e ainda acha que a CULPA é do PNEU BARATO."
Oficina do Zé. Abre colado numa pilha de pneus velhos deitados com as BEIRADAS gastas (ombros lisos e claros, miolo
com sulco); em "troca" o último pneu velho cai na pilha (assenta com quique pequeno) e a câmera recua, revelando o
cara de braços cruzados ao lado e o Zé ao fundo. Em "e ainda acha" o cara fecha a cara (bravo) e em "culpa" aponta a
etiqueta amarela "BARATO" pendurada na pilha, falando; a etiqueta balança. O Zé balança a cabeça ("não é isso")."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _rua as R
C = R.C
import bpy
import boneco_adulto as ba
import motor as mt
from mathutils import Vector

P = C.plano("H_resultado")
D = P["dur"]
t_troca = R.palavra(P, "troca", reserva=0.13)
t_hora = R.palavra(P, "antes da hora", "antes", reserva=0.36)
t_acha = R.palavra(P, "e ainda acha", "ainda", reserva=0.55)
t_culpa = R.palavra(P, "culpa", reserva=0.75)
t_barato = R.palavra(P, "barato", reserva=0.89)
sc = C.setup(P)
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = -1.0
w = bpy.data.worlds.new("mundo"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = mt.lin("#2A2F36")
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4
M = {}
ba.oficina(M, largura=9, fundo_y=1.9)


def luz(pos, energia, tam, cor, alvo=(0.2, 0.5, 1.0)):
    d = bpy.data.lights.new("a", "AREA"); d.energy, d.size = energia, tam; d.color = mt.lin(cor)[:3]
    o = mt.link(bpy.data.objects.new("a", d)); o.location = pos
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")


luz((-2.2, -2.4, 2.2), 480, 2.0, "#FFE8D0")
luz((3.0, -2.2, 1.8), 300, 3.0, "#DCE6FF")
luz((1.8, 1.4, 2.4), 380, 1.0, "#CFE0FF")

# ---- pilha de pneus velhos (deitados) + pilha de pneus novos atrás
PX, PY = 0.35, 0.55
h = 0.178
pilha = []
for k in range(4):
    pv = R.pneu_velho(f"velho{k}", M, gasto=1.0)
    pv.rotation_euler = (math.radians(90), 0, math.radians(k * 37))
    pv.location = (PX + 0.012 * ((k * 5) % 3 - 1), PY + 0.01 * ((k * 3) % 3 - 1), h / 2 + k * h)
    pilha.append(pv)
for k in range(4):
    nv = R.pneu_velho(f"novo{k}", M, gasto=0.0)
    nv.rotation_euler = (math.radians(90), 0, 0)
    nv.location = (PX + 0.85, PY + 0.75, h / 2 + k * h)
# o último pneu velho cai na pilha em "troca"
topo = pilha[-1]
z_fim = topo.location.z
tc = t_troca + 0.12
R.kloc(topo, 0, (PX, PY, z_fim + 0.9))
R.kloc(topo, tc, (PX, PY, z_fim + 0.9))
R.kloc(topo, tc + 0.28, (PX, PY, z_fim))
R.kloc(topo, tc + 0.38, (PX, PY, z_fim + 0.025))
R.kloc(topo, tc + 0.48, (PX, PY, z_fim))
R.krot(topo, tc, (90, 0, 140))
R.krot(topo, tc + 0.28, (92, 0, 111))
R.krot(topo, tc + 0.6, (90, 0, 111))
topo.hide_render = True
topo.keyframe_insert("hide_render", frame=1)
topo.hide_render = False
topo.keyframe_insert("hide_render", frame=C.F(tc))

# ---- etiqueta "BARATO" pendurada no pneu de cima (balança quando é apontada)
et_piv = mt.empty("et_piv", (PX - 0.05, PY - 0.3, 3 * h - 0.01))
et = R.etiqueta("etiqueta", M)
et.parent = et_piv
et.location = (-0.12, 0, -0.12)
et.rotation_euler = (0, math.radians(-25), 0)
t_bal = t_culpa + 0.25
for k, a in enumerate((0, 10, -7, 5, -3, 1.5, 0)):
    R.krot(et_piv, t_bal + k * 0.22, (a * 0.3, a, 0))
R.krot(et_piv, 0, (0, 0, 0))

# ---- o cara: braços cruzados → bravo → aponta a etiqueta falando
Z = ba.ze_adulto("cara", M, expressao="neutro", maos="todas", **R.CARA)
arm, V = Z["arm"], Z["rosto"]
Z["raiz"].location = (PX - 0.72, PY - 0.2, 0)
Z["raiz"].rotation_euler = (0, 0, math.radians(18))
cruz = {"tronco": (0, -3, 0), "pescoco": (0, 0, 0), "cabeca": (0, 3, 8),        # mãos na cintura
        "ombro_e": (5, -28, -20), "cotovelo_e": (-70, 0, -30), "ombro_d": (5, 28, 20), "cotovelo_d": (-70, 0, 30),
        "mao_e": (0, 0, 0)}
aponta = dict(cruz, tronco=(6, -4, 14), pescoco=(4, 0, 8), cabeca=(10, 0, 18),
              ombro_e=(-38, -42, 0), cotovelo_e=(-12, 0, 0), mao_e=(-8, 0, 0))
ba.mao(Z, "e", "punho", 1)
ba.mao(Z, "d", "punho", 1)
R.pose(Z, 0, cruz)
R.pose(Z, t_acha, dict(cruz, cabeca=(-2, 3, 0)))
R.pose(Z, t_acha + 0.3, dict(cruz, tronco=(2, -3, 0), cabeca=(4, -4, -10)))       # encara a câmera, bravo
R.pose(Z, t_culpa - 0.05, dict(cruz, tronco=(2, -3, 4), cabeca=(4, -4, -8)))
R.pose(Z, t_culpa + 0.25, aponta)
R.pose(Z, t_barato + 0.1, dict(aponta, ombro_e=(-42, -42, 0), cabeca=(8, -4, 6)))
R.pose(Z, D, dict(aponta, ombro_e=(-41, -42, 0), cabeca=(8, -5, 4)))
ba.mao(Z, "e", "aponta", C.F(t_culpa + 0.1))
for no, keys in (("sobr_inc", [(0, 0), (t_acha, 0), (t_acha + 0.3, 0.45)]),
                 ("sobr_alt", [(0, 0), (t_acha, 0), (t_acha + 0.3, -0.6)]),
                 ("sorriso", [(0, 0.1), (t_acha, 0.0), (t_acha + 0.3, -0.6)]),
                 ("abre_olho", [(0, 1), (t_acha + 0.3, 0.85)])):
    for t, v in keys:
        C.key_val(V[no], t, v)
R.fala(V, t_acha + 0.1, D - 0.05, forte=0.75, seed=7)
R.piscar(V, 0.9)

# ---- o Zé ao fundo, braços cruzados, balança a cabeça
ZZ = ba.ze_adulto("ze", M, pose="parado", expressao="preocupado", maos="todas")
ba.mao(ZZ, "e", "punho", 1); ba.mao(ZZ, "d", "punho", 1)
for o_, v_ in cruz.items():
    if o_.startswith(("ombro", "cotovelo")):
        ba.girar(ZZ["arm"], o_, *v_)
ZZ["raiz"].location = (PX + 1.3, PY + 1.25, 0)
ZZ["raiz"].rotation_euler = (0, 0, math.radians(-30))
for k, z in enumerate((0, -9, 7, -7, 5, 0)):
    R.pose(ZZ, t_culpa + k * 0.2, {"cabeca": (4, 3, z)})
R.pose(ZZ, 0, {"cabeca": (4, 3, 0)})

# ---- câmera: abre colada nas beiradas gastas, recua em "troca" para o plano dos dois; push-in leve no fim
cA = Vector((PX + 0.5, PY - 1.1, 0.75)); aA = Vector((PX - 0.08, PY, 0.42))
cB = Vector((PX - 0.1, PY - 3.7, 1.35)); aB = Vector((PX - 0.15, PY, 0.95))
cam, al = R.camera(cA, aA, lens=32, dof=4.0)
R.kloc(cam, 0, cA); R.kloc(al, 0, aA)
R.kloc(cam, tc, cA + (aA - cA) * 0.05); R.kloc(al, tc, aA)
tm = (tc + t_hora + 0.5) / 2               # recua pela direita (não passa pelo cara)
R.kloc(cam, tm, (PX + 0.75, PY - 2.4, 1.05)); R.kloc(al, tm, (PX - 0.05, PY, 0.7))
R.kloc(cam, t_hora + 0.5, cB); R.kloc(al, t_hora + 0.5, aB)
R.kloc(cam, D, cB + (aB - cB) * 0.04); R.kloc(al, D, aB + Vector((0.1, 0, -0.05)))

C.renderizar(P, sys.argv)
