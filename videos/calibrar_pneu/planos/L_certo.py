"""Plano L: "O certo é simples: uma vez por mês, com o pneu frio, calibra no número da plaquinha da porta ou do
manual. E não esquece o estepe."  Três ilhas na mesma cena, trocadas por corte seco (câmera com chave CONSTANT):
  1) oficina: Zé aponta o pneu do carro (o certo é simples / 1x por mês / pneu frio);
  2) close da coluna da porta: a plaquinha de pressão acende em verde ("plaquinha da porta");
  3) porta-malas aberto com o estepe: anel verde pulsa ("não esquece o estepe").
Tempos das palavras lidos de palavras.json (globais) → locais."""
import sys, os, math, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import comum as C
import bpy
from mathutils import Vector
import motor as mt
import boneco_adulto as ba
import veiculos3 as v3
import veiculos_antigos as va

P = C.plano("L_certo")
D = P["dur"]
W = json.load(open(os.path.join(C.HERE, "palavras.json")))


def tw(palavra, depois=0.0):
    """tempo local da 1ª palavra (prefixo) que começa depois de `depois` (local)."""
    for w, a, b in W:
        tl = a - P["ini"]
        if tl >= depois - 0.01 and w.lower().strip(",.?!").startswith(palavra):
            return tl
    raise KeyError(palavra)


t_mes, t_frio = tw("vez"), tw("frio")
t_plaq, t_manual = tw("plaquinha"), tw("manual")
t_estepe0, t_estepe = tw("não", t_manual), tw("step")
corte2 = tw("calibra", t_frio) - 0.05          # → plaquinha
corte3 = t_estepe0 - 0.05                      # → estepe

