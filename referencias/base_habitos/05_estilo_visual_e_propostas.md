# @construindo3d: estilo visual e de edição (12 vídeos) e proposta de identidade própria

Material de trabalho, todo em `.../habitos/an_estilo/`:
- `folhas/<id>.jpg`: 1 quadro a cada 2,5 s.
- `det/`: quadros em resolução cheia, títulos de 0 a 8 s e os 4 s finais.
- `cortes.json`: detector de cortes próprio, por diferença de quadros a 30 q/s.
- `visual.json`: paleta k-means e tempo de título.
- `scripts/`: scripts de cortes, visual, áudio e SFX.

Todos os vídeos são 576x1024, 30 fps, áudio de 44,1 kHz, com duração entre 60,5 e 82,5 s.

**Correções à análise anterior (`referencias/canais/construindo3d.md`):**
1. **As views subiram.** Porta: 4,4 M (não 2,7 M). TV: 1,8 M. Coberta: 2,0 M. Panela: 922 mil. Toalha: 1,5 M. Óleo: 859 mil.
2. **"CUIDADO / com…" não é mais fixo.** Nos 2 vídeos mais novos analisados (07/11 e 08/11), o título virou **"VOCÊ FAZ ISSO?" / [hábito no infinitivo]**.
3. **O loop "último plano = quadro de abertura" foi abandonado** a partir de 02/11. O final agora é um close do rosto olhando para a câmera, com um selo "?" amarelo.
4. **O personagem mudou.** A partir de 28/10 (toalha) entra uma **personagem feminina de corpo "pino/cabaça"**, com braços de tubo articulados. Ela é a protagonista de todos os vídeos de cabelo.
5. **Ritmo.** Com o detector automático, conferido a olho na porta (18 cortes, igual à contagem manual), os planos ficaram um pouco mais curtos que os números manuais anteriores: TV 1,75 s, panela 1,43 s, coberta 1,45 s. O detector também conta trocas bruscas de luz e cor (piscadas da TV), então a diferença é de ±10–15 %.

---

## 1. Bíblia visual

### 1.1 Tipo de render e materiais
- **3D "brinquedo de vinil / argila lisa"**, não low-poly. Superfícies muito arredondadas (bevel/subdivisão), sem facetas e sem contorno (outline).
  Parece Cycles/Eevee com AO, sombras macias, profundidade de campo nos closes e bloom leve. A referência mais próxima é o estilo "Pixar-toy" de apps 3D de IA ou kits prontos de Blender.
- **A pele mudou com o tempo.**
  - 1ª geração (22–26/10): pele fosca, quase sem brilho.
  - 2ª geração (28/10 →): **pele com brilho especular de vinil/plástico** (reflexos brancos nos ombros e na cabeça) e gotinhas d'água brilhantes sobre a pele no banho.
- **Cabelo.**
  - Liso: "casca" com textura de fios em listras marrom-escuro e caramelo, franja reta.
  - Cacheado (amassar e cacho): **centenas de tubos helicoidais brilhantes**, cor chocolate #6D3F2E–#A0644A com destaque #CF8660. É o elemento mais caro e mais "uau" dos vídeos novos.
- **Tecidos e objetos:**
  - Coberta salmão com leve textura (o xadrez rosa aparece só na metáfora da cúpula).
  - Toalha amarela com "laços" (macro).
  - Frascos de plástico liso com tampa branca (condicionador amarelo, shampoo rosa).
  - Ventilador azul-turquesa com grade cromada.
- **Água e espuma:** esferas brancas opacas (espuma de shampoo, "bolhas") e gotinhas translúcidas pequenas. Nunca há simulação de fluido: são esferas e tubos animados.

