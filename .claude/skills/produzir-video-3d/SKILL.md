---
name: produzir-video-3d
description: Produz vídeo explicativo 3D vertical (9:16, estilo low-poly "Você construiu") a partir de um roteiro .srt — monta a cena em corte no Blender (bpy) com o motor3d, renderiza na CPU, gera efeitos sonoros CC0 sincronizados e entrega MP4 + WAV. Use sempre que o usuário enviar um roteiro/.srt ou pedir um novo vídeo desse formato.
---

# Produção de vídeo 3D explicativo

O usuário manda o roteiro com tempos (.srt) e quer o vídeo pronto, sem precisar aprovar etapas.
**Se ele mandar só o tema:** escreva `videos/<tema>/roteiro_rascunho.md` no formato do canal (texto para narrar com
~230 palavras, dicas de gravação, conferência técnica com fontes e plano visual) e **mande o texto para ele gravar
na hora** (ele devolve o .srt do CapCut). Enquanto espera, adiante as peças novas e o cenário (`cenario.py` com
`montar()`, sem tempos) e mande uma prancha de quadros de teste. Modelo: `videos/ralo_esgoto/`.
Ele faz narração e legenda no CapCut — **não coloque legenda nem título formal no vídeo**. Entram só
carimbos curtos nos momentos-chave (`<tema>/carimbos.json`, aplicados na montagem final pelo `transicoes.py`):
um a cada ~5 s no máximo, 1–3 palavras, tipos "tempo" / "problema" / "solucao" (cores do canal).

## Entregável (UM arquivo só, via SendUserFile)
O usuário pediu (31/10/2026): mande **só o vídeo final com efeitos** — com os carimbos, se houver
(`<tema>_texto_9x16_com_efeitos.mp4`; sem carimbos, `<tema>_9x16_com_efeitos.mp4`). Vários arquivos confundem.
576×1024, 24 fps, duração do roteiro (+0,1 s). Os outros (só imagem, sem texto, `efeitos.wav`) continuam sendo gerados
pelo `transicoes.py`, mas só são enviados se ele pedir. Prévias parciais durante o render podem ir (também 1 arquivo).

## Passo a passo
0. **Ambiente:** `bash scripts/instalar.sh` (idempotente, 1–3 min na 1ª vez). Use `PY=~/.venv-video/bin/python`.
   Rascunhos e quadros vão no scratchpad; o projeto fica em `videos/<tema>/`.
1. **Plano visual:** leia o .srt e escreva para o usuário uma tabela curta *tempo → narração → o que aparece*.
   Não espere aprovação (só pergunte se o roteiro for ambíguo). Regras do plano:
   - estrutura problema → solução: mostre o problema acontecendo (efeito visível), depois "reset" e a solução sendo construída;
   - toda frase tem uma mudança visual que começa até ~0,3 s depois da palavra-chave; nada parado mais de ~2 s;
   - "essa é a/o X" (termo técnico) → destaque com brilho amarelo pulsando no elemento (`glow`), não texto;
   - "parabéns, você construiu…" → plano geral com tudo pronto e câmera se afastando;
   - locações diferentes (ex.: lixão × aterro) = "ilhas" separadas em x (ex.: x = −100), trocadas com transição whip.
2. **Cena:** crie `videos/<tema>/cena.py` (modelo mais completo: `videos/aterro_sanitario/cena.py`), copie o .srt para
   `roteiro.srt`. Use `motor.py` + `pecas.py`; peça genérica nova → crie em `pecas.py` (não no cena.py).
   `$PY cena.py` gera `<tema>.blend` e `cortes.json` (tempos das transições whip).
3. **Quadros de teste:** 25–30 tempos cobrindo todas as cenas, 8 amostras:
   `$PY motor3d/render.py stills videos/<tema>/<tema>.blend <scratch>/stills 8 t1 t2 …`
   Monte uma grade (`ffmpeg -pattern_type glob -i 't*.png' -vf "scale=240:-1,tile=8x4"`), **olhe a imagem** e passe o
   checklist abaixo. Corrija e renderize de novo só os tempos alterados. Mande a grade ao usuário se ajudar.