sc = C.setup(P)
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = -1.0
w = bpy.data.worlds.new("mundo"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = mt.lin("#2A2F36")
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4
M = {}


def luz(pos, energia, tam, cor, alvo):
    d = bpy.data.lights.new("a", "AREA"); d.energy, d.size = energia, tam; d.color = mt.lin(cor)[:3]
    o = mt.link(bpy.data.objects.new("a", d)); o.location = pos
    o.rotation_mode = "QUATERNION"; o.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")


def emissor(nome, cor, forca):
    m = bpy.data.materials.new(nome); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = mt.lin(cor)
    b.inputs["Emission Color"].default_value = mt.lin(cor)
    b.inputs["Emission Strength"].default_value = forca
    return m, b


VERDE = "#2BD576"
# ---------------------------------------------------------------- ilha 1: oficina, Zé aponta o pneu
ba.oficina(M, largura=9, fundo_y=2.0)
MV = {}
car = va.carro_antigo("carro", MV, "bolinha", "prata", conservacao="ok", escala=0.5)
car["raiz"].location = (0.75, 0.6, 0)
car["raiz"].rotation_euler = (0, 0, math.radians(-150))
Z = ba.ze_adulto("ze", M, pose="aponta", expressao="fala", olhar=(0.6, -0.2))
Z["raiz"].location = (-0.45, -0.3, 0)
Z["raiz"].rotation_euler = (0, 0, math.radians(55))           # de frente para o carro (à direita)
R = Z["rosto"]
t, k = 0.0, 0
while t < corte2:
    C.key_val(R["boca_aberta"], t, 0.7 if k % 2 == 0 else 0.1)
    t += 0.14 + 0.04 * ((k * 5) % 3); k += 1
C.key_rot(Z["arm"], "ombro_e", 0.0, -70, -30, 0)
C.key_rot(Z["arm"], "ombro_e", t_mes, -55, -35, 0)        # baixa o braço para o pneu
luz((-2.2, -2.2, 1.9), 420, 2.0, "#FFE8D0", (0, 0, 1.0))
luz((3.0, -2.2, 1.8), 300, 3.0, "#DCE6FF", (0, 0, 1.0))
luz((1.8, 1.2, 2.2), 900, 1.0, "#CFE0FF", (0, 0, 1.0))

# ---------------------------------------------------------------- ilha 2: coluna da porta com a plaquinha
X2 = 30.0
pint = va.pintura_antiga_mat(MV, "prata", False) if hasattr(va, "pintura_antiga_mat") else v3.pintura("pint", "#C4C9CF")
coluna = mt.box("coluna", X2 - 0.12, X2 + 0.12, -0.02, 0.02, 0.4, 1.4, pint)
borr = mt.box("borracha", X2 - 0.14, X2 - 0.12, -0.03, 0.03, 0.4, 1.4, mt.mat("borr", "#15161A", rough=0.8))
painel_fundo = mt.box("fundo2", X2 - 2, X2 + 2, 0.6, 0.62, -1, 3, mt.mat("fundo2", "#1E2228", rough=0.9))
etq = mt.box("etiqueta", X2 - 0.07, X2 + 0.07, -0.026, -0.02, 0.86, 0.96, mt.mat("etq", "#F4F4F0", rough=0.5))
for i in range(4):          # linhas de "tabela" (sem números reais)
    mt.box(f"linha{i}", X2 - 0.055, X2 + 0.055, -0.0275, -0.026, 0.875 + i * 0.02, 0.879 + i * 0.02,
           mt.mat("tinta", "#2A2E35", rough=0.6))
mborda, bborda = emissor("borda_verde", VERDE, 0.0)
for nome, (x0, x1, z0, z1) in {"b_cima": (-0.08, 0.08, 0.96, 0.967), "b_baixo": (-0.08, 0.08, 0.853, 0.86),
                                "b_esq": (-0.08, -0.073, 0.853, 0.967), "b_dir": (0.073, 0.08, 0.853, 0.967)}.items():
    mt.box(nome, X2 + x0, X2 + x1, -0.03, -0.024, z0, z1, mborda)
luz((X2 - 0.6, -1.0, 1.4), 60, 1.0, "#FFF1E0", (X2, 0, 0.9))
luz((X2 + 0.7, -0.8, 0.9), 25, 1.0, "#DCE6FF", (X2, 0, 0.9))
for t_, f in ((0.0, 0.0), (corte2 + 0.15, 0.0), (t_plaq + 0.1, 6.0), (t_plaq + 0.5, 3.0), (t_plaq + 0.8, 6.0),
              (t_manual + 0.3, 4.0)):
    bborda.inputs["Emission Strength"].default_value = f
    bborda.inputs["Emission Strength"].keyframe_insert("default_value", frame=C.F(t_))

# ---------------------------------------------------------------- ilha 3: porta-malas com o estepe
X3 = 60.0
carpete = mt.mat("carpete", "#26282D", rough=0.95)
mt.box("pm_fundo", X3 - 0.55, X3 + 0.55, -0.45, 0.45, 0.3, 0.33, carpete)
for nome, (x0, x1, y0, y1) in {"pm_e": (-0.58, -0.55, -0.45, 0.45), "pm_d": (0.55, 0.58, -0.45, 0.45),
                                "pm_t": (-0.58, 0.58, 0.45, 0.48), "pm_f": (-0.58, 0.58, -0.48, -0.45)}.items():
    mt.box(nome, X3 + x0, X3 + x1, y0, y1, 0.3, 0.62, pint if nome == "pm_f" else carpete)
MR = v3.materiais_real({}) if hasattr(v3, "materiais_real") else {}
try:
    est = v3.roda_real("estepe", MR, R=0.3)
except Exception:
    est = v3.roda("estepe", v3.materiais({}), R=0.3)
est.location = (X3, 0.0, 0.43)
est.rotation_euler = (math.radians(90), 0, 0)
manel, banel = emissor("anel_verde", VERDE, 0.0)
bm = __import__("bmesh").new()
__import__("bmesh").ops.create_circle(bm, segments=64, radius=0.36)
anel = mt.mesh_obj("anel", bm, manel, (X3, 0, 0.55))
sk = anel.modifiers.new("skin", "SKIN")
for v in anel.data.skin_vertices[0].data:
    v.radius = (0.008, 0.008)
for t_, f in ((0.0, 0.0), (t_estepe + 0.05, 0.0), (t_estepe + 0.25, 8.0), (t_estepe + 0.55, 3.0), (D, 6.0)):
    banel.inputs["Emission Strength"].default_value = f
    banel.inputs["Emission Strength"].keyframe_insert("default_value", frame=C.F(t_))
luz((X3 - 0.5, -1.2, 1.8), 120, 1.5, "#FFF1E0", (X3, 0, 0.4))
luz((X3 + 0.9, 0.4, 1.4), 60, 1.0, "#DCE6FF", (X3, 0, 0.4))

# ---------------------------------------------------------------- câmera: 3 enquadramentos, cortes secos
cd = bpy.data.cameras.new("cam"); cd.dof.use_dof = True
cam = mt.link(bpy.data.objects.new("cam", cd)); sc.camera = cam
cam.rotation_mode = "QUATERNION"


def chave(f, pos, alvo, lente, foco):
    """Chave da câmera no QUADRO local f (inteiro)."""
    cam.location = pos
    cam.rotation_quaternion = (Vector(alvo) - Vector(pos)).to_track_quat("-Z", "Y")
    cd.lens = lente
    cd.dof.focus_distance = foco
    cd.dof.aperture_fstop = 2.8
    cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_quaternion", frame=f)
    cd.keyframe_insert("lens", frame=f); cd.dof.keyframe_insert("focus_distance", frame=f)


f2, f3, fD = C.F(corte2), C.F(corte3), C.F(D)
I1 = ((0.25, -3.9, 1.2), (0.2, 0.1, 0.78), 42, 3.9), ((0.25, -3.6, 1.15), (0.2, 0.1, 0.76), 42, 3.6)
I2 = ((X2 - 0.25, -0.75, 1.0), (X2, 0, 0.9), 60, 0.8), ((X2 - 0.2, -0.62, 0.98), (X2, 0, 0.9), 60, 0.66)
I3 = ((X3 - 0.35, -1.1, 1.45), (X3, 0, 0.42), 45, 1.4), ((X3 - 0.3, -0.98, 1.38), (X3, 0, 0.42), 45, 1.28)
# cada ilha: chave no 1º e no último quadro (push-in linear); quadros vizinhos no corte = corte seco
chave(1, *I1[0]); chave(f2 - 1, *I1[1])
chave(f2, *I2[0]); chave(f3 - 1, *I2[1])
chave(f3, *I3[0]); chave(fD, *I3[1])
C.renderizar(P, sys.argv)
