"""Animação PRONTA: personagens já animados (Quaternius, CC0) e captura de movimento (CMU) no motor3d.

Em vez de keyframes à mão (boneco_adulto.pose), usa movimento real:
    import animacao_pronta as ap
    P = ap.importar(".../UAL1_Standard.glb", "motorista", altura=1.76)   # personagem + todas as ações do arquivo
    ap.acoes(P)                                                           # nomes das ações
    ap.encadear(P, [("Walk_Loop", 0.0, 1.6), ("Idle_Loop", 1.6, 0.6)], fps=24)   # NLA com transição (blend)
    ap.colocar(P, (x, y, 0), rumo=158)                                    # lugar e direção na cena
    ap.caminhar(P, "Walk_Loop", t0, t1, p0, p1)                           # anda de p0 a p1 sem o pé escorregar

Captura de movimento (CMU, formato ASF/AMC → BVH, conversão própria e sem dependências do Blender):
    ap.asf_amc_para_bvh("141.asf", "141_21.amc", "141_21.bvh", fps=24)
    src = ap.importar_bvh("141_21.bvh")
    ap.retarget(src, P["arm"], ap.MAPA_CMU_UE, q0=1, q1=60, inicio=1, nome_acao="encolher")   # → ação do alvo
    ap.retarget(src, Z["arm"], ap.MAPA_CMU_ZE, ...)                       # no NOSSO Zé (boneco_adulto)

O retarget é por DIREÇÃO de osso: calibra cada osso do alvo para a pose de repouso da fonte (T-pose da CMU), então
funciona com repousos diferentes (o Zé fica de braços para baixo, o manequim UE em A-pose) e grava keyframes
(quaternion) na ação do alvo. Tempos em segundos; quadros como no resto do motor (1 = t 0).
"""
import math, os, re

# ======================================================================= ASF/AMC (CMU) → BVH, puro numpy
_POL_M = 2.54 / 100 / 0.45            # unidade da CMU ("length 0.45" em polegadas) → metros


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    import numpy as np
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    import numpy as np
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    import numpy as np
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def _euler(vals, ordem="XYZ"):
    """Rotação de eixos fixos aplicada na ordem dada (X depois Y depois Z → Rz·Ry·Rx), em graus."""
    import numpy as np
    R = np.eye(3)
    f = {"X": _rx, "Y": _ry, "Z": _rz}
    for eixo, v in zip(ordem, vals):
        R = f[eixo](math.radians(v)) @ R
    return R


def ler_asf(caminho):
    """Esqueleto ASF: {nome: {dir, len, C, dof, pai, filhos}} + ordem dos ossos."""
    import numpy as np
    txt = open(caminho).read().splitlines()
    ossos = {"root": {"dir": np.zeros(3), "len": 0.0, "C": np.eye(3), "dof": ["rx", "ry", "rz"], "pai": None,
                      "filhos": []}}
    ordem = ["root"]
    i, sec = 0, None
    while i < len(txt):
        l = txt[i].strip()
        if l.startswith(":"):
            sec = l.split()[0]
            if sec == ":root":
                pass
        elif sec == ":root" and l.startswith("axis"):
            pass
        elif sec == ":root" and l.startswith("order"):
            ossos["root"]["ordem_amc"] = [x.lower() for x in l.split()[1:]]
        elif sec == ":bonedata" and l == "begin":
            b = {"dof": [], "filhos": []}
            i += 1
            while txt[i].strip() != "end":
                p = txt[i].split()
                if p[0] == "name":
                    nome = p[1]
                elif p[0] == "direction":
                    b["dir"] = np.array([float(x) for x in p[1:4]])
                elif p[0] == "length":
                    b["len"] = float(p[1]) * _POL_M
                elif p[0] == "axis":
                    b["C"] = _euler([float(x) for x in p[1:4]], p[4] if len(p) > 4 else "XYZ")
                elif p[0] == "dof":
                    b["dof"] = [x.lower() for x in p[1:]]
                i += 1
            ossos[nome] = b
            ordem.append(nome)
        elif sec == ":hierarchy" and l not in ("begin", "end") and l:
            p = l.split()
            for f in p[1:]:
                ossos[f]["pai"] = p[0]
                ossos[p[0]]["filhos"].append(f)
        i += 1
    return ossos


