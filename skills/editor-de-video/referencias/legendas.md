> **Leia quando** for gerar, corrigir, posicionar ou queimar legendas em vídeo vertical, ou revisar a legibilidade de texto na tela.
> **Comandos:** `vedit transcribe`, `vedit captions` (`--style viral|limpo`, `--max-words`, `--y` padrão 0.62, `--srt`, `--highlight`, `--accent`), `vedit burn`, `vedit sheet --guides` (formato em `formatos.md`).
> **Limite:** o `vedit` gera legenda estática por bloco. Legenda animada (palavra a palavra com easing, pílulas, CSS) é do HyperFrames.

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

- Medição em referência de estilo (talking head vertical): ~94% das linhas em branco puro, 3,5% e 2,4% em cor. Pintar a palavra-chave em toda frase **mata** o dispositivo.
- Máximo 1-3 palavras por beat, e com >= 2 blocos normais entre destaques; quando há, a palavra de ênfase fica **sozinha** no bloco (ou claramente separada). Candidatas: número, contraste, verbo de mudança, conclusão, nome essencial.
- **Não há destaque automático.** O destaque é a lista explícita que o editor (você) passa: `--highlight "palavra1,palavra2"` pinta só essas palavras, na cor de `--accent` (ex.: `"#FFD400"`). Sem `--highlight`, a legenda sai toda em branco. Escolha as palavras lendo o digest, nunca por regra.
- **Nunca destaque um número ou afirmação contestável** ("100%", estimativa, cifra que o falante corrige): o destaque dá autoridade que a fala não tem. Quando o falante se corrige, vale o último número.
- Cor tem função: um acento principal por vídeo; se usar vermelho/verde por semântica (alarme x solução), mantenha o código no vídeo inteiro.

## 6. Corte seco + cadência, em vez de easing por bloco

Medido em referência (30 fps): a entrada do bloco tem ~93% da massa no 1º quadro (deslocamento 0,7 px, escala 0%); duração mediana 10 quadros (~0,33 s); cadência ~2,45 blocos/s. A "fluidez" vem da **cadência no tempo exato da palavra**, não de easing. Animar a entrada de um bloco de 0,33 s gasta metade da vida dele em transição e lê como arrastado. Default: **entra em corte seco** no quadro da palavra; se o estilo pedir animação, no máximo escala 0,86 -> 1 em ~0,12 s e só em blocos longos. Meça a referência antes de imitar: "parece mais fluido" estava errado por 4 quadros de easing.

## 7. Posição, tamanho e zonas seguras (1080x1920)

| Item | Default | Observação |
|---|---|---|
| Faixa de legenda | `--y 0.62` (padrão do `vedit captions`; centro do texto em y ~1190 de 1920, dentro da faixa 1040-1220 e acima da zona de interface). Para talking head com o rosto alto no quadro, `--y` 0.70 a 0.78 (faixa ~1270-1540, abaixo do queixo) | **sempre** confirme numa prancha com `vedit sheet --guides` (retângulo do rosto no pior quadro + retângulo da faixa): se cruzam, mova `--y` ou reenquadre |
| Zona livre geral | topo ~14% (~270 px), base ~35% (~670 px), laterais ~6% (~65 px) | números da Meta para Reels/Stories; TikTok não publica pixels fixos |
| Conservador (todas as plataformas) | margem esq. 90, dir. 170, topo 160, base 310 px; sem texto crítico em y > ~1250 | direita maior por causa dos botões laterais |
| Largura de linha | p90 ~0,48 da largura em estilo viral; nunca passar da zona lateral | |
| Corpo da fonte | ~74-80 px (estilo viral); ênfase ~2x o corpo; **teste**: o mesmo corpo varia ~2x entre fontes por métrica | fontes largas parecem menores em libass |
| Contorno | 6-10 px escuro + sombra leve; sem caixa permanente | `-webkit-text-stroke` come o glifo em HTML: use anel de sombras |
| Alinhamento | centrado; empilhamento por tinta, entrelinha ~0,96 | |

A altura sobre o peito, sobre roupa escura, já dá contraste em talking head; se não, contorno e sombra. Em cima de rosto, **nunca**: ver `enquadramento-vertical.md`, seção 9.

