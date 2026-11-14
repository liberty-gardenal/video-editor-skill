> **Leia quando** for gerar, corrigir, posicionar ou queimar legendas em vídeo vertical, ou revisar a legibilidade de texto na tela.
> **Comandos:** `vedit transcribe`, `vedit captions` (`--style viral|limpo`, `--max-words`, `--y` padrão 0.62, `--srt`, `--highlight`, `--accent`, `--mode bloco|palavra|karaoke`, `--case upper|lower|sentence|keep`, `--emphasis`, `--headline*`, `--keep-under-cards`), `vedit burn`, `vedit sheet --guides` (formato em `formatos.md`).
> **Limite:** o `vedit` gera legenda estática (bloco, palavra ou karaoke com palavra acesa). Texto animado ou digitado, easing, pílulas, cor por falante e legenda bilíngue são do HyperFrames.

# Legendas

## 1. Premissa

Legenda é parte do conteúdo: ajuda quem está sem som e, segundo a literatura (Gernsbacher, 2015), melhora compreensão e atenção em vários públicos; mal segmentada ou excessiva, aumenta carga. Objetivo: **sincronizar texto, voz e imagem**, não ocupar a tela. O vídeo funciona sem som, mas não é desenhado como se áudio não importasse.

## 2. Gerar a partir de tempos por palavra, depois dos cortes

- Fonte: `words.json` do `vedit transcribe`; `vedit captions --edl` remapeia os tempos para o clipe final. Legenda é sempre gerada **depois** dos cortes e em tempo de saída: `t_saida = t_palavra - inicio_do_segmento + offset_do_segmento`.
- Início da legenda = início da palavra segundo o `words.json`, **sem deslocamento automático** (o `vedit captions` não soma ms). O `vedit transcribe` já refina o início das palavras por energia, porque o ASR adianta o início; se um caso específico ainda parecer adiantado, corrija o `words.json` ou o `.ass` à mão e registre.
- Legenda é a **última camada** do render, depois de qualquer overlay (`vedit burn` roda depois do `cut` e antes do `mux`/`master`).

## 3. Segmentação

| Regra | Default | Motivo |
|---|---|---|
| Palavras por bloco | 2-4 em estilo viral (`--max-words 3`); 2-6 em estilo limpo | leitura em 1 olhada |
| Linhas | até 2 (1 na maioria) | menos varredura |
| Quebrar por | pontuação, unidade sintática, mudança de trecho; **não** por pausa do ASR | pausas do ASR geram blocos de uma palavra ("E", "o", "que") |
| Não separar | artigo do substantivo, preposição do complemento, nome próprio, auxiliar do verbo | quebra a leitura (Netflix pt-BR) |
| Número + símbolo | juntos ("100" + "%") | símbolo sozinho lê como erro |
| Duração do bloco | mínimo ~0,55 s; alvo 0,8-2,2 s (viral: pode cair a ~0,3-0,5 s com cadência alta) | abaixo disso não dá tempo de ler |
| Bloco de 1 palavra | só se carrega sentido ou ênfase intencional; fundir conjunção solta com o seguinte | |
| Sobreposição | **nunca**: trunque o fim de um bloco no início do próximo | com sobreposição o render escolhe o primeiro que casa e o seguinte entra atrasado |
| Atravessar corte | **nunca**: bloco que junta fim de uma frase e começo de outra lê como erro | |

Referências de legibilidade (adaptar, não copiar): o guia de legendas pt-BR da Netflix usa 42 caracteres por linha, no máximo 2 linhas, **17 caracteres/s** (adulto; 13 infantil), duração mínima de 5/6 s e máxima de 7 s por evento, quebra após pontuação e antes de conjunção/preposição. Em vídeo curto de fala rápida, o limite de tela é diferente: o TikTok recomenda **5-10 palavras por segundo** de texto na tela (guia de criativo de anúncios). Use o intervalo largo como teto e priorize sintaxe: se `chars/duração > ~20 cps` num bloco, divida ou encurte. Defaults operacionais, não leis.

## 4. O que pode e o que não pode ser corrigido

| Pode | Não pode |
|---|---|
| pontuação, maiúsculas | reescrever a fala para soar melhor |
| grafia de nome confirmada | remover negação |
| erro inequívoco de ASR confirmado no áudio | alterar número |
| | trocar dúvida por certeza; apresentar paráfrase como literal |

Registre toda correção (lista de `transcript_corrections`) para o humano revisar. Se a legenda difere da fala por limite de espaço, diga ao humano.

## 5. Ênfase: acento raro funciona porque é raro