def ler_amc(caminho):
    """Lista de quadros {osso: [valores]} (graus; root com tx ty tz rx ry rz)."""
    quadros, q = [], None
    for l in open(caminho):
        l = l.strip()
        if not l or l[0] in "#:":
            continue
        if l.isdigit():
            q = {}
            quadros.append(q)
        elif q is not None:
            p = l.split()
            q[p[0]] = [float(x) for x in p[1:]]
    return quadros


def asf_amc_para_bvh(asf, amc, saida, fps=24, fps_fonte=120, q0=0, q1=None):
    """Converte uma tomada da CMU (ASF+AMC, 120 qps) em BVH (Y para cima, metros), reamostrando para `fps`.
    q0/q1 = recorte em quadros da fonte. Devolve o caminho do BVH."""
    import numpy as np
    from scipy.spatial.transform import Rotation
    S = ler_asf(asf)
    Q = ler_amc(amc)[q0:q1]
    passo = fps_fonte / fps
    idx = [int(round(k * passo)) for k in range(int(len(Q) / passo))]

    def local(nome, q):
        b = S[nome]
        if nome == "root":
            v = q["root"]
            R = _euler(v[3:6], "XYZ")
            return R
        vals = q.get(nome)
        if not vals:
            return np.eye(3)
        ang = {"rx": 0.0, "ry": 0.0, "rz": 0.0}
        for d, v in zip(b["dof"], vals):
            ang[d] = v
        R = _euler([ang["rx"], ang["ry"], ang["rz"]], "XYZ")
        return b["C"] @ R @ b["C"].T

    lin = []

    def escreve(nome, nivel):
        b = S[nome]
        ind = "  " * nivel
        if nome == "root":
            lin.append("HIERARCHY")
            lin.append("ROOT hips")
            lin.append("{")
            lin.append(f"{ind}  OFFSET 0 0 0")
            lin.append(f"{ind}  CHANNELS 6 Xposition Yposition Zposition Zrotation Yrotation Xrotation")
        else:
            pai = S[b["pai"]]
            off = pai["dir"] * pai["len"]
            lin.append(f"{ind}JOINT {nome}")
            lin.append(f"{ind}{{")
            lin.append(f"{ind}  OFFSET {off[0]:.6f} {off[1]:.6f} {off[2]:.6f}")
            lin.append(f"{ind}  CHANNELS 3 Zrotation Yrotation Xrotation")
        if b["filhos"]:
            for f in b["filhos"]:
                escreve(f, nivel + 1)
        else:
            e = b["dir"] * b["len"]
            lin.append(f"{ind}  End Site")
            lin.append(f"{ind}  {{")
            lin.append(f"{ind}    OFFSET {e[0]:.6f} {e[1]:.6f} {e[2]:.6f}")
            lin.append(f"{ind}  }}")
        lin.append(f"{ind}}}")

    escreve("root", 0)
    ordem = []

    def percorre(n):
        ordem.append(n)
        for f in S[n]["filhos"]:
            percorre(f)

    percorre("root")
    lin.append("MOTION")
    lin.append(f"Frames: {len(idx)}")
    lin.append(f"Frame Time: {1.0 / fps:.6f}")
    for k in idx:
        q = Q[k]
        v = q["root"]
        vals = [v[0] * _POL_M, v[1] * _POL_M, v[2] * _POL_M]
        for n in ordem:
            z, y, x = Rotation.from_matrix(local(n, q)).as_euler("ZYX", degrees=True)
            vals += [z, y, x]
        lin.append(" ".join(f"{x:.5f}" for x in vals))
    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    with open(saida, "w") as f:
        f.write("\n".join(lin) + "\n")
    return saida


# ======================================================================= Blender
def _bpy():
    import bpy
    return bpy