4. **Render final** em segundo plano (`run_in_background`, timeout máximo):
   `$PY motor3d/render.py range <blend> <scratch>/quadros 4 1 <último_quadro>` (~40 min para 70 s; retomável —
   pula quadros prontos). Para ganhar ~5%, duas metades em paralelo (cada uma é uma tarefa separada).
   Uma tarefa em segundo plano morre com 2 h: nunca planeje uma tarefa única maior que isso.
5. **Enquanto renderiza:** escreva `videos/<tema>/efeitos.py` (modelo: aterro) com `motor3d/sons.py` →
   `efeitos.wav`; meça o volume por trecho (transições ≈ −38 dB, ações −20 a −30 dB, clímax ≈ −12 dB).
   Mande uma prévia parcial com os quadros já prontos (o usuário quer acompanhar).
6. **Final:** `$PY motor3d/transicoes.py <quadros> videos/<tema>/cortes.json <saida> <tema> videos/<tema>/efeitos.wav`
   e, com carimbos, de novo com nome `<tema>_texto` e `videos/<tema>/carimbos.json` como 6º argumento.
   Extraia uma grade de quadros do MP4 final (inclusive em volta de cada transição), confira e entregue os três arquivos.
7. **Guardar:** commit de `videos/<tema>/` (scripts, roteiro, cortes.json — sem .blend, quadros, wav ou mp4) e das peças
   novas em `pecas.py`; rode `$PY motor3d/catalogo.py` se adicionou peças; push.

## Padrão visual
- Low-poly com cores chapadas; terreno em corte (`terrain` + camadas `LAYERS`), face do corte em y = 0, câmera em y negativo.
- Câmera lente 35 mm vertical: largura visível ≈ 0,59 × distância; altura ≈ 1,03 × distância.
- Paleta base: grama `#6cc24a`; solos `#c8945c` `#a87447` `#8a5d3b`; água subterrânea `#86b4d8`; rocha `#6e6c75`;
  destaque amarelo `#ffc928`; forças/peso em setas vermelhas `#e53935`; contaminação em marrom-escuro/verde tóxico.
- Objetos aparecem com `pop_in`, crescem com `grow`/`fill` (camadas que enchem acompanhando paredes inclinadas usam
  `prism_fill`), somem com `pop_out`/`hide_from`. Clima/tempo com `Sky` (`day_night`, `sunset`, `state`).
- Rebobinar (`"rebobinar"` no `cortes.json`, feito pelo `transicoes.py`): trecho em P&B voltando no tempo antes de
  "o certo é…"; os quadros desse intervalo não precisam ser renderizados.
- Peças de casa por dentro em `pecas.py` (`materiais_casa`, `rolo_pintura`, `lata_tinta`, `balde`, `xis`, `cama`,
  `rosto`/`expressao`, `manchas`, `particulas`, `chuva`). Modelo de quarto em corte: `videos/mofo_pintura/cena.py`.
- Banheiro e prédio em corte: `materiais_banheiro`, `vaso_sanitario`, `pia_banheiro`, `espelho` + `embacar`, `exaustor` +
  `girar`, `vitro`, `chuveiro`, `cortina_box`, `esfregao`, `porta`, `interruptor`, `temporizador`, `vapor` (sobe e se
  espalha no teto, sai pelo exaustor/janela), `mancha_agua`, `toalha_ombro`/`turbante`/`touca`, `ladrilho_mat`.
  Modelo: `videos/mofo_banheiro/cena.py` (prédio de 5 andares, teto em camadas, vizinho de cima).
