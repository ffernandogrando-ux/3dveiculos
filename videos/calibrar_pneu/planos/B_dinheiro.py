"""Plano B: "Essa pessoa tá deixando DINHEIRO no ASFALTO e NEM SABE."
Câmera rasteira junto ao pneu murcho. Em "dinheiro" as moedinhas (1 real, bimetálicas) começam a sair debaixo do
pneu e rolam pelo asfalto na direção da câmera, desacelerando, bambeando e caindo deitadas (uma a uma). Em "asfalto"
as botas do Zé entram pela direita e param ao lado das moedas; em "nem sabe" a câmera sobe e mostra o Zé olhando para
baixo, preocupado. Push-in leve."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _rua as R
C = R.C
import boneco_adulto as ba
from mathutils import Vector

P = C.plano("B_dinheiro")
D = P["dur"]
t_din = R.palavra(P, "dinheiro", reserva=0.4)
t_asf = R.palavra(P, "asfalto", reserva=0.55)
t_nem = R.palavra(P, "nem sabe", "nem", reserva=0.8)
sc = C.setup(P)
R.dia(sc, sol=(50, 0, -35))
M = {}
c, xf, pn = R.cena_carro_rua(M)
yT = pn.y
# ---- moedas: saem do contato do pneu (lado de fora) e rolam para a câmera, em leque
import random
rnd = random.Random(5)
N = 8
for i in range(N):
    t0 = t_din + 0.05 + i * 0.13 + rnd.uniform(0, 0.05)
    rumo = -90 + rnd.uniform(-28, 32)                  # -90° = para -y (a câmera)
    ini = (pn.x + rnd.uniform(-0.12, 0.12), yT - 0.1, 0)
    dur = min(D - t0 - 0.05, 1.1 + rnd.uniform(0, 0.4))
    R.moeda_rolando(f"moeda{i}", M, ini, rumo, 0.35 + rnd.uniform(0, 0.45), t0, dur,
                    lado_cai=1 if i % 2 else -1, seed=i)
# moedas já caídas no chão (ele vem perdendo faz tempo)
for i in range(3):
    m = R.moeda(f"moeda_chao{i}", M)
    m.location = (pn.x + 0.25 - i * 0.2, yT - 0.32 - i * 0.07, 0.0015)
    m.rotation_euler = (math.radians(90), 0, math.radians(30 * i))

# ---- o Zé entra pela direita andando e para do lado do pneu, olhando para baixo
Z = ba.ze_adulto("ze", M, expressao="neutro", maos="todas")
arm, V = Z["arm"], Z["rosto"]
tz0 = t_asf + 0.05 - 0.9
tz1 = t_asf + 0.75
R.andar(Z, tz0, tz1, (pn.x + 1.9, yT - 0.35, 0), (pn.x + 0.42, yT - 0.2, 0))
Z["raiz"].location = (pn.x + 1.9, yT - 0.35, 0)
olha = {"tronco": (14, 0, -10), "pescoco": (12, 0, -6), "cabeca": (16, 0, -14), "quadril": (0, 0, 0),
        "coxa_e": (-4, -3, 0), "coxa_d": (0, 2, 0), "canela_e": (8, 0, 0), "canela_d": (4, 0, 0),
        "ombro_e": (-12, -14, 0), "cotovelo_e": (-55, 0, 10), "ombro_d": (-12, 14, 0), "cotovelo_d": (-55, 0, -10)}
R.krot(Z["raiz"], tz1 + 0.1, (0, 0, 90))
R.krot(Z["raiz"], tz1 + 0.55, (0, 0, 60))              # gira para a câmera/moedas
R.pose(Z, tz1 + 0.6, olha)
R.pose(Z, D, dict(olha, tronco=(17, 0, -10), cabeca=(19, -5, -14)))
ba.mao(Z, "e", "relaxada", 1)
ba.mao(Z, "d", "relaxada", 1)
ba.mao(Z, "e", "aberta", C.F(tz1 + 0.45))
ba.mao(Z, "d", "aberta", C.F(tz1 + 0.45))
for no, keys in (("sobr_inc", [(0, 0), (t_nem, 0), (t_nem + 0.3, -0.35)]),
                 ("sobr_alt", [(0, 0), (t_nem, 0.2), (t_nem + 0.3, 0.7)]),
                 ("sorriso", [(0, 0.15), (t_nem, 0.0), (t_nem + 0.3, -0.4)]),
                 ("olhar_z", [(0, 0), (tz1 + 0.4, -0.8)])):
    for t, v in keys:
        C.key_val(V[no], t, v)

# ---- câmera rasteira: push-in leve; em "nem sabe" sobe e inclina para mostrar o Zé
c0 = Vector((pn.x + 0.55, yT - 1.35, 0.26))
a0 = Vector((pn.x + 0.05, yT - 0.15, 0.2))
cam, al = R.camera(c0, a0, lens=24, dof=2.8)
R.kloc(cam, 0, c0)
R.kloc(cam, t_asf + 0.4, c0 + (a0 - c0) * 0.04)
R.kloc(cam, D, c0 + (a0 - c0) * 0.05 + Vector((0, 0, 0.12)))
R.kloc(al, 0, a0)
R.kloc(al, t_asf + 0.4, a0)
R.kloc(al, D, a0 + Vector((0.18, 0, 0.75)))
cam.data.dof.focus_object = None
cam.data.dof.focus_distance = 1.25

C.renderizar(P, sys.argv)
