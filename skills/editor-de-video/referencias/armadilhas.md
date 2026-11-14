> **Leia quando** algo quebrou ou estiver prestes a ser feito pela primeira vez (build do ffmpeg, HDR, legenda, matte, render longo). Cada linha custou pelo menos uma rodada de retrabalho.
> **Formato:** `# | falha | sintoma | correção`. Numeração contínua para citar ("armadilha 17"). Nenhuma depende de uma máquina específica.

# Armadilhas

## A. ffmpeg e builds

| # | Falha | Sintoma | Correção |
|---|---|---|---|
| 1 | ffmpeg sem libass (comum em pacotes de gerenciador) | filtro `ass`/`subtitles` ausente; legenda não queima | `vedit doctor`; usar build com libass ou o fallback Pillow do `vedit burn` |
| 2 | ffmpeg sem `drawtext` | texto não renderiza | legenda por ASS; texto com estilo por HTML -> PNG transparente + `overlay` |
| 3 | Testar a presença de "ass" por substring na lista de filtros | falso positivo (`lowpass`, `highpass`, `bass`...) | casar por palavra inteira |
| 4 | `-c copy` para cortar | corta no keyframe; in/out não bate com o transcrito | sempre reencodar (`vedit cut`) |
| 5 | Instalar ferramenta pesada por compilação no meio de um job | horas de build, job parado | instalar antes, em Fase 0; preferir binário estático pronto |
| 6 | Dependência com wheel indisponível para a combinação SO/CPU/Python (ex.: OpenCV, PyAV em Python recente) | compila do zero ou falha | fixar versão conhecida; usar ffmpeg para redimensionar e Python só para mapear quadros; Python 3.10-3.12 |
| 7 | Versão do ffmpeg difere entre `PATH` e o pretendido | filtro some "do nada" | `which ffmpeg`, `vedit doctor`, prefixar o `PATH` do build certo |

## B. Taxa de quadros e base de tempo

| # | Falha | Sintoma | Correção |
|---|---|---|---|
| 8 | Confiar em `r_frame_rate` ("120 fps") | cortes e câmera lenta errados | usar `avg_frame_rate` e `nb_frames` (`vedit probe`) |
| 9 | Celular "quase CFR" (8789 quadros em vez de 8791) | deriva de ~2 quadros em fonte longa | decodificar com `fps=N` para o quadro n = n/N s |
| 10 | Fronteiras de trecho em tolerâncias diferentes entre scripts | um quadro cai em layout errado/sem máscara | `round(t*fps)` em tudo; intervalo `[ini, fim)` |
| 11 | Fonte 23,976/29,97 em saída 60 fps sem mapa | judder, deriva | mapa quadro-saída -> quadro-fonte monotônico; sem interpolar |
| 12 | Timeline de motion em 24 fps exportada para 29,97 convertendo depois | judder | avaliar cada quadro de saída no tempo real (`frame24 = t*24`, com fração) |
| 13 | Prancha com `fps=1` após `-ss` | deslocamento de 1-2 s | `fps=2/4` na janela; ou `-ss` depois do `-i` quando a precisão importa |
| 14 | Altura de vídeo varia entre arquivos (1840 vs 1824) | crop 9:16 com largura errada | calcular o crop pela altura de cada arquivo |

## C. Cor e HDR

| # | Falha | Sintoma | Correção |
|---|---|---|---|
| 15 | Vídeo HLG/PQ sem converter | imagem lavada em player SDR | converter para BT.709 (`vedit cut` faz); conferir `probe` |
| 16 | Tonemap padrão (`zscale`+`mobius`) em cor saturada | laranja vira vermelho | testar `colorspace=all=bt709:iall=bt2020...` + `eq` leve; olhar as cores fortes |
| 17 | Sharpen/saturação/HDR aplicados "por padrão" | aspecto artificial, bandas | não aplicar automaticamente |
| 18 | Metadados HDR mantidos na saída | player escolhe tonemap próprio | saída `yuv420p` BT.709 limpa |

## D. Áudio