- Banheiro e esgoto do vídeo do ralo em `pecas_esgoto.py` (`import pecas_esgoto as pc`; mesmos nomes do banheiro acima, com outros parâmetros): `vaso_sanitario` (inteiro ou cortado ao meio, com sifão e
  água), `cano_corte` (PVC cortado ao meio por uma polilinha, com curvas, `aberturas` e `pontas` para junções),
  `caminho_sifao`, `agua_cano` + `nivel_agua`/`nivel` (água que esvazia e enche), `bolhas_cano`, `furo_cano` (furo no
  terreno e em `bloco_corte`), `ralo_grelha`, `chuveiro`, `pia_banheiro`, `espelho`, `box_vidro`, `toalha`, `frasco`,
  `jarra`, `escova`, `bolo_cabelo`, `barata` (+ `andar_barata`, `seguir_caminho`), `ovo_podre`, `fedor`, `nuvem`,
  `bacterias`, `caixa_inspecao`, `rede_esgoto`, `terminal_ventilacao`, `ladrilho_mat`. Qualquer peça pode ser
  cortada ao meio para o raio-x com `cortar_y`. Modelo de banheiro térreo em corte com o encanamento até a rua:
  `videos/ralo_esgoto/cenario.py`.
- Transição whip (`cortes.json`) só em troca de locação ou "reset" depois de um problema; o resto é corte seco ou
  movimento de câmera. Tremor de câmera em impactos (`cameras(..., shakes=[...])`).
- Render: `motor.setup()` já vem otimizado (Cycles, 4 amostras + OpenImageDenoise, dados persistentes). Só suba para 8 se
  os quadros de teste mostrarem manchas (muito vidro, brilho ou noite). EEVEE sem GPU é mais lento — não use.

## Sons (motor3d/sons.py + biblioteca CC0 em biblioteca_sons/)
- Transições: `whoosh()` (vento gravado, suave) a ~0,28 de volume, centrado no corte. Nada de chiado sintético.
- Use som gravado do contexto: `stones`, `rumble`, `thunder`, `engine` (+ `beeps` de ré), `drill`, `water`, `bubbling`,
  `clank`, `thud`, `scrape`, `crumple` (sacola), `paper`, `wind`. Sintéticos só para interface: `ding` (destaques),
  `chime` (parabéns), `pop` (aparecer), `squeak`, `zap`, `crackle` (fogo), `drone` (tensão), `buzz_fly`.
- Som novo: baixe só CC0 (OpenGameArt funciona daqui; freesound/kenney são bloqueados), coloque na pasta da categoria e
  registre em `biblioteca_sons/CREDITOS.md`. Você não ouve: escolha medindo duração, volume e brilho (centroide).

## Armadilhas já resolvidas (não repetir)
- `import bpy` antes de `import bmesh`.
- Objeto com escala 0 só em z vira "folha" visível (linhas pretas no corte): use `grow`/`hide_until`, que zeram a escala inteira.
- Camada escavada encolhida para altura 0 vira tampa que escurece o buraco: esconda por completo (`grow(..., to=0)` já faz).
- Face de objeto coincidindo com a face do corte (y = 0) pisca/escurece: desloque alguns centímetros (y = −0,03 a −0,15).
- Nó Mix do Blender tem várias entradas "A"/"B": use `sock(node.inputs, nome, tipo)`.
- `prism_fill`: a base do polígono precisa ter vértices exatamente em `zb`; formas com relação entre si (ex.: lixo
  compactado) usam `add_relative_key` com a mesma ordem de vértices.
- Câmeras: cada plano é uma câmera própria (marcador); `render.py` escolhe a câmera ativa por quadro.
- Tarefa em segundo plano encerrada pelo limite de 2 h não pode ser reiniciada sem pedir ao usuário — divida antes.
- Ao matar processos, não use `pgrep -f` com um padrão que também aparece no próprio comando (mata o seu shell).
- Render lento (> 3 s/quadro): meça antes de culpar a cena — o denoise em qualidade máxima custava 3 s/quadro;
  `setup()` agora usa `denoising_quality = "FAST"` (diferença invisível). Dois renders em paralelo na mesma
  máquina de 4 núcleos ficam MAIS lentos que um só.
- Material que sai PRETO em parte do render final (mas certo num quadro de teste) é falha dos dados persistentes
  numa sequência longa: depois do render, varra os quadros procurando áreas pretas e refaça só esses com
  `SEM_PERSISTENTE=1 $PY motor3d/render.py range ...` (apague os quadros ruins antes).
- Parede com 50 cm: o vão da janela fica preto visto de lado — revista o vão com material claro levemente emissivo.
- Objeto "escondido" movendo para baixo do chão aparece na frente do corte (o terreno só existe em y ≥ 0): esconda
  com `hide_at` depois do movimento.
