"""C_olha_so — "Olha só." (transição rápida para o mundo técnico)

Pneu inteiro (metade de trás em corte + metade da frente que some) no estúdio escuro, com push-in rápido.
Uma varredura de raio-X ciano atravessa o pneu da esquerda para a direita: atrás da linha a borracha da frente
vira casca de raio-X (Fresnel ciano) e aparece o pneu em corte. Linha de varredura também no HUD.
Começa até 0,3 s depois de "Olha" (palavras.json).
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _tec as T
C, tc = T.C, T.tc
import bpy
from mathutils import Vector

P = C.plano("C_olha_so")
D = P["dur"]
sc = T.setup(P)

t_olha = T.palavra(P, "Olha", padrao=0.1) or 0.0
t0, t1 = min(t_olha + 0.02, D * 0.3), D * 0.85          # varredura

alvo = (0.0, 0.0, 0.30)
cam = T.camera((0, -3.4, 1.2), alvo, lente=70)
T.cam_key(cam, 0, (-0.35, -3.45, 1.20), alvo)
T.cam_key(cam, D, (-0.22, -2.95, 1.08), alvo)
T.linear([cam])
bpy.context.view_layer.update()
direcao = (cam.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()


def mat_varredura():
    """Borracha que vira raio-X atrás da linha de varredura (nó Value 'varre', em metros ao longo de 'direcao')."""
    m = tc.mat_borracha("borr_varre")
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    out = N["Material Output"]
    borr = N["Principled BSDF"]
    geo = N.new("ShaderNodeNewGeometry")
    dot = N.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = tuple(direcao)
    L.new(geo.outputs["Position"], dot.inputs[0])
    v = N.new("ShaderNodeValue"); v.name = v.label = "varre"
    sub = N.new("ShaderNodeMath"); sub.operation = "SUBTRACT"
    L.new(dot.outputs["Value"], sub.inputs[0]); L.new(v.outputs[0], sub.inputs[1])
    lt = N.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = 0.0
    L.new(sub.outputs[0], lt.inputs[0])
    # casca de raio-X
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.45
    pw = N.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 2.0
    mr = N.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 0.06; mr.inputs["To Max"].default_value = 0.45
    L.new(lw.outputs["Facing"], pw.inputs[0]); L.new(pw.outputs[0], mr.inputs["Value"])
    em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = tc.lin(tc.RAIO_X); em.inputs["Strength"].default_value = 1.2
    tr = N.new("ShaderNodeBsdfTransparent")
    rx = N.new("ShaderNodeMixShader")
    L.new(mr.outputs["Result"], rx.inputs[0]); L.new(tr.outputs[0], rx.inputs[1]); L.new(em.outputs[0], rx.inputs[2])
    mx = N.new("ShaderNodeMixShader")
    L.new(lt.outputs[0], mx.inputs[0]); L.new(borr.outputs[0], mx.inputs[1]); L.new(rx.outputs[0], mx.inputs[2])
    # faixa brilhante na linha
    ab = N.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"
    L.new(sub.outputs[0], ab.inputs[0])
    fx = N.new("ShaderNodeMapRange"); fx.inputs["From Min"].default_value = 0.0; fx.inputs["From Max"].default_value = 0.015
    fx.inputs["To Min"].default_value = 8.0; fx.inputs["To Max"].default_value = 0.0
    L.new(ab.outputs[0], fx.inputs["Value"])
    eb = N.new("ShaderNodeEmission"); eb.inputs["Color"].default_value = tc.lin(tc.CIANO)
    L.new(fx.outputs["Result"], eb.inputs["Strength"])
    ad = N.new("ShaderNodeAddShader")
    L.new(mx.outputs[0], ad.inputs[0]); L.new(eb.outputs[0], ad.inputs[1])
    L.new(ad.outputs[0], out.inputs["Surface"])
    return m, v.outputs[0]


mv, varre = mat_varredura()
tras = tc.pneu_corte("pneu", loc=(0, 0, 0), yaw=-26, pressao=1.0, seg_ang=300)
frente = tc.pneu_corte("frente", loc=(0, 0, 0), yaw=-26, pressao=1.0, seg_ang=300, metade="frente", aro=False,
                       mat_borracha_pneu=mv)
V0, V1 = -0.55, 0.55
T.key_no(varre, 0, V0)
T.key_no(varre, t0, V0)
T.key_no(varre, t1, V1)
T.linear([mv.node_tree])


@T.hud
def desenhar(h, t):
    h.cantos()
    v = varre.default_value
    if V0 < v < V1:
        x, _ = h.px(Vector((0, 0, 0.30)) + direcao * v)
        for w, a in ((40, 30), (18, 70), (6, 200)):
            h.d.line([(x, 0), (x, h.H)], fill=T.rgb(tc.CIANO) + (a,), width=max(1, int(w * h.k)))
        h.tag((x / h.k + 14, 260), "RAIO-X", tc.CIANO, 30, ancora="l")


C.renderizar(P, sys.argv)