| # | Falha | Sintoma | Correção |
|---|---|---|---|
| 19 | `loudnorm` sai em 192 kHz e entra em `sidechaincompress`/`amix` com stem a 48 kHz | música acaba antes do vídeo; cartão final mudo | `aresample=48000` após todo `loudnorm`; `apad=whole_dur`; `amix=duration=first:normalize=0` |
| 20 | Mono duplicado em estéreo medido no `ebur128` | +3 LU; voz 3 dB baixa por canal | normalizar o stem já em estéreo |
| 21 | Voz em -14 LUFS com pico verdadeiro > 0 dBTP | clip no AAC | limitador com lookahead ~5 ms na voz; TP -1,5 no master |
| 22 | Redutor de ruído errado (RNNoise em voz com eco) | som metálico/aquoso | diagnosticar SNR; redutor de reverberação; ver `audio.md` |
| 23 | Latência do filtro não compensada (~10-30 ms) | boca dessincroniza, início de frase cortado | medir por correlação cruzada e descartar as amostras |
| 24 | Limiar de silêncio aplicado ao sinal bruto | junções "crescem" na medição final; ruído acima do limiar | tratar e normalizar antes; medir no stem final; folga de ~100 ms |
| 25 | Fade e limitador reduzem a cauda | junção projetada com 130 ms mede 160-180 ms | projetar com folga; medir logo após montar a voz |
| 26 | Respiração dentro da pausa | pausa > 250 ms não detectada | revisar pausas longas no stem |
| 27 | `afade=t=out:st=0:d=0` | áudio inteiro zerado | duração > 0 |
| 28 | `-shortest` ao muxar com cartão final | cartão cortado | `-af apad -t <duração do vídeo>` |
| 29 | Expressão `volume` com `<`/`>` | erro de parse | `clip()` e vírgulas escapadas |
| 30 | Música de terceiros ou fala com palavrão no fundo | risco de direitos/reprovação de anúncio | trilha sintetizada ou livre; cortar fala |

## E. Transcrição

| # | Falha | Sintoma | Correção |
|---|---|---|---|
| 31 | Início de palavra adiantado pelo ASR (absorve silêncio) | corte pega cauda da palavra anterior; legenda adiantada | refinar por energia (3 janelas >= -35 dB após >= 40 ms de silêncio; o `vedit transcribe` já faz); o `vedit captions` não soma deslocamento: ajuste à mão se preciso |
| 32 | ASR cola a palavra seguinte à anterior | gap < 0,12 s, ponto de corte errado | procurar a janela mais silenciosa (20 ms) de `fim-0,03` a `fim+0,6` |
| 33 | `condition_on_previous_text` ligado em tomadas repetidas | tomadas "fundidas" | desligar |
| 34 | Biblioteca de áudio nova quebra o transcritor (erro de metadados) | falha ao abrir o arquivo | passar array numpy decodificado em vez do caminho |
| 35 | Transcrever o episódio inteiro para cortar 1 min | custo de centenas de vezes em tokens | `vedit digest --windows` |
| 36 | Trecho com palavras curtas repetidas ("é", "o") | cena ancorada na ocorrência errada | conferir a n-ésima ocorrência em `words.json` |
| 37 | Legenda de vídeo de plataforma com cue rolante | texto triplicado, tempo por palavra perdido | parser dedicado; dedupe por sufixo |

## F. Legendas e libass