- Prévias: `ffmpeg -framerate 24 -start_number 1 -i %04d.png` para no primeiro quadro faltando — serve para prévias parciais.
- Céu com cor animada (`Sky.state`, dia/noite) + amostragem de importância do mundo: o mapa do céu é refeito a cada
  quadro (+2 s/quadro). Ponha `world.cycles.sampling_method = "NONE"` e `emission_sampling = "NONE"` nos materiais que
  só brilham (gotas, vapor, destaques); a luz vem das lâmpadas. Meça trocando de quadro (o 2º render do MESMO quadro
  engana) e com `render_stats` para ver a etapa lenta.
- Parede com janela no meio (furo interno) feita com shapely: `ring()` usa só o contorno externo e o furo some (o vidro
  fica escondido). Corte em faixas verticais, como `parede_furada` em `videos/mofo_banheiro/cena.py`.
- Piso acabado com a face de cima no mesmo plano do topo da laje sai PRETO: a laje termina abaixo do piso.
- Luz pontual a poucos cm do teto estoura o teto (mancha branca): no plafon use luz de área virada para baixo e uma
  luz de área fraca virada para cima para o teto.
- Roteiro escrito por nós antes da gravação: monte a cena com os tempos pela FRASE (`motor3d/roteiro.py`,
  `R.t("um mês")`), com um .srt provisório no ritmo do usuário (~6,2 sílabas/s, pausas de ~0,25 s). Quando chegar a
  gravação, troque o .srt e rode `cena.py` e `efeitos.py` de novo (cortes, carimbos e efeitos se reajustam).
  Frase repetida no texto ("exaustor", "água"): use `depois=` para pegar a ocorrência certa.
- Faces de corte de peças DIFERENTES sobrepostas no mesmo plano saem PRETAS no Cycles (não é só piscar): partes de
  uma peça cortada (`cortar_y` já corta cada parte `passo` atrás da anterior), canos em corte que se encaixam (use y
  diferentes: YC, YC − 0,001, YC − 0,002…) e blocos encostados de frente (meio-fio × calçada, parede × fundo de caixa).
- Água com nível animado (`nivel_agua`) é um booleano: não esconda a peça dona dela com escala 0 — guarde longe
  (ex.: z = −100) e traga com `jump` na posição.
- Junção de canos em corte: abra o cano que recebe (`aberturas`) e faça o que chega entrar até o meio dele, sem borda
  na ponta (`pontas`); senão aparece uma linha branca ou um vão escuro na emenda.

## Checklist dos quadros de teste (antes do render final)
- [ ] Cada frase do roteiro tem sua ação visual, no tempo certo.
- [ ] Nada de linha preta, tampa, objeto atravessando onde não deveria ou flutuando sem motivo.
- [ ] Contraste: peças importantes se destacam do fundo (ex.: cano claro sobre brita escura).
- [ ] Enquadramento 9:16: a ação principal ocupa o centro e não é cortada; objetos pequenos (animais, sacolas) legíveis.
- [ ] Final com plano geral bonito e completo (sem lixo/obra exposta se o roteiro diz que ficou pronto).
- [ ] Variedade: composição, câmera e cores diferentes do vídeo anterior, mesmo usando as mesmas peças.

## Reutilização consciente
- **Sempre reutilizar:** motor (render, terreno, animações, câmera), catálogo de peças, biblioteca de sons, scripts de
  render/transição/som, padrões e checklist.
- **Sempre adaptar:** composição, roteiro de câmera, cores e arranjo das peças, ritmo.
- **Nunca:** copiar uma cena inteira de outro vídeo, repetir a mesma coreografia de câmera, baixar a qualidade do render
  para ganhar tempo, usar som sintético cru onde existe gravação adequada.

## Comunicação
Português, direto. Ao começar, dê o plano e o tempo estimado (≈ 20–30 min de montagem + ≈ 40 min de render para 70 s).
Durante o render, mande prévias parciais. O usuário não tem placa de vídeo: todo render é na nuvem, na CPU.
