"""Trilha de efeitos do vídeo "mofo no teto do banheiro" (tempos do tempos.json, que a cena.py gera a partir do .srt).

Uso:  python cena.py (gera tempos.json)  ->  python efeitos.py  ->  efeitos.wav
Assinatura do canal: o "raio-x" (laje abrindo) é sempre whoosh curto + estalo.
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "motor3d"))
from sons import *

HERE = os.path.dirname(os.path.abspath(__file__))
cortes = json.load(open(os.path.join(HERE, "cortes.json")))
T = json.load(open(os.path.join(HERE, "tempos.json")))
mx = Mix(cortes["duracao"])
put = mx.put

for c in cortes["transicoes"]:
    put(c - 0.55, whoosh(), 0.2)


# ---------------------------------------------------------------- sons do banheiro
def chuveiro(d, lvl=0.5):
    """Água do chuveiro: chiado de jato (gravação de torneira), mais macio."""
    return loop_sample("agua/tap-water-1.wav", d, lp=5200, peak=lvl)


def ventoinha(d, lvl=0.35, parando=0.0):
    """Exaustor girando (motor em loop, abafado). parando: s finais em que o giro morre."""
    x = loop_sample("maquina_bomba/sfx100v2_loop_machine_02.ogg", d, lp=1300, pitch=1.15, peak=lvl)
    if parando:
        n = int(parando * SR)
        x[-n:] *= np.linspace(1, 0, n) ** 1.5
    return x


def interruptor(t, vol=0.5):
    put(t, clank(3.2), vol * 0.5)
    put(t + 0.01, pop(2.6), vol * 0.35)


def porta_fecha(t, vol=0.6):
    put(t, sample("impacto_madeira/sfx100v2_wood_hit_02.ogg", pitch=0.8, peak=0.6, fade=0.003), vol)


def esfrega(t0, t1, n, pitch=1.25, vol=0.55):
    """Esponja/rolo no teto: um arrasto macio por passada."""
    d = (t1 - t0) / max(1, n - 1)
    for i in range(n - 1):
        put(t0 + i * d, scrape(pitch + 0.06 * (i % 2), 0.22), vol, pan=-0.15)


def pingos(lista, vol=0.16):
    for t in lista:
        put(t, pop(0.55), vol)


def quedas(t0, t1, periodo, fase):
    """Instantes em que uma gota do mt.loop_fall chega no chão."""
    out, t = [], t0 + fase
    while t + periodo <= t1:
        out.append(t + periodo * 0.98)
        t += periodo
    return out


# ---------------------------------------------------------------- gancho: esfregando o teto com água sanitária
esfrega(T["T0a"], T["T0b"], T["n0"])
put(T["t_agua_s"] + 0.1, ding(1760, 0.12), 0.35)              # frasco de água sanitária
put(T["t_branco"] + 0.05, ding(1568, 0.18), 0.45)             # "fica branquinho"

# ---------------------------------------------------------------- raio-x: a laje abre em corte
td = T["t_dentro"]
put(td - 0.05, clank(0.55), 0.35)
put(td + 0.05, thud(0.6, metal=False), 0.65)
put(td + 0.1, stones(1, 0.35), 0.45)
for i in range(16):
    put(td + 0.45 + 0.03 * i, pop(0.75 + 0.03 * i), 0.14)      # colônias
put(T["t_clareou"], ding(1320, 0.12), 0.3)
for i in range(26):
    put(T["t_umido"] + 0.03 * i, pop(1.7 + 0.05 * (i % 3)), 0.1)   # umidade nas camadas
put(T["t_fungo"] + 0.2, drone(2.4, 52, 0.12), 0.9)            # fungo vivo
put(T["t_agua"], bubbling(1.2, 0.25), 0.4)                    # "água"
put(T["t_agua"] + 0.05, ding(990, 0.15), 0.35)

# ---------------------------------------------------------------- o banho
tb = T["t_banho"]
put(tb + 0.25, scrape(1.9, 0.3), 0.45, pan=-0.3)              # cortina correndo
put(tb + 0.55, chuveiro(T["t_fech"] - 0.15 - tb - 0.55), 0.55, pan=-0.25)
put(T["t_vapor"] - 0.3, wind(4.0, 0.3), 0.35)                 # vapor subindo
put(T["t_frio"], ding(2093, 0.1), 0.4)                        # teto frio
put(T["t_frio"] + 0.08, ding(2637, 0.08), 0.3)
for i in range(30):
    put(T["t_gota"] + 0.025 * i, pop(1.5 + 0.08 * (i % 4)), 0.08)   # gotinhas se formando
put(T["t_esp"] + 0.1, squeak(), 0.12)                         # espelho embaçado
for i in range(10):
    put(T["t_esp"] + 0.12 + 0.07 * i, pop(1.9), 0.07)

# ---------------------------------------------------------------- tudo fechado, molhado por horas, todo santo dia
tf = T["t_fech"]
put(tf + 0.05, scrape(1.9, 0.3), 0.4, pan=-0.3)               # abre a cortina
put(tf + 0.45, sad(440, 392, 0.4), 0.35)                      # vitrô e porta fechados
interruptor(T["t_horas"] + 0.1)
porta_fecha(T["t_horas"] + 0.32)
put(T["t_horas"] + 0.4, drone(2.0, 58, 0.1), 0.7)
pingos([t for i in range(4) for t in quedas(T["t_horas"] + 0.3 + 0.2 * i, T["t_sem"] - 0.02, 0.9 + 0.15 * i, 0.3 * i)])
for i in range(6):                                            # dia/noite e luz piscando
    interruptor(T["t_santo"] + 0.13 * i, 0.3)
put(T["t_santo"], chuveiro(0.8, 0.4), 0.3, pan=-0.25)

# ---------------------------------------------------------------- linha do tempo
for t in (T["t_sem"], T["t_mes"]):
    put(t - 0.05, whoosh(0.5), 0.3)
    put(t, clank(1.6), 0.4)                                   # tic do tempo
for i in range(34):
    put(T["t_pont"] + 0.035 * i, pop(2.1), 0.06)              # pontinhos pretos
put(T["t_inteira"], drone(1.8, 46, 0.15), 1.0)                # a mancha volta inteira
put(T["t_inteira"], bubbling(1.6, 0.2), 0.3)
put(T["t_molhar"], water(1.0, 0.3), 0.3)
for i in range(9):
    put(T["t_estufa"] + 0.07 * i, pop(0.45), 0.22)            # bolhas estufando
for i in range(9):
    put(T["t_desc"] + 0.06 * i, paper(0.3), 0.3)              # lascas caindo
    put(T["t_desc"] + 0.06 * i + 0.8, pop(0.4), 0.08)         # caem no chão

# ---------------------------------------------------------------- desculpa 1: exaustor que desliga com a luz
te, tl = T["t_exa"], T["t_luz"]
put(te - 0.1, ventoinha(tl + 1.1 - te + 0.1, parando=0.8), 0.5, pan=0.3)
interruptor(tl + 0.3)
put(tl + 0.4, sad(392, 262, 0.8), 0.35)                       # o exaustor para
put(T["t_sai"] + 0.05, scrape(0.7, 0.2), 0.3, pan=0.4)        # abre a porta
porta_fecha(T["t_sai"] + 1.0)
put(T["t_sai"] + 0.75, sad(), 0.6)                            # X: errado
put(T["t_sai"] + 0.75, pop(0.8), 0.25)

# ---------------------------------------------------------------- desculpa 2: vizinho de cima
tv = T["t_viz"]
put(tv - 0.1, whoosh(0.7), 0.3)
put(tv + 0.6, water(1.0, 0.25), 0.3)                          # poça no piso do vizinho
put(T["t_amar"] - 0.4, water(3.4, 0.25), 0.28)                # água descendo pela laje
put(T["t_amar"] + 0.5, drone(1.6, 49, 0.1), 0.7)
put(T["t_amar"] + 1.0, ding(784, 0.15), 0.35)                 # mancha amarelada
pingos([t for i in range(3) for t in quedas(T["t_semb"] + 0.1 * i, T["REW0"] - 0.05, 0.85, 0.25 * i)], vol=0.2)
put(T["t_preto"] + 0.25, ding(1320), 0.5)                     # seta nos pontinhos
put(T["t_preto"] + 0.27, pop(1.0), 0.3)
put(T["t_evap"] - 0.1, wind(0.9, 0.3), 0.35)                  # "é vapor"

# ---------------------------------------------------------------- rebobinar
put(T["REW0"] - 0.05, rise_tone(T["REW1"] - T["REW0"] + 0.1, 260, 1300), 0.22)
put(T["REW0"], wind(T["REW1"] - T["REW0"], 0.35), 0.4)

# ---------------------------------------------------------------- o certo
r1, t20 = T["REW1"], T["t_20"]
put(r1, chuveiro(t20 + 0.15 - r1), 0.5, pan=-0.25)
put(r1 + 0.2, wind(2.5, 0.25), 0.3)
put(T["t_exa2"] - 0.05, ventoinha(T["t_q"] + 0.9 - T["t_exa2"], parando=0.5), 0.55, pan=0.3)
interruptor(T["t_exa2"] - 0.1, 0.4)
put(T["t_exa2"] + 0.05, ding(1320), 0.5)                      # exaustor ligado
put(T["t_jan"] + 0.05, squeak(), 0.15)                        # vitrô abrindo
put(T["t_jan"] + 0.1, ding(1568), 0.5)
put(T["t_jan"] + 0.45, wind(1.6, 0.3), 0.3)                   # vapor saindo
put(t20 + 0.2, scrape(1.9, 0.3), 0.4, pan=-0.3)               # cortina
for i in range(12):
    put(t20 + 0.35 + 0.15 * i, clank(2.8), 0.12)              # +20 minutos (relógio)
put(t20 + 0.95, scrape(0.7, 0.2), 0.25, pan=0.4)              # porta
porta_fecha(t20 + 2.05, 0.45)
# exaustor que desliga com a luz -> temporizador
interruptor(T["t_q"] + 0.35)
put(T["t_q"] + 0.45, sad(392, 294, 0.6), 0.3)
put(T["t_tmp"] + 0.1, pop(0.9), 0.4)                          # temporizador aparece
put(T["t_tmp"] + 0.3, ding(1320), 0.55)
for i in range(10):
    put(T["t_tmp"] + 0.5 + 0.14 * i, clank(3.0), 0.1)         # tique-taque do temporizador
put(T["t_tmp"] + 0.45, ventoinha(cortes["duracao"] - T["t_tmp"] - 0.45, lvl=0.3), 0.4, pan=0.3)
# limpa de luva e máscara
put(T["t_limpa"], water(0.7, 0.3), 0.35)                      # balde
esfrega(T["T3a"], T["T3b"], T["n3"])
put(T["t_luva"] + 0.2, ding(1568), 0.45)
put(T["t_luva"] + 0.55, ding(1760), 0.4)
# pinta com tinta antimofo
put(T["t_pinta"], pop(0.8), 0.3)                              # lata
esfrega(T["T3c"], T["T3d"], T["n3r"], pitch=0.9, vol=0.5)
put(T["T3d"] + 0.05, ding(1320), 0.55)
# final: banheiro seco, recua até o prédio
put(T["t_manda"], chime(), 0.75)
put(T["t_manda"] + 0.6, wind(3.5, 0.3), 0.25)
put(T["t_pjan"], ding(1568, 0.15), 0.35)
put(T["t_pexa"], ding(1760, 0.15), 0.35)

mx.save(os.path.join(HERE, "efeitos.wav"))
