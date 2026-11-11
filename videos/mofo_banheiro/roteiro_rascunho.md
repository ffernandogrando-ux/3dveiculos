# Mofo no teto do banheiro limpo todo mês: roteiro

Tema 3 da `referencias/formula_mofo.md`. O vídeo responde aos comentários de quem mora em apartamento ("o meu é no
teto do banheiro", "moro no 5º andar…") **sem ser continuação**: quem nunca viu o canal entende sozinho. O conserto
errado (limpar todo mês com água sanitária) está na primeira frase. A virada é que a água vem do próprio banho, e por
isso a pessoa consegue resolver mesmo morando em prédio.

Meta: ~76 s, 225 palavras (o vídeo do mofo que viralizou tinha 230 palavras em 76 s).
O vídeo já foi montado com **tempos estimados no seu ritmo de fala** (`roteiro.srt` provisório, calibrado nas gravações
do mofo e do T: ~6,2 sílabas/s e pausas de ~0,25 s). Quando gravar, mande o .srt do CapCut. A `cena.py` procura as
frases no .srt (`motor3d/roteiro.py`), então a cena, os cortes, os carimbos e os efeitos se reajustam sozinhos às
suas pausas. Depois disso, é só renderizar de novo.

## Texto para narrar

| ~tempo | Fala |
|---|---|
| 0,2 | Você conhece alguém que limpa o mofo do teto do banheiro todo mês? |
| 4,2 | Passa água sanitária, fica branquinho. Mas olha o que tá acontecendo lá dentro. |
| 9,4 | A mancha clareou, mas o teto continua úmido. E o fungo só precisa de uma coisa pra voltar: água. |
| 15,9 | E de onde vem essa água? Do seu próprio banho. |
| 18,9 | O banho quente solta vapor. O vapor sobe, encosta no teto mais frio e vira gotinha. Igual no espelho embaçado. |
| 25,9 | Com tudo fechado, o teto fica molhado por horas. Todo santo dia. |
| 30,1 | Uma semana depois, voltam os pontinhos pretos. Um mês, a mancha volta inteira. |
| 35,2 | E de tanto molhar, a tinta estufa e descasca. |
| 38,3 | "Ah, mas meu banheiro tem exaustor." Que desliga junto com a luz. Você sai, e o vapor fica. |
| 43,5 | "Ah, mas é infiltração do vizinho de cima." Infiltração faz mancha amarelada e molha até sem banho. Pontinho preto em cima do box é vapor. |
| 52,3 | O certo é simples: tira o vapor. Liga o exaustor ou abre a janela no banho, e deixa ventilar mais vinte minutos depois. |
| 59,7 | Exaustor que desliga com a luz? Pede pra instalar um temporizador. |
| 63,7 | Só depois limpa com água sanitária diluída, de luva e máscara. Depois de seco, pinta com tinta antimofo. |
| 70,2 | Manda esse vídeo pra quem limpa o teto todo mês. |
| 72,9 | E aí, seu banheiro tem janela, exaustor ou nenhum dos dois? |

Dicas de gravação:
- Leia as desculpas ("Ah, mas meu banheiro…", "Ah, mas é infiltração…") com voz de outra pessoa, imitando.
- Faça uma pausa curta antes de "Mas olha", "E de onde vem essa água?", "Uma semana depois" e "O certo é simples":
  são os pontos onde a câmera muda.
- "Janela, exaustor ou nenhum dos dois?" é a pergunta dos comentários: cada um responde com o caso dele.
- Se quiser encurtar (~70 s), corte "Todo santo dia" e "Depois de seco, pinta com tinta antimofo".

Conferência técnica: no banheiro, a fonte de umidade mais comum é a condensação. O banho quente enche o ar de vapor,
que sobe e vira água ao encostar em superfícies mais frias que o ponto de orvalho (teto, quinas, espelho, azulejo). O
teto pintado (tinta, massa, reboco) é poroso e segura essa água por horas, sobretudo de porta e janela fechadas. A
água sanitária (hipoclorito) clareia a mancha e mata o fungo da superfície, mas não tira a umidade, e por isso o mofo
volta. Com a pintura molhando todo dia, a tinta perde aderência e estufa. Recomendação usual de ventilação: exaustor
(ou janela aberta) durante o banho e por ~20 min depois. Exaustor ligado no mesmo interruptor da luz é comum, e um
temporizador (relé de tempo, instalado por eletricista) mantém o exaustor funcionando depois que a luz apaga.
Infiltração vinda do andar de cima costuma deixar mancha amarelada ou marrom com borda, estufamento e gotejamento, e
aparece sem relação com o uso do chuveiro. O mofo de condensação aparece em pontinhos pretos espalhados, em cima do box
e nas quinas, e piora depois do banho e no frio. Limpeza: água sanitária diluída (ex.: 1 parte para 3 de água), luva,
máscara e ambiente ventilado, sem misturar com outros produtos. Pintura só com a superfície seca, com tinta com
fungicida ("antimofo").

## Carimbos (`carimbos.json`, gerado pela `cena.py` a partir das frases)
TODO MÊS · ÚMIDO · SEU BANHO · TETO FRIO · POR HORAS · 1 SEMANA DEPOIS · 1 MÊS · EXAUSTOR? · VIZINHO DE CIMA? ·
PRETO = VAPOR · O CERTO · +20 MIN · TEMPORIZADOR · LUVA + MÁSCARA · TINTA ANTIMOFO

## Plano visual

Cenário: **prédio de apartamentos em corte** (casa de bonecas). O banheiro do morador fica no meio (azulejo verde-água,
box com cortina translúcida, vaso, pia, espelho, vitrô e exaustor), com o banheiro do vizinho de cima (rosa) e o de
baixo (amarelo) visíveis e, dos lados, um quarto e uma sala. O teto é a estrela: a laje aparece em corte com as camadas
(tinta, massa, reboco, laje, contrapiso, piso do vizinho).

| Trecho | O que aparece | Câmera |
|---|---|---|
| Gancho (0–6,4) | morador sem luva nem máscara esfregando o teto preto do box com um esfregão de cabo; frasco de água sanitária e balde no chão; a mancha some e o teto brilha branco | plano médio já em movimento, aproximando |
| "lá dentro" (6,8–9,4) | **a laje se abre em corte** (a tampa voa): tinta, massa, reboco, laje com ferragem | chicote até o corte do teto (assinatura) |
| Úmido / fungo / água (9,4–15,8) | no corte, os fios verdes do fungo continuam na tinta e na massa; gotinhas ciano aparecem dentro das camadas e a faixa úmida sobe; na palavra "água", os fios pulsam e crescem | close no corte, aproximando |
| Seu banho (15,9–18,8) | o morador entra de touca, a cortina fecha e o chuveiro liga | chicote para o banheiro inteiro |
| Vapor (18,9–23,9) | nuvens de vapor sobem por cima da cortina e se espalham no teto; em "mais frio" o teto brilha azul; em "gotinha" o teto se enche de gotas | sobe junto com o vapor até o teto |
| Espelho (23,9–25,8) | o espelho embaça e junta gotinhas | close no espelho |
| Tudo fechado (25,9–29,7) | o morador sai de roupão e toalha na cabeça, fecha a porta e apaga a luz; vitrô e porta piscam em vermelho; a janela vira noite e o teto continua cheio de gotas brilhando; "todo santo dia" com dia e noite piscando | plano geral e depois olhando para o teto no escuro |
| Linha do tempo (30,1–37,9) | **mesmo enquadramento** do canto do teto: 1 semana (pontinhos pretos no canto) → 1 mês (mancha inteira de volta) → tinta estufando em bolhas e lascas caindo | câmera fixa, tranco e céu passando a cada etapa |
| Desculpa 1 (38,3–43,1) | depois do banho, o exaustor gira com vapor no teto; o morador apaga a luz, o exaustor para (pisca em vermelho), ele sai e o vapor fica; X vermelho | parede da direita: interruptor, porta e exaustor |
| Desculpa 2 (43,5–51,8) | a câmera sobe e mostra a laje e o vizinho de cima; um vazamento no piso dele desce pela laje em corte e faz uma mancha amarelada com borda, que pinga até sem banho; depois a seta amarela aponta os pontinhos pretos em cima do box e o vapor aparece | sobe até o andar de cima, depois volta para o box |
| Rebobinar (52,2–53,4) | ◀◀ em cinza | — |
| Solução (53,4–69,8) | banho de novo: o exaustor liga (destaque amarelo) e o vitrô abre, e o vapor sai por eles; "+20 MIN"; o interruptor apaga e o exaustor para; o temporizador aparece e o exaustor volta a girar com a luz apagada; morador de luva e máscara limpa a mancha, e o close mostra a luva e a máscara; com o teto seco, pinta com rolo de cabo (lata antimofo no chão) e o teto brilha amarelo | um plano por passo, cada um com destaque amarelo |
| Final (70,2–76) | banheiro seco e claro, vitrô aberto com sol, exaustor girando, morador acenando; na pergunta, vitrô e exaustor brilham | recua até mostrar o prédio inteiro em corte (5 andares) |

Peças novas no catálogo (`motor3d/pecas.py`, seção "banheiro"): vaso sanitário, pia com gabinete, espelho que embaça,
exaustor com hélice (`girar`), vitrô basculante, chuveiro, cortina de box, esfregão de teto, frasco de água sanitária,
interruptor, temporizador, porta com batente, plafon, toalha, frascos de xampu, touca e turbante para o personagem,
mancha de infiltração, vapor que sobe e se espalha no teto (`vapor`), azulejo/piso (`ladrilho_mat`); `manchas` agora
aceita teto (`normal="z"`) e gotas (`achatado`).