| # | Falha | Sintoma | Correção |
|---|---|---|---|
| 38 | Quebrar bloco por pausa do ASR | blocos de uma palavra ("E", "o") | quebrar por pontuação/sintaxe; fundir blocos fracos |
| 39 | Blocos sobrepostos no tempo | bloco seguinte entra atrasado | truncar o fim no início do próximo |
| 40 | Bloco que atravessa corte | lê como erro de decupagem | quebrar no corte |
| 41 | Cor em RGB no ASS | cor trocada (amarelo vira ciano) | ASS usa BGR |
| 42 | Fonte de métrica larga em libass | texto ~metade do esperado | calibrar o corpo num quadro real |
| 43 | `\t` de alfa por palavra no meio da linha | não anima | um evento por palavra com as seguintes em `\alpha&HFF&` |
| 44 | Pontuação fora do `<em>` em HTML | ponto cai sozinho na linha de baixo | pontuação dentro do span |
| 45 | `-webkit-text-stroke` no contorno | glifo "comido" | anel de `text-shadow` em ~16 direções |
| 46 | Legenda sobre tipografia de motion | duas tipografias brigam | calar sob motion; janelas < 2 s sem legenda |
| 47 | Faixa de legenda decidida após o layout | cai em cima dos olhos; render refeito | geometria + faixa juntas num quadro real |
| 91 | Legenda corrida sobre cartão de prova com texto próprio | texto sobre texto, ilegível (visto numa referência viral) | `vedit captions` cala sob cartões; não use `--keep-under-cards` se o cartão tem texto |
| 92 | Copiar o pico de áudio das referências (6 de 12 acima de -1 dBTP, um em +0,2) | clip no AAC, `verify` reprova | alvo da skill: -14 LUFS, -1,5 dBTP; meça no arquivo final |
| 93 | Imagem de enchimento ocupando meia tela (janela de b-roll sem coisa nomeada) | metade do quadro sem informação | só insira imagem que mostra o que a palavra nomeia; sem imagem, `cover` em tela cheia |
| 94 | Erro de transcrição queimado na legenda | texto errado na tela (nome, número, termo técnico) | conferir cada bloco queimado contra o áudio e o `words.json`; corrigir só grafia (`legendas.md`, seção 4) |
| 95 | Overlay `top` sobre clipe que não é `lower` | b-roll cobre o rosto | `top` só sobre `lower`; o `ve-qc` confere |
| 96 | `lower` sem overlay na região de cima | metade do quadro vazia | `cover` onde não há b-roll |
| 97 | Overlays sobrepostos no tempo | o `cut` recusa ou mostra a imagem errada | um overlay por vez; deixe intervalo entre eles |
| 98 | `lower` com a metade de cima só desfocada (motion "depois") | o usuário lê como corte quebrado | `cover` em tela cheia; motion por cima como trilha transparente (`padrao-excelencia.md`) |
| 99 | Manchete em caixinha pequena fixa por vários segundos | "nada profissional" | gancho cinético grande nos 2 primeiros s, depois sai |
| 100 | Legenda com corpo ~111 em fonte condensada | altura de caixa alta ~45 px, some no celular | Montserrat Black 138, contorno 9; meça num quadro real |
| 101 | Ponto/vírgula do ASR na legenda | "MOLEQUE." na tela | `vedit captions` remove por padrão (`--keep-punct` mantém) |
| 102 | Legenda e motion dizendo a mesma frase | texto duplicado brigando | `--mute "a-b,..."` nos intervalos do motion |
| 103 | Palavra que atravessa o corte some da legenda | buraco na frase | ajustar o tempo no `words.json` para dentro do clipe |
| 104 | `burn` caindo no Pillow por ffmpeg sem libass | texto fino, quebra errada | apontar `VEDIT_FFMPEG` para um ffmpeg com libass; `--fontsdir` para fontes baixadas |
| 105 | Foto de stock com texto legível (ex.: "Happy Birthday") | ruído e idioma errado | conferir cada foto; trocar por uma sem texto |
| 106 | Partícula/anel/cursor de motion solto sobre rosto ou texto | parece bug | revisar prancha de ~20 quadros do composite e mandar remover |
| 107 | Cenas de motion soltas, uma por trecho | sistema visual incoerente, muito composite | uma composição transparente do comprimento do vídeo (ProRes 4444) + `vedit composite` |
| 108 | Download do modelo large-v3 travado sem progresso | transcrição parada | usar `--model small` e corrigir à mão as palavras de borda |

## G. Crop e tracking

| # | Falha | Sintoma | Correção |
|---|---|---|---|
| 48 | Escolher o maior rosto | crop no ouvinte | correlação boca x áudio |
| 49 | Movimento de boca puro | ouvinte inquieto vence o locutor | correlação com energia do áudio + histerese |
| 50 | Comparar recortes de boca por shape | movimento 0,00 para o locutor principal | redimensionar a tamanho fixo antes |
| 51 | Silhueta cuja ponta é a mão levantada | crop sobe e perde a cabeça | se `|cabeça - corpo| > 0,12`, usar o centro do corpo |
| 52 | Suavização que atravessa cortes | crop "arrasta" do plano anterior | reiniciar em cada corte |
| 53 | Crop estático com câmera em zoom | pessoas cortadas na 2ª metade | enquadramento por subsegmento se a variação > ~25% |
| 54 | Pan além da folga do push | borda preta | `pan_max = (escala-1)*largura/2` |
| 55 | Troca de enquadramento no meio da palavra | salto visível | só em corte de câmera ou fronteira de turno |

## H. Composição e matte

| # | Falha | Sintoma | Correção |
|---|---|---|---|
| 56 | Feathering da máscara centrado na borda do cartão | faixa clara no cabelo | feathering todo dentro do cartão |
| 57 | Encosto de cadeira na máscara | fantasma semitransparente | corte geométrico (pico, vale, rampa) validado em todos os quadros |
| 58 | Cor da cabeça vinda do recorte | cabeça descola do corpo em movimento | cor do quadro do cartão, só o alfa do recorte |
| 59 | Máscara por quadro de saída | 1000 máscaras caras | máscara por quadro único da fonte, indexada pelo índice da fonte |
| 60 | Fundo "transparente" pedido ao gerador | RGB com fundo sólido | fundo neutro por luminância + recorte |
| 61 | Fundo chroma | spill em ~65% da borda | neutro escolhido por afastamento de luminância |
| 62 | Sombra embutida no asset | sombra dupla na cena | no prompt "sem sombra"; remover por faixa; sombra é camada |
| 63 | Regra de remoção de sombra de objeto claro aplicada a objeto escuro | objeto comido | inverter a regra (`dark_floor`) |

