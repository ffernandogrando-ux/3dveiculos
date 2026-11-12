"""F_achata — "Com pouco ar, o pneu achata no chão, igual chinelo velho. As beiradas pisam mais que o meio e
gastam primeiro."

Close baixo na seção de baixo do pneu em corte. Em "achata" a pressão cai (shape key) e a pegada alarga e passa
de verde a vermelho; aparece o contorno verde tracejado do pneu calibrado (preso ao chão). Em "beiradas" os
ombros da banda ficam vermelhos e lisos (sulcos comidos); em "gastam primeiro" o desgaste fecha.
Tempos lidos de palavras.json.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _tec as T
C, tc = T.C, T.tc
import bpy
import numpy as np
from mathutils import Vector

P = C.plano("F_achata")
D = P["dur"]
sc = T.setup(P, alvo=(0, 0, 0.12))

t_achata = T.palavra(P, "achata", padrao=0.2)
t_chinelo = T.palavra(P, "chinelo velho", padrao=0.43)
t_beira = T.palavra(P, "beiradas", padrao=0.57)
t_gasta = T.palavra(P, "gastam primeiro", padrao=0.88)

borr = tc.mat_borracha_viva("borr_F")
secv = tc.mat_secao_viva("sec_F")
pn = tc.pneu_animado("pneu", (1.0, 0.45), kw_b={"gasto_ombro": 1.0}, loc=(0, 0, 0), yaw=-14, seg_ang=300,
                     cor_pegada=tc.VERDE, fantasma=tc.VERDE, mat_borracha_pneu=borr, mat_secao_pneu=secv)
# pressão: começa um pouco baixa e achata em "achata"
tc.pneu_estado(pn, 0.15, C.F(0))
tc.pneu_estado(pn, 0.15, C.F(t_achata))
tc.pneu_estado(pn, 1.0, C.F(t_achata + 1.1))
# pegada verde -> vermelha junto com o achatamento
mpeg = T.mat_mix_emissivo(tc.VERDE, tc.VERMELHO, 6.0, nome="peg_borda")
mveu = T.mat_mix_emissivo(tc.VERDE, tc.VERMELHO, 1.4, alpha=0.22, nome="peg_veu")
for o in pn["objs"]:
    if o.name.endswith("_pegada_borda"):
        o.data.materials[0] = mpeg
    elif o.name.endswith("_pegada_veu"):
        o.data.materials[0] = mveu
for m in (mpeg, mveu):
    v = tc.no_valor(m, "mix")
    T.key_no(v, t_achata + 0.3, 0.0)
    T.key_no(v, t_achata + 1.1, 1.0)
# fantasma (calibrado) aparece logo depois de achatar
fant = [o for o in pn["objs"] if o.name.endswith("_fantasma")][0]
fant.hide_render = True
fant.keyframe_insert("hide_render", frame=C.F(0))
fant.hide_render = False
fant.keyframe_insert("hide_render", frame=C.F(t_achata + 0.6))
# desgaste das beiradas
for des in (tc.no_valor(borr, "desgaste"), tc.no_valor(secv, "desgaste")):
    T.key_no(des, 0, 0.0)
    T.key_no(des, t_beira, 0.0)
    T.key_no(des, t_beira + 0.8, 0.6)
    T.key_no(des, t_gasta, 0.6)
    T.key_no(des, t_gasta + 0.4, 1.0)

# câmera baixa na seção de baixo, push-in leve
alvo0, alvo1 = (0.0, 0.0, 0.17), (0.0, 0.0, 0.15)
cam = T.camera((0, -1.8, 0.5), alvo0, lente=85)
T.cam_key(cam, 0, (-0.45, -2.75, 0.55), alvo0)
T.cam_key(cam, D, (-0.32, -2.55, 0.48), alvo1)
T.linear([cam])

pf = pn["perfil"]
i_omb = T.i_perfil(pn, a_alvo=-0.084, lado=-1)
i_omb_d = T.i_perfil(pn, a_alvo=0.084, lado=1)
gv = fant.data.vertices
i_fant = max(range(len(gv)), key=lambda i: gv[i].co.x - 0.3 * abs(gv[i].co.z + 0.2))


@T.hud
def desenhar(h, t):
    h.cantos()
    f = pn["chaves"][0].value if pn["chaves"] else 0
    pneu = pn["objs"][0]
    p_omb = T.vert_mundo(pneu, T.idx_pneu(pn, 0, i_omb))
    p_peg = tc.ancora_mix(pn, "pegada_canto", f)
    p_fan = fant.matrix_world @ gv[i_fant].co
    h.tag((540, 1690), "POUCO AR", tc.LARANJA, 40, alpha=T.suave(t, 0.1, 0.4))
    h.texto((540 * h.k, 1760 * h.k), "IGUAL CHINELO VELHO", 28, "#DDE3EA", "ms", espaco=0.14,
            alpha=255 * T.suave(t, t_chinelo, t_chinelo + 0.25))
    h.callout(p_fan, (790, 820), "CALIBRADO", None, tc.VERDE, lado=1, tam=30,
              crescer=T.suave(t, t_achata + 0.7, t_achata + 1.2))
    h.callout(p_peg, (600, 1480), "PEGADA LARGA", None, tc.VERMELHO, lado=1, tam=32,
              crescer=T.suave(t, t_chinelo, t_chinelo + 0.5))
    h.callout(p_omb, (330, 1380), "BEIRADAS", "GASTAM PRIMEIRO" if t >= t_gasta else "PISAM MAIS", tc.VERMELHO,
              lado=-1, tam=34, crescer=T.suave(t, t_beira, t_beira + 0.5))


C.renderizar(P, sys.argv)