### 1.2 Iluminação e fundos
- **Cenas internas:** luz de dia difusa e alta (high-key), sem sombras duras, sombra de contato suave. Paredes lavanda, que já dão o tom frio-pastel.
- **Quarto à noite:** abajur quente com bloom e um azul-lavanda geral.
- **"Palco escuro"** (a marca do canal): gradiente azul-marinho→quase preto **#0F1434 → #070A22**, com **estrelinhas brancas** minúsculas. Ele serve de fundo para:
  - todos os macros (pele, folículo, fio, cacho);
  - os "objetos-herói" (frasco sobre um disco lavanda #8C84E0 com halo de pontos vermelhos brilhantes = "o culpado");
  - todas as inserções 2D.

  Fração do vídeo no palco escuro, medida pelo topo do quadro:

| vídeo | % no palco escuro |
|---|---|
| óleo | 56 % (fundo de estúdio cinza-escuro #15212B, outro estilo) |
| porta | 30 % |
| TV | 51 % (inclui quarto escuro) |
| panela | 9 % |
| coberta | 27 % |
| ventilador | 17 % |
| toalha | 11 % |
| desodorante | 41 % |
| shampoo | 25 % |
| condicionador | 24 % |
| amassar | 34 % |
| cacho | 20 % |

### 1.3 Paleta (k-means em 1 quadro a cada 0,5 s; % de área)

| vídeo | cores dominantes |
|---|---|
| porta | #0F1434 19 %, lavanda #A7A2CF 15 %, #CCBDD6 14 %, pele/salmão #E4B29B 12 %, #C1876E, azul pijama #6C7BD8, cabeceira #824A3C |
| coberta | #0F1335 19 %, coberta #E89280 15 %, madeira #733E2A 13 %, lavanda #A09DC5 12 %, tapete #D2AC65 |
| panela | armário azul #849ADC / #5471C8 33 %, madeira #DAA76A, laranja térmico #E35D1B, azulejo #64BEC4 |
| ventilador | coberta/pele #D19074 21 % e #EAAC8F 17 %, #0F132F 12 %, cabeceira #703D2A, parede #909FCA |
| toalha | parede #7B89B6, marinho #26286B, toalha #D3A877, roupão rosa #C57991, azulejo #3E809E |
| desodorante | #15123D 23 %, parede #8DA1C8, pele #E3A685 / #D88967, azulejo #4BA7A8, toalha vermelha #DD543F |
| shampoo | parede #A4BBE3, pele #F2CAA8 / #D9A385, #0D1339, cabelo #774C36 / #503228, toalha #DD6A50 |
| condicionador | pele #E3AE87 19 %, parede #ABC7E6 18 %, pele clara #EED7C7, #111742, toalha #DA7B56 |
| amassar | parede #A4BEE4, #0F1641 + #070D33 (23 %), cabelo #4E2F27 / #7B5040, camiseta #6388EB |
| cacho | #0A1034 24 %, parede #9BB6E6, camiseta #6389EF, pele #EBBB97, cabelo #6D3F2E / #CF8660 |

**Paleta-mestra do canal:**
- Palco escuro #0F1434 / #070A22.
- Paredes azul-lavanda #A4BEE4 (banheiro) e #A7A2CF (quarto).
- Pele pêssego #E3AE87 / #EBBB97, com sombra #C27C5C.
- Azul-royal das roupas #6388EB.
- Azulejo turquesa #4BA7A8 / #64BEC4.
- Salmão-coral #E89280 / #DD543F.
- Mostarda #D2AC65.
- Marrom madeira #733E2A.

**Leitura:** frio (lavanda e marinho) + pele quente pêssego. É uma paleta de "pele sobre azul", sem verdes e sem cinzas neutros.

### 1.4 Personagens
**Geração 1 ("Boneco-bola"; porta, TV, panela, coberta, ventilador):**
- **Corpo:** cabeça esférica enorme (~40 % da altura do corpo sentado), corpo de cápsula azul (pijama), braços cápsula sem mão definida.
- **Cabelo:** "tampa" marrom #5A3A28.
- **Rosto:**
  - olhos fechados em arco preto (dormindo);
  - meia pálpebra rabugenta, com olheira rosa/vermelha e olho vermelho no ventilador;
  - "> <" (dor);
  - olhos esbugalhados com pupila pequena.
- **Detalhes do rosto:** bochechas rosa em degradê, nariz-bolinha rosado (vermelho quando "entupido"), boca pequena.
- **Versão 2D:** existe uma versão 2D chapada do mesmo personagem, em busto sobre fundo pêssego ou marinho ("dor de cabeça", "dor de barriga") e em perfil anatômico (corte do nariz e da garganta no ventilador).

**Geração 2 ("Moça-pino"; toalha, desodorante, shampoo, condicionador, amassar, cacho):**
- **Corpo:** cabeça esférica sobre um tronco em forma de garrafa/cabaça, sem pescoço marcado.
- **Braços:** tubos longos com **cotovelo e ombro em bola visíveis**, como um manequim articulado. Mão em luva de 4 dedos gordinhos (os closes de mão no cacho são enormes, em primeiro plano).
- **Proporção:** ~3 cabeças de altura no corpo inteiro, pernas finas, camiseta azul-royal com manga bufante e short marinho. No banho, está nua com toalha vermelha-coral enrolada no peito.
- **Rosto:**
  - olhos brancos com pupila preta e **cílios** (3 traços);
  - fechados em arco feliz "^ ^";
  - sobrancelhas finas que sobem (dúvida);
  - boca vermelha pequena, de sorriso ou de "u" invertido.
- **Acessórios:** brincos dourados e coque (desodorante), franja reta.
- **Uso:** a mesma personagem, com outro cabelo, aparece em todos os vídeos de cabelo. **O canal virou "de mulher"** a partir de 28/10.
- **Expressões por textura:** feliz, dúvida (olhos arregalados + "?" amarelo), dor (> <, "AI!"), triste (boca para baixo) e apaixonada/contente (olhos fechados e bochecha forte).

### 1.5 Cenários recorrentes
- **Quarto** (porta, TV, coberta, ventilador): é o mesmo set reaproveitado.
  - Parede lavanda, quadro abstrato (círculo amarelo + retângulo azul em fundo coral), cama de cabeceira marrom #824A3C.
  - Coberta salmão, piso de tábua, tapete oval mostarda, criado-mudo com relógio digital vermelho, abajur.
  - Mostrado em plano geral 3/4 "casa de bonecas" flutuando no marinho.
- **Cozinha** (panela): armários azuis, azulejo turquesa, geladeira amarela.
- **Banheiro/box** (toalha, desodorante, shampoo, condicionador): azulejo turquesa claro, piso cobalto, box de vidro com estrutura cinza, chuveiro de teto redondo, tapetinho amarelo, frascos coloridos e patinho amarelo.
- **Banheiro com pia/armário** (amassar, cacho): parede azul-clara, armário de madeira clara com espelho e lâmpada-barra, azulejo turquesa. É o set das cenas "seco, fora do box".
- **Tendência:** cada vez **menos plano geral do cômodo e mais closes do corpo**. Nos vídeos de cabelo, o "cenário" é a parede atrás da cabeça.

### 1.6 Macros e "como mostram o invisível"
Os vídeos novos priorizam este repertório:

| técnica | onde | como é |
|---|---|---|
| **Terreno de pele** | desodorante, condicionador | Plano deslocado (ruído) cor pêssego/laranja, visto rasante contra o céu marinho. Gotas d'água = semiesferas translúcidas; produto = manchas lilás escorrendo; poros entupidos = esferas brancas/amarelas; espinhas = bolinhas rosa-vermelhas; arranhões da lâmina = rasgos vermelhos |
| **Folículos** | shampoo | Pele bege com fios-cilindros espetados e anéis vermelhos na base. Sujeira = seixos marrons; espuma = bolhas; ressecado = fios finos e emaranhados |
| **Fio isolado** | toalha, shampoo | Tubo com cutícula em escamas; quebra com "CREC!/PLEC!" e lascas voando; "sem brilho" = fio com escamas abertas, de perfil |
| **Cacho helicoidal** | amassar, cacho | Hélice de vários fios (molinha) sobre o marinho. Água = bolinhas azuis grudadas; "capinha" de gel = **tubo translúcido branco em volta da hélice** que trinca em flocos; mão gigante empurrando a mola de baixo para cima com seta verde ↑ / azul ↓ |
| **Corte transversal do fio** | amassar | Disco "liso = redondo" x "cacheado = achatadinho" (fatia elíptica marrom com miolo) |
| **Objeto-herói / culpado** | condicionador, ventilador (hélice) | Frasco gigante num pedestal de disco lavanda, câmera de baixo, halo de pontos vermelhos, ⚠️ |
| **Partículas** | porta, ventilador, coberta | Pontinhos brilhantes (vento, poeira, calor) |
| **Mapa térmico** | panela | Plano com gradiente azul→laranja |
| **Anatomia 2D chapada** | ventilador, TV | Perfil de cabeça com cavidade nasal (tubo listrado), catarro verde, garganta em vermelho, músculo do pescoço |
| **Personagem-micro** | toalha, panela | Fungos e bactérias com olhinhos |
| **Lupa** | nenhum | Não há lupa nem máscara circular. O macro é sempre um **corte seco** para o palco escuro. Também não há cortes "raio-x" do corpo em 3D |

---

## 2. Sistema gráfico (texto e ícones queimados no vídeo)

### 2.1 Título de abertura

| item | valor |
|---|---|
| Palavra 1 | **"CUIDADO"** (até 04/11) → **"VOCÊ FAZ ISSO?"** (07–08/11) |
| Fonte | Sans arredondada extra-negra (Nunito Black / Baloo 2 ExtraBold / Fredoka Bold), caixa alta |
| Cor | Vermelho #E8322E com **contorno escuro grosso** (~3 px, bordô quase preto) e sombra |
| Linha 2 | "com [hábito]" / "deixando o condicionador durante o banho" / "amassar o cabelo pra formar cachos": branco, minúscula, contorno escuro fino, 1–2 linhas |
| Posição | Centralizado, topo da palavra a ~6–7 % da altura; a linha 2 termina a ~19–22 % |
| Tamanho | "CUIDADO" ocupa ~45 % da largura; "VOCÊ FAZ ISSO?" ~68 % |
| Duração (medida) | porta 2,7 s; TV 3,3; panela 3,5; coberta ~2,8; ventilador 3,8; toalha 3,7; desodorante 3,2; shampoo 3,5; **condicionador 4,6; amassar 4,3; cacho 5,8**. Sai com fusão de ~0,3 s |

**Leitura:** o título ficou mais longo e passou de "alerta" para "pergunta direta ao espectador". Combina com as legendas do post, que a partir de 06/11 trocam "Você conhece alguém que…" por "Você [faz X]?".

### 2.2 Legenda de 1 palavra
- Está presente em todos os 12. É uma palavra por vez em Title Case ("Alguém", "Lugar", "Resumindo").
- Branca, mesma fonte arredondada negra, contorno e sombra escuros, ~5 % da altura, centralizada a **~65 % da altura**.
- Sem cor de destaque. No óleo, a legenda fica no centro (50 %).

### 2.3 Chips (pílulas)
- Pílula de canto totalmente arredondado, texto branco minúsculo negrito, ~3,5 % da altura.
- Centralizada a **~17 % da altura**, logo abaixo da zona do título.
- Entra em pop (escala) e troca a cada ~2–3 s.

| cor | hex aprox. | significado (observado) | exemplos |
|---|---|---|---|
| Vermelho | #E0393E | problema, consequência, culpado | "no mesmo lugar", "tampa os poros", "costas", "o culpado", "quebram", "acaba 2x mais rápido", "torcicolo", "nariz entupido", "mexer enquanto seca" |
| Laranja | #F07A2A | processo quente/irritante | "garganta seca", "secando tudo", "quentinha", "banho quente", "úmida e quente", "resseca" |
| Mostarda | #D99A1E | substância/conceito neutro | "oleosidade", "condicionador", "ombros", "creme ou gelatina", "capinha dura", "o creme seca" |
| Azul | #3F6FE0 | fato/processo neutro | "horas e horas", "olhos", "dilui", "espuma", "a água vai tirando", "lava o rosto", "molhado = pesado", "peso da água" |
| Verde | #2EA84A | bom, solução, efeito positivo | "1ª lavada", "limpou!", "segura o cacho", "costas livres", "o certo é", "amassa de leve", "mais leve", "macio e definido" |
| Roxo | #7B57E0 | sono, tempo, "lisinho" | "sono leve", "age enquanto você dorme", "hora de dormir", "lisinha" |
| Cinza-ardósia | #3A4256 | **citação/objeção entre aspas, passos numerados e CTA** | "\"ventilador dá gripe?\"", "\"nunca tive nada!\"", "\"menos creme?\"", "1. espera secar", "manda pra quem faz isso", "depois de alguns dias" |

### 2.4 Ícones, carimbos e contadores
- **✓** círculo verde #2EB34A com check branco. **✗** círculo vermelho com X branco. **⚠️** triângulo amarelo com "!". **?** círculo amarelo #F5C518 com "?" preto.
  Todos entram em pop, ~10 % da largura, na lateral direita alta (perto da cabeça) ou no topo.
- **Selos de anel:** anel verde com "100%", "seco", "8h"; anel âmbar com "10 min" e "20 min".
- **Setas** grossas chapadas: verde ↑ (empurra para cima, bom) e azul ↓ (peso), ao lado do objeto.
- **Badges** "1x" / "2x" (círculo cinza ou balão rosa) e números de passo em círculo azul ("1 cabelo", "2" verde nas costas).
- **Carimbos de onomatopeia:** balão serrilhado (estrela) branco com texto vermelho e contorno vermelho, levemente inclinado.
  Exemplos: "COF COF!", "AI!", "CREC!", "PLEC!", "NÃO!", "BRRR!", "EI!". Variante laranja: "FRIZZ!".
  Com a palavra riscada ("~~frescura~~"), vira chip.
- **Inserções 2D chapadas** sobre o palco escuro:
  - relógios digitais vermelhos;
  - frascos 1x/2x com nível rosa;
  - escudo + barra verde "100%";
  - calendário "2";
  - cama com "zZ" e lua;
  - card-ícone arredondado azul ("vento") ou marrom ("quentinho" 🔥);
  - medidor em arco azul-verde-vermelho;
  - escada de estágios do sono;
  - termômetro;
  - lista "1 cabelo" (card escuro com número em círculo azul), que é nova nos vídeos com "Resumindo".

### 2.5 Tabela por vídeo

| vídeo (data, views) | título | personagem | macro / 2D principal | onomatopeias | outros | final |
|---|---|---|---|---|---|---|
| óleo (14/10, 859k) | — | — | sifão em corte semirrealista, contadores °C, foto real | — | chips de contador | CTA, sem loop |
| porta (22/10, 4,4M) | CUIDADO | boneco-bola | 2D quarto + relógio 22→03h + medidor; partículas | — | ⚠️✗✓, bateria 2D | loop ao quadro 0 |
| TV (22/10, 1,8M) | CUIDADO | boneco-bola | 2D cérebro, escada do sono; TV com telas 2D | — | timer 3D | mesmo enquadramento do início |
| panela (23/10, 922k) | CUIDADO | boneco-bola + vovó 2D | mapa térmico, bactérias com olhos | MULTIDÃO! | anel 20 min, x1→x2 | loop |
| coberta (25/10, 2,0M) | CUIDADO | boneco-bola (casal) | cúpula sobre cérebro, medidor em arco | EI!, BRRR! | "frescura" riscado | loop |
| ventilador (26/10, 1,6M) | CUIDADO | boneco-bola | **2D anatômico de perfil** (nariz, garganta, pescoço) | COF COF!, AI! | relógio 06:36, card "vento" | loop |
| toalha (28/10, 1,5M) | CUIDADO | **1ª moça-pino** + homem no box | fio com cutícula, fibras da toalha, fungos | PLEC!, PESA!, NÃO! | anel 10 min | loop |
| desodorante (29/10, 1,8M) | CUIDADO | moça-pino de coque | **terreno de pele** (gotas, lâmina) | AI! | escudo 100 %, cama 2D | loop |
| shampoo (02/11, 1,4M) | CUIDADO | moça-pino cabelo liso | **folículos**, fio quebrando | CREC! | frascos 1x/2x, ⚠️ | **close do rosto + "?"** |
| condicionador (04/11, 4,2M) | CUIDADO | moça-pino cabelo liso | terreno de pele + poros; **frasco-culpado em pedestal** | — | calendário "2", lista 1-2 "Resumindo" | close do rosto + "?" |
| amassar (07/11, 3,3M) | **VOCÊ FAZ ISSO?** | moça-pino cacheada | **hélice-mola**, mão gigante, corte do fio | NÃO! | setas ↑↓, passos "3." "4." | close do rosto + "?" |
| cacho (08/11, 568k) | **VOCÊ FAZ ISSO?** | moça-pino cacheada | hélice com **capinha translúcida que trinca** | CREC!, FRIZZ! | anel 100 %/seco, passos 1-2 | close do rosto + "?" |

---

## 3. Edição

### 3.1 Ritmo (detector próprio, cortes com 0,3 s ou mais entre si)

| vídeo | dur. | cortes | plano médio | mediana | maior plano | 1º corte | % quadros quase parados* |
|---|---|---|---|---|---|---|---|
| óleo | 63,7 | 12 | 4,9 s | 3,9 | 12,4 | 7,9 | 38 % |
| porta | 60,5 | 18 | 3,2 | 2,7 | 9,7 (2D) | 2,8 | 53 % |
| TV | 61,2 | 34 | 1,75 | 1,1 | 12,5 (2D) | 0,2 (luz) | 45 % |
| panela | 64,6 | 44 | 1,43 | 1,3 | 5,0 | 1,3 | 27 % |
| coberta | 68,0 | 46 | 1,45 | 1,4 | 3,9 | 1,3 | 33 % |
| ventilador | 72,0 | 42 | 1,67 | 1,6 | 3,6 | 1,1 | 31 % |
| toalha | 79,5 | 50 | 1,56 | 1,4 | 7,5 | 1,5 | 31 % |
| desodorante | 64,5 | 47 | 1,34 | 1,05 | 3,5 | 1,0 | 31 % |
| shampoo | 68,8 | **63** | **1,07** | 0,98 | 2,4 | 1,8 | 16 % |
| condicionador | 82,4 | 59 | 1,37 | 1,23 | 4,5 | 1,3 | 25 % |
| amassar | 72,2 | 48 | 1,47 | 1,5 | 2,7 | 1,6 | 19 % |
| cacho | 78,0 | 44 | 1,73 | 1,5 | 5,0 | 2,3 | 26 % |

*Diferença média entre quadros < 0,8/255. Os quadros "parados" caíram de 45–53 % para 16–26 %: há menos inserções 2D longas e mais animação em todo plano.

**Padrão atual:** um plano de 1,0–1,7 s (≈ 1 corte a cada 4–6 palavras; a fala tem 3,4–3,6 palavras/s), 1º corte em 1–2 s e nenhum plano acima de ~5 s. Os planos parados de 9–12 s do 2D sumiram.

### 3.2 Transições e câmera
- **Cortes secos** em quase tudo, sincronizados com a palavra-chave.
- **Fusões curtas** (~0,2–0,3 s) só na saída do título e em algumas entradas do palco escuro.
- Não há whip, zoom-through nem wipe. O "zoom pelo ralo" existia só no formato antigo.
- **Câmera:** sempre em deriva ou push-in lento, nos closes um leve balanço de "mão". Nos macros, travelling lateral ou subida lenta ao longo do cacho ou do fio.
  - Muitos **closes frontais de rosto** (o rosto ocupa 60–80 % do quadro) para reação.
  - Planos de **costas** (cabelo escorrendo nas costas).
  - **Mão gigante em primeiro plano** (nos vídeos de cacho).
- **Animação:** espuma brotando, gotas escorrendo em linhas brancas pelas costas, molas encolhendo, capinha trincando em flocos, espinhas aparecendo em pop.

### 3.3 Áudio
- **Música de fundo:** **é a mesma faixa nos 11 vídeos do molde novo e começa sempre em t = 0.**
  A correlação cruzada entre pares dá pico em atraso 0,00 s em todos os 4 trechos testados (10, 25, 40 e 55 s), com coeficientes de 0,1 a 0,46. Isso só acontece com a mesma trilha alinhada no início.
  O óleo (formato antigo) não correlaciona: a trilha é outra.
  A correlação cresce nos vídeos mais novos (condicionador e cacho, 0,3–0,46): **a música ficou relativamente mais alta**.
  É compatível com a faixa de biblioteca "Investigations" citada antes, aplicada por template. Não confirmei o nome pelo áudio.
- **Voz:** feminina, F0 mediano de 176–225 Hz (p10–p90: ~100–320 Hz), ritmo constante de 3,4–3,6 palavras/s em todos.
  Tem os erros típicos de TTS e transcrição ("caixinhos", "olhoso", "antidranspirante"), entonação de "contadora" animada e frases-molde idênticas ("Essa pessoa nem imagina…", "Olha só!", "E tem mais!", "Resumindo…", "Manda esse vídeo pra…", "E aí, você também…?").
  É muito provavelmente **TTS** (padrão ElevenLabs PT-BR), a mesma voz desde 22/10. No óleo o F0 é mais grave (162 Hz), o que sugere outra voz ou outra configuração.
- **Efeitos sonoros:** não há "whoosh" sistemático nos cortes. O salto de energia no instante do corte (+0 a +4 dB) é explicado pelo início da palavra.
  Deve haver SFX pontuais nas onomatopeias ("CREC!", "COF COF!") e nos pops, mas eles não são detectáveis de forma confiável por análise automática. Fica para conferir de ouvido.

---

## 4. Evolução e correlação com views

**Linha do tempo:**

| período | posts | mediana de views | posts ≥ 1 M | o que muda |
|---|---|---|---|---|
| antes de 22/10 | 20 | 87 mil | 0 | formato antigo: semirrealista, sem título, planos de 5 s |
| 22–31/10 | 30 | 265 mil | 6 | molde CUIDADO + boneco-bola + quarto; cortes caem de 3,2 s para 1,4 s; a moça-pino entra em 28/10 |
| 01–05/11 | 11 | 371 mil | 2 | **guinada para cabelo/banho**; fim do loop; close final com "?"; "Resumindo" com lista |
| 06–10/11 | 15 | 306 mil | 1 (sutiã 726k, cortar pontas 717k) | título "VOCÊ FAZ ISSO?"; legendas "Você [faz X]?"; títulos de 4–6 s; quase tudo sobre cabelo cacheado |

**O que correlaciona com mais views (amostra pequena, então são indícios):**
1. **Tema universal com "nojo/perigo escondido no próprio corpo ou quarto"** vence:
   - porta 4,4 M e condicionador 4,2 M ("espinha nas costas, o culpado está no seu banho");
   - amassar 3,3 M (um gesto que toda cacheada faz).
   
   Temas mais nichados ou "de pós-produto" ficaram abaixo de 600 mil: cacho durinho 568k, shampoo nas pontas 51k, chapinha 50k.
2. **Cabelo rende mais na média:** 706 mil (média) x 390 mil nos outros temas, desde 28/10. Mas a série cacheada saturou rápido: 08–11/11 com 40–300 mil.
3. **O ritmo não explica as views.**
   - O mais rápido (shampoo, 1,07 s) teve 1,4 M.
   - O mais lento do molde (porta, 3,2 s) teve 4,4 M.
   
   Abaixo de ~1,7 s por plano, não há ganho.
4. **Objeto "culpado" concreto e visual de "sujeira em você"** (poros entupidos, espinhas nas costas, gotas escorrendo) aparece nos dois maiores do molde novo.
5. **Duração:** sem efeito claro (< 70 s: mediana 219k; 70–74 s: 265k; ≥ 75 s: 293k). Todos passam de 60 s.
6. **Troca do título por "VOCÊ FAZ ISSO?":** só 2 vídeos analisados (3,3 M e 568k). Ainda é inconclusivo.

---

## 5. Três direções de estilo próprio

Restrições do nosso lado:
- **Motor:** `motor3d/` com Cycles otimizado (4 amostras, ~1,5–4 s por quadro em 576x1024). No benchmark de 30/10, o **EEVEE em software foi mais lento** (3,2 s por quadro com 4 amostras) que o Cycles. Ou seja, nesta máquina Eevee não é atalho.
  **Workbench** (flat ou studio, com cavidade, sombra e contorno nativos) deve ficar em fração de segundo por quadro. Isso é estimativa, não foi medido: fazer um `benchmark.py` antes.
- **Peças reaproveitáveis:**
  - `personagem()` com `rosto_expr()` (rosto por expressão);
  - cenários em corte do quarto e do banheiro: `cama`, `chuveiro`, `cortina_box`, `pia_banheiro`, `espelho`, `frascos_shampoo`, `toalha`, `turbante`, `touca`;
  - `vapor`, `particulas`, `manchas` / `aparecer_manchas`, `pop_in`, `grow`, `fill`;
  - `cameras` com cortes e tremor, `transicoes.py`, `carimbos.py` (pílulas com 3 tipos de cor), `sons.py`, `roteiro.py` (tempos pela frase do .srt).
- **Regra do projeto:** o usuário faz legenda e narração no CapCut. Chips, ícones e onomatopeias entram como **carimbos** (`carimbos.json`), então precisamos ampliar os tipos de `carimbos.py`.

O que **copiar** porque funciona:
- pergunta em 2ª pessoa no gancho;
- corte para o "mundo micro" num palco escuro;
- um "culpado" visual;
- objeções derrubadas com ✗ / ✓;
- "Resumindo" com passos;
- close final perguntando ao espectador;
- planos de 1,3–2 s;
- trilha fixa de "investigação";
- mais de 60 s.

O que **diferenciar:** material, paleta, fundo do palco, personagem e moldura do texto.

### Direção A: "Feltro e lã" (stop-motion de tecido)
- **Visual:**
  - Tudo parece feltro e lã: superfícies com micro-felpa (bump de ruído fino + sheen), costuras tracejadas nas bordas, olhos de botão.
  - Personagem fixa **"Dona Fia"**, uma boneca de pano com cabelo de lã grossa, que serve de cacho pronto: tubos com textura de fio torcido.
  - Fundo do palco micro: **tecido xadrez verde-musgo escuro #1F3B2E** (em vez do marinho estrelado).
  - Paleta quente: creme #F3E6CF, terracota #D2643C, mostarda #E0A526, verde-sálvia #8DB48E, rosa-chá #E8A7A0.
- **Prós:** identidade muito distinta do vinil azul do concorrente; casa com "cuidados de casa e de corpo" e com público feminino; o "artesanal" gera comentário.
- **Contras:**
  - felpa e sheen pedem Cycles (Workbench mata o efeito), então ~2–4 s por quadro, ~1 h por vídeo;
  - fios de lã em hélice são pesados se forem muitos;
  - o macro "científico" (poros, folículos) fica menos crível em feltro.
- **Viabilidade em bpy:** média.
  - Material = Principled com sheen + bump de Noise/Wave; costura = curva tracejada.
  - Reaproveita toda a geometria do `pecas.py`: só troca materiais em `materiais_*()`, com um "tema" global.
  - Prever cache de geometria e poucos fios por cacho (6–8 hélices por mecha).

### Direção B: "Laboratório de bolso" (vinil fosco + mascote cientista + lupa), a mais recomendada
- **Visual:**
  - Mantém o 3D liso e fofo (o que funciona), mas **fosco tipo argila**, sem o brilho de vinil, com **contorno fino escuro** (inverted hull, sai barato).
  - **Mascote fixo:** **"Gota"**, uma gotinha-cientista de óculos (ou uma lupa com olhos) que "entra" no corpo da pessoa.
  - **Transição-assinatura:** em vez de cortar para o micro, a câmera entra numa **lupa circular** (máscara redonda com aro amarelo) que abre para tela cheia. É uma moldura própria e reconhecível.
  - Palco micro: **verde-petróleo #0E3B3A com grade milimetrada clara** (papel de laboratório) no lugar do marinho estrelado.
  - Paleta: petróleo #0E3B3A, menta #7FD6B5, coral #FF6B5A, amarelo-gema #FFC928 (já é o "solução" do `carimbos.py`), creme #FFF4E0, pele #F1B98F.
  - Personagens humanos com proporção própria: cabeça oval, corpo "feijão" com mãos de 3 dedos, sem os braços de manequim do concorrente.
- **Gráficos:**
  - Gancho em **placa de laboratório** ("TESTE: você faz isso?") num cartão creme inclinado, em vez de texto vermelho com contorno.
  - Carimbos em **etiqueta de frasco** (retângulo com canto cortado) em vez de pílula, com o código de cor mantido: vermelho = problema, amarelo = solução, petróleo = tempo, cinza = objeção.
  - "Resumindo" como **receita/bula numerada**.
- **Prós:** reaproveita quase tudo (o `personagem()` é muito próximo, o banheiro e o quarto em corte já existem, partículas e vapor também). O mascote vira marca e permite séries ("A Gota investiga…"). A lupa resolve a transição para o micro de forma memorável.
- **Contras:** a lupa e o mascote exigem design cuidadoso para não parecer genérico. O contorno com inverted hull dobra a geometria (custo baixo, mas é preciso cuidar das escalas).
- **Viabilidade em bpy:** alta.
  - Cycles 4 amostras como hoje (~1,5–2,5 s por quadro em cenas fechadas).
  - Lupa = segunda câmera renderizada no mesmo quadro (compositor com máscara circular) ou feita na pós em `transicoes.py` (máscara PIL animada entre dois planos). A pós é mais barata.
  - Peças novas:
    - `terreno_pele()` (plano subdividido + displace por Noise);
    - `foliculo()` (cilindros + anel);
    - `mola_cacho()` (curva helicoidal com bevel; a capinha = cópia com alpha 0,3 que se quebra em fragmentos via `pop_out` em lote);
    - `heroi_pedestal()` (disco + halo de esferas emissivas).

### Direção C: "Diorama de papel low-poly" (o nosso estilo atual, assumido)
- **Visual:**
  - Low-poly facetado com flat shading (o que o motor já faz em "casa de bonecas"), cores chapadas sem textura e **contorno preto grosso de HQ** (Workbench outline/cavity).
  - Sombras recortadas, como dioramas de papel com camadas.
  - Palco micro: **amarelo-papel #F6D55C com meio-tom (halftone)**.
  - Paleta de quadrinho: preto #1D2333, branco, vermelho #E53935, amarelo #FFC928, azul-ciano #2BB3E6.
  - Personagem fixo de linhas simples (cabeça cubo-chanfrada, olhos de ponto).
  - Onomatopeias são naturais neste estilo (balões de HQ).
- **Prós:** o mais **rápido de renderizar** (Workbench: dá para fazer vídeos em minutos e postar 3–4 por dia como o concorrente); é o mais diferente do concorrente; é coerente com o "Você construiu" que o motor já produz.
- **Contras:**
  - perde o "fofo e tátil" que talvez explique parte da retenção do concorrente;
  - macros de pele e cabelo ficam menos sedutores em facetas;
  - o Workbench não tem DOF bonito nem bloom, e a névoa e o vapor precisam ser simulados por camadas.
- **Viabilidade em bpy:** muito alta.
  - `scene.render.engine = "BLENDER_WORKBENCH"`, shading flat, `show_object_outline`, `show_cavity`, `show_shadows`, cor por material.
  - Testar no `benchmark.py` com a cena do quarto.
  - O halftone pode ser feito na pós com PIL.

### Recomendação
**Direção B**, com dois empréstimos da C:
- contorno fino (legibilidade no celular);
- onomatopeias em balão de HQ.

Plano de implementação no motor:
1. **Tema de cores global** em `motor.py`: `TEMA = {...}` lido por `materiais_*()`.
2. **Peças macro novas** em `pecas.py`: `terreno_pele`, `foliculo`, `fio_cuticula` (tubo + escamas), `mola_cacho` + `capinha`, `heroi_pedestal`, `palco_micro` (fundo petróleo com grade).
3. **Mascote "Gota"** e uma personagem fixa feminina nova, com corpo "feijão", mãos de 3 dedos e cabelo liso, ondulado ou cacheado (curva helicoidal).
4. **`carimbos.py`:**
   - novos tipos: `objecao` (cinza, entre aspas), `passo` (número em círculo), `onomatopeia` (estrela serrilhada inclinada), `icone` (✓ ✗ ⚠ ? em pop), `titulo_gancho` (cartão de laboratório 0–4 s);
   - posições: gancho no topo (6–20 %), chips a ~17 %, longe da legenda do CapCut (~65–70 %).
5. **`transicoes.py`:** transição "lupa" (máscara circular abrindo, 0,35 s) para entrar e sair do micro. O padrão continua sendo o corte seco.
6. **Edição:**
   - planos de 1,3–2 s ancorados no .srt via `roteiro.py`;
   - final com close do personagem olhando para a câmera + "?" (sem loop);
   - trilha CC0 fixa começando em t = 0 em todos os vídeos (uma assinatura sonora nossa);
   - um "tuc" de lupa e pops nos ícones via `sons.py`.
