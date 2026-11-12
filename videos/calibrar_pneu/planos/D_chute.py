"""Plano D: "Ela OLHA o pneu, dá um CHUTINHO… TÁ BOM AINDA. E SEGUE A VIDA."
O cara de frente para o pneu murcho (câmera baixa de 3/4 pela frente do carro). Em "olha" baixa a cabeça; antes de
"chutinho" recua a perna direita e chuta o flanco do pneu (TUM ≈ 0,16 s depois de "chutinho"): o pneu e a carroceria
balançam de leve (oscilação amortecida); em "tá bom ainda" dá de ombros (mãos abertas, cabeça de lado, cara de
desdém, boca mexendo) e em "segue a vida" vira e vai embora andando ao longo do carro. Push-in leve."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _rua as R
C = R.C
import boneco_adulto as ba
from mathutils import Vector

P = C.plano("D_chute")
D = P["dur"]
t_olha = R.palavra(P, "olha", reserva=0.06)
t_chute = R.palavra(P, "chutinho", reserva=0.36)
t_bom = R.palavra(P, "ta bom ainda", "bom", reserva=0.52)
t_vida = R.palavra(P, "segue a vida", "segue", reserva=0.8)
t_tum = t_chute + 0.16
sc = C.setup(P)
R.dia(sc, sol=(50, 0, -35))
M = {}
c, xf, pn = R.cena_carro_rua(M)
yT = pn.y
rd = R.roda_dd(c)

# ---- o cara, de frente para o pneu (frente do boneco = +y)
Z = ba.ze_adulto("cara", M, expressao="neutro", maos="todas", **R.CARA)
arm, V = Z["arm"], Z["rosto"]
base = Vector((pn.x + 0.25, yT - 0.6, 0))
Z["raiz"].location = base
Z["raiz"].rotation_euler = (0, 0, math.radians(158))
ba.mao(Z, "e", "relaxada", 1)
ba.mao(Z, "d", "relaxada", 1)
de_pe = {"tronco": (0, -3, 0), "pescoco": (0, 0, 0), "cabeca": (0, 3, 0), "quadril": (0, 0, 0),
         "coxa_e": (-4, -3, 0), "coxa_d": (0, 2, 0), "canela_e": (6, 0, 0), "canela_d": (3, 0, 0),
         "ombro_e": (-4, -7, 0), "cotovelo_e": (-14, 0, 0), "ombro_d": (-4, 7, 0), "cotovelo_d": (-14, 0, 0),
         "mao_e": (0, 0, 0), "mao_d": (0, 0, 0)}
olhando = dict(de_pe, tronco=(7, -2, 0), pescoco=(8, 0, 0), cabeca=(14, 4, -4))
R.pose(Z, 0.0, de_pe)
R.pose(Z, t_olha + 0.45, olhando)
# recua a perna (antecipação) → chute rápido → volta
prep = max(t_olha + 0.6, t_chute - 0.3)
R.pose(Z, prep, olhando)
R.pose(Z, t_chute + 0.02, dict(olhando, tronco=(2, -2, 4), coxa_d=(20, 2, 0), canela_d=(62, 0, 0), coxa_e=(-6, -3, 0),
                               canela_e=(10, 0, 0), ombro_e=(-18, -12, 0), ombro_d=(14, 10, 0)))
R.pose(Z, t_tum, dict(olhando, tronco=(-6, -2, -3), coxa_d=(-42, 2, 0), canela_d=(14, 0, 0), coxa_e=(-6, -3, 0),
                      canela_e=(12, 0, 0), ombro_e=(14, -14, 0), ombro_d=(-22, 12, 0)))
R.pose(Z, t_tum + 0.12, dict(olhando, tronco=(-4, -2, -2), coxa_d=(-34, 2, 0), canela_d=(26, 0, 0),
                             ombro_e=(10, -12, 0), ombro_d=(-16, 10, 0)))
R.pose(Z, t_tum + 0.42, dict(olhando, coxa_d=(-2, 2, 0), canela_d=(6, 0, 0)))
# dá de ombros: "tá bom ainda"
ombros = dict(de_pe, tronco=(-2, -4, -18), pescoco=(0, 0, -15), cabeca=(2, 12, -40),
              ombro_e=(-10, -34, 0), cotovelo_e=(-72, 0, -30), ombro_d=(-10, 34, 0), cotovelo_d=(-72, 0, 30),
              mao_e=(0, 0, -35), mao_d=(0, 0, 35))
tb = max(t_bom, t_tum + 0.45)
R.pose(Z, tb + 0.05, dict(olhando, coxa_d=(-2, 2, 0), canela_d=(6, 0, 0)))
R.pose(Z, tb + 0.35, ombros)
R.pose(Z, tb + 0.7, dict(ombros, cabeca=(2, 15, -42), ombro_e=(-12, -36, 0), ombro_d=(-12, 36, 0)))
ba.mao(Z, "e", "aberta", C.F(tb + 0.12))
ba.mao(Z, "d", "aberta", C.F(tb + 0.12))
R.fala(V, tb, tb + 0.55, forte=0.6, seed=3)
for no, keys in (("sobr_alt", [(0, 0), (tb, 0), (tb + 0.3, 1.0), (D, 0.8)]),
                 ("sorriso", [(0, 0.1), (tb, 0.1), (tb + 0.3, -0.2)]),
                 ("abre_olho", [(0, 1), (tb, 1), (tb + 0.3, 0.75)]),
                 ("olhar_z", [(0, 0), (t_olha + 0.3, -0.6), (tb, -0.6), (tb + 0.3, 0.0)]),
                 ("olhar_x", [(0, 0), (tb + 0.3, 0.0)])):
    for t, v in keys:
        C.key_val(V[no], t, v)
# "segue a vida": vira e sai andando ao longo do carro (para trás dele, -x)
tv = max(t_vida - 0.15, tb + 0.75)
ba.mao(Z, "e", "relaxada", C.F(tv))
ba.mao(Z, "d", "relaxada", C.F(tv))
R.kloc(Z["raiz"], tv, base)
R.krot(Z["raiz"], tv, (0, 0, 158))
R.pose(Z, tv, dict(de_pe, cabeca=(0, 3, 0)))
R.andar(Z, tv + 0.3, tv + 2.2, base + Vector((-0.15, -0.1, 0)), base + Vector((-2.4, -0.25, 0)), parar=False,
        extra={"tronco": (3, 0, 0), "cabeca": (0, 0, 0)})

# ---- TUM: pneu e carroceria balançam (oscilação amortecida)
car = c["raiz"]
for k in range(10):
    t = t_tum + k * 0.06
    a = 0.9 * math.exp(-k * 0.45) * (1 if k % 2 == 0 else -1) if k else 0.0
    R.krot(car, t, (a, 0, 0))
    R.krot(rd, t, (a * 2.2, 0, 0) if rd.rotation_euler.z == 0 else (a * 2.2, 0, 180))
R.krot(car, t_tum - 0.04, (0, 0, 0))
pneu = [o for o in rd.children if o.name.endswith("_pneu")][0]
s0 = tuple(pneu.scale)
R.kesc(pneu, t_tum - 0.02, s0)
R.kesc(pneu, t_tum + 0.05, (s0[0] * 1.015, s0[1] * 0.96, s0[2] * 0.985))
R.kesc(pneu, t_tum + 0.2, s0)

# ---- câmera: baixa, 3/4 pela frente; push-in de 4 % e acompanha a saída
c0 = Vector((pn.x + 2.45, yT - 1.45, 0.85))
a0 = Vector((pn.x - 0.05, yT - 0.35, 0.72))
cam, al = R.camera(c0, a0, lens=28, dof=4.0)
R.kloc(cam, 0, c0)
R.kloc(cam, tv, c0 + (a0 - c0) * 0.04)
R.kloc(cam, D, c0 + (a0 - c0) * 0.045 + Vector((-0.2, 0, 0)))
R.kloc(al, 0, a0)
R.kloc(al, tv, a0)
R.kloc(al, D, a0 + Vector((-0.7, -0.1, 0.1)))

C.renderizar(P, sys.argv)