def importar(caminho, nome="personagem", altura=None, pai=None):
    """Importa FBX/GLB/GLTF. Devolve {raiz (vazio), arm, malhas, acoes(lista)}. altura (m) reescala o conjunto.
    Remove o 'Icosphere' solto que os pacotes UAL trazem. A ação ativa é retirada (use encadear/aplicar)."""
    bpy = _bpy()
    antes = set(bpy.data.objects)
    acoes_antes = set(bpy.data.actions)
    ext = caminho.lower().rsplit(".", 1)[-1]
    if ext == "fbx":
        bpy.ops.import_scene.fbx(filepath=caminho, automatic_bone_orientation=True)
    else:
        bpy.ops.import_scene.gltf(filepath=caminho)
    novos = [o for o in bpy.data.objects if o not in antes]
    for o in list(novos):
        if o.type == "MESH" and o.name.startswith("Icosphere") and o.parent is None:
            bpy.data.objects.remove(o)
            novos.remove(o)
    arm = next(o for o in novos if o.type == "ARMATURE")
    raiz = bpy.data.objects.new(nome, None)
    bpy.context.scene.collection.objects.link(raiz)
    for o in novos:
        if o.parent is None:
            o.parent = raiz
    if pai:
        raiz.parent = pai
    acoes = [a for a in bpy.data.actions if a not in acoes_antes]
    for a in acoes:
        a.use_fake_user = True
    if arm.animation_data:
        arm.animation_data.action = None
        for t in list(arm.animation_data.nla_tracks):
            arm.animation_data.nla_tracks.remove(t)
    P = {"raiz": raiz, "arm": arm, "malhas": [o for o in novos if o.type == "MESH"], "acoes": acoes}
    if altura:
        bpy.context.view_layer.update()
        h = max((o.matrix_world @ __import__("mathutils").Vector(c)).z
                for o in P["malhas"] for c in o.bound_box)
        raiz.scale = (altura / h,) * 3
    return P


def acoes(P):
    """Nomes das ações do personagem (importadas com ele)."""
    return [a.name for a in P["acoes"]]


def _acao(P, nome):
    bpy = _bpy()
    for a in P["acoes"]:
        if a.name == nome:
            return a
    return bpy.data.actions[nome]


def _slot(acao):
    sl = getattr(acao, "slots", None)
    return sl[0] if sl else None


def aplicar_acao(P, nome):
    """Põe a ação como ativa no esqueleto (sem NLA)."""
    arm = P["arm"]
    a = _acao(P, nome)
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = a
    s = _slot(a)
    if s is not None:
        ad.action_slot = s
    return a


def encadear(P, trechos, fps=24, transicao=0.25):
    """Monta a sequência no NLA. trechos = [(acao, t_ini, dur, {opções})...] em segundos; opções: vel (velocidade),
    q0/q1 (recorte em quadros da ação), loop (repete até dur; padrão: True se a ação termina com _Loop),
    blend (s de transição; padrão `transicao`). Trilhas alternadas A/B para o cross-fade funcionar."""
    arm = P["arm"]
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = None
    trilhas = [ad.nla_tracks.new(), ad.nla_tracks.new()]
    trilhas[0].name, trilhas[1].name = "A", "B"
    strips = []
    for k, tr in enumerate(trechos):
        nome, t0, dur = tr[:3]
        op = tr[3] if len(tr) > 3 else {}
        a = _acao(P, nome)
        f0 = t0 * fps + 1
        st = trilhas[k % 2].strips.new(f"{k}_{nome}", int(round(f0)), a)
        s = _slot(a)
        if s is not None and hasattr(st, "action_slot"):
            st.action_slot = s
        q0, q1 = op.get("q0", a.frame_range[0]), op.get("q1", a.frame_range[1])
        st.action_frame_start, st.action_frame_end = q0, q1
        st.scale = 1.0 / op.get("vel", 1.0)
        comp = (q1 - q0) * st.scale
        loop = op.get("loop", nome.endswith("_Loop") or "loop" in nome.lower())
        alvo = dur * fps
        if loop and comp > 0:
            st.repeat = max(alvo / comp, 0.01)
        st.frame_end = st.frame_start + max(alvo, 1)
        b = op.get("blend", transicao) * fps
        st.blend_in = min(b, (st.frame_end - st.frame_start) / 2) if k else 0
        st.blend_out = 0
        st.extend_mode = "HOLD_FORWARD" if k else "HOLD"
        st.use_auto_blend = False
        strips.append(st)
    # a transição entra no começo do trecho seguinte: estende o anterior até lá + blend
    for k in range(len(strips) - 1):
        a, b = strips[k], strips[k + 1]
        if a.frame_end < b.frame_start + b.blend_in:
            if a.repeat != 1.0 and a.action_frame_end > a.action_frame_start:
                a.repeat = (b.frame_start + b.blend_in - a.frame_start) / ((a.action_frame_end - a.action_frame_start) * a.scale)
            a.frame_end = b.frame_start + b.blend_in
    return strips


def colocar(P, pos, rumo=0.0):
    """Lugar (x, y, z) e direção (graus em z; 0 = de frente para -y, como o Zé)."""
    P["raiz"].location = pos
    P["raiz"].rotation_euler = (0, 0, math.radians(rumo))


