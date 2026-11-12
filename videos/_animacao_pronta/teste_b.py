"""Teste B: captura de movimento da CMU (retarget) no NOSSO Zé (boneco_adulto, roupa civil, esqueleto de 15 ossos)
na mesma rua: anda (141_25), chuta o pneu (143_24) e dá de ombros (141_21), encadeado no NLA. O rosto continua
sendo o nosso (fala/olhar/sobrancelha por nós Value) e as mãos trocam por pose, como no D_chute.

    AMOSTRAS=8 ~/.venv-video/bin/python teste_b.py teste 1.0 2.4 3.8
    AMOSTRAS=8 ~/.venv-video/bin/python teste_b.py video 24
"""
import os, sys, math, subprocess
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "videos", "calibrar_pneu", "planos"))
import _rua as R
C = R.C
import bpy
from mathutils import Vector
import animacao_pronta as ap
import boneco_adulto as ba

BVH = os.path.join(RAIZ, "assets", "mocap", "cmu_bvh")
FPS = 24
D = 4.8
P0 = {"nome": "teste_b", "ini": 0.0, "fim": D, "dur": D}
sc = C.setup(P0, amostras=int(os.environ.get("AMOSTRAS", 8)))
R.dia(sc, sol=(50, 0, -35))
M = {}
c, xf, pn = R.cena_carro_rua(M)
yT = pn.y

# ---- o NOSSO motorista (mesmo do D_chute)
Z = ba.ze_adulto("cara", M, expressao="neutro", maos="todas", **R.CARA)
ba.mao(Z, "e", "relaxada", 1)
ba.mao(Z, "d", "relaxada", 1)
P = {"raiz": Z["raiz"], "arm": Z["arm"], "acoes": []}
bpy.context.view_layer.update()
vel_andar = None
for tk, q0, q1, nome, amp in (("141_25", 40, 110, "cmu_andar", 1.0), ("143_24", 106, 136, "cmu_chute", 0.6),
                              ("141_21", 24, 64, "cmu_ombros", 1.0)):
    src = ap.importar_bvh(os.path.join(BVH, tk + ".bvh"), "src_" + tk)
    a = ap.retarget(src, Z["arm"], ap.MAPA_CMU_ZE, q0, q1, nome_acao=nome, amplitude=amp)
    if nome == "cmu_andar":
        vel_andar = ap.velocidade_bvh(src, q0, q1, escala=a["k_alt"])
    P["acoes"].append(a)
    ap.apagar(src)

t_para, t_chute, t_omb = 1.6, 1.9, 3.1
p_fim = Vector((pn.x + 0.05, yT - 0.62, 0))
p_ini = p_fim - Vector((vel_andar * t_para, 0, 0))
print("velocidade da caminhada CMU no Zé: %.2f m/s" % vel_andar)
ap.colocar(P, p_ini, rumo=90)
ap.caminhar(P, "cmu_andar", 0.0, t_para, p_ini, p_fim, vel=vel_andar)
raiz = P["raiz"]
for t, r in ((t_para - 0.1, 90), (t_chute, 150), (t_omb - 0.05, 150), (t_omb + 0.4, 55)):
    raiz.rotation_euler = (0, 0, math.radians(r))
    raiz.keyframe_insert("rotation_euler", frame=C.F(t))
ap.encadear(P, [("cmu_andar", 0.0, t_para, {"loop": False}),
                ("cmu_chute", t_para, t_omb - t_para, {"blend": 0.3, "loop": False}),
                ("cmu_ombros", t_omb, D - t_omb, {"blend": 0.25, "loop": False})], fps=FPS)

# ---- rosto e mãos (o que o pacote pronto não tem): olha o pneu, desdém + fala no "tá bom ainda"
V = Z["rosto"]
tb = t_omb + 0.3
ba.mao(Z, "e", "aberta", C.F(tb))
ba.mao(Z, "d", "aberta", C.F(tb))
R.fala(V, tb, tb + 0.7, forte=0.6, seed=3)
for no, keys in (("sobr_alt", [(0, 0), (tb, 0), (tb + 0.3, 1.0), (D, 0.8)]),
                 ("sorriso", [(0, 0.1), (tb, 0.1), (tb + 0.3, -0.2)]),
                 ("abre_olho", [(0, 1), (tb, 1), (tb + 0.3, 0.75)]),
                 ("olhar_z", [(0, 0), (t_para, -0.6), (tb, -0.6), (tb + 0.3, 0.0)])):
    for t, v in keys:
        C.key_val(V[no], t, v)

# ---- TUM
t_tum = t_para + 0.3 + 0.5
car = c["raiz"]
for k in range(8):
    a = 0.8 * math.exp(-k * 0.45) * (1 if k % 2 == 0 else -1) if k else 0.0
    R.krot(car, t_tum + k * 0.06, (a, 0, 0))

# ---- câmera (a mesma do teste A)
c0 = Vector((pn.x + 2.7, yT - 2.6, 1.05))
a0 = Vector((pn.x - 0.5, yT - 0.5, 0.85))
cam, al = R.camera(c0, a0, lens=26, dof=5.6)
R.kloc(cam, 0, c0)
R.kloc(cam, D, c0 + (a0 - c0) * 0.06)

a = [x for x in sys.argv[1:] if x != "--"]
modo = a[0] if a else "teste"
saida = os.path.join(AQUI, "_quadros_b")
os.makedirs(saida, exist_ok=True)
if modo == "teste":
    for t in map(float, a[1:] or ["1.0", "2.4", "3.8"]):
        sc.frame_set(C.F(t))
        sc.render.filepath = os.path.join(AQUI, f"teste_b_{t:04.2f}.png")
        bpy.ops.render.render(write_still=True)
else:
    fps_v = int(a[1]) if len(a) > 1 else 12
    passo = FPS // fps_v
    fs = list(range(1, C.F(D) + 1, passo))
    for i, f in enumerate(fs):
        p = os.path.join(saida, f"{i:04d}.png")
        if os.path.exists(p):
            continue
        sc.frame_set(f)
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(fps_v), "-i", os.path.join(saida, "%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", os.path.join(AQUI, "teste_b.mp4")], check=True)
