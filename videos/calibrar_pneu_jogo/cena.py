"""Vídeo 02 (calibrar o pneu) no ESTILO JOGO: câmera de terceira pessoa, bairro brasileiro low-poly, cor
chapada + contorno. Cenas de rua renderizadas aqui; o raio-X (cenas técnicas) vem de videos/calibrar_pneu/quadros.
    AMOSTRAS=6 ~/.venv-video/bin/python cena.py teste 34 39 55 58 62 65
    AMOSTRAS=6 THREADS=2 ~/.venv-video/bin/python cena.py video 0 2   (fila 0 de 2)
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
import estilo_jogo as ej

T_AUDIO = 0.0                                  # início do trecho na narração
D = 66.2
tl = lambda g: g - T_AUDIO                     # tempo global da narração → local
P0 = {"nome": "jogo", "ini": 0.0, "fim": D, "dur": D}
sc = C.setup(P0, amostras=int(os.environ.get("AMOSTRAS", 6)))
sol = R.dia(sc, sol=(50, 0, -150), forca=4.6, ceu=1.6, exposicao=-0.3)
sol.data.color = (1.0, 0.86, 0.68)
sol.data.angle = math.radians(0.6)            # sombra dura (desenho)
M = {}
_rua_orig = R.rua
R.rua = lambda M, **k: _rua_orig(M, **dict(dict(x0=-60, x1=60, muro=False, arvores=False, postes=False, outro_lado=-7.3), **k))
c, xf, pn = R.cena_carro_rua(M)
ej.bairro(M, x0=-60, x1=60)
cr = c["raiz"]
Y_CALC = 3.5                                   # duas rodas em cima da calçada

# ---------------- 1) carro chegando (câmera de perseguição)
T_PARK = tl(7.1)
X0 = -34.0
ROLL = 5.0                                     # graus: lado da calçada mais alto
for k in range(0, 41):
    u = k / 40
    t = T_PARK * u
    x = X0 * (1 - u) ** 2.2
    v = min(max((u - 0.62) / 0.3, 0), 1)
    v = v * v * (3 - 2 * v)
    y = 1.3 + (Y_CALC - 1.3) * v
    sobe = min(max((y - 2.9) / 0.35, 0), 1)     # roda subindo no meio-fio
    R.kloc(cr, t, Vector((x, y, 0.07 * sobe)))
    R.krot(cr, t, (ROLL * sobe, 0, 8 * math.sin(math.pi * v) ))
R.girar_rodas(c, 0.0, T_PARK, X0, 0.0, passo=0.1)
sc.frame_set(C.F(T_PARK + 0.1))
bpy.context.view_layer.update()
pn = [r for r in c["rodas"] if r.name.endswith("_roda_dd")][0].matrix_world.translation.copy()
yT = pn.y

# ---------------- 2) o cara
Q = pq.personagem("cara")
T_CORTE = 7.74                                  # "Olha só"
t_para, t_chute, t_omb, t_sai = 8.95, 9.4, 10.14, 11.1
p_fim = Vector((pn.x + 0.05, yT - 0.62, 0))
p_ini = p_fim - Vector((2.6, 0.25, 0))
p_longe = p_fim - Vector((2.6, 1.0, 0))
p_h = p_fim + Vector((-0.7, -0.55, 0))           # volta para perto do pneu (de costas para a rua)
pq.animar(Q, [("andar", T_CORTE - 0.3, t_para, p_ini, p_fim), ("parado", t_para), ("chutar", t_chute),
              ("ombros", t_omb), ("andar", t_sai, 13.0, p_fim, p_longe), ("parado", 13.0),
              ("andar", 30.5, 32.8, p_longe, p_h), ("parado", 32.8), ("apontar", 33.5), ("nao", 35.5),
              ("bracos_cruzados", 37.6), ("parado", 41.0), ("falar", 53.1), ("apontar", 57.4), ("falar", 58.9),
              ("acenar", 61.0), ("falar", 63.4, 66.3),
              ("virar", t_para - 0.1, t_chute, 150), ("virar", t_omb - 0.05, t_omb + 0.4, 55),
              ("virar", 32.8, 33.3, -11)])
_esc = bpy.data.objects.new("esc_cabeca", None)
sc.collection.objects.link(_esc)
_esc.scale = (1.4, 1.4, 1.4)
_cs = Q["arm"].pose.bones["Head"].constraints.new("COPY_SCALE")
_cs.target, _cs.owner_space, _cs.target_space = _esc, "LOCAL", "LOCAL"
pq.piscar(Q, 0.0, D)
for nome, t in (("neutro", 0.0), ("neutro", t_para - 0.1), ("careta", t_para + 0.2), ("careta", t_omb),
                ("desdem", t_omb + 0.3), ("preocupado", 33.2), ("bravo", 36.3), ("desdem", 37.8),
                ("neutro", 41.0), ("sorriso", 53.3), ("neutro", 57.0), ("sorriso", 60.5), ("duvida", 63.6)):
    pq.rosto(Q, nome, t)
V = Q["rosto"]
for t, v in ((0, 0.0), (t_para, -0.5), (t_omb, -0.5), (t_omb + 0.35, 0.0)):
    C.key_val(V["olhar_z"], t, v)
R.fala(V, t_omb + 0.05, t_omb + 0.8, forte=0.5, seed=3)
R.fala(V, 37.7, 40.3, forte=0.6, seed=4)          # "Ah, mas eu calibro no posto, depois de rodar"
R.fala(V, 53.2, 61.0, forte=0.5, seed=5)
R.fala(V, 63.6, 65.6, forte=0.6, seed=6)
objs = [Q["raiz"]] + list(Q["raiz"].children_recursive)
for o in objs:
    o.hide_render = True
    o.keyframe_insert("hide_render", frame=C.F(T_CORTE) - 1)
    o.hide_render = False
    o.keyframe_insert("hide_render", frame=C.F(T_CORTE))
t_tum = t_chute + 0.5
for k in range(8):
    a = 0.8 * math.exp(-k * 0.45) * (1 if k % 2 == 0 else -1) if k else 0.0
    R.krot(cr, t_tum + k * 0.06, (ROLL + a, 0, 0))

ej.chapar_cena(excecoes=("rosto", "Eyes"), cores={"calca": "#3E6FB8", "passante": "#3E6FB8", "camisa": "#F3F1EA",
               "ribana": "#F3F1EA", "sapato": "#EDEDED", "couro": "#4A3020", "pinta_vermelho": "#C9282C",
               "MI_Hair": "#1A1410", "cabelo": "#17110D"})
ej.contornar_cena()

# ---------------- câmera (cortes secos: chave de "segura" no quadro anterior)
cam, al = R.camera(Vector((-30, 2.95, 2)), Vector((0, 2.95, 1)), lens=18)
ef = 1.0 / C.FPS
_ult = {}


def chave(t, pc, pa):
    R.kloc(cam, t, pc)
    R.kloc(al, t, pa)
    _ult["c"], _ult["a"] = pc.copy(), pa.copy()


def corte(t, pc, pa):
    if _ult:
        chave(t - ef, _ult["c"], _ult["a"])
    chave(t, pc, pa)


def cara(t):
    sc.frame_set(C.F(t))
    m = Q["raiz"].matrix_world
    return m.translation.copy(), -m.to_3x3().col[1].normalized()     # posição, frente


def lado(f):
    return Vector((-f.y, f.x, 0))


# A–C (0–7,74): perseguição do carro
t = 0.0
while t < T_CORTE - ef:
    sc.frame_set(C.F(t))
    x, y = cr.location.x, cr.location.y
    lag = 0.6 * (1 - min(t / T_PARK, 1))
    alto = 2.1 + 3.0 * max(0, 1 - t / 3.0) ** 2       # abre de cima (drone) e desce para a perseguição
    chave(t, Vector((x - 5.0 - lag * 2 - 2.0 * max(0, 1 - t / 3.0), y * 0.5 + 0.2, alto)), Vector((x + 2.5, y, 0.9)))
    t += 0.25
# D (7,74–11,92): atrás do ombro → chute → rosto → sai
t = T_CORTE
p, f = cara(t)
corte(t, p + Vector((-2.1, -0.75, 1.75)), p + Vector((1.6, 0.35, 1.05)))
while t <= t_para + 0.2:
    p, f = cara(t)
    chave(t, p + Vector((-2.1, -0.75, 1.75)), p + Vector((1.6, 0.35, 1.05)))
    t += 0.2
p, f = cara(t_chute)
chave(t_chute, p + Vector((-1.4, -2.4, 1.3)), p + Vector((0.6, 0.6, 0.45)))
chave(t_omb + 0.1, p + Vector((0.95, -0.4, 1.6)), p + Vector((0.0, 0.0, 1.5)))
chave(t_sai, p + Vector((0.85, -0.35, 1.6)), p + Vector((0.0, 0.0, 1.45)))
t = t_sai + 0.3
while t <= 11.95:
    q, f = cara(t)
    chave(t, q + Vector((2.0, 0.3, 1.7)), q + Vector((-0.5, -0.3, 1.1)))
    t += 0.3
# H (33,0–37,66): de frente, baixo (ele aponta o pneu), depois push-in no rosto bravo
p, f = cara(33.4)
corte(33.0, p + f * 2.4 + lado(f) * 1.3 + Vector((0, 0, 0.7)), p + Vector((0, 0, 1.0)) + lado(f) * -0.3)
chave(35.3, p + f * 1.9 + lado(f) * 0.5 + Vector((0, 0, 0.9)), p + Vector((0, 0, 1.1)))
corte(35.5, p + f * 1.1 + lado(f) * -0.25 + Vector((0, 0, 1.55)), p + Vector((0, 0, 1.55)))
chave(37.6, p + f * 0.85 + lado(f) * -0.2 + Vector((0, 0, 1.58)), p + Vector((0, 0, 1.55)))
# I (37,66–40,6): objeção, braços cruzados, órbita lenta
corte(37.66, p + f * 1.9 + lado(f) * 1.2 + Vector((0, 0, 1.3)), p + Vector((0, 0, 1.25)))
chave(40.6, p + f * 1.7 + lado(f) * -0.6 + Vector((0, 0, 1.4)), p + Vector((0, 0, 1.3)))
# L (53,16–61,04): "o certo é simples" — de frente com o carro atrás; plaquinha da porta; volta
corte(53.16, p + f * 2.6 + lado(f) * 0.4 + Vector((0, 0, 1.4)), p + Vector((0, 0, 1.2)) - f * 0.6)
chave(57.2, p + f * 2.0 + lado(f) * -0.3 + Vector((0, 0, 1.5)), p + Vector((0, 0, 1.25)) - f * 0.6)
corte(57.4, p + f * 0.6 + lado(f) * 1.6 + Vector((0, 0, 1.35)), p - f * 0.9 + Vector((0, 0, 0.9)))
chave(58.9, p + f * 0.5 + lado(f) * 1.4 + Vector((0, 0, 1.3)), p - f * 0.9 + Vector((0, 0, 0.9)))
corte(58.9, p + f * 1.8 + lado(f) * 0.6 + Vector((0, 0, 1.45)), p + Vector((0, 0, 1.3)))
chave(61.0, p + f * 1.5 + lado(f) * 0.3 + Vector((0, 0, 1.5)), p + Vector((0, 0, 1.35)))
# M (61,04–63,52): drone subindo enquanto ele acena
corte(61.04, p + f * 3.0 + Vector((0, 0, 2.5)), p + Vector((0, 0, 1.2)))
chave(63.5, p + f * 2.5 + lado(f) * 7.0 + Vector((0, 0, 8.0)), p + Vector((0, 0, 0.8)))
# N (63,52–66,2): close no rosto
corte(63.52, p + f * 0.95 + lado(f) * 0.25 + Vector((0, 0, 1.6)), p + Vector((0, 0, 1.58)))
chave(66.2, p + f * 0.7 + lado(f) * 0.15 + Vector((0, 0, 1.6)), p + Vector((0, 0, 1.58)))

FAIXAS = [(0.0, 11.92), (33.0, 40.6), (53.16, 66.2)]      # o resto é o raio-X (quadros técnicos prontos)

if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if x != "--"]
    pasta = os.path.join(AQUI, "_quadros")
    os.makedirs(pasta, exist_ok=True)
    if a and a[0] == "teste":
        for t in map(float, a[1:]):
            sc.frame_set(C.F(t))
            sc.render.filepath = os.path.join(AQUI, "_testes", f"t_{t:05.2f}.png")
            t0 = time.time(); bpy.ops.render.render(write_still=True); print("quadro %.1fs" % (time.time() - t0), flush=True)
    else:
        k, n = (int(a[1]), int(a[2])) if len(a) > 2 else (0, 1)
        sc.render.threads_mode = "FIXED"
        sc.render.threads = int(os.environ.get("THREADS", 4))
        fs = sorted({f for t0, t1 in FAIXAS for f in range(C.F(t0), C.F(t1) + 1)})
        for f in fs[k::n]:
            p_ = os.path.join(pasta, f"{f:04d}.png")
            if os.path.exists(p_):
                continue
            sc.frame_set(f)
            sc.render.filepath = p_
            t0 = time.time(); bpy.ops.render.render(write_still=True); print("quadro %d %.1fs" % (f, time.time() - t0), flush=True)
