"""K_max — "Ah, e eu encho até o número escrito no pneu! Esse é o máximo que o pneu aguenta, não o certo pro
seu carro."

Close na lateral de um pneu inteiro (sem marca nem modelo) com "MAX 51 PSI" em relevo, curvado no flanco
(valor genérico). Em "número escrito no pneu" o texto ganha destaque (callout); em "máximo que o pneu aguenta"
o relevo vira aviso laranja; em "não o certo" uma seta ciano marca "NÃO É ESTE" e outra aponta para a porta
("O CERTO ESTÁ NA PORTA"), puxando o plano seguinte. Tempos de palavras.json.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _tec as T
C, tc = T.C, T.tc
import bpy
import numpy as np
from mathutils import Vector

P = C.plano("K_max")
D = P["dur"]
sc = T.setup(P, alvo=(0, 0, 0.5), luz=0.45)

t_num = T.palavra(P, "número escrito no pneu", padrao=0.23)
t_max = T.palavra(P, "máximo que o pneu aguenta", padrao=0.52)
t_nao = T.palavra(P, "não o certo", padrao=0.77)

pn = tc.pneu_corte("pneu", loc=(0, 0, 0), yaw=-70, pressao=1.0, seg_ang=360, metade="inteiro")
pf = pn["perfil"]
a0, r0 = pf["a0"], pf["r0"]
lado = np.where(a0 > 0)[0]
ordem = lado[np.argsort(r0[lado])]
R_, A_ = r0[ordem], a0[ordem]

# material do relevo: borracha que acende em laranja (nó Value "alerta")
mt = tc.mat_fosco("#2A2B2F", 0.6, "relevo")
b = mt.node_tree.nodes["Principled BSDF"]
v = mt.node_tree.nodes.new("ShaderNodeValue"); v.name = v.label = "alerta"
mul = mt.node_tree.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 3.5
mt.node_tree.links.new(v.outputs[0], mul.inputs[0])
mt.node_tree.links.new(mul.outputs[0], b.inputs["Emission Strength"])
b.inputs["Emission Color"].default_value = tc.lin(tc.LARANJA)
T.key_no(v.outputs[0], 0, 0.0)
T.key_no(v.outputs[0], t_max, 0.0)
T.key_no(v.outputs[0], t_max + 0.35, 1.0)
mt_cinza = tc.mat_fosco("#2A2B2F", 0.6, "relevo_cinza")

fonte = bpy.data.fonts.load(T.FONTE)


def relevo(txt, r_t, theta_c, tam, mat, esp=0.0005):
    """Texto em relevo curvado no flanco (lado +X), centrado no ângulo theta_c, raio r_t."""
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = txt
    cu.font = fonte
    cu.size = tam
    cu.extrude = esp / 2
    cu.align_x = "CENTER"
    cu.space_character = 1.15
    ob = bpy.data.objects.new("txt", cu)
    sc.collection.objects.link(ob)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob)
    for vv in me.vertices:
        u, w, z = vv.co
        th = theta_c - u / r_t
        rr = r_t + w - tam * 0.35
        a = float(np.interp(rr, R_, A_)) + 0.0004 + (z + esp / 2)
        vv.co = (a, rr * math.sin(th), -rr * math.cos(th))
    me.materials.append(mat)
    o = bpy.data.objects.new(txt, me)
    sc.collection.objects.link(o)
    o.parent = pn["pai"]
    return o


txt_max = relevo("MAX 51 PSI", 0.250, math.pi, 0.017, mt)
relevo("TUBELESS", 0.283, math.pi + 0.30, 0.011, mt_cinza)
relevo("RADIAL", 0.283, math.pi - 0.27, 0.011, mt_cinza)
bpy.context.view_layer.update()
mw = pn["pai"].matrix_world
centro = mw @ Vector((float(np.interp(0.25, R_, A_)), 0.0, 0.25))
normal = (mw.to_3x3() @ Vector((1, 0, 0))).normalized()
direita = (mw.to_3x3() @ Vector((0, 1, 0))).normalized()

cam = T.camera(tuple(centro + normal), tuple(centro), lente=85)
T.cam_key(cam, 0, tuple(centro + normal * 0.86 + direita * 0.16 + Vector((0, 0, 0.10))), tuple(centro - Vector((0, 0, 0.01))))
T.cam_key(cam, D, tuple(centro + normal * 0.72 + direita * 0.09 + Vector((0, 0, 0.07))), tuple(centro - Vector((0, 0, 0.012))))
T.linear([cam])


@T.hud
def desenhar(h, t):
    k = h.k
    h.cantos()
    cx, cy = h.px(centro)
    # destaque do número (moldura ciano em volta do relevo)
    d = T.suave(t, t_num, t_num + 0.3)
    if d > 0:
        cor = tc.CIANO if t < t_max else tc.LARANJA
        wbox, hbox = 330 * k, 80 * k
        h.d.rounded_rectangle([cx - wbox, cy - hbox, cx + wbox, cy + hbox], radius=int(14 * k),
                              outline=T.rgb(cor) + (int(255 * d),), width=max(1, int(4 * k)))
    h.texto((540 * k, 1180 * k), "NÚMERO DO PNEU", 34, "#DDE3EA", "ms", espaco=0.14,
            alpha=255 * d * (1 - T.suave(t, t_max, t_max + 0.2)))
    m = T.suave(t, t_max, t_max + 0.3)
    h.tag((540, 1210), "MÁXIMO QUE AGUENTA", tc.LARANJA, 40, alpha=m)
    # "não é este": seta ciano + aviso; e a dica da porta
    n_ = T.suave(t, t_nao, t_nao + 0.35)
    if n_ > 0:
        p1 = (cx - 150 * k, cy - 95 * k)
        p0 = (p1[0] - 120 * k * n_, p1[1] - 200 * k * n_)
        T.seta(h, p0, p1, tc.CIANO, esp=7, cab=30, alpha=255 * n_)
        h.texto((p0[0] - 60 * k, p0[1] - 24 * k), "NÃO É ESTE", 44, tc.CIANO, "ls", alpha=255 * n_)
    p_ = T.suave(t, t_nao + 0.6, t_nao + 0.9)
    if p_ > 0:
        h.tag((500, 1620), "O CERTO ESTÁ NA PORTA", tc.VERDE, 34, alpha=p_)
        T.seta(h, (850 * k, 1607 * k), ((850 + 140 * p_) * k, 1607 * k), tc.VERDE, esp=8, cab=28, alpha=255 * p_)


C.renderizar(P, sys.argv)