## 8. Legenda cala sob tipografia em tela cheia

Cena de motion que já tem texto próprio não aguenta uma segunda tipografia por cima. Regras: legenda corre nas janelas livres e **cala** sob os motions; janela livre < 2 s fica sem legenda (pisca entre dois motions lê como defeito); a troca de cor (claro/escuro) depende do tipo de saída da cena, não da janela inteira. Frase de impacto só entra em janela sem motion. Mede-se no **pior quadro** da janela.

## 9. Palavra por palavra: só se justificado

Movimento constante divide atenção. Use quando: tempos por palavra confiáveis, fala curta, imagem simples, estilo pedido. Default: blocos por frase curta. **O `vedit captions` não faz palavra a palavra nem animação**: isso é do HyperFrames (skill `/hyperframes:embedded-captions`) ou de um `.ass` escrito à mão. Em libass, `\t` de alfa por palavra no meio da linha não funcionou (0.17); faça um evento por palavra com as seguintes em `\alpha&HFF&` (layout fixo, palavras acendendo).

## 10. libass x fallback

- `vedit burn`: usa o filtro `ass` se o ffmpeg tiver libass; senão, fallback com Pillow + overlay. `vedit doctor` mostra qual existe. Um ffmpeg sem libass (comum em instalações por gerenciador de pacotes) **não** é falha: use o fallback ou um ffmpeg com libass.
- Cuidados do ASS: cores em BGR (amarelo = `00FFFF`); filtro `ass=arquivo.ass:fontsdir=pasta`; fontes embarcadas na pasta de fontes; tamanhos validados num quadro real (em libass o corpo sai menor que o esperado com fontes de métrica larga).
- Em HTML->PNG (pílulas, gradiente, fonte do site): pontuação depois de `<em>` vai **dentro** do span, senão pode quebrar sozinha na linha de baixo.
- Exporte também `.srt` (`--srt`) para acessibilidade e reaproveitamento.

## 11. Capa / título

- Texto curto de 2 linhas (<= ~14 caracteres por linha a ~110 px), caixa clara arredondada (raio ~3% da largura) com sombra suave, aplicada **só no quadro 0** quando a plataforma usa o 1º quadro como capa; gráficos na introdução abaixo da faixa do título.
- Instagram e TikTok permitem escolher o quadro de capa na publicação e o grid do perfil recorta (hoje com proporção 3:4 no Instagram; **confirme**). Mantenha o texto da capa no terço central do 9:16.
- Capa mentirosa (promete algo que o vídeo não entrega) reprova no portão editorial.

## 12. Checklist

- [ ] Nenhum bloco sobrepõe outro ou atravessa corte
- [ ] Faixa não cobre rosto no pior quadro; dentro das zonas seguras
- [ ] Nenhuma palavra dita ficou de fora (fora das janelas de motion)
- [ ] Números e nomes conferidos contra o áudio
- [ ] Acentos <= 1-3 por beat e raros no vídeo
- [ ] Legenda é a última camada

## Fontes
- Netflix, "Brazilian Portuguese Timed Text Style Guide", https://partnerhelp.netflixstudios.com/hc/en-us/articles/215600497-Portuguese-Brazil-Timed-Text-Style-Guide (aberta em 2026-11: 42 caracteres/linha, 2 linhas, 17 cps adulto/13 infantil, regras de quebra).
- Netflix, "Timed Text Style Guide: General Requirements", https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617 (aberta em 2026-11: duração mínima 5/6 s, máxima 7 s).
- TikTok, "Creative best practices", https://ads.tiktok.com/resources/help/article/creative-best-practices?lang=en (aberta em 2026-11: 5-10 palavras/s).
- Instagram/Meta Ads Guide, https://www.facebook.com/business/ads-guide/update/image/instagram-reels (aberta em 2026-11: 14%/35%/6%).
- Sem acesso ao texto completo na pesquisa (reconfirmar): Gernsbacher (2015); Szarkowska et al. sobre legendas rápidas e segmentação. Diretrizes da BBC não puderam ser abertas.
