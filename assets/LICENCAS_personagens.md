# Licenças: personagens animados e captura de movimento

Baixados em **12/11/2026** por `scripts/baixar_personagens.sh` (rode de novo para refazer; os arquivos pesados não
vão para o git). Usados por `motor3d/animacao_pronta.py` e pelos testes em `videos/_animacao_pronta/`.

## Quaternius (CC0 1.0: domínio público, uso comercial livre, sem atribuição obrigatória)

| Pasta em `assets/personagens/` | Pacote | Origem | Licença | Situação |
|---|---|---|---|---|
| `quaternius_ual/` | Universal Animation Library [Standard] (45 animações: Walk_Loop, Idle_Loop, Idle_Talking_Loop, Fixing_Kneeling, Driving_Loop, Interact, Push_Loop, Sitting_*...; manequim UE, GLB e FBX, com e sem root motion) | https://quaternius.itch.io/universal-animation-library (página: https://quaternius.com/packs/universalanimationlibrary.html) | CC0 1.0 (`License.txt` no zip) | baixado (15 MB zip) |
| `quaternius_ual2/` | Universal Animation Library 2 [Standard] (43 animações: Idle_FoldArms_Loop, Idle_No_Loop, Yes, Idle_TalkingPhone_Loop, Consume, Walk_Carry_Loop...; + manequim feminino) | https://quaternius.itch.io/universal-animation-library-2 | CC0 1.0 (`License.txt`) | baixado (18 MB zip) |
| `quaternius_ubc/` | Universal Base Characters [Standard] (corpo-base masculino e feminino, mesmo esqueleto da UAL, cabelos, sobrancelhas, olhos) | https://quaternius.itch.io/universal-base-characters | CC0 1.0 (`License_Standard.txt`) | baixado (129 MB zip) |
| `quaternius_ultimate_animated/` | Ultimate Animated Character Pack (Worker_Male, Casual_Male...) | Google Drive da página https://quaternius.com/packs/ultimatedanimatedcharacter.html | CC0 1.0 | **não baixou**: o Drive respondeu "Quota exceeded" a todos os arquivos (até o `License.txt`); só ficou a lista `_lista.json` |
| `quaternius_modular_men/` | Ultimate Modular Men (Worker, Casual, Farmer; versão "Humanoid Rig") | Google Drive da página https://quaternius.com/packs/ultimatemodularcharacters.html | CC0 1.0 | **não baixou** (mesmo motivo) |
| `quaternius_animated_men/` | Animated Men Pack | Google Drive da página https://quaternius.com/packs/animatedmen.html | CC0 1.0 | **não baixou** (mesmo motivo) |

Os pacotes do itch são "name your own price" com mínimo 0: baixados sem pagar, como o botão "No thanks, just take me
to the downloads". As versões [Pro]/[Source] (pagas) não foram baixadas.

## CMU Graphics Lab Motion Capture Database

- **Origem:** http://mocap.cs.cmu.edu (arquivos `subjects/NN/NN.asf` e `NN_TT.amc`, baixados direto da fonte).
- **Licença (termos do site):** "This data is free for use in research projects. You may include this data in
  commercially-sold products, but you may not resell this data directly, even in converted form." Ou seja: pode usar
  em vídeo comercial; não pode vender/redistribuir os dados de movimento em si (nem convertidos).
- **Agradecimento pedido** (colocar na descrição do canal ou de um vídeo, se quiser citar): "The data used in this
  project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217."
- **Conversão:** `assets/mocap/cmu_bvh/*.bvh` foram gerados aqui por `animacao_pronta.asf_amc_para_bvh` (24 qps,
  metros, Y para cima). Os sujeitos 141 e 143 estão a **60 qps** (a página diz 120; a 120 o passo fica com cadência de
  corrida, 2,4 m/s; a 60 dá 1,29 m/s, caminhada normal).
- Não usei os espelhos do Hugging Face (ex.: `EntVista/metrixel-cmu-mocap-clean`, ~100 BVH da CMU com os mesmos
  termos): a fonte original estava acessível.

| Arquivo | Movimento (descrição da CMU) | Uso |
|---|---|---|
| `141_19`, `141_25` | Walk (sujeito 141, "General Subject Capture") | andar (teste B usa 141_25, quadros 40–110 a 24 qps) |
| `141_21` | Shrug | dar de ombros (testes A e B, quadros 24–64) |
| `141_14` | Punch and Kick | chute alto (reserva) |
| `141_16` | Wave Hello | aceno |
| `141_20` | Waiting | parado, esperando (ocioso) |
| `143_24` | Kicking (sujeito 143) | chute (testes A e B: quadros 106–136, chute de pé direito, amplitude 0,6) |
| `143_25` | Waving | aceno |
| `13_27` | direct traffic, wave, point | apontar |
| `13_29` | jumping jacks, side twists, bend over, squats | agachar / abaixar |

Não há na CMU tomada de "conversa gesticulando" com nome claro; para isso a UAL tem `Idle_Talking_Loop` e a UAL2
`Idle_TalkingPhone_Loop`, `Idle_No_Loop` e `Yes`.
