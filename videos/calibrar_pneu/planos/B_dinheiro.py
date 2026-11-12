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
    R.moeda_rolando(f"moeda{i}", M, ini, rumo, 0.3 + rnd.uniform(0, 0.4), t0, dur, r=0.03,
                    lado_cai=1 if i % 2 else -1, seed=i)
# moedas já caídas no chão (ele vem perdendo faz tempo)
for i in range(3):
    m = R.moeda(f"moeda_chao{i}", M, r=0.03)
    m.location = (pn.x + 0.25 - i * 0.2, yT - 0.32 - i * 0.07, 0.0015)
    m.rotation_euler = (math.radians(90), 0, math.radians(30 * i))

# ---- o Zé entra pela direita andando e para do lado do pneu, olhando para baixo
Z = ba.ze_adulto("ze", M, expressao="neutro", maos="todas")
arm, V = Z["arm"], Z["rosto"]
tz0 = t_asf + 0.05 - 0.9
tz1 = t_asf + 0.75
dest = (pn.x + 0.88, yT + 0.12, 0)
R.andar(Z, tz0, tz1, (pn.x + 2.3, yT + 0.05, 0), dest)
R.krot(Z["raiz"], tz1 + 0.05, (0, 0, 90))
R.krot(Z["raiz"], tz1 + 0.45, (0, 0, -22))              # vira para as moedas
fica = {"tronco": (0, -3, 0), "pescoco": (0, 0, 0), "cabeca": (8, 0, 0), "quadril": (0, 0, 0),
        "coxa_e": (-4, -3, 0), "coxa_d": (0, 2, 0), "canela_e": (6, 0, 0), "canela_d": (4, 0, 0),
        "ombro_e": (-5, -6, 0), "cotovelo_e": (-20, 0, 0), "ombro_d": (-5, 6, 0), "cotovelo_d": (-20, 0, 0)}
curva = {"tronco": (34, 0, 0), "pescoco": (-6, 0, 0), "cabeca": (-4, 0, 0), "quadril": (8, 0, 0),
         "coxa_e": (-30, -4, 0), "coxa_d": (-30, 4, 0), "canela_e": (42, 0, 0), "canela_d": (42, 0, 0),
         "ombro_e": (-50, -6, 0), "cotovelo_e": (-14, 0, 0), "ombro_d": (-50, 6, 0), "cotovelo_d": (-14, 0, 0)}
R.pose(Z, tz1 + 0.3, fica)
R.pose(Z, min(D - 0.1, max(t_nem, tz1 + 0.5) + 0.25), curva)            # mãos nos joelhos, olha as moedas
R.pose(Z, D, dict(curva, cabeca=(-2, -6, 0)))
R.kloc(Z["raiz"], tz1 + 0.3, dest)
R.kloc(Z["raiz"], min(D - 0.1, max(t_nem, tz1 + 0.5) + 0.25), (dest[0], dest[1], -0.07))
R.kloc(Z["raiz"], D, (dest[0], dest[1], -0.075))
ba.mao(Z, "e", "relaxada", 1)
ba.mao(Z, "d", "relaxada", 1)
ba.mao(Z, "e", "punho", C.F(t_nem + 0.2))
ba.mao(Z, "d", "punho", C.F(t_nem + 0.2))
for no, keys in (("sobr_inc", [(0, 0), (t_nem, 0), (t_nem + 0.3, -0.55)]),
                 ("sobr_alt", [(0, 0), (t_nem, 0.2), (t_nem + 0.3, 1.0)]),
                 ("sorriso", [(0, 0.15), (t_nem, 0.0), (t_nem + 0.3, -0.55)]),
                 ("olhar_z", [(0, 0), (tz1 + 0.4, -0.5)])):
    for t, v in keys:
        C.key_val(V[no], t, v)

# ---- câmera rasteira: push-in leve; em "nem sabe" sobe e inclina para mostrar o Zé
c0 = Vector((pn.x + 0.6, yT - 2.1, 0.42))
a0 = Vector((pn.x + 0.25, yT - 0.3, 0.22))
cam, al = R.camera(c0, a0, lens=27, dof=2.8)
R.kloc(cam, 0, c0)
R.kloc(cam, t_asf + 0.4, c0 + (a0 - c0) * 0.04)
R.kloc(cam, D, c0 + (a0 - c0) * 0.05 + Vector((0, 0, 0.08)))
R.kloc(al, 0, a0)
R.kloc(al, t_asf + 0.4, a0)
R.kloc(al, D, a0 + Vector((0.35, 0.1, 0.45)))
cam.data.dof.focus_object = None
cam.data.dof.focus_distance = 2.1

C.renderizar(P, sys.argv)
