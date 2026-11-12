"""Teste A: personagem Quaternius (Universal Base Characters, CC0) na rua do vídeo 02, animado só com movimento
PRONTO: anda até o carro (Walk_Loop da Universal Animation Library), para (Idle_Loop), chuta o pneu e dá de ombros
(captura de movimento CMU 143_24 e 141_21 com retarget, porque a UAL grátis não tem chute nem "dar de ombros").
Tudo encadeado no NLA com transições. Luz/câmera/cena = _rua.py.

    AMOSTRAS=8 ~/.venv-video/bin/python teste_a.py teste 0.8 2.3 3.2     # quadros soltos (s)
    AMOSTRAS=8 ~/.venv-video/bin/python teste_a.py video 12              # todos os quadros a 12 qps → MP4
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

A = os.path.join(RAIZ, "assets")
UBC = os.path.join(A, "personagens/quaternius_ubc/Universal Base Characters[Standard]/Base Characters/Godot - UE/Superhero_Male_FullBody.gltf")
UAL = os.path.join(A, "personagens/quaternius_ual/Universal Animation Library[Standard]/Unreal-Godot/UAL1_Standard.glb")
BVH = os.path.join(A, "mocap/cmu_bvh")
FPS = 24
D = 4.8
P0 = {"nome": "teste_a", "ini": 0.0, "fim": D, "dur": D}
sc = C.setup(P0, amostras=int(os.environ.get("AMOSTRAS", 8)))
R.dia(sc, sol=(50, 0, -35))
M = {}
c, xf, pn = R.cena_carro_rua(M)
yT = pn.y

# ---- personagem + ações
P = ap.importar(UBC, "motorista")
ap.vestir(P, camisa="#B5452F", calca="#3A5A86", sapato="#E8E4DC")      # mesma roupa do motorista do vídeo 02
P["raiz"].scale = (1.76 / 1.81,) * 3
P["acoes"] += ap.carregar_acoes(UAL)
for tk, q0, q1, nome, amp in (("143_24", 106, 136, "cmu_chute", 0.6), ("141_21", 24, 64, "cmu_ombros", 1.0)):
    src = ap.importar_bvh(os.path.join(BVH, tk + ".bvh"), "src_" + tk)
    P["acoes"].append(ap.retarget(src, P["arm"], ap.MAPA_CMU_UE, q0, q1, nome_acao=nome, amplitude=amp))
    ap.apagar(src)

# ---- caminho: vem de trás do carro (-x) pela calçada, para em frente ao pneu e vira para ele
t_para, t_chute, t_omb = 1.6, 1.9, 3.1
p_ini = Vector((pn.x - 2.3, yT - 0.8, 0))
p_fim = Vector((pn.x + 0.05, yT - 0.62, 0))
ap.colocar(P, p_ini, rumo=90)
vel = ap.caminhar(P, "Walk_Loop", 0.0, t_para, p_ini, p_fim)
raiz = P["raiz"]
for t, r in ((t_para - 0.1, 90), (t_chute, 150), (t_omb - 0.05, 150), (t_omb + 0.4, 55)):   # vira para a câmera no "tá bom"
    raiz.rotation_euler = (0, 0, math.radians(r))
    raiz.keyframe_insert("rotation_euler", frame=C.F(t))
ap.encadear(P, [("Walk_Loop", 0.0, t_para, {"vel": vel}),
                ("Idle_Loop", t_para, t_chute - t_para, {"blend": 0.3}),
                ("cmu_chute", t_chute, t_omb - t_chute, {"blend": 0.2, "loop": False}),
                ("cmu_ombros", t_omb, D - t_omb, {"blend": 0.25, "loop": False})], fps=FPS)

# ---- TUM no pneu (chute da CMU: pé mais à frente ~quadro 118 da tomada → t_chute + 12/24 s)
t_tum = t_chute + 0.5
car = c["raiz"]
for k in range(8):
    a = 0.8 * math.exp(-k * 0.45) * (1 if k % 2 == 0 else -1) if k else 0.0
    R.krot(car, t_tum + k * 0.06, (a, 0, 0))

# ---- câmera: baixa, 3/4 pela frente do carro, vê a chegada e o pneu
c0 = Vector((pn.x + 2.7, yT - 2.6, 1.05))
a0 = Vector((pn.x - 0.5, yT - 0.5, 0.85))
cam, al = R.camera(c0, a0, lens=26, dof=5.6)
R.kloc(cam, 0, c0)
R.kloc(cam, D, c0 + (a0 - c0) * 0.06)

# ---- render
a = [x for x in sys.argv[1:] if x != "--"]
modo = a[0] if a else "teste"
saida = os.path.join(AQUI, "_quadros_a")
os.makedirs(saida, exist_ok=True)
if modo == "teste":
    for t in map(float, a[1:] or ["0.8", "2.4", "3.6"]):
        sc.frame_set(C.F(t))
        sc.render.filepath = os.path.join(AQUI, f"teste_a_{t:04.2f}.png")
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
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", os.path.join(AQUI, "teste_a.mp4")], check=True)