O padrão da skill é conservador: legenda branca, acento raro. Em 5 de 12 referências virais observadas não há destaque nenhum; as demais usam salto de tamanho (3), palavra acesa (1) ou cor. Os estilos mais densos (seção 9) são **escolhas deliberadas, casadas com um formato** (`formatos-virais.md`), não o novo padrão. Se o usuário não pediu um estilo, use o padrão.

- Medição em referência de estilo (talking head vertical): ~94% das linhas em branco puro, 3,5% e 2,4% em cor. Pintar a palavra-chave em toda frase **mata** o dispositivo.
- Máximo 1-3 palavras por beat, e com >= 2 blocos normais entre destaques; quando há, a palavra de ênfase fica **sozinha** no bloco (ou claramente separada). Candidatas: número, contraste, verbo de mudança, conclusão, nome essencial.
- **Não há destaque automático.** O destaque é a lista explícita que o editor (você) passa: `--highlight "palavra1,palavra2"` pinta só essas palavras, na cor de `--accent` (ex.: `"#FFD400"`). Sem `--highlight`, a legenda sai toda em branco. Escolha as palavras lendo o digest, nunca por regra.
- **Nunca destaque um número ou afirmação contestável** ("100%", estimativa, cifra que o falante corrige): o destaque dá autoridade que a fala não tem. Quando o falante se corrige, vale o último número.
- Cor tem função: um acento principal por vídeo; se usar vermelho/verde por semântica (alarme x solução), mantenha o código no vídeo inteiro.
- **Ênfase por tamanho** (`--emphasis "a,b"`): a palavra ou frase listada sai num bloco bem maior (observado em 3 de 12, em números e frases-chave). Mesma disciplina do acento: poucas por vídeo, só o que é verificável, o bloco ampliado continua dentro das zonas seguras. Tamanho ou cor: escolha **um** vetor por vídeo; os dois juntos pesam. Tamanho funciona melhor em caixa alta e em bloco curto; cor, em frase/minúscula.

## 6. Corte seco + cadência, em vez de easing por bloco

Medido em referência (30 fps): a entrada do bloco tem ~93% da massa no 1º quadro (deslocamento 0,7 px, escala 0%); duração mediana 10 quadros (~0,33 s); cadência ~2,45 blocos/s. A "fluidez" vem da **cadência no tempo exato da palavra**, não de easing. Animar a entrada de um bloco de 0,33 s gasta metade da vida dele em transição e lê como arrastado. Default: **entra em corte seco** no quadro da palavra; se o estilo pedir animação, no máximo escala 0,86 -> 1 em ~0,12 s e só em blocos longos. Meça a referência antes de imitar: "parece mais fluido" estava errado por 4 quadros de easing.

## 7. Posição, tamanho e zonas seguras (1080x1920)

> Padrão aprovado em teste real (talking head com motion): Montserrat Black, caixa alta,
> `--size 138 --outline 9 --shadow 3`, `--y 0.70`, `--mode karaoke --max-words 3`, sem
> pontuação e `--mute` sob o motion. Detalhes em `padrao-excelencia.md`.

| Item | Default | Observação |
|---|---|---|
| Faixa de legenda | A posição **segue o layout**: tela cheia `--y 0.62` (ou 0,62-0,78 conforme o rosto); layout empilhado (`lower`, janela de b-roll em cima) na **costura**, y ≈ 0,43-0,50, que é o padrão dos clipes `lower` (ajuste por clipe com `caption_y`). `--y 0.62` (padrão do `vedit captions`; centro do texto em y ~1190 de 1920, dentro da faixa 1040-1220 e acima da zona de interface). Para talking head com o rosto alto no quadro, `--y` 0.70 a 0.78 (faixa ~1270-1540, abaixo do queixo) | **sempre** confirme numa prancha com `vedit sheet --guides` (retângulo do rosto no pior quadro + retângulo da faixa): se cruzam, mova `--y` ou reenquadre |
| Zona livre geral | topo ~14% (~270 px), base ~35% (~670 px), laterais ~6% (~65 px) | números da Meta para Reels/Stories; TikTok não publica pixels fixos |
| Conservador (todas as plataformas) | margem esq. 90, dir. 170, topo 160, base 310 px; sem texto crítico em y > ~1250 | direita maior por causa dos botões laterais |
| Largura de linha | p90 ~0,48 da largura em estilo viral; nunca passar da zona lateral | |
| Corpo da fonte | ~74-80 px (estilo viral); ênfase ~2x o corpo; **teste**: o mesmo corpo varia ~2x entre fontes por métrica | fontes largas parecem menores em libass |
| Contorno | 6-10 px escuro + sombra leve; sem caixa permanente | `-webkit-text-stroke` come o glifo em HTML: use anel de sombras |
| Alinhamento | centrado; empilhamento por tinta, entrelinha ~0,96 | |

