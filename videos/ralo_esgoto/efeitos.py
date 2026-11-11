"""Trilha de efeitos do vídeo do ralo com cheiro de esgoto (tempos iguais aos de cena.py).

Uso:  python efeitos.py  ->  efeitos.wav
Assinatura do canal: o "raio-x" (aqui o piso caindo) é whoosh curto + estalo.
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "motor3d"))
from sons import *

HERE = os.path.dirname(os.path.abspath(__file__))
cortes = json.load(open(os.path.join(HERE, "cortes.json")))
mx = Mix(cortes["duracao"])
put = mx.put
LOOP = 75.45

for c in cortes["transicoes"]:
    put(c - 0.55, whoosh(), 0.18)


def despejo(t0, t1, vol=0.45):
    put(t0, water(t1 - t0, 0.5), vol, pan=-0.2)


def bolhas(t0, d, vol=0.3):
    put(t0, bubbling(d, 0.35), vol)


def gancho(t0, d):
    despejo(t0 + 0.15, t0 + min(d, 4.3))
    put(t0 + 0.05, buzz_fly(min(d, 3.0), 0.05), 0.35, pan=0.3)     # fedor


# ---------------------------------------------------------------- gancho
gancho(0.0, 4.4)
for i in range(4):
    put(4.75 + i * 0.09, pop(1.3 + 0.1 * i), 0.18)                  # perfume
put(4.9, ding(1760, 0.15), 0.35)                                     # "funciona"
# ---------------------------------------------------------------- raio-x: o piso cai
put(7.1, whoosh(0.7), 0.35)
put(7.3, clank(0.55), 0.35)
put(7.45, thud(0.7, metal=False), 0.7)
put(7.5, stones(2, 0.4), 0.45)
# ---------------------------------------------------------------- sifão e fecho hídrico
put(8.4, water(2.0, 0.3), 0.2)
put(12.35, ding(1320), 0.45)                                         # fecho hídrico
bolhas(14.1, 2.2, 0.28)                                              # gás batendo na água
# quando ela some
put(16.4, water(0.8, 0.5), 0.35)
bolhas(17.0, 2.0, 0.4)
put(17.4, buzz_fly(1.7, 0.06), 0.35)
put(18.2, sad(330, 220, 0.6), 0.2)
# evapora: dia e noite
for i in range(6):
    put(20.3 + i * 0.3, whoosh(0.35), 0.1)
put(22.0, rise_tone(0.5, 600, 900), 0.08)
# descarga sem respiro
put(24.4, water(1.6, 0.7), 0.55)
put(24.45, rumble(1.2, 0.4), 0.35)
put(24.8, drone(1.0, 70, 0.14), 0.3)
put(25.0, water(0.6, 0.6), 0.35, pan=-0.3)                           # sifão sendo puxado
# o desinfetante de novo
despejo(26.3, 29.2)
for i in range(4):
    put(27.2 + i * 0.09, pop(1.3 + 0.1 * i), 0.16)
put(29.35, ding(1568), 0.5)                                          # é a água
# ---------------------------------------------------------------- linha do tempo
for t in (31.13, 34.33, 37.67):
    put(t - 0.05, whoosh(0.5), 0.3)
    put(t, thud(0.5, metal=False), 0.25)
put(32.2, water(0.6, 0.3), 0.2)
bolhas(33.3, 1.0, 0.35)
put(33.4, buzz_fly(0.9, 0.06), 0.35)
put(34.5, drone(3.0, 55, 0.14), 0.3)                                 # noite
put(35.0, scrape(1.6, 0.12), 0.35)                                   # barata subindo
put(35.7, scrape(1.8, 0.12), 0.35)
for i in range(6):
    put(36.6 + i * 0.15, scrape(2.2, 0.08), 0.25)                    # passinhos no piso
for i in range(4):
    put(38.8 + 0.4 * i, clank(1.8), 0.22)                            # frasco vazio caindo
put(39.4, buzz_fly(2.0, 0.06), 0.35)
# ---------------------------------------------------------------- gás sulfídrico
put(41.9, pop(0.9), 0.4)                                             # ovo
put(41.95, crumple(0.2), 0.25)
put(44.5, drone(3.2, 60, 0.12), 0.3)
put(45.9, sad(300, 200, 0.8), 0.22)
# ---------------------------------------------------------------- desculpa 1: bactérias
for i in range(9):
    put(48.0 + 0.06 * i, pop(1.8 + 0.05 * i), 0.12)
despejo(49.0, 50.4, 0.35)
for i in range(9):
    put(49.6 + 0.08 * i, pop(2.2), 0.1)
# rua: gás subindo da rede
bolhas(50.9, 2.6, 0.45)
put(51.0, rumble(2.2, 0.3), 0.2)
# ---------------------------------------------------------------- desculpa 2: água sanitária
put(54.1, pop(1.0), 0.35)
put(56.8, zap(), 0.25)                                               # X vermelho
put(56.85, thud(0.6), 0.3)
put(57.8, whoosh(0.8), 0.3)
put(57.9, crackle(1.4, 0.2), 0.25)
for t in (58.1, 58.5, 58.9):                                         # tosse
    put(t, thud(0.35, metal=False), 0.35)
# ---------------------------------------------------------------- rebobinar e solução
for i in range(10):
    put(59.75 + i * 0.12, squeak(), 0.06)
put(60.1, chime((659.25, 783.99)), 0.3)                              # o certo
despejo(62.3, 63.4, 0.5)
put(63.4, ding(1568), 0.45)                                          # água toda semana
put(64.3, clank(1.4), 0.3)                                           # grelha sai
for t in (65.2, 65.5, 65.8, 66.1, 66.4):
    put(t, scrape(1.2, 0.2), 0.4)                                    # escova
put(66.7, pop(0.8), 0.3)
put(67.2, clank(1.5), 0.3)                                           # grelha volta
put(68.5, water(0.6, 0.4), 0.25)
put(68.9, buzz_fly(0.8, 0.06), 0.3)
put(69.75, pop(0.9), 0.4)                                            # encanador
for t in (70.2, 70.6, 71.0):
    put(t, clank(1.2), 0.3)
put(70.9, ding(1320), 0.4)                                           # sifão
put(71.6, rise_tone(0.9, 220, 660), 0.3)                             # respiro subindo
put(72.45, pop(1.2), 0.35)
put(72.5, ding(1568), 0.45)
put(73.0, water(1.4, 0.6), 0.4)                                      # descarga com respiro
put(73.6, chime(), 0.4)
# ---------------------------------------------------------------- loop
gancho(LOOP, 2.1)

mx.save(os.path.join(HERE, "efeitos.wav"))
print("efeitos.wav")
