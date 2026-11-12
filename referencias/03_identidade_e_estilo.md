# Identidade e estilo do canal de veículos (proposta, ainda não aprovada)

## Nome (conferir se o @ está livre no TikTok, Instagram e YouTube)
| nome | @ | por quê |
|---|---|---|
| **Raio-X do Motor** | @raioxdomotor | diz o que o canal faz (abre o veículo e mostra por dentro) e já sugere a transição-assinatura |
| **Parafuso Explica** | @parafusoexplica | o mascote vira a marca e dá tom de série ("O Parafuso explica…") |
| **Por Dentro do Motor** | @pordentrodomotor | irmão direto do "Por Dentro do Hábito" |
| **Você Faz Isso no Carro?** | @vocefazissonocarro | o gancho vira o nome; ruim para moto/jet ski |

Minha preferência: **Raio-X do Motor** (funciona para carro, moto, caminhão e jet ski, porque todos têm motor).

## Bio
> 🔧 O Parafuso mostra o que seus hábitos fazem com o seu carro (e com a sua moto).
> Manda pra quem faz isso 👇

## Plano de postagem
- **61 a 75 s** sempre. Começar com 1 por dia; subir para 2 quando o motor de render estiver rápido.
- **Horários de teste:** 12 h e 19 h (fim do expediente / volta do trabalho no trânsito) e sábado de manhã (dia de
  lavar o carro).
- **Mistura por semana:** 4 carro, 2 moto, 1 caminhão/barco/jet ski.
- **Legenda:** "Você [hábito]? [emoji] [mecanismo em 1 frase]. O certo: [solução]. Manda pra quem [hábito] 👇
  #carro #moto #mecanica #curiosidades + 2 do tema".
- **Comentário fixado:** a pergunta final + "Qual hábito de motorista você quer que eu explique?" (vira pauta).
- **Série:** um vídeo que passar de 3x a mediana ganha a versão moto/caminhão/bike nos dias seguintes.

## Estilo visual: "Oficina de bolso"
Mesmo motor 3D e o mesmo cuidado do canal de hábitos (liso, fofo, fosco tipo argila, contorno fino), com outra cor,
outro palco e outro mascote, para os dois canais não se confundirem.

- **Mascote fixo: Parafuso.** Um parafusinho de cabeça sextavada (a cabeça é o rosto), macacão azul curto, luvas
  laranja e uma **lanterna** no lugar da lupa da Gota. Aparece no gancho e no close final com "?".
- **Transição-assinatura: o "raio-X".** Uma faixa de luz laranja passa pelo veículo e, por onde ela passa, a lataria
  fica transparente e aparece o motor/pneu em corte. (O motor já faz cenas em corte desde o 3Douro: é o que ele faz
  melhor.)
- **Palco micro:** **grafite #1E2329 com piso de chapa xadrez** (a chapa antiderrapante de oficina) e um leve brilho
  laranja no horizonte, no lugar do verde-petróleo com grade.
- **Paleta:** grafite #1E2329, laranja-segurança #FF7A1A, amarelo-gema #FFC928 (solução, como no `carimbos.py`),
  azul-macacão #2F6FB3, vermelho-freio #E5484D (problema), creme #FFF4E0.
- **Veículos:** carrinhos de brinquedo arredondados (proporção "chibi": rodas grandes, cabine alta), sempre com
  rostinho nos faróis só nos planos de "sentimento" (pneu cansado, motor suando). Nos planos de corte, sem rosto.
- **Etiquetas:** em formato de **plaquinha de oficina** (retângulo com 2 parafusos nos cantos). Código de cor igual
  aos outros canais: vermelho = problema, amarelo = solução, grafite = tempo, cinza = objeção. Ícone extra **R$**
  para consequência no bolso.
- **Gancho:** "VOCÊ FAZ ISSO?" em placa de trânsito amarela (losango) de 0 a ~4 s.

## Peças novas a criar (`motor3d/pecas_veiculos.py`)
| peça | o que é | reaproveita |
|---|---|---|
| `parafuso()` | mascote | `personagem()`/`rosto_expr()` e o esquema de `gota()` |
| `carro_chibi()`, `moto_chibi()` | veículos fofos com lataria que pode ficar transparente | `carro()` de `pecas.py` como base |
| `motor_corte()` | bloco em corte: cilindro, pistão, biela, virabrequim, cárter com óleo | `particulas()`, `fill`, `grow` |
| `pneu_corte()` | pneu com a pegada deformando conforme a pressão | `disc()` + deformação simples por shape key |
| `corrente()`, `coroa()`, `pinhao()` | transmissão da moto com elos que giram | `girar()` |
| `jetski()`, `canal_agua()` | casco + caminho da água de refrigeração com cristais de sal | `particulas()`, `manchas()` |
| `palco_oficina()` | piso de chapa xadrez + fundo grafite | esquema do `palco_micro()` |
| `raio_x()` | faixa de luz que troca o material da lataria para vidro | `transicoes.py` |

Antes de renderizar o primeiro vídeo, fazer um quadro de teste do estilo (como o `videos/_estilo_b/` do repositório 3DNOVO) e mostrar ao
usuário para aprovar.

## Implementado: prévia v2 (12/11/2026, aguardando aprovação)
Ficha: `videos/_estilo/ficha_identidade.jpg` e quadro 9:16 `videos/_estilo/quadro_teste.png` (refazer com
`~/.venv-video/bin/python videos/_estilo/ficha.py`). Passou por 2 rodadas de crítico visual + revisor (notas finais: mascote 7,
veículos 6,5, paleta/luz 6,5, quadro 7; veredito "aprovar com ajustes", ajustes feitos).
- **Parafuso** (`parafuso()`): cabeça sextavada larga e chata com chanfro claro e fenda Phillips em cima, flange, pescoço
  de haste rosqueada, macacão azul com bolso laranja, luvas laranja, pernas de aço e botinas. Lanterna amarela na mão
  direita (feixe em degradê + spot real) ou guardada no cinto. Bocas: sorriso, aberta ("D" largo com dentes), "o", reta.
- **Carros** (`carro_chibi()`): `hatch`, `popular`, `suv`, `picape` (capota marítima + santo-antônio), `seda`. Olhos só
  nos faróis (nunca no para-brisa), boca na grade, humor feliz/cansado/susto. Placa Mercosul sem letras.
- **Motos** (`moto_chibi()`): `street` (tipo CG), `cub` (tipo Biz/Pop), `trail` (tipo Bros); grelha, baú laranja.
- **Cores de rua:** figurantes em branco, prata, cinza e preto (preto clareado #3A3F47 para não sumir no grafite); o
  veículo "do cara" em **laranja** (vermelho fica para "problema"; azul é do macacão). Baú nunca vermelho+amarelo (app).
- **Etiquetas:** plaquinha creme com parafuso em cada ponta; R$ é ícone (moedinha), não categoria.
- Pesquisa de referência: `referencias/04_referencia_visual_veiculos.md`.