A altura sobre o peito, sobre roupa escura, já dá contraste em talking head; se não, contorno e sombra. Em cima de rosto, **nunca**: ver `enquadramento-vertical.md`, seção 9.

## 8. Legenda cala sob tipografia em tela cheia

Cena de motion que já tem texto próprio não aguenta uma segunda tipografia por cima. Regras: legenda corre nas janelas livres e **cala** sob os motions; janela livre < 2 s fica sem legenda (pisca entre dois motions lê como defeito); a troca de cor (claro/escuro) depende do tipo de saída da cena, não da janela inteira. Frase de impacto só entra em janela sem motion. Mede-se no **pior quadro** da janela.

**Sob cartões de prova** (`overlays` com `region: "card"`): o `vedit captions` **descarta os blocos** que caem sob um cartão, para a legenda não colidir com o texto dele (defeito observado em uma referência). `--keep-under-cards` desliga isso; só use se o cartão não tiver texto. Palavra dita sob o cartão fica sem legenda: confirme que a fala continua inteligível (a prova está na tela). Janela livre < 2 s entre cartões, sem legenda.

## 9. Modos e caixa: bloco, palavra, karaoke

| Modo (`--mode`) | O que faz | Quando serve | Custo |
|---|---|---|---|
| `bloco` (padrão) | 2-4 palavras por bloco, corte seco | quase tudo; leitura em 1 olhada | nenhum |
| `palavra` | uma palavra por bloco, troca a cada ~0,3-0,5 s | fala curta e densa, imagem simples, estilo pedido (3 de 12, sempre em caixa alta) | **conforto de leitura**: o texto pisca, o olho não tem contexto de frase, abaixo de ~0,3 s não se lê; ruim para frase longa, palavra técnica e quem lê rápido pouco |
| `karaoke` | bloco de frase com a palavra ativa acesa e as anteriores esmaecidas | frase de 4-8 palavras em que o ritmo da leitura importa (1 de 12) | mais ruído visual; a cor de "ativa" vira o acento do vídeo |

- Movimento constante divide atenção: `palavra` só com tempos por palavra confiáveis (`words.json` refinado) e conteúdo que aguenta. Se um bloco de 1 palavra cair abaixo de ~0,3 s, o `--mode palavra` não ajuda: use `bloco`.
- Caixa (`--case`): `sentence` (frase) ou `lower` leem melhor em fala corrida (6 de 12); `upper` combina com `palavra` e com ênfase por tamanho (5 de 12); `keep` preserva a grafia da transcrição. Não misture caixas no mesmo vídeo.
- Entrada continua em corte seco (seção 6); easing, entrada digitada, pílula e cor por falante **não** são do `vedit`: HyperFrames (`/hyperframes:embedded-captions`) ou `.ass` escrito à mão. Em libass, `\t` de alfa por palavra no meio da linha não funcionou (0.17); um evento por palavra com as seguintes em `\alpha&HFF&` (layout fixo, palavras acendendo) resolve se precisar de algo que o `karaoke` não cobre.

## 10. libass x fallback

- `vedit burn`: usa o filtro `ass` se o ffmpeg tiver libass; senão, fallback com Pillow + overlay. `vedit doctor` mostra qual existe. Um ffmpeg sem libass (comum em instalações por gerenciador de pacotes) **não** é falha: use o fallback ou um ffmpeg com libass.
- Cuidados do ASS: cores em BGR (amarelo = `00FFFF`); filtro `ass=arquivo.ass:fontsdir=pasta`; fontes embarcadas na pasta de fontes; tamanhos validados num quadro real (em libass o corpo sai menor que o esperado com fontes de métrica larga).
- Em HTML->PNG (pílulas, gradiente, fonte do site): pontuação depois de `<em>` vai **dentro** do span, senão pode quebrar sozinha na linha de baixo.
- Exporte também `.srt` (`--srt`) para acessibilidade e reaproveitamento.

## 11. Capa / título

- Texto curto de 2 linhas (<= ~14 caracteres por linha a ~110 px), caixa clara arredondada (raio ~3% da largura) com sombra suave, aplicada **só no quadro 0** quando a plataforma usa o 1º quadro como capa; gráficos na introdução abaixo da faixa do título. Isto é a **capa** (quadro 0); a manchete que permanece na tela durante o vídeo está na seção 12.
- Instagram e TikTok permitem escolher o quadro de capa na publicação e o grid do perfil recorta (hoje com proporção 3:4 no Instagram; **confirme**). Mantenha o texto da capa no terço central do 9:16.
- Capa mentirosa (promete algo que o vídeo não entrega) reprova no portão editorial.