def velocidade_passo(P, acao, pe="foot_l", fps=24):
    """Velocidade (m/s, na escala do personagem) de uma caminhada no lugar: mede o pé de apoio andando para trás."""
    bpy = _bpy()
    arm = P["arm"]
    ad = arm.animation_data or arm.animation_data_create()
    velho_a, velho_nla = ad.action, ad.use_nla
    aplicar_acao(P, acao)
    ad.use_nla = False
    a = _acao(P, acao)
    sc = bpy.context.scene
    f_velho = sc.frame_current
    pts = []
    for f in range(int(a.frame_range[0]), int(a.frame_range[1]) + 1):
        sc.frame_set(f)
        m = arm.matrix_world @ arm.pose.bones[pe].matrix
        pts.append((m.translation.y, m.translation.z))
    zmin = min(p[1] for p in pts)
    v = [abs(pts[i + 1][0] - pts[i][0]) * fps for i in range(len(pts) - 1)
         if pts[i][1] < zmin + 0.02 and pts[i + 1][1] < zmin + 0.02]
    ad.action, ad.use_nla = velho_a, velho_nla
    sc.frame_set(f_velho)
    v.sort()
    return v[len(v) // 2] if v else 1.2


def caminhar(P, acao, t0, t1, p0, p1, fps=24, vel=None):
    """Move a raiz de p0 a p1 entre t0 e t1 (linear, como o passo em ciclo) e devolve a velocidade da ação
    (vel) que faz o pé não escorregar: use-a no trecho de encadear (opção vel)."""
    from mathutils import Vector
    raiz = P["raiz"]
    v_acao = velocidade_passo(P, acao, fps=fps) * raiz.scale.x
    d = (Vector(p1) - Vector(p0)).length
    v_real = d / max(t1 - t0, 1e-3)
    raiz.location = p0
    raiz.keyframe_insert("location", frame=int(round(t0 * fps)) + 1)
    raiz.location = p1
    raiz.keyframe_insert("location", frame=int(round(t1 * fps)) + 1)
    for fc in _curvas(raiz.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    return v_real / v_acao


def _curvas(action):
    if hasattr(action, "fcurves") and len(getattr(action, "fcurves", [])):
        return list(action.fcurves)
    out = []
    for ly in getattr(action, "layers", []):
        for st in ly.strips:
            for cb in st.channelbags:
                out.extend(cb.fcurves)
    return out


# ----------------------------------------------------------------------- BVH + retarget
def importar_bvh(caminho, nome=None):
    """Importa um BVH (Y para cima) como esqueleto-fonte; quadros a partir de 1, sem reescala de fps."""
    bpy = _bpy()
    antes = set(bpy.data.objects)
    bpy.ops.import_anim.bvh(filepath=caminho, axis_forward="-Z", axis_up="Y", frame_start=1,
                            use_fps_scale=False, update_scene_fps=False, update_scene_duration=False,
                            rotate_mode="NATIVE")
    o = next(x for x in bpy.data.objects if x not in antes)
    if nome:
        o.name = nome
    return o


# (osso do alvo, osso da fonte que dá a rotação, osso-início da direção, osso-fim da direção)
# fonte = BVH da CMU feito por asf_amc_para_bvh (a CMU olha para +z; a direção usa as cabeças dos ossos)
MAPA_CMU_UE = [  # manequim Quaternius UAL / UBC (esqueleto padrão Unreal)
    ("pelvis", "hips", "lowerback", "upperback"),
    ("spine_01", "lowerback", "lowerback", "upperback"),
    ("spine_02", "upperback", "upperback", "thorax"),
    ("spine_03", "thorax", "thorax", "lowerneck"),
    ("neck_01", "lowerneck", "lowerneck", "upperneck"),
    ("Head", "head", "upperneck", "head+"),
    ("clavicle_l", "lclavicle", "lclavicle", "lhumerus"),
    ("upperarm_l", "lhumerus", "lhumerus", "lradius"),
    ("lowerarm_l", "lradius", "lradius", "lwrist"),
    ("hand_l", "lwrist", "lwrist", "lhand+"),
    ("clavicle_r", "rclavicle", "rclavicle", "rhumerus"),
    ("upperarm_r", "rhumerus", "rhumerus", "rradius"),
    ("lowerarm_r", "rradius", "rradius", "rwrist"),
    ("hand_r", "rwrist", "rwrist", "rhand+"),
    ("thigh_l", "lfemur", "lfemur", "ltibia"),
    ("calf_l", "ltibia", "ltibia", "lfoot"),
    ("foot_l", "lfoot", "lfoot", "ltoes"),
    ("thigh_r", "rfemur", "rfemur", "rtibia"),
    ("calf_r", "rtibia", "rtibia", "rfoot"),
    ("foot_r", "rfoot", "rfoot", "rtoes"),
]
MAPA_CMU_ZE = [  # nosso boneco_adulto (15 ossos; tronco = coluna inteira; ombro = braço)
    ("quadril", "hips", "lowerback", "upperback"),
    ("tronco", "thorax", "lowerback", "lowerneck"),
    ("pescoco", "lowerneck", "lowerneck", "upperneck"),
    ("cabeca", "head", "upperneck", "head+"),
    ("ombro_e", "lhumerus", "lhumerus", "lradius"),
    ("cotovelo_e", "lradius", "lradius", "lwrist"),
    ("mao_e", "lwrist", "lwrist", "lhand+"),
    ("ombro_d", "rhumerus", "rhumerus", "rradius"),
    ("cotovelo_d", "rradius", "rradius", "rwrist"),
    ("mao_d", "rwrist", "rwrist", "rhand+"),
    ("coxa_e", "lfemur", "lfemur", "ltibia"),
    ("canela_e", "ltibia", "ltibia", "lfoot"),
    ("coxa_d", "rfemur", "rfemur", "rtibia"),
    ("canela_d", "rtibia", "rtibia", "rfoot"),
]


def _ponta(arm, nome, mw):
    """Cabeça do osso no mundo; 'osso+' = cauda do osso."""
    if nome.endswith("+"):
        pb = arm.pose.bones[nome[:-1]]
        return mw @ pb.tail
    return mw @ arm.pose.bones[nome].head


def _rot_mundo(arm, osso):
    return (arm.matrix_world @ arm.pose.bones[osso].matrix).to_quaternion().normalized()


def retarget(fonte, alvo, mapa, q0, q1, inicio=1, passo=1.0, nome_acao="retarget", raiz_osso=None,
             mover_raiz="altura"):
    """Copia o movimento do esqueleto `fonte` (BVH) para `alvo` e grava numa ação nova do alvo.
    q0..q1: quadros da fonte; inicio: 1º quadro na ação do alvo; passo: quadros da fonte por quadro do alvo.
    mover_raiz: "altura" = só sobe/desce o quadril (ande com a raiz do objeto); "tudo" = deslocamento completo
    (relativo ao 1º quadro); None = quadril fixo. A fonte fica intacta (apague-a depois).
    O giro em z do ator no quadro q0 é anulado: o alvo começa olhando para a frente dele (-y no Zé e no UE)."""
    bpy = _bpy()
    from mathutils import Quaternion, Matrix, Vector
    sc = bpy.context.scene
    mapa = [m for m in mapa if m[0] in alvo.pose.bones and m[1] in fonte.pose.bones]
    raiz_osso = raiz_osso or mapa[0][0]
    raiz_fonte = mapa[0][1]
    # ---- repouso: alvo sem pose, fonte na pose de repouso (BVH: rotações zero = T-pose da CMU)
    ad_f = fonte.animation_data
    acao_f = ad_f.action if ad_f else None
    if ad_f:
        ad_f.action = None
    for pb in fonte.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    ad_a = alvo.animation_data or alvo.animation_data_create()
    ad_a.action = None
    usa_nla = ad_a.use_nla
    ad_a.use_nla = False
    for pb in alvo.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    mwf, mwa = fonte.matrix_world.copy(), alvo.matrix_world.copy()
    rest_f = {m[1]: _rot_mundo(fonte, m[1]) for m in mapa}
    # ---- direção de frente (lado esquerdo × cima) da fonte e do alvo, para alinhar o giro em z
    src_l = next(m for m in mapa if m[1] == "lfemur")
    src_r = next(m for m in mapa if m[1] == "rfemur")

    def frente(lado_e, lado_d):
        v = (lado_e - lado_d)
        v.z = 0
        f = v.normalized().cross(Vector((0, 0, 1)))
        return f

    fr_alvo = frente(mwa @ alvo.pose.bones[src_l[0]].head, mwa @ alvo.pose.bones[src_r[0]].head)
    fr_rest = frente(mwf @ fonte.pose.bones["lfemur"].head, mwf @ fonte.pose.bones["rfemur"].head)
    G = fr_rest.rotation_difference(fr_alvo)
    calib = {}
    for t, s, a, b in mapa:
        ds = G @ (_ponta(fonte, b, mwf) - _ponta(fonte, a, mwf)).normalized()
        pb = alvo.pose.bones[t]
        ref = None
        for ch in pb.children:
            if any(ch.name == m[0] for m in mapa):
                ref = mwa @ ch.head
                break
        dt = ((ref if ref is not None else mwa @ pb.tail) - mwa @ pb.head).normalized()
        al = dt.rotation_difference(ds)
        calib[t] = al @ _rot_mundo(alvo, t)
    h_a0 = (mwa @ alvo.pose.bones[raiz_osso].head)

    def perna(arm, mw, coxa, canela, pe):
        a, b, c = (mw @ arm.pose.bones[x].head for x in (coxa, canela, pe))
        return (b - a).length + (c - b).length

    t_coxa = src_l[0]
    t_canela = next(m[0] for m in mapa if m[1] == "ltibia")
    pe_alvo = alvo.pose.bones[t_canela]
    pe_alvo_ponta = mwa @ pe_alvo.tail
    perna_a = (mwa @ pe_alvo.head - mwa @ alvo.pose.bones[t_coxa].head).length + (pe_alvo_ponta - mwa @ pe_alvo.head).length
    for ch in pe_alvo.children:          # se houver osso do pé, a canela vai até a cabeça dele
        perna_a = (mwa @ pe_alvo.head - mwa @ alvo.pose.bones[t_coxa].head).length + (mwa @ ch.head - mwa @ pe_alvo.head).length
        break
    perna_f = perna(fonte, mwf, "lfemur", "ltibia", "lfoot")
    k_alt = perna_a / max(perna_f, 1e-3)
    if ad_f:
        ad_f.action = acao_f
    sc.frame_set(int(q0))
    fr_q0 = frente(mwf @ fonte.pose.bones["lfemur"].head, mwf @ fonte.pose.bones["rfemur"].head)
    Y = fr_q0.rotation_difference(fr_rest)          # tira o giro do ator no 1º quadro da tomada
    W = G @ Y
    Ginv = G.inverted()
    # ---- ação nova do alvo
    acao = bpy.data.actions.new(nome_acao)
    acao.use_fake_user = True
    ad_a.action = acao
    if hasattr(ad_a, "action_slot") and getattr(acao, "slots", None) is not None and not len(acao.slots):
        try:
            ad_a.action_slot = acao.slots.new("OBJECT", alvo.name)
        except Exception:
            pass
    ordem = [pb for pb in alvo.pose.bones]          # pose.bones já vem de pai para filho
    nomes = {m[0]: m for m in mapa}
    arm_inv = mwa.to_quaternion().inverted()
    base_xy = None
    f, k = float(q0), 0
    while f <= q1 + 1e-6:
        sc.frame_set(int(f), subframe=f - int(f))
        P = {}
        for pb in ordem:
            pai = pb.parent
            Rb = pb.bone.matrix_local
            if pai is not None:
                E = P[pai.name] @ pai.bone.matrix_local.inverted() @ Rb
            else:
                E = Rb.copy()
            if pb.name in nomes:
                t, s, _, _ = nomes[pb.name]
                delta = W @ _rot_mundo(fonte, s) @ rest_f[s].inverted() @ Ginv
                q_mundo = delta @ calib[t]
                q_arm = arm_inv @ q_mundo
                qb = E.to_quaternion().inverted() @ q_arm
                pb.rotation_mode = "QUATERNION"
                pb.rotation_quaternion = qb
                M = E @ qb.to_matrix().to_4x4()
                if pb.name == raiz_osso and mover_raiz:
                    hf = mwf @ fonte.pose.bones[raiz_fonte].head
                    if base_xy is None:
                        base_xy = hf.copy()
                    d = W @ ((hf - base_xy) * k_alt)
                    d.z = hf.z * k_alt - h_a0.z
                    if mover_raiz == "altura":
                        d.x = d.y = 0.0
                    loc_arm = (mwa.inverted().to_3x3() @ d)
                    # location do pose bone é no espaço do osso em repouso
                    pb.location = Rb.to_3x3().inverted() @ loc_arm
                    M = Matrix.Translation(loc_arm) @ M
                    pb.keyframe_insert("location", frame=inicio + k)
                pb.keyframe_insert("rotation_quaternion", frame=inicio + k)
            else:
                M = E @ pb.matrix_basis
            P[pb.name] = M
        f += passo
        k += 1
    ad_a.action = None
    ad_a.use_nla = usa_nla
    return acao


def apagar(obj):
    bpy = _bpy()
    for c in list(obj.children):
        apagar(c)
    bpy.data.objects.remove(obj)
