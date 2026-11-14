> **Leia quando** for inserir motion (gráficos, objetos, anotações, tipografia animada) sobre um clipe falado ou sobre narração, ou revisar motion já feito.
> **Divisão de trabalho:** este arquivo é o método (o que ilustrar, quando, com qual registro). A composição HTML/GSAP e o render ficam no HyperFrames (https://github.com/heygen-com/hyperframes); aqui só se descreve como **briefar** e como **revisar**, não um motor concorrente.

# Motion editorial

## 1. Regra-mãe

> **Mostrar a evidência, apontar o detalhe, concluir, nesta ordem.** O movimento acompanha o raciocínio. Nada se mexe só para "dar dinâmica".

Estilo de referência = princípios gerais de motion editorial/colagem (papel, objetos fotografados, anotação à mão, fita, carimbo), **não** a réplica de um kit visual de terceiros. A identidade (paleta, fontes, tom) vem do briefing de cada cliente.

## 2. Âncora: cada evento visual trava numa palavra

- Converta cada palavra em quadro local: `frame = (t_palavra - t_inicio_do_plano) * fps_timeline`. Use os tempos de `vedit transcribe`.
- Todo evento (entrada, carimbo, número) cai na palavra com tolerância **±3 quadros**. Fora disso vira enfeite: o espectador não liga uma coisa à outra.
- Palavras curtas se repetem ("é", "o", "de"): confira a n-ésima ocorrência no `words.json`; `at("na", 2)` errado desloca a cena inteira.
- Melhor ponto de corte para entrar/sair de uma cena = o silêncio entre palavras; entrada depois da consoante, não antes.

## 3. Quais frases merecem motion

| Entra | Não entra |
|---|---|
| tem objeto, substantivo concreto ou unidade de medida | só conceito ("transformação digital") |
| é a **instrução** ou o **payoff** do clipe | piada lateral, aparte |
| número verificável | número que o falante estima, arredonda ou corrige |
| prova mostrável (documento, tela, objeto) | grandiloquência sem objeto ("primeira vez na história") |
| | frase já ilustrada por outra cena |

- **Objeto vence palavra.** Antes de escrever uma palavra na tela, pergunte que **objeto** diria aquilo: "centenas -> milhares" em marcador estava certo no conteúdo e errado no registro; um maço de notas diz o mesmo sem uma letra.
- **Número estimado nunca em tipografia de dado limpa** (ganha autoridade que a fala não tem): use marcador manual (hachura, número à mão) ou não use. Se o falante se corrige, o número que vale é o último.
- Registre a tabela do que ficou de fora, com o motivo; evita refazer a discussão.

### 3b. B-roll por palavra-chave e cartões de prova (observado)

Em 5 de 12 referências virais (pt-BR, verticais) a imagem da janela de b-roll mostra **a coisa quando ela é nomeada**; em 2, uma montagem de inserts de 0,7-2 s abre o vídeo (3+ trocas de imagem nos 3 s iniciais). Cartões de prova (print ou estatística, ~75% da largura, centro em y ≈ 0,30-0,36, 1,5-3 s) apareceram em uma referência com ~9 cartões e como cartão de referência no gancho de outra. É prática observada, não causa comprovada de retenção, e vale a mesma triagem da seção 3: objeto concreto, número verificável, prova mostrável.

- **Cadência da janela**: 1,5-3 s por imagem (4-6 por 10 s nos trechos densos); montagem de gancho em tela cheia, 0,7-2 s. Cada troca nasce numa palavra (seção 2, ±3 quadros). Imagem de enchimento sem palavra que a peça é defeito (`armadilhas.md`).
- **Cobertura**: as referências cobriram de 40 a 100% do tempo com janela de b-roll. Isso conflita com a meta de 30-40% de motion da seção 4. Reconciliação: a meta de 30-40% vale para **motion desenhado** (cenas de objeto, anotação) que cobre o rosto; a janela de b-roll em layout `lower` **não cobre o rosto** (o apresentador continua visível embaixo) e pode passar disso. Cobertura total em tela cheia continua sendo falha por esconder o rosto.
- **Cartão de prova no `vedit`**: `overlays` com `region: "card"` (`width`, `y`); a legenda cala sob o cartão (`legendas.md`, seção 8). Base escurecida, em cinza e desfocada, número circulado, cantos arredondados e sombra do cartão: HyperFrames.

### 3c. O que o `vedit` faz e o que é do HyperFrames

| Necessidade | `vedit` (EDL `overlays`) | HyperFrames |
|---|---|---|
| imagem ou vídeo em janela de cima, tela cheia ou cartão, no tempo de saída | sim: `region` `top`/`full`/`card`, `at`, `dur`, `feather`, `zoom`, `crop_x` | |
| camada só de vídeo; áudio base intocado; sem sobreposição entre overlays | sim | |
| entradas animadas, transições (dissolve, glitch, whip), máscara atrás do sujeito, cantos arredondados, sombra, PiP com etiqueta, texto digitado | | sim |
| cena de motion desenhada (registros da seção 5), explicador animado | | sim |

## 4. Densidade e respiro

- Meta: **30-40% do clipe coberto por motion**. Abaixo de ~20% o vídeo fica parado; acima de ~50% o rosto some.
- **Pelo menos ~1,5 s de rosto entre cenas.** Trecho parado > 1,5 s dentro de uma cena: meça, não estime.
- Cena que cobre rosto, olhos ou boca = falha. Elementos persistentes (contador no canto) ficam dentro da zona segura, fora da faixa de legenda.

## 5. Varie o registro entre cenas vizinhas

Três cenas seguidas de "mesa + objeto + fita" leem como a mesma cena mesmo trocando o objeto. Alterne o **registro**:

| Registro | Quando | Herói | Anotação |
|---|---|---|---|
| Mesa de pesquisa | objeto concreto sendo nomeado | objeto fotografado de cima | fita + marcador |
| Documentário retrô | "rodando", passagem de época | aparelho antigo, tela em blocos (nunca texto/interface falsa) | nenhuma, a tela fala; use uma vez por vídeo (tempero) |
| Foto em cartão | pessoa, cena, prova de que alguém fez | cópia impressa com margem branca grossa | círculo manual |
| Dado à mão | número que o falante estima | pizza/barra em hachura de marcador | o número à mão |
| Processo | "de X para Y" | dois objetos + seta | seta longa |
| Anotação de campo | faixa, ordem de grandeza | cartão com escrita à mão | seta curta |

Regra prática: **nunca repita registro em cenas vizinhas**. Foto escura sobre footage escuro precisa de cartão com margem branca grossa (é a margem que separa).

## 6. Divisão de camadas

| Camada | Origem | Motivo |
|---|---|---|
| fundo, objetos físicos, fotografias | imagem gerada **apenas para objetos físicos** | materialidade |
| **todo texto** | renderizado por código, fonte local | grafia garantida; IA erra letras |
| **toda anotação** (círculo, seta, sublinhado, linha) | procedural (código/SVG) | precisa ser desenhável em progresso ("seta 40% desenhada") |
| sombra de contato, grão, vinheta | código | intensidade por camada |

Não gere vídeo por IA de vídeo para isto: composição por camadas dá controle exato de posição, tempo e grafia, a custo menor. Texto se **insere**, nunca se gera; sem pessoas reais, logos de terceiros, prints de sites reais nem dinheiro legível.

## 7. Geração e recorte de assets

- Um prompt por objeto; objeto isolado, de cima, luz difusa uniforme, 2-3 variantes para o herói da cena (a rejeitada costuma mostrar texto de IA que passaria se fosse a única).
- **Fundo neutro escolhido pelo maior afastamento de luminância do objeto**: objeto claro (papel) -> cinza médio (~#8A8A8A); objeto escuro (teclado, metal escuro) -> cinza claro (~#D8D8D8); chroma só como último recurso (contamina ~65% dos pixels de borda com spill, e a borda é a matéria neste estilo).
- Pedir "fundo transparente" **não funciona**: devolve RGB com fundo cinza sólido.
- No prompt, sempre: sem sombra projetada no fundo (sombra é camada), sem texto/letras/números/logo, sem glow/bloom/neon/gradiente/HDR, acabamento fosco, cores dessaturadas.
- Mostrador/relógio: peça sem números, só marcas; redesenhe os ponteiros por código. Cédula/embalagem: impressão **ilegível**; teclas: legendas desgastadas.
- Recorte em 3 passes: *flood* semeado nas bordas com tolerância escolhida num **platô de varredura**; remoção de sombra restrita à faixa onde ela mora (pixel neutro, liso, do lado certo em luminância; a regra inverte para objeto escuro); fundo encapsulado (miolo de clipe de papel). Tolerância relativa ao vizinho foi testada e reprovada (escorre por gradiente liso).
- Luz sem glow: gere a foto com a fonte como única luz e **construa** a cor por mapa de gradiente sobre a luminância; normalize por percentil 2.

## 8. Parâmetros de movimento (defaults)

| Parâmetro | Valor |
|---|---|
| Entrada | 8-18 quadros (timeline a 24 fps) |
| Overshoot | 2-4% |
| Stagger entre objetos | 2-4 quadros |
| Push de câmera | 100 -> 103-106% |
| Hold antes da saída | 8-18 quadros |
| Easing de pouso | `cubic-bezier(0.20, 0.80, 0.20, 1.00)` |
| Easing de traço | velocidade quase constante (caneta não desacelera no fim) |
| Easing de saída | aceleração (~t^2,4) |
| Texto editorial | entra em **bloco** (opacidade 0->1 + subida ~14 px, 6-10 quadros); marcador = "write" esquerda->direita; **nunca caractere a caractere** (efeito máquina de escrever) |

- **Câmera OU objeto se move, nunca os dois** na mesma cena.
- Objeto parado por segundos "morre" em cena: dê ao menos um movimento lento e contínuo.
- Verbos permitidos: pousar, deslizar, revelar, desenhar, conectar, comparar, aproximar, afastar, segurar.

## 9. Saídas

Cutaway que cobre o vídeo: entrada em corte seco com o herói **já em voo no quadro 0** (o corte é a revelação). Saída **alternando três tipos**: `slide` (a mesa é puxada para fora), `wipe` (uma folha cruza a lente) e `push` (a câmera acelera para dentro e o corte cai na velocidade); ~13 quadros (~0,43 s) com aceleração. Corte seco sozinho lê como tranco; repetir a mesma saída vira tique. **Sem flash branco, whip-pan ou glitch** (as referências virais observadas usam dissolve na abertura em 1 de 12, glitch em 1, rajada radial em 1 e whip-pan de câmera em 1; a skill mantém corte seco como padrão e o `vedit` não faz essas transições): se pedirem flash, entregue o `wipe` (mesmo clarão, mas material); se pedirem efeito de câmera, o `push`. Overlay sobre o vídeo: entra animado com trajetória e volta por onde entrou, fitas e anotações presas ao objeto.

## 10. Acabamento "feito à mão" e custo

- **Grão em "twos"** (cada campo por 2 quadros) e **borrado** (sigma ~0,9): ruído por pixel e por quadro é incompressível (120 Mbps contra ~4 Mbps do resto). Grão em tela cheia custou render ~4x mais lento (11 min contra 2,5 min para 61 s).
- **Boil** (objeto "redesenhado" a cada passo, ~9 fps, troca de semente do campo de ruído, não evolução suave): aplicado **por camada**, nunca no quadro inteiro (o fundo ondula e vira distorção de lente). Semente por elemento, estável entre quadros; elemento fisicamente único (fita + palavra) compartilha a mesma semente. Intensidade: tinta/anotação ~2x o que um objeto fotografado aguenta (objeto acima do limite "derrete"); tipografia usa ruído fino que erode a borda, não a forma. Zere o estado de boil antes da passada de legenda.
- **Aberração cromática radial**, nula no centro; deslocamento horizontal uniforme franja toda letra e lê como erro.
- Meça bitrate **por trecho** do master: assim se acha um plano explodindo.

## 11. Motion só com narração (sem footage)

- **Uma ideia visual por beat do roteiro**, com entrada exatamente na palavra-chave (a mala reabre em "voltar", o carimbo bate em "entrou").
- Metáforas **concretas**: mala, documento caindo, lista com X, contador de custo, ponte, checklist, carimbo, mapa com seta tracejada, pasta recebendo documentos, bifurcação.
- Lógica de cor: **alarme** (vermelho, vinheta leve) para o medo/problema; **solução** (verde) para a saída e o CTA. Mantenha o código no vídeo inteiro.
- Legenda queimada junto, 2-4 palavras por grupo, números sempre em algarismo.
- **Cartão final** segura >= 1,4 s depois da última palavra (muxar com `-af apad -t`).
- Se a narração gravada diferir do roteiro do briefing, **a narração manda** e a divergência é avisada. Liste os textos inventados (rótulos, títulos de cartão) para revisão no preview.
- Etapas: áudio -> palavras -> grupos de legenda à mão -> cenas ancoradas -> `hyperframes lint`/snapshot -> prancha -> preview 540x960 -> aprovação -> final 1080x1920.

## 12. Como briefar o HyperFrames

Entregue por cena: duração exata (`data-duration`), lista de eventos `(palavra, ocorrência, ação, quadro)`, registro visual, assets (PNG com alfa, SVG) e paleta; uma composição por trecho; relógio determinístico (tweens por seek, nunca `onUpdate`). Prévia a baixa taxa (`--fps 5 -q draft`) e monte a prancha; render final em segundo plano com log em arquivo. Consulte a documentação atual do projeto para flags.

## 13. Rubrica do diretor (perguntas fechadas, 5 pontos de controle)

Quem revisa **responde todas, por escrito, mesmo quando aprova**, e só escreve número que mediu.

| Ponto | Alvo | Perguntas-chave (sim/não) |
|---|---|---|
| D1 | cada asset isolado | borda física irregular? sombra embutida (bloqueia)? texto de IA (bloqueia)? brilho/glow/3D plástico (bloqueia)? recortável sem fundir? |
| D2 | quadro composto, parado | entendo em < 1 s? há uma evidência dominante? a anotação aponta algo específico? legível a 300 px de largura (renderize e olhe)? tirar um elemento pioraria? cobre rosto? invade as zonas seguras? |
| D3 | os 4 estados em sequência (START, MID, END, EXIT) | dá para narrar só olhando os quatro? cada estado tem exatamente uma novidade? `END` cai depois do último evento? há hold de 8-18 quadros? |
| D4 | sobre o vídeo, em tempo real | palavra e entrada coincidem (±3)? retorno ao rosto antes da próxima frase? sem áudio o motion ainda faz sentido? algum trecho parado > 1,5 s? |
| D5 | master | duração, cadência, contagem de quadros e **MD5 do áudio** iguais à fonte? bitrate por trecho? |

Severidades: BLOCKER, HIGH, MEDIUM, LOW. Proibido ao revisor: aprovar "porque ficou bonito", pedir redesenho geral para defeito localizado, aprovar sem a rubrica inteira.

## 14. Lista de proibições

neon, glow, bloom, HDR, gradiente decorativo, 3D plástico, dashboard "SaaS", cartão arredondado sem função, partículas de "IA", glitch como transição, impacto de câmera em toda frase, tudo centralizado, movimento constante, texto repetindo a narração, objeto flutuando sem contato, seta que não leva a nada, flash branco, whip-pan, máquina de escrever em tipografia editorial, texto gerado por IA, logos e pessoas reais de terceiros.

## 15. Handoff: do corte ao motion e de volta

> Padrão aprovado: **uma** composição HyperFrames transparente do comprimento do vídeo
> (ProRes 4444), sincronizada pela lista de palavras na timeline de saída, aplicada com
> `vedit composite` (motion por baixo, legenda por cima, SFX misturado). Roteiro de batidas,
> zonas e brief em `padrao-excelencia.md`.

O `vedit` compõe **inserts simples** (janela de b-roll, tela cheia e cartão, via `overlays` da EDL; seção 3c). Gráficos desenhados, motion editorial e legenda animada são do HyperFrames (`/hyperframes:hyperframes` e as skills dele). O fluxo:

```
vedit cut --edl X.json -o out/limpo.mp4      # vertical limpo, sem legenda
HyperFrames: overlays, legenda animada, card final (usa out/limpo.mp4 como vídeo base)
vedit master out/composto.mp4 -o out/final.mp4
vedit verify out/final.mp4 --platform reels --json
```

- Os tempos do `words.json` são da **fonte**; para o clipe final, remapeie pelos clipes da EDL (o `vedit captions` já faz isso para ASS; em HTML, faça o mesmo cálculo).
- Se a legenda será animada no HyperFrames, **não** queime também a do `vedit burn`.
- Defina um dono do áudio: o vídeo base entra mudo na composição se o áudio for mixado depois. Se o mux acontecer fora do HyperFrames, use `vedit mux --video composto.mp4 --audio mix.wav -o ...` (o áudio é ajustado à duração exata do vídeo, então o card final não é cortado) e masterize com `vedit master`.
- Verifique no arquivo final, nunca no intermediário.
- Instalado como plugin, o HyperFrames pede que a CLI dele seja chamada pelo lançador do próprio plugin: siga `/hyperframes:hyperframes-cli`.

## Fontes
- TikTok, "Creative best practices", https://ads.tiktok.com/resources/help/article/creative-best-practices?lang=en (aberta em 2026-11: elementos nativos, transições e gráficos; proposta em 3 s).
- Parâmetros de motion, registros, rubricas e custos de render: consolidação operacional própria; valores são defaults, medidos em projetos reais e a recalibrar.