## 12. Manchete fixa

Texto fixo no alto ou na costura durante parte do vídeo ou ele todo (6 de 12; manchete já no quadro 0 em 7 de 12 vídeos). Variantes observadas:

| Variante | Duração | Nota |
|---|---|---|
| Faixa ou fita com caixa alta e palavras-chave em amarelo, na costura ou embaixo | do ~3 s ao fim | combina com formato empilhado |
| Caixa amarela por linha | só os ~3 s iniciais | função de gancho |
| Manchete empilhada em duas cores | só os ~3 s finais | função de fechamento |
| Rótulo pequeno de série, fixo no topo | o vídeo todo | marca, não gancho |
| Manchete fixa na costura (y ~0,35-0,52), do início ao fim | o vídeo todo | observada em várias referências de formato empilhado; `--headline-y 0.42 --headline-end` na duração do vídeo |
| Manchete atrasada: entra no momento da virada (payoff) | do payoff ao fim | observada em uma referência; `--headline-start` no tempo da virada |

```bash
vedit captions 01-words.json --edl edl/c1.json -o out/c1/leg.ass --headline "LINHA 1|LINHA 2" --headline-y 0.12 --headline-start 0 --headline-end 3 --headline-box "#FFD400" --headline-color "#000000"
```

- **Máximo ~2 linhas**, curtas (<= ~18-22 caracteres por linha); `|` separa as linhas. Mais que isso vira parágrafo que ninguém lê.
- **Zonas seguras**: dentro das do plano (topo >= 14% / ~270 px, laterais ~6%); `--headline-y` 0,12 fica na borda, confira numa prancha com `--guides`. Se a plataforma cobre o topo com interface, desça. Na costura, não cubra o rosto.
- Duração: decida pela **função**, não por um número. Gancho (~3 s no início), fechamento (~3 s no fim) ou fixa o vídeo inteiro (rótulo/título do formato empilhado, na costura) são escolhas coerentes; entrada atrasada serve para destacar a virada. A pior escolha é a duração **intermediária sem função** (some no meio do vídeo sem marcar gancho, virada nem fim), porque compete com a legenda à toa. Manchete fixa o vídeo todo é prática observada em formato empilhado, não prova de desempenho. `--headline-start`/`--headline-end` (segundos de saída) e `--headline-y` cobrem todos os casos.
- A manchete **não substitui** a legenda e não pode colidir com ela: se a manchete fica na costura, afaste a legenda (`--y`) para o outro lado da costura; senão, legenda na costura e manchete acima.
- Texto da manchete é **texto inventado** por você: entra na lista de revisão (regra 9). Nunca promete o que o vídeo não entrega (capa mentirosa, seção 11).
- Animada, digitada ou com segundo tipo de letra (itálico serifado na palavra de destaque): HyperFrames.

## 13. Checklist

- [ ] Nenhum bloco sobrepõe outro ou atravessa corte
- [ ] Faixa não cobre rosto no pior quadro; dentro das zonas seguras
- [ ] Nenhuma palavra dita ficou de fora (fora das janelas de motion)
- [ ] Números e nomes conferidos contra o áudio
- [ ] Acentos <= 1-3 por beat e raros no vídeo
- [ ] Legenda é a última camada
- [ ] Modo e caixa casam com o formato; um só vetor de ênfase (cor **ou** tamanho)
- [ ] Nenhum bloco sob cartão de prova; manchete <= 2 linhas e dentro das zonas seguras
- [ ] Todo texto queimado conferido contra o áudio (sem erro de transcrição)

## Fontes
- Netflix, "Brazilian Portuguese Timed Text Style Guide", https://partnerhelp.netflixstudios.com/hc/en-us/articles/215600497-Portuguese-Brazil-Timed-Text-Style-Guide (aberta em 2026-11: 42 caracteres/linha, 2 linhas, 17 cps adulto/13 infantil, regras de quebra).
- Netflix, "Timed Text Style Guide: General Requirements", https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617 (aberta em 2026-11: duração mínima 5/6 s, máxima 7 s).
- TikTok, "Creative best practices", https://ads.tiktok.com/resources/help/article/creative-best-practices?lang=en (aberta em 2026-11: 5-10 palavras/s).
- Instagram/Meta Ads Guide, https://www.facebook.com/business/ads-guide/update/image/instagram-reels (aberta em 2026-11: 14%/35%/6%).
- Sem acesso ao texto completo na pesquisa (reconfirmar): Gernsbacher (2015); Szarkowska et al. sobre legendas rápidas e segmentação. Diretrizes da BBC não puderam ser abertas.