## I. Motion e tipografia

| # | Falha | Sintoma | Correção |
|---|---|---|---|
| 64 | Texto gerado por IA no asset | letras erradas | prompt sem texto; todo texto por código |
| 65 | Âncora medida no bitmap original e rotacionada com `expand` | círculo no lugar errado | rotacionar a âncora junto (erro < 1 px) |
| 66 | Largura de texto estimada pela fonte | rótulo vaza (até 20%) | medir o desenho |
| 67 | `END` amostrado antes do último evento | texto pela metade | `END >= max(fim de eventos)` |
| 68 | Boil no quadro inteiro | fundo ondula, tremor de câmera | por camada, semente por elemento |
| 69 | Estado de boil que vaza entre passadas | legenda torta e parada | zerar no início de cada passada |
| 70 | Grão por pixel e por quadro | 120 Mbps | borrado e em "twos" |
| 71 | Aberração cromática horizontal uniforme | franja em toda letra | radial, nula no centro |
| 72 | Mesma saída em todas as cenas | tique | alternar `slide`/`wipe`/`push` |
| 73 | Erro de console a cada quadro (ex.: raio negativo em SVG) | "não pronto para render"; snapshot estoura | `Math.max(0, ...)` |

## J. HyperFrames e HTML

| # | Falha | Sintoma | Correção |
|---|---|---|---|
| 74 | Regra CSS genérica `svg { inset: 0 }` | ícones vão para o canto | classe específica |
| 75 | Tela sobreposta sem `background` | a anterior aparece por baixo | fundo opaco |
| 76 | `index.html` em symlink; duas composições raiz na mesma pasta | "index.html not found"; erro de lint | copiar o `index.html`; symlink só em `assets/` |
| 77 | `onUpdate` para lógica por quadro | suprimido em seek, não determinístico | tween-proxy com *modifiers* / relógio ligado |
| 78 | Captura por Chrome headless com usuário já aberto | conflito de perfil; código de saída != 0 com PNG gravado | `--user-data-dir` próprio; aceitar se o arquivo existir |
| 79 | Plano de fundo escuro pelo prompt de estilo (moldura preta contada como "área escura") | revisor reprova | usar cor clara |

## K. Processo e jobs longos

| # | Falha | Sintoma | Correção |
|---|---|---|---|
| 80 | `| tail` num job longo | traceback some; composição inteira perdida | log em arquivo |
| 81 | Geometria decidida depois da etapa cara | refazer render/máscara | prancha de geometria antes (ver `enquadramento-vertical.md`) |
| 82 | Indexar visualmente o vídeo inteiro antes de selecionar | execução travada em fonte de horas | selecionar sobre texto; visual só nas janelas |
| 83 | Analisar com sinal diferente do stem final | ~1 h de ajuste depois | analisar no nível do stem desde o início |
| 84 | Preview com voz sintética de teste | humano rejeita tudo | pedir narração real antes |
| 85 | `str.replace` que não casa | patch silencioso | confirmar cada patch com `grep -c` |
| 86 | Procurar chave de API na máquina | bloqueio de segurança; risco | perguntar ao humano (ver `narracao-tts.md`) |

## L. Shell

| # | Falha | Sintoma | Correção |
|---|---|---|---|
| 87 | zsh não divide variável em palavras | `for s in ${@:-a b c}` vira uma palavra | arrays: `list=($@)`; ou `bash -c` |
| 88 | `===` em `echo` no zsh | erro de sintaxe | aspas / `printf` |
| 89 | Vírgulas em `filter_complex` dentro de expressões | parse quebra | escapar com `\,` |
| 90 | Spotlight indexando mp4 intermediários | CPU e disco | pasta de trabalho excluída da indexação |

## Fontes
- FFmpeg Filters Documentation, https://ffmpeg.org/ffmpeg-filters.html (aberta em 2026-11: `loudnorm` e `dual_mono`, upsampling a 192 kHz, `silenceremove`).
- Demais itens: registro de falhas reais de projetos, generalizado e sem referência a máquina específica; reconfirmar versões de ferramentas antes de aplicar.
