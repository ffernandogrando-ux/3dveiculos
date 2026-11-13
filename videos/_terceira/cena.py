"""Teste "câmera em terceira pessoa" (jogo de mundo aberto), 10 s: narração 2,0–12,0 s do vídeo 02.
0–5,7 s: câmera atrás do carro chegando e estacionando. 5,7 s: corte, câmera atrás do ombro do cara andando até o
pneu; chutinho; "tá bom ainda" (a câmera gira para o rosto); "segue a vida" (ele vira e sai).
Visual de desenho: Cycles com poucas amostras + filtro de contorno/cor chapada em pos.py.
    AMOSTRAS=6 ~/.venv-video/bin/python cena.py teste 2.0 6.5 7.8 8.6     (quadros de teste)
    AMOSTRAS=6 ~/.venv-video/bin/python cena.py video [ini fim]            (quadros em _quadros/)
"""
import os, sys, math, time
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "videos", "calibrar_pneu", "planos"))
import _rua as R
C = R.C
import bpy
from mathutils import Vector
import personagem_q as pq

T_AUDIO = 2.0                                  # início do trecho na narração
D = 10.0
tl = lambda g: g - T_AUDIO                     # tempo global da narração → local
P0 = {"nome": "terceira", "ini": 0.0, "fim": D, "dur": D}
sc = C.setup(P0, amostras=int(os.environ.get("AMOSTRAS", 6)))
sol = R.dia(sc, sol=(55, 0, -50), forca=4.0)
sol.data.angle = math.radians(0.6)            # sombra dura (desenho)
M = {}
_rua_orig = R.rua
R.rua = lambda M, **k: _rua_orig(M, **dict(dict(x0=-45, x1=40), **k))
c, xf, pn = R.cena_carro_rua(M)
yT = pn.y
cr = c["raiz"]

# ---------------- 1) carro chegando (câmera de perseguição)
T_PARK = tl(7.1)
X0 = -22.0
for k in range(0, 21):
    u = k / 20
    t = T_PARK * u
    x = X0 * (1 - u) ** 2.2                   # desacelera até parar em x=0
    R.kloc(cr, t, Vector((x, 2.95 + 0.9 * (1 - u) ** 3, 0)))   # encosta no meio-fio no fim
R.girar_rodas(c, 0.0, T_PARK, X0, 0.0, passo=0.1)

# ---------------- 2) o cara
Q = pq.personagem("cara")
T_CORTE = tl(7.74)                             # "Olha só"
t_para, t_chute, t_omb, t_sai = tl(8.95), tl(9.4), tl(10.14), tl(11.1)
p_fim = Vector((pn.x + 0.05, yT - 0.62, 0))
p_ini = p_fim - Vector((2.6, 0.25, 0))
pq.animar(Q, [("andar", T_CORTE - 0.3, t_para, p_ini, p_fim), ("parado", t_para), ("chutar", t_chute),
              ("ombros", t_omb), ("andar", t_sai, D + 0.6, p_fim, p_fim - Vector((2.2, 0.9, 0))),
              ("virar", t_para - 0.1, t_chute, 150), ("virar", t_omb - 0.05, t_omb + 0.4, 55)])
pq.piscar(Q, 0.0, D)
pq.rosto(Q, "neutro", 0.0)
pq.rosto(Q, "neutro", t_para - 0.1)
pq.rosto(Q, "careta", t_para + 0.2)
pq.rosto(Q, "careta", t_omb)
pq.rosto(Q, "desdem", t_omb + 0.3)
V = Q["rosto"]
for t, v in ((0, 0.0), (t_para, -0.5), (t_omb, -0.5), (t_omb + 0.35, 0.0)):
    C.key_val(V["olhar_z"], t, v)
R.fala(V, t_omb + 0.05, t_omb + 0.8, forte=0.5, seed=3)
# antes do corte o cara não existe (está "dentro" do carro)
objs = [Q["raiz"]] + list(Q["raiz"].children_recursive)
for o in objs:
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=C.F(T_CORTE) - 1)
    o.hide_render = False
    o.keyframe_insert("hide_render", frame=C.F(T_CORTE))
