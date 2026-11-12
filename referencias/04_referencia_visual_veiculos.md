# Referência visual: veículos populares no Brasil (pesquisa de 12/11/2026, dados de 2025)

Base para os arquétipos "chibi" de `motor3d/pecas_veiculos.py`. **Arquétipos genéricos: nada de logo, grade ou farol
copiado de um modelo.** O veículo tem que parecer "o carro do vizinho", nunca "um Strada".

## Mais vendidos em 2025
**Carros e comerciais leves** (K.Lume/Fenabrave): 1 Fiat Strada (picape compacta) · 2 VW Polo (hatch) · 3 Fiat Argo
(hatch) · 4 VW T-Cross (SUV compacto) · 5 Hyundai HB20 (hatch) · 6 Chevrolet Onix (hatch) · 7 Hyundai Creta (SUV) ·
8 Fiat Mobi (hatch de entrada) · 9 VW Saveiro (picape) · 10 Jeep Compass (SUV médio).
Fontes: garagem360.com.br/ranking-dos-10-carros-mais-vendidos-do-brasil-em-2025-tem-fiat-strada-isolada-e-a-surpresa-dos-suvs/ ·
vrum.com.br/noticias/2026/01/7332772-strada-domina-vendas-2025-vw-tera-ja-supera-fiat-pulse.html

**Motos** (Fenabrave 2025, via imprensa): 1 Honda CG 160 (478 mil, o veículo mais vendido do país) · 2 Biz 125 ·
3 Pop 110i · 4 NXR 160 Bros · 5 Mottu Sport 110i (aluguel para entregador) · 6 Yamaha YBR 150. ~2,19 milhões no ano.
Fontes: garagem360.com.br/?p=300701 · motorshow.com.br/10-motos-mais-vendidas-de-2025

## Arquétipos usados (`tipo=`)
| tipo | inspira-se em | traços |
|---|---|---|
| `carro_chibi(tipo="hatch")` | Polo, Argo, HB20, Onix | 2 volumes, traseira curta quase vertical, faróis estreitos puxados para os lados, grade baixa e larga, lanternas horizontais |
| `"popular"` | Mobi | mais curto e alto, quase um cubo arredondado; bom para "o carro do cara" |
| `"suv"` | T-Cross, Creta | mais alto, moldura preta nos para-lamas e na saia, barras de teto |
| `"picape"` | Strada, Saveiro | cabine curta + caçamba com capota marítima e santo-antônio |
| `"seda"` | (figurante) | terceiro volume |
| `moto_chibi(tipo="street")` | CG 160, YBR 150 | tanque em gota, banco reto de 2 lugares, farol redondo, motor e escape aparentes, grelha atrás |
| `"cub"` | Biz, Pop, Sport 110 | quadro rebaixado aberto, escudo das pernas, farol no guidão, rodas menores, grelha |
| `"trail"` | Bros 160 | mais alta, para-lama dianteiro alto, banco longo, garfo longo |

## Cores
Frota (Senatran, 2025): branco 21,7 %, preto 18,9 %, prata 16,5 % (motorshow.com.br/branca-preta-e-prata-veja-ranking-das-cores-com-mais-carros-no-brasil).
Buscas de usados (Webmotors 2025): branco 22,2 %, preto 22,2 %, prata 18,2 %, cinza 17,8 %, azul 7,4 %.
Regra do canal: o veículo "do cara" (protagonista) em cor de destaque (vermelho, azul, laranja); os figurantes em
branco, preto, prata e cinza, como na rua. Motos: não há ranking oficial de cor (não afirmar em vídeo).

## Cara de Brasil sem marca
Placa Mercosul (Contran 780/2019): branca com faixa azul no alto; na moto, quase quadrada e só atrás. **No 3D a placa
não tem letras** (tracinhos), para nunca parecer uma placa real. Baú de motoboy com faixa refletiva, grelha,
capota marítima e santo-antônio na picape, calota de plástico, adesivo no vidro traseiro, posto "Gasolina / Etanol",
lombada amarela, borracharia com pneus empilhados.
