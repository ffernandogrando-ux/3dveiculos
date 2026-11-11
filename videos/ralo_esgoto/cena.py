"""Vídeo: ralo com cheiro de esgoto "tratado" com desinfetante (roteiro 1031_22.srt, 77,5 s) — canal "dentro da sua casa".

Uso:  python cena.py   ->  ralo_esgoto.blend + cortes.json
Cenário (banheiro térreo em corte + encanamento até a rua) vem de cenario.py; aqui fica só a história.
Tempos em segundos, copiados do roteiro.
"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cenario as cn
from cenario import FL, RALO_X, VASO_X, RESP_X, YC, REDE, mt, pc, bpy
from mathutils import Vector
from motor import (mat, box, empty, arrow, pop_in, pop_out, grow, hide_until, hide_from, jump, k, glow, cameras,
                   write_cuts, save)

HERE = os.path.dirname(os.path.abspath(__file__))
DUR = 77.6
mt.setup(DUR)
M = cn.materiais()
M["shirt_enc"] = mat("shirt_enc", "#2e5fa8", rough=0.7)
S = cn.montar(M)
LOOP = 75.45

# ================================================================ estado (para trocas instantâneas e movimentos)
_ult = {}


def _val(o, attr):
    key = (o.name, attr)
    if key not in _ult:
        v = getattr(o, attr)
        _ult[key] = tuple(v) if hasattr(v, "__len__") else v
    return _ult[key]


def pular(o, attr, t, v):
    """Troca instantânea em t."""
    jump(o, attr, t, _val(o, attr), v)
    _ult[(o.name, attr)] = v


def mudar(o, attr, t0, t1, v):
    """Movimento suave de t0 a t1."""
    k(o, attr, t0, _val(o, attr))
    k(o, attr, t1, v)
    _ult[(o.name, attr)] = v


def rad(*a):
    return tuple(math.radians(x) for x in a)


def tubo_arco(nome, a, b, r, m, sobe=0.04, frac=0.55):
    a, b = Vector(a), Vector(b)
    c = Vector((a.x + (b.x - a.x) * frac, (a.y + b.y) / 2, a.z + sobe))
    pts = [tuple((1 - u) ** 2 * a + 2 * (1 - u) * u * c + u * u * b) for u in [i / 12 for i in range(13)]]
    o = pc._tubo_poli(nome, pts, r, m)
    o.scale = (0, 0, 0)
    return o


def janelas(o, faixas):
    """Mostra o objeto só nos intervalos [(t0, t1), ...] (troca instantânea de escala)."""
    for a, b in faixas:
        pular(o, "scale", a, (1, 1, 1))
        pular(o, "scale", b, (0, 0, 0))


# ================================================================ materiais próprios (destaques)
agua = S["agua_sifao"]
m_agua = M["water_c"].copy(); m_agua.name = "agua_fecho"
agua.data.materials[0] = m_agua
m_ramal = M["pvc"].copy(); m_ramal.name = "pvc_ramal"
S["ramal"].data.materials[0] = m_ramal; S["ramal"].data.materials[2] = m_ramal
m_resp = M["pvc"].copy(); m_resp.name = "pvc_respiro"
S["respiro"].data.materials[0] = m_resp; S["respiro"].data.materials[2] = m_resp

# ================================================================ água do sifão (fecho hídrico)
nv = S["nivel_sifao"]
ZF, ZE = S["z_fecho"] + 0.001, -0.42
_ult[(nv.name, "location")] = (0, 0, ZF)
k(nv, "location", 0.0, (0, 0, ZF))
mudar(nv, "location", 16.4, 17.1, (0, 0, ZE))            # quando ela some
pular(nv, "location", 19.2, (0, 0, ZF))
mudar(nv, "location", 20.4, 22.2, (0, 0, ZE))            # evapora
pular(nv, "location", 22.9, (0, 0, ZF))
mudar(nv, "location", 25.0, 25.55, (0, 0, ZE))           # descarga puxa
mudar(nv, "location", 29.3, 30.3, (0, 0, ZF))            # a água que desce junto
mudar(nv, "location", 32.2, 33.0, (0, 0, ZE))            # 1 semana: secou
pular(nv, "location", 61.0, (0, 0, ZE))
mudar(nv, "location", 62.8, 63.6, (0, 0, ZF))            # jarra toda semana
mudar(nv, "location", 68.5, 69.1, (0, 0, ZE))            # voltou logo
pular(nv, "location", 72.65, (0, 0, ZF))                 # com respiro, segura
pular(nv, "location", LOOP, (0, 0, ZF))
glow(m_agua, 12.35, 14.1, peak=0.45, pulses=2)
glow(m_agua, 29.4, 30.9, peak=0.45, pulses=2)
glow(m_agua, 63.4, 64.2, peak=0.45, pulses=1)
glow(m_ramal, 70.9, 71.6, peak=1.2, pulses=1)            # "o sifão"
glow(m_resp, 72.4, 73.6, peak=1.4, pulses=2)             # "o respiro"

# ================================================================ raio-x: a pele da frente cai (lá embaixo)
TX = 7.25
pele = S["pele"]
mudar(pele, "location", TX, TX + 0.45, (0, -0.5, -1.4))
mudar(pele, "rotation_euler", TX, TX + 0.45, rad(-25, 0, 0))
pular(pele, "scale", TX + 0.47, (0, 0, 0))
pular(pele, "location", LOOP, (0, 0, 0))
pular(pele, "rotation_euler", LOOP, (0, 0, 0))
pular(pele, "scale", LOOP, (1, 1, 1))
for inteiro, cortado, guardado in ((S["vaso"]["raiz"], S["vaso_corte"]["raiz"], True), (S["grelha"], S["grelha_corte"], False)):
    pular(inteiro, "scale", TX, (0, 0, 0))
    pular(inteiro, "scale", LOOP, (1, 1, 1))
    if guardado:
        pular(cortado, "location", TX, (VASO_X, 0, FL))
        pular(cortado, "location", LOOP, (VASO_X, 0, -100))
    else:
        pular(cortado, "scale", TX, (1, 1, 1))
        pular(cortado, "scale", LOOP, (0, 0, 0))

# ================================================================ gás do esgoto (bolhas)
rc, cc = S["ramal_cam"], S["col_cam"]
i_stop = len(rc) - 1 - S["i_sifao"] + 2
pc.bolhas_cano("gas_col", M, cc, 8.0, LOOP, n=7, periodo=3.2, inverter=True)
for nm, a, b in (("gas_preso_a", 12.4, 16.45), ("gas_preso_b", 29.6, 31.1), ("gas_preso_c", 63.6, 68.5),
                 ("gas_preso_d", 72.7, LOOP)):
    pc.bolhas_cano(nm, M, rc, a, b, n=4, periodo=1.6, inverter=True, ate=i_stop)
sobe = list(reversed(rc)) + [(RALO_X, FL + 0.5)]
for nm, a, b in (("gas_sobe_a", 17.0, 19.15), ("gas_sobe_b", 33.3, 37.6), ("gas_sobe_c", 39.2, 41.65),
                 ("gas_sobe_d", 68.9, 69.7)):
    pc.bolhas_cano(nm, M, sobe, a, b, n=6, periodo=1.3)
pc.particulas("gas_sala", M, "gas", 10, (RALO_X, 0.05, FL + 0.05), (0.85, 0.45, FL + 1.5), 17.4, 19.15, espalha=0.2, r=0.02, seed=4)

# fedor saindo do ralo
fed = pc.fedor("fedor", M, (RALO_X, 0.06, FL + 0.03), n=4, altura=0.5, largura=0.2, r=0.013)
for a, b in ((0.0, 3.1), (17.4, 19.15), (33.3, 34.3), (39.3, 41.65), (41.7, 44.4), (68.9, 69.7), (LOOP, DUR)):
    pc.animar_fedor(fed, a, b, periodo=1.1)

# ================================================================ morador
mor = S["morador"]
R = mor["raiz"]
BD, BE = mor["braco_d"], mor["braco_e"]
fr = S["frasco"]
HOOK_LOC, HOOK_ROT = (0.6, 0.36, FL), rad(0, 0, -12)
REPOUSO = (0, 0, 0)
M["brilho"] = mat("brilho", "#b86ef0", rough=0.4, emit=0.5)
M["espuma"] = mat("espuma", "#f6efff", rough=0.5)


def melhor_braco(ombro, mao, alvo, xs, zs):
    """Procura a rotação do ombro que leva a mão mais perto do alvo (pose montada antes das chaves)."""
    best = None
    for ax in xs:
        for az in zs:
            ombro.rotation_euler = rad(ax, 0, az)
            bpy.context.view_layer.update()
            d = (mao.matrix_world.translation - Vector(alvo)).length
            if best is None or d < best[0]:
                best = (d, rad(ax, 0, az))
    ombro.rotation_euler = best[1]
    bpy.context.view_layer.update()
    return best[1]


R.location, R.rotation_euler = HOOK_LOC, HOOK_ROT
bpy.context.view_layer.update()
DESPEJA = melhor_braco(BD, mor["mao_d"], (0.6, 0.06, FL + 0.98), range(-130, -10, 3), range(-45, 46, 3))
MAO = mor["mao_d"].matrix_world.translation.copy()
nariz = bpy.data.objects["morador_nariz"].matrix_world.translation.copy()
NARIZ = melhor_braco(BE, mor["mao_e"], nariz + Vector((0, -0.06, -0.02)), range(-170, -60, 4), range(-60, 40, 4))
BE.rotation_euler = REPOUSO
# frasco na mão, com o bico virado para o ralo: centro do frasco na mão
CENTRO = MAO + Vector((-0.03, -0.05, -0.02))
ALVO_BICO = Vector((RALO_X, 0.03, CENTRO.z - 0.12))
D_FULL = (ALVO_BICO - CENTRO).normalized()
D_MEIO = (D_FULL + Vector((0, 0, 1.1))).normalized()
BICO = CENTRO + D_FULL * 0.13
GRELHA = Vector((RALO_X, 0.03, FL + 0.004))

for o, a, v in ((R, "location", HOOK_LOC), (R, "rotation_euler", HOOK_ROT), (BD, "rotation_euler", DESPEJA),
                (BE, "rotation_euler", NARIZ), (R, "scale", (1, 1, 1)), (fr, "scale", (0, 0, 0))):
    setattr(o, a, v)
    k(o, a, 0.0, v)
    _ult[(o.name, a)] = v


def despejar(nome, t0, t1, perfume, perf_t):
    """Frasco virado sobre o ralo: jato reto e curto, gotas, respingos e espuma na grelha; depois brilhinhos de
    perfume subindo até o nariz."""
    f = pc.frasco(nome + "_frasco", M)
    f.rotation_mode = "QUATERNION"
    for t, d in ((t0 - 0.3, D_MEIO), (t0, D_FULL), (t1, D_FULL), (t1 + 0.35, D_MEIO)):
        q = Vector((0, 0, 1)).rotation_difference(d)
        k(f, "rotation_quaternion", t, q)
        k(f, "location", t, CENTRO - q @ Vector((0, 0, 0.12)))
    hide_until(f, t0 - 0.3)
    hide_from(f, t1 + 0.45)
    j = mt.tube(nome + "_jato", BICO, GRELHA, 0.011, M["stream"], seg=10)
    grow(j, t0 + 0.02, t0 + 0.14, "z")
    k(j, "scale", t1, (1, 1, 1))
    k(j, "scale", t1 + 0.12, (1, 1, 0.0))
    hide_from(j, t1 + 0.14)
    for i in range(5):
        g = pc.esfera(f"{nome}_gota{i}", 0.014, tuple(BICO), M["stream"], scale=(1, 1, 1.5), seg=10)
        mt.loop_fall(g, t0 + 0.05, t1, BICO, GRELHA, 0.32, phase=0.064 * i)
    pc.particulas(nome + "_respingo", M, "stream", 10, tuple(GRELHA), tuple(GRELHA + Vector((0, -0.02, 0.07))),
                  t0 + 0.15, t1, espalha=0.07, r=0.007, seed=21)
    rr = __import__("random").Random(len(nome))
    for i in range(8):
        a = rr.uniform(0, 6.28); d = rr.uniform(0.02, 0.075)
        e = pc.esfera(f"{nome}_espuma{i}", rr.uniform(0.012, 0.02), (RALO_X + d * math.cos(a), 0.04 + abs(d * math.sin(a)) * 0.6,
                      FL + 0.008), M["espuma"], seg=12)
        pop_in(e, t0 + 0.4 + 0.12 * i, 0.25)
        pop_out(e, t1 + 1.2 + 0.05 * i, 0.25)
    if perfume:
        pc.particulas(nome + "_perfume", M, "brilho", 16, tuple(GRELHA + Vector((0, 0.02, 0.05))),
                      (HOOK_LOC[0] + 0.05, HOOK_LOC[1] - 0.15, FL + 1.45), perf_t, perf_t + 2.6, espalha=0.22, r=0.016, seed=17)


# gancho: tampa o nariz e despeja; "até funciona": cheira o perfume, satisfeito
despejar("d1", 0.25, 4.4, True, 4.6)
pc.rosto_expr(mor, 0.0, boca="neutra")
mudar(BE, "rotation_euler", 3.3, 3.7, REPOUSO)
mudar(BD, "rotation_euler", 4.5, 4.95, REPOUSO)
pc.rosto_expr(mor, 4.75, olhos="fechados", boca="sorriso")
mudar(R, "rotation_euler", 4.75, 5.6, rad(-6, 0, -12))
pc.rosto_expr(mor, 6.3, olhos="abertos")
mudar(R, "rotation_euler", 6.3, 6.8, HOOK_ROT)
# "quando ela some": tapa o nariz e faz cara feia
mudar(BE, "rotation_euler", 17.9, 18.25, rad(-135, 0, -25))
pc.rosto_expr(mor, 18.2, boca="triste")
pular(R, "scale", 19.2, (0, 0, 0))
pular(BE, "rotation_euler", 19.2, REPOUSO)
# "e o desinfetante?": despeja de novo
pular(R, "scale", 25.95, (1, 1, 1))
pular(R, "location", 25.95, HOOK_LOC)
pular(R, "rotation_euler", 25.95, HOOK_ROT)
pular(BD, "rotation_euler", 25.95, DESPEJA)
pc.rosto_expr(mor, 25.95, boca="sorriso")
despejar("d2", 26.25, 29.2, True, 27.2)
mudar(BD, "rotation_euler", 29.3, 29.75, REPOUSO)
pular(R, "scale", 31.1, (0, 0, 0))
# gás sulfídrico: enjoo
POS_MEIO, ROT_MEIO = (0.85, 0.62, FL), rad(0, 0, 8)
pular(R, "location", 41.7, POS_MEIO)
pular(R, "rotation_euler", 41.7, ROT_MEIO)
pular(R, "scale", 41.7, (1, 1, 1))
pc.rosto_expr(mor, 41.7, boca="neutra")
pc.rosto_expr(mor, 44.5, boca="triste")
mudar(BE, "rotation_euler", 45.5, 45.9, rad(-150, 0, -30))
pc.rosto_expr(mor, 45.9, olhos="fechados")
pc.particulas("gas_rosto", M, "gas", 14, (RALO_X, 0.05, FL + 0.05), (0.85, 0.5, FL + 1.45), 44.4, 47.85, espalha=0.15, r=0.02, seed=6)
pular(R, "scale", 47.85, (0, 0, 0))
pular(BE, "rotation_euler", 47.85, REPOUSO)
# água sanitária: um frasco em cada mão; tosse com a mistura
pular(R, "scale", 53.6, (1, 1, 1))
pc.rosto_expr(mor, 53.6, olhos="abertos", boca="sorriso")
pular(BD, "rotation_euler", 53.6, rad(-45, 0, 8))
pular(BE, "rotation_euler", 53.6, rad(-45, 0, -8))
pular(fr, "rotation_euler", 53.6, rad(45, 0, 0))
pular(fr, "scale", 53.6, (1, 1, 1))
san = pc.frasco("sanitaria", M, corpo="bleach", rotulo="bleach_label", tampa="bleach_label", altura=0.28, largura=0.11)
san.parent = mor["mao_e"]
san.location = (0.0, -0.02, -0.06)
san.rotation_euler = rad(45, 0, 0)
pop_in(san, 54.1, 0.35)
pc.rosto_expr(mor, 56.8, boca="neutra")
pc.rosto_expr(mor, 57.8, olhos="fechados", boca="o")
xis = pc.xis("xis_mistura", M, tamanho=0.32)
xis.location = (0.85, 0.05, FL + 1.15)
pop_in(xis, 56.8, 0.3)
pop_out(xis, 59.45, 0.25)
tox = pc.nuvem("toxico", M, (0.85, 0.3, FL + 1.05), raio=0.3, n=14, mat_nome="toxic", seed=13)
pop_in(tox, 57.8, 0.8)
hide_from(tox, 59.75)
# depois do rebobinar: jarra
pular(fr, "scale", 59.75, (0, 0, 0))
pular(san, "scale", 59.75, (0, 0, 0))
pular(R, "location", 61.0, HOOK_LOC)
pular(R, "rotation_euler", 61.0, HOOK_ROT)
pular(BE, "rotation_euler", 61.0, REPOUSO)
pular(BD, "rotation_euler", 61.0, rad(-50, 0, 15))
pc.rosto_expr(mor, 61.0, olhos="abertos", boca="sorriso")
pular(R, "scale", 64.2, (0, 0, 0))
# encanador e plano geral
POS_FIM, ROT_FIM = (1.55, 1.05, FL), rad(0, 0, 10)
pular(R, "location", 67.87, POS_FIM)
pular(R, "rotation_euler", 67.87, ROT_FIM)
pular(BD, "rotation_euler", 67.87, REPOUSO)
pular(R, "scale", 67.87, (1, 1, 1))
pc.rosto_expr(mor, 69.2, boca="triste")
pc.rosto_expr(mor, 72.7, boca="sorriso")
for t in (72.9, 73.4, 73.9, 74.4, 74.9):
    k(BD, "rotation_euler", t, rad(0, -150, 0))
    k(BD, "rotation_euler", t + 0.25, rad(0, -120, 0))
_ult[(BD.name, "rotation_euler")] = rad(0, -120, 0)
# loop: volta ao primeiro quadro
pular(R, "location", LOOP, HOOK_LOC)
pular(R, "rotation_euler", LOOP, HOOK_ROT)
pular(BD, "rotation_euler", LOOP, DESPEJA)
pular(BE, "rotation_euler", LOOP, NARIZ)
despejar("d3", LOOP + 0.25, DUR + 1, False, 0)

enc = pc.personagem("encanador", M, camisa="shirt_enc", altura=1.15)
E = enc["raiz"]
E.location = (2.3, 0.95, FL)
E.rotation_euler = rad(0, 0, -15)
hide_until(E, 69.75)
hide_from(E, LOOP)
chave = pc.capsula("chave_grifo", 0.018, 0.22, M["steel"])
chave.parent = enc["mao_d"]
chave.location = (0, -0.02, 0.0)
for t in (70.2, 70.6, 71.0):
    k(enc["braco_d"], "rotation_euler", t, rad(-70, 0, 0))
    k(enc["braco_d"], "rotation_euler", t + 0.2, rad(-40, 0, 0))
k(enc["braco_d"], "rotation_euler", 71.6, rad(-150, 0, 20))          # aponta para o respiro
k(enc["braco_d"], "rotation_euler", 73.8, rad(-150, 0, 20))

# ================================================================ descarga sem respiro (24,4–25,9)
nc = S["nivel_caixa"]
_ult[(nc.name, "location")] = tuple(nc.location)
mudar(nc, "location", 24.4, 24.95, (0, 0, FL + 0.5))
pular(nc, "location", 26.0, (0, 0, FL + 0.746))
descarga = list(S["queda_cam"]) + [p for p in cc if p[0] > VASO_X + 0.1]
pc.bolhas_cano("descarga", M, descarga, 24.5, 25.9, n=8, periodo=0.7, r=0.026, mat_nome="water_c")
pc.bolhas_cano("descarga2", M, descarga, 73.0, 74.4, n=8, periodo=0.7, r=0.026, mat_nome="water_c")
for i, (tip, d) in enumerate((((1.02, -0.07, 0.0), (1, 0, 0)), ((1.05, -0.07, -0.26), (0, 0, -1)),
                              ((2.2, -0.08, -0.48), (1, 0, 0)))):
    a = arrow(f"seta_succao{i}", 0.26, M["red"], tip, direction=d, r=0.018, head=0.045)
    pop_in(a, 24.75 + 0.1 * i, 0.3)
    pop_out(a, 25.8, 0.2)

# ================================================================ linha do tempo: barata e frascos vazios
bar, pernas = pc.barata("barata", M, tam=0.16)
caminho = [(x, 0.035, z) for x, z in reversed(rc)] + [(RALO_X, 0.035, FL + 0.01)]
pc.seguir_caminho(bar, caminho, 34.9, 36.5, cima=(0, -1, 0))
pc.seguir_caminho(bar, [(RALO_X, 0.04, FL + 0.005), (0.75, 0.2, FL + 0.005), (0.95, 0.35, FL + 0.005)], 36.55, 37.6,
                  cima=(0, 0, 1))
pc.andar_barata(pernas, 34.9, 37.6)
hide_until(bar, 34.9)
hide_from(bar, 37.66)
vaz = []
for i, (x, y, rz) in enumerate(((0.25, 0.3, 20), (0.85, 0.22, 70), (0.4, 0.55, 140), (0.95, 0.5, 100))):
    f = pc.frasco(f"vazio{i}", M)
    f.location = (x, y, FL + 0.05)
    f.rotation_euler = rad(90, 0, rz)
    pop_in(f, 38.8 + 0.4 * i, 0.3)
    hide_from(f, 53.6)
    vaz.append(f)
ovo = pc.ovo_podre("ovo", M, tam=0.13)
ovo.location = (0.32, 0.3, FL)
pop_in(ovo, 41.9, 0.35)
hide_from(ovo, 47.85)

# ================================================================ bactérias na grelha (47,9–50,8)
bact = pc.bacterias("bact", M, (RALO_X, 0.045, FL + 0.004), raio=0.04, n=9, tam=0.009)
for i, b in enumerate(bact):
    pop_in(b, 48.0 + 0.06 * i, 0.25)
    pop_out(b, 49.6 + 0.08 * i, 0.2)
fb = pc.frasco("frasco_b", M)
fb.location = (0.768, 0.04, FL + 0.32)
fb.rotation_euler = rad(0, -40, 0)
hide_until(fb, 48.5)
k(fb, "rotation_euler", 48.6, rad(0, -40, 0))
k(fb, "rotation_euler", 49.0, rad(0, -120, 0))
hide_from(fb, 50.6)
jato_b = tubo_arco("jato_b", (0.56, 0.04, FL + 0.2), (RALO_X + 0.01, 0.04, FL + 0.005), 0.007, M["stream"], sobe=0.0)
janelas(jato_b, [(49.0, 50.4)])

# ================================================================ rua (50,9–53,5): gás subindo da rede
pc.bolhas_cano("gas_pred", M, S["pred_cam"], 50.6, 53.6, n=8, periodo=1.6, inverter=True)
pc.particulas("gas_rede", M, "gas", 12, (REDE[0] + 0.1, 0.05, REDE[1] - 0.12), (REDE[0] - 0.2, 0.05, REDE[1] + 0.2), 50.6,
              53.6, espalha=0.08, r=0.025, seed=8)

# ================================================================ solução: jarra (61–64,2) e limpeza (64,2–67,8)
jar = pc.jarra("jarra", M)
jar.location = (0.787, 0.03, FL + 0.54)
jar.rotation_euler = (0, 0, 0)
hide_until(jar, 61.0)
k(jar, "rotation_euler", 61.9, (0, 0, 0))
k(jar, "rotation_euler", 62.3, rad(0, -60, 0))
k(jar, "rotation_euler", 63.4, rad(0, -60, 0))
k(jar, "rotation_euler", 63.8, (0, 0, 0))
hide_from(jar, 64.2)
jato_j = tubo_arco("jato_agua", (0.55, 0.03, FL + 0.55), (RALO_X, 0.02, FL + 0.005), 0.012, M["water_c"], sobe=0.0)
janelas(jato_j, [(62.3, 63.4)])

grc = S["grelha_corte"]
G0 = tuple(grc.location)
mudar(grc, "location", 64.3, 64.6, (RALO_X + 0.22, 0.0, FL + 0.12))
mudar(grc, "location", 67.1, 67.45, G0)
cab = pc.bolo_cabelo("cabelo", M, tam=0.045)
cab.location = (RALO_X, 0.03, FL - 0.02)
pop_in(cab, 64.5, 0.3)
k(cab, "location", 66.2, (RALO_X, 0.03, FL - 0.02))
k(cab, "location", 66.6, (RALO_X + 0.12, 0.05, FL + 0.08))
pop_out(cab, 66.65, 0.25)
esc = pc.escova("escova", M)
esc.location = (RALO_X, 0.04, FL + 0.03)
hide_until(esc, 64.9)
pop_in(esc, 64.9, 0.25)
t = 65.2
while t < 66.5:
    k(esc, "location", t, (RALO_X - 0.03, 0.04, FL + 0.03))
    k(esc, "location", t + 0.15, (RALO_X + 0.03, 0.04, FL + 0.03))
    t += 0.3
pop_out(esc, 66.8, 0.25)

# ================================================================ respiro (71,6–72,6): cresce do coletor ao telhado
resp = S["respiro"]
org = Vector((RESP_X, 0.0, -0.475))
for v in resp.data.vertices:
    v.co -= org
resp.location = org
grow(resp, 71.6, 72.5, "z")
pop_in(S["respiro_ponta"], 72.45, 0.3)
pular(S["coletor"], "scale", 71.6, (0, 0, 0))
pular(S["coletor_b"], "scale", 71.6, (1, 1, 1))
for o in S["tampas_resp"]:
    pular(o, "scale", 71.6, (0, 0, 0))

# ================================================================ céu e luzes (tempo passando)
sky = S["sky"]
sky.day(0.0)
sky.day_night(20.3, cycles=3, step=0.3)                  # evapora
sky.day(34.3)
sky.state(34.45, 0.15, 0.18, "#1b2747", "#41507a")       # à noite
sky.state(37.6, 0.15, 0.18, "#1b2747", "#41507a")
sky.day(37.75)
for t, f in ((0.0, 1.0), (31.13, 1.0), (31.3, 0.4), (31.47, 1.0), (31.64, 0.4), (31.81, 1.0),
             (34.3, 1.0), (34.45, 0.35), (37.6, 0.35), (37.75, 1.0)):
    cn.luzes(S, t, f)

# ================================================================ câmeras
TRAP = ((0.70, -1.05, 0.0), (0.70, 0.3, -0.05))
SPLIT = ((0.75, -2.5, 0.8), (0.72, 0.3, 0.8))
H0 = ((0.12, -2.05, 1.5), (0.62, 0.3, 0.86))
shots = [
    (0.0, [(0.0, *H0), (4.4, (0.22, -1.8, 1.42), (0.62, 0.3, 0.84)), (6.3, (0.2, -1.95, 1.45), (0.62, 0.3, 0.84)),
           (7.15, (0.3, -1.9, 1.3), (0.62, 0.3, 0.7)), (7.95, *TRAP), (12.2, (0.70, -0.95, -0.01), (0.70, 0.3, -0.05))]),
    (12.25, [(12.25, (0.86, -0.85, -0.03), (0.76, 0.3, -0.08)), (16.2, (0.84, -0.78, -0.03), (0.76, 0.3, -0.08)),
             (16.35, (0.72, -1.05, 0.0), (0.72, 0.3, -0.05)), (17.1, (0.72, -1.05, 0.0), (0.72, 0.3, -0.05)),
             (18.3, (0.78, -2.7, 0.75), (0.74, 0.3, 0.6)), (19.15, (0.78, -2.6, 0.75), (0.74, 0.3, 0.6))]),
    (19.2, [(19.2, (1.25, -4.2, 1.3), (1.25, 0.5, 1.25)), (22.85, (1.2, -3.85, 1.25), (1.2, 0.5, 1.2))]),
    (22.9, [(22.9, (1.75, -4.5, 0.6), (1.75, 0.5, 0.5)), (25.9, (1.75, -4.15, 0.55), (1.75, 0.5, 0.45))]),
    (25.95, [(25.95, (0.8, -2.7, 0.85), (0.72, 0.3, 0.8)), (31.05, *SPLIT)]),
    (31.1, [(31.1, *SPLIT), (41.65, (0.75, -2.42, 0.8), (0.72, 0.3, 0.8))]),
    (41.7, [(41.7, (0.95, -1.9, 1.3), (0.8, 0.5, 0.95)), (44.4, (0.92, -1.5, 1.4), (0.82, 0.55, 1.15)),
            (47.8, (0.88, -1.05, 1.55), (0.85, 0.6, 1.45))]),
    (47.9, [(47.9, (0.62, -0.6, 0.72), (0.56, 0.06, 0.3)), (50.8, (0.6, -0.5, 0.65), (0.56, 0.06, 0.3))]),
    (50.85, [(50.85, (7.6, -3.3, -0.95), (7.6, 0.5, -1.15)), (51.8, (7.5, -3.3, -0.95), (7.5, 0.5, -1.15)),
             (53.5, (5.6, -3.6, -0.6), (5.6, 0.5, -0.75))]),
    (53.55, [(53.55, (1.0, -2.3, 1.25), (0.85, 0.5, 1.05)), (57.75, (0.98, -2.0, 1.3), (0.85, 0.5, 1.1)),
             (59.7, (0.95, -1.85, 1.35), (0.85, 0.5, 1.15))]),
    (61.0, [(61.0, *SPLIT), (64.15, (0.75, -2.35, 0.78), (0.72, 0.3, 0.78))]),
    (64.2, [(64.2, (0.62, -0.85, 0.62), (0.56, 0.15, 0.22)), (67.8, (0.6, -0.72, 0.58), (0.56, 0.15, 0.22))]),
    (67.87, [(67.87, (1.45, -5.6, 1.1), (1.45, 0.5, 0.95)), (69.7, (1.55, -5.4, 1.2), (1.55, 0.5, 1.05)),
             (71.55, (2.1, -6.6, 1.7), (2.1, 0.5, 1.55)), (72.65, (2.15, -6.8, 1.75), (2.15, 0.5, 1.6))]),
    (72.7, [(72.7, (2.3, -7.6, 1.55), (2.3, 0.5, 1.2)), (75.4, (3.3, -11.0, 1.7), (3.3, 0.5, 0.9))]),
    (LOOP, [(LOOP, *H0), (LOOP + 4.4, (0.22, -1.8, 1.42), (0.62, 0.3, 0.84))]),
]
cameras(shots, shakes=[(7.3, 7.6, 0.01), (31.13, 31.4, 0.01), (34.33, 34.6, 0.01), (37.67, 37.95, 0.01),
                       (57.8, 58.7, 0.012)])

write_cuts(os.path.join(HERE, "cortes.json"), [50.85, 53.55], DUR)
info = json.load(open(os.path.join(HERE, "cortes.json")))
info["rebobinar"] = [{"ini": 59.75, "fim": 61.0, "de": 31.1, "ate": 59.6}]
json.dump(info, open(os.path.join(HERE, "cortes.json"), "w"), indent=1)

pc.rosto_expr(mor, LOOP, olhos="abertos", boca="neutra")
save(os.path.join(HERE, "ralo_esgoto.blend"))