t_tum = t_chute + 0.5
for k in range(8):
    a = 0.8 * math.exp(-k * 0.45) * (1 if k % 2 == 0 else -1) if k else 0.0
    R.krot(cr, t_tum + k * 0.06, (a, 0, 0))

# ---------------- câmera
cam, al = R.camera(Vector((-30, 2.95, 2)), Vector((0, 2.95, 1)), lens=18)
ef = 1.0 / C.FPS


def pos_cara(t):
    sc.frame_set(C.F(t))
    return Q["raiz"].matrix_world.translation.copy()


def hold(o, t, v):
    """Corte seco: chave no quadro anterior segura o valor antigo."""
    R.kloc(o, t, v)


# perseguição: atrás e acima do carro, um pouco para o lado da calçada
t = 0.0
while t <= T_CORTE - ef:
    sc.frame_set(C.F(t))
    x = cr.location.x
    lag = 0.6 * (1 - min(t / T_PARK, 1))       # câmera "atrasa" quando o carro está rápido
    R.kloc(cam, t, Vector((x - 5.0 - lag * 2, 2.95 - 1.1, 2.1)))
    R.kloc(al, t, Vector((x + 2.5, 2.95, 0.9)))
    t += 0.25
R.kloc(cam, T_CORTE - ef, cam.location.copy())
R.kloc(al, T_CORTE - ef, al.location.copy())
# atrás do ombro do cara (segue a posição real do corpo)
t = T_CORTE
while t <= t_para + 0.2:
    p = pos_cara(t)
    R.kloc(cam, t, p + Vector((-2.1, -0.75, 1.75)))
    R.kloc(al, t, p + Vector((1.6, 0.35, 1.05)))
    t += 0.2
# chute: abre para o lado, vendo pé, pneu e carro
p = pos_cara(t_chute)
R.kloc(cam, t_chute, p + Vector((-1.4, -2.4, 1.3)))
R.kloc(al, t_chute, p + Vector((0.6, 0.6, 0.45)))
# "tá bom ainda": gira para o rosto (3/4 de frente)
R.kloc(cam, t_omb + 0.1, p + Vector((0.95, -0.4, 1.6)))
R.kloc(al, t_omb + 0.1, p + Vector((0.0, 0.0, 1.5)))
R.kloc(cam, t_sai, p + Vector((0.85, -0.35, 1.6)))
R.kloc(al, t_sai, p + Vector((0.0, 0.0, 1.45)))
# "segue a vida": volta para trás dele saindo
t = t_sai + 0.3
while t <= D:
    q = pos_cara(t)
    R.kloc(cam, t, q + Vector((2.0, 0.3, 1.7)))
    R.kloc(al, t, q + Vector((-0.5, -0.3, 1.1)))
    t += 0.3

if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if x != "--"]
    modo = a[0] if a else "teste"
    if modo == "teste":
        for t in map(float, a[1:] or ["2.0", "6.5", "7.8", "8.6"]):
            sc.frame_set(C.F(t))
            sc.render.filepath = os.path.join(AQUI, "_testes", f"t_{t:05.2f}.png")
            t0 = time.time(); bpy.ops.render.render(write_still=True); print("quadro %.1fs" % (time.time() - t0), flush=True)
    else:
        f0 = int(a[1]) if len(a) > 1 else 1
        f1 = int(a[2]) if len(a) > 2 else C.F(D)
        os.makedirs(os.path.join(AQUI, "_quadros"), exist_ok=True)
        for f in range(f0, f1 + 1):
            p = os.path.join(AQUI, "_quadros", f"{f:04d}.png")
            if os.path.exists(p):
                continue
            sc.frame_set(f)
            sc.render.filepath = p
            t0 = time.time(); bpy.ops.render.render(write_still=True); print("quadro %d %.1fs" % (f, time.time() - t0), flush=True)
