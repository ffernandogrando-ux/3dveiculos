"""Trilha de efeitos do vídeo do aterro sanitário (tempos iguais aos de cena.py).

Uso:  python efeitos.py  ->  efeitos.wav
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "motor3d"))
from sons import *

HERE = os.path.dirname(os.path.abspath(__file__))
cortes = json.load(open(os.path.join(HERE, "cortes.json")))
mx = Mix(cortes["duracao"])
put = mx.put

# transições suaves (vento) centradas nos cortes com desfoque
for c in cortes["transicoes"]:
    put(c - 0.55, whoosh(), 0.28)

# ---------------------------------------------------------------- lixão
put(0.1, engine(2.9, 0.35), 0.8, pan=0.4)
put(0.15, beeps(0.85), 0.9, pan=0.4)                     # caminhão de ré
put(0.95, scrape(0.7, 0.3), 0.6)                         # caçamba levantando
put(1.15, stones(3, 0.7), 0.9); put(1.3, rumble(0.9, 0.5), 0.7)
for i in range(5):
    put(1.4 + i * 0.16, pop(0.6 + 0.05 * i), 0.35)
put(3.1, buzz_fly(8.8), 1.0)                              # moscas
put(4.2, thunder(0.7), 0.7)
put(4.25, rain(2.9, 0.4), 1.0)
for i in range(6):
    put(5.1 + i * 0.32, pop(0.45), 0.3)                   # gotas pretas
put(6.4, drone(3.6, 55, 0.16), 1.0)                       # chorume descendo
put(9.3, ding(330, 0.22), 0.9)                            # poço contaminado
put(10.0, sad(), 0.8)
put(10.3, ding(990), 0.6)                                 # "esse caldo é o chorume"

# ---------------------------------------------------------------- impermeabilização
put(13.95, thud(0.4, metal=False), 0.6)
put(14.1, engine(1.6, 0.3, 0.7), 0.8)
put(14.2, rumble(1.4, 0.4), 0.7)
put(15.8, scrape(0.5, 0.3), 0.8); put(16.6, scrape(0.6, 0.3), 0.7); put(17.4, scrape(0.55, 0.3), 0.7)
put(18.37, ding(1320), 0.6)                               # geomembrana

# ---------------------------------------------------------------- chorume empoçado
put(19.95, rain(1.7, 0.35), 0.9)
put(20.0, stones(2, 0.6), 0.8); put(20.1, thud(0.5, metal=False), 0.6)
for i in range(5):
    put(20.6 + i * 0.35, pop(0.5), 0.25)
put(21.0, water(3.3, 0.35), 0.8)
put(22.6, drone(2.1, 49, 0.16), 1.0)
put(22.7, bubbling(2.0, 0.35), 0.9)

# ---------------------------------------------------------------- drenagem de chorume
put(24.9, clank(0.9), 0.6); put(25.3, scrape(0.7, 0.25), 0.6); put(25.7, clank(0.8), 0.6)
for i in range(6):
    put(24.95 + i * 0.13, pop(1.4), 0.2)
put(25.9, stones(3, 0.6), 0.8)
put(27.2, water(2.6, 0.45), 0.9)
put(28.6, clank(1.1), 0.4)
put(29.87, ding(1320), 0.6)                               # drenagem de chorume

# ---------------------------------------------------------------- urubus, ratos, vento
put(31.75, stones(2, 0.7), 0.9); put(31.8, thud(0.5, metal=False), 0.6)
for i in range(4):
    put(32.0 + i * 0.08, pop(1.0 + 0.1 * i), 0.3)
for i, t in enumerate((32.3, 33.1, 34.0, 34.9, 35.8, 36.7, 37.5)):
    put(t, flap(), 0.5, pan=-0.3 + 0.2 * (i % 3))
for t in (32.75, 33.55, 34.8, 35.95, 37.35):
    put(t, squeak(), 0.7, pan=0.2)
put(34.1, wind(2.4, 0.5), 0.9)
for i in range(4):
    put(34.3 + i * 0.35, crumple(0.3), 0.5, pan=0.5)

# ---------------------------------------------------------------- fim do dia: trator
put(36.55, chime((392.0, 329.6, 261.6), gap=0.18), 0.4)
put(37.9, engine(2.6, 0.4, 0.75), 0.9)
put(38.0, stones(3, 0.5), 0.7); put(38.9, stones(2, 0.45), 0.6)
put(38.2, squeak(), 0.6); put(38.35, squeak(), 0.5)
put(39.5, rumble(1.0, 0.45), 0.7)

# ---------------------------------------------------------------- camadas e célula
for t, metal in ((43.45, False), (44.0, False), (44.7, False), (45.15, False)):
    put(t, thud(0.45, metal), 0.7)
    put(t, stones(1, 0.4), 0.5)
put(45.75, ding(1320), 0.6)                               # célula

# ---------------------------------------------------------------- metano, fogo, explosão
put(46.9, drone(5.0, 46, 0.14), 1.0)
for i in range(10):
    put(48.0 + i * 0.25, pop(0.4 + 0.03 * (i % 4)), 0.25)
put(50.5, rumble(1.0, 0.45), 0.8)
put(51.55, whoosh(0.8), 0.5)
put(51.6, crackle(2.4, 0.4), 0.9)
put(52.5, thud(1.0, metal=False), 1.0)
put(52.5, rumble(1.5, 0.9), 1.0)
put(52.55, stones(3, 0.6), 0.8)

# ---------------------------------------------------------------- drenos de gás e energia
put(54.3, scrape(0.5, 0.3), 0.7)
for i in range(3):
    put(55.9 + i * 0.2, clank(0.9 - 0.05 * i), 0.6)
for i in range(3):
    put(56.75 + i * 0.12, stones(1, 0.5), 0.6)
for i in range(8):
    put(57.8 + i * 0.22, pop(0.55), 0.22)
put(59.0, whoosh(0.7), 0.4)
put(59.0, crackle(13.8, 0.12), 1.0)                       # chamas dos drenos até o fim
put(60.2, clank(1.0), 0.4)
put(60.25, pop(0.8), 0.5)
put(60.7, zap(), 0.7)
for i in range(4):
    put(60.75 + i * 0.1, pop(1.1), 0.3)
put(60.9, hum_elec(2.0), 0.9)
put(61.0, ding(1568, 0.2), 0.6)                           # luzes acendendo
put(61.8, ding(1320), 0.6)                                # drenos de gás

# ---------------------------------------------------------------- jornal de 40 anos
put(66.3, paper(0.5), 0.8)
put(66.35, rise_tone(1.2, 300, 700), 0.3)
put(67.55, paper(0.4), 0.6)

# ---------------------------------------------------------------- parabéns
for t in (70.05, 70.3, 70.45):
    put(t, pop(0.8), 0.4)
put(70.1, chime(), 0.9)

mx.save(os.path.join(HERE, "efeitos.wav"))
