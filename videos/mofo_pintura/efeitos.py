"""Trilha de efeitos do vídeo "pintar por cima do mofo" (tempos iguais aos de cena.py).

Uso:  python efeitos.py  ->  efeitos.wav
Assinatura do canal: o "raio-x" (parede abrindo) é sempre whoosh curto + estalo.
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "motor3d"))
from sons import *

HERE = os.path.dirname(os.path.abspath(__file__))
cortes = json.load(open(os.path.join(HERE, "cortes.json")))
mx = Mix(cortes["duracao"])
put = mx.put

for c in cortes["transicoes"]:
    put(c - 0.55, whoosh(), 0.28)


def rolo(t0, t1, passos=5):
    """Rolo de pintura: arrasto macio a cada ida e volta."""
    d = (t1 - t0) / (passos * 2)
    for i in range(passos * 2):
        put(t0 + i * d, scrape(0.9 + 0.08 * (i % 2), 0.18), 0.6, pan=-0.2)


# ---------------------------------------------------------------- gancho: pintando por cima
rolo(0.3, 2.9)
put(3.25, ding(1760, 0.15), 0.4)                          # "branquinha"
put(5.75, whoosh(0.7), 0.35)

# ---------------------------------------------------------------- raio-x: a parede abre
put(6.3, clank(0.55), 0.35)
put(6.4, thud(0.6, metal=False), 0.7)
put(6.45, stones(1, 0.35), 0.5)
for i in range(9):
    put(7.45 + i * 0.05, pop(0.7 + 0.04 * i), 0.18)       # colônias
put(7.7, squeak(), 0.12)
for i in range(14):
    put(9.2 + i * 0.04, pop(1.6 + 0.05 * (i % 3)), 0.12)  # gotinhas

# ---------------------------------------------------------------- chuva, trinca, esponja
put(11.0, thunder(0.55), 0.6)
put(11.0, rain(17.9, 0.35), 0.4)
put(14.35, sample("rachadura/sfx100v2_wood_01.ogg", peak=0.6), 0.55)
for i in range(10):
    put(15.2 + i * 0.35, pop(1.9), 0.12)
put(16.9, water(3.6, 0.3), 0.55)
put(19.5, bubbling(1.2, 0.25), 0.4)
put(21.2, ding(1320), 0.55)                               # tinta nova por cima
put(22.9, drone(2.0, 62, 0.12), 0.9)                      # molhada por baixo
put(25.3, drone(1.4, 49, 0.14), 0.9)                      # fungo vivo
for i in range(4):
    put(25.35 + i * 0.33, pop(0.5), 0.15)
put(26.95, scrape(0.4, 0.25), 0.4)                        # raízes entrando

# ---------------------------------------------------------------- linha do tempo
for t in (28.97, 32.45, 36.3):
    put(t - 0.05, whoosh(0.5), 0.3)
    put(t, clank(1.6), 0.4)                              # tic do tempo
for i in range(26):
    put(29.9 + i * 0.09, pop(2.0), 0.07)                  # pontinhos
for i in range(7):
    put(33.35 + i * 0.13, pop(0.45), 0.25)                # bolhas estufando
for i in range(7):
    put(34.6 + i * 0.22, paper(0.35), 0.35)               # lascas caindo
put(36.5, drone(2.0, 44, 0.16), 1.0)                      # 1 ano: mancha crescendo
put(36.5, bubbling(1.8, 0.2), 0.35)

# ---------------------------------------------------------------- cheiro, esporos, tosse
put(38.95, wind(2.6, 0.3), 0.45)
put(41.75, drone(4.5, 52, 0.12), 0.55)
put(41.8, wind(4.4, 0.35), 0.28)
for t in (46.45, 46.95, 47.7, 48.05):
    put(t, thud(0.3, metal=False), 0.45)
    put(t, rumble(0.25, 0.3), 0.35)

# ---------------------------------------------------------------- desculpa 1: antimofo
put(49.05, pop(0.8), 0.4)
put(49.3, clank(0.9), 0.35)
put(49.5, scrape(0.95, 0.2), 0.4); put(50.0, scrape(0.9, 0.2), 0.4)
put(50.5, ding(1568, 0.15), 0.35)
put(51.9, water(1.2, 0.25), 0.35)
for i in range(12):
    put(53.3 + i * 0.05, pop(1.8), 0.1)
put(53.45, sad(), 0.6)                                    # X: errado

# ---------------------------------------------------------------- desculpa 2: água sanitária
put(54.15, pop(0.7), 0.4)
put(54.3, water(0.9, 0.4), 0.45)
put(55.0, wind(1.3, 0.25), 0.35)                          # mancha sumindo
put(57.75, bubbling(1.2, 0.3), 0.45)                      # a água continua lá
put(57.8, drone(1.2, 62, 0.12), 0.8)

# ---------------------------------------------------------------- rebobinar
put(59.05, rise_tone(1.3, 260, 1300), 0.22)
put(59.1, wind(1.3, 0.35), 0.4)

# ---------------------------------------------------------------- o certo
put(60.4, rain(5.5, 0.32), 0.4)
put(61.5, ding(660, 0.2), 0.5)                            # achou a trinca
put(61.6, pop(1.0), 0.3)
put(63.0, scrape(0.7, 0.3), 0.55)                         # massa na trinca
put(63.5, ding(1320), 0.45)
put(64.3, scrape(0.6, 0.3), 0.5); put(64.85, scrape(0.65, 0.3), 0.5)
put(65.6, ding(1320), 0.55)                               # impermeabilizou
put(65.95, wind(0.9, 0.3), 0.4)                           # secando
put(66.4, chime((523.25, 659.25), gap=0.1), 0.25)
put(66.8, water(0.8, 0.3), 0.4)                           # balde
for i in range(10):
    put(67.25 + i * 0.3, scrape(1.05 + 0.05 * (i % 2), 0.16), 0.5)   # esponja
rolo(70.95, 71.85, passos=3)
put(71.9, ding(1320), 0.6)
put(72.3, chime(), 0.8)                                   # pronto
rolo(74.83, 77.43)                                       # loop: o começo de novo

mx.save(os.path.join(HERE, "efeitos.wav"))
