# Playbook: anúncio com footage real + narração

Objetivo: fotos e vídeos reais de um cliente, mais uma narração, viram um criativo vertical
de 20 a 30 s para social pago. A duração de cada cena **segue a voz**: nada de corte na
batida aqui.

```
mídias + copy do site -> roteiro por cena -> narração (1 take) -> transcrição por palavra
-> fronteiras de cena nas pausas da narração -> cena dura o que a fala dura -> texto por cima (HyperFrames ou HTML->PNG)
-> música -> mix com ducking -> mux no vídeo -> -14 LUFS -> 1080x1920
```

Referências: `psicologia-do-feed.md`, `legendas.md`, `audio.md`, `narracao-tts.md`,
`plataformas.md` (safe zones de anúncio), `formatos.md` (EDL, `--guides`), `verificacao.md`, `armadilhas.md`.

## Fase 0 — kickoff (uma rodada)
Peça: pasta de mídias; site ou texto do cliente (para tirar diferenciais, preço, prova,
cores, fontes, logo); **a narração pronta** (ou como gerá-la; veja `narracao-tts.md`);
CTA de baixo atrito e contato; prova social disponível (nota, avaliações); afirmações
proibidas (superlativos, garantias que o cliente não pode prometer). Formato 9:16; 4:5
só se pedirem (recorte do mesmo layout, conteúdo entre y 340 e 1000).
Nunca invente número, preço, nota ou depoimento: se não veio do cliente, não entra.

## Fase 1 — conhecer as mídias
```bash
vedit init ./run-anuncio
for f in midias/*; do vedit probe "$f" > "run-anuncio/probe-$(basename "$f").json" 2>/dev/null; done
vedit sheet midias/video1.mp4 -o run-anuncio/qc/v1.jpg --every 2 --cols 4 --width 360
```
Foto de celular em HEIC: converta para JPG antes. Anote, por mídia, o que **prova** algo
(sujeira saindo, antes/depois, o dono falando, o resultado). Vídeo HDR é convertido pelo
`vedit cut`.

## Fase 2 — roteiro por cena (7 cenas, ~22 a 29 s)
| # | Cena | Função |
|---|---|---|
| 1 | Gancho (até 2 s) | **prova visual** + palavra ou número em destaque, ou pergunta de identificação |
| 2 | Dor / contexto local | 2 a 3 palavras curtas na tela, o problema do público |
| 3 | Mecanismo | por que o óbvio não resolve; cria a necessidade antes da oferta |
| 4 | Prova do processo | mostrar o que acontece, de preferência com som do próprio serviço |
| 5 | Antes/depois | tela dividida, com "sem filtro" se for verdade |
| 6 | Prova social / oferta | nota real, preço "a partir de", garantia que o cliente confirmou |
| 7 | Card final | logo, ação única de baixo atrito, contato em pílula |

Texto na tela **não repete** a narração: a tela leva a versão curta (3 a 6 palavras), a
voz explica. Destaque de cor em 1 a 3 palavras por cena, na palavra que carrega a ideia.
**Portão 1:** mostre o roteiro por cena, a mídia escolhida para cada cena e todos os textos
que você escreveu. Espere aprovação.

## Fase 3 — narração e tempo de cada cena
A narração é **um arquivo próprio** (`narracao.wav`) e é a régua do vídeo: as cenas são cortadas
nas durações que a fala pede, e o áudio do footage é descartado (só entra se você decidir
mantê-lo, ver Fase 5).
```bash
vedit transcribe narracao.wav -o run-anuncio/01-words.json --lang pt
vedit digest run-anuncio/01-words.json -o run-anuncio/02-digest.md
vedit silences narracao.wav --noise -35 --min 0.15 > run-anuncio/silences.json
```
Marque as fronteiras de cena **nas pausas entre frases**, na linha do tempo da própria
narração. Duração da cena = do início da fala dela até o início da próxima (mínimo ~1,4 s);
o card final soma ~1,6 s depois da última palavra. Fala longa (> 4 s) ganha 2 planos,
para nada ficar parado mais de ~3 s. Arredonde a quadro inteiro.
Escreva `run-anuncio/04-edl.json` com **um clipe por plano, cada um com o próprio `source`**
(`../midias/video1.mp4`, `../midias/foto3.jpg`...; relativo ao arquivo da EDL), em que
`out − in` é a duração do plano na narração (ou `(out − in) / speed` se usar `speed`).
Foto vira still (`out − in` segundos, sem áudio); um zoom lento `{"from": 1.0, "to": 1.06}`
dá vida a ela. `cover`/`fit` conforme a mídia (4:3 ou paisagem sem o que cortar: `fit`).
O card final pode ser um still (PNG do card, feito em HTML ou no HyperFrames) de ~1,6 s como
último clipe. A soma dos clipes tem de igualar a narração mais o card final.
```bash
vedit cut --edl run-anuncio/04-edl.json -o run-anuncio/out/base.mp4 --preview
vedit probe narracao.wav          # compare a duração com a de out/base.mp4 (card final à parte)
```

## Fase 4 — texto por cima
Opção A, HyperFrames: composição por cena com entrada animada (subir ~26 px enquanto
aparece, 0,25 s), sombra em gradiente escuro atrás do texto para ler sobre qualquer imagem,
pontuação dentro do destaque para não quebrar linha. Skills: `/hyperframes:talking-head-recut`
ou `/hyperframes:general-video`; handoff em `motion.md`, seção 15.
Opção B, sem HyperFrames: HTML -> PNG transparente (Chrome headless, fontes locais por
`@font-face`) e `overlay` no ffmpeg com `fade ... alpha=1`. O Chrome às vezes sai com código
diferente de 0 mesmo gravando o PNG: aceite se o arquivo existe.
Antes/depois: "antes" em cima, divisória fina na cor da marca, "depois" entra deslizando
pela lateral (~0,25 s), com a etiqueta logo depois.
**Área segura:** nada importante nos 14% de cima nem nos 35% de baixo (referência em
1080x1920: texto entre y 290 e 1250 no feed, conferir `plataformas.md`). Use `vedit sheet --guides`.

## Fase 5 — áudio
A voz do anúncio é a `narracao.wav`. O vídeo cortado traz o som do footage, que você
**descarta** trocando a trilha de áudio; o `mix` junta narração e música, e o `mux` põe o
resultado no vídeo. Música livre de direitos ou sintetizada (`musica.wav`, fornecida pelo
usuário ou gerada por você); SFX que ilustram o serviço (água, sucção, estalo) valem mais
que whoosh genérico, um por evento visual, mas o `vedit` não os insere: eles entram na
composição do HyperFrames ou num `musica.wav` que já os contenha.
```bash
vedit mix --voice narracao.wav --music musica.wav -o run-anuncio/out/mix.wav --music-lufs -27 --duck
```
Se o som real do serviço (ex.: o ruído do equipamento) faz parte da prova, extraia-o do corte
(`vedit extract-audio run-anuncio/out/base.mp4 -o run-anuncio/out/som-footage.wav`) e use-o
como `--music` no lugar da trilha, ou mixe-o por fora; um único `mix` aceita voz + um fundo.
Confira que a música **dura até o fim** (cauda audível no card final) com `vedit probe` e que
o `mix.wav` cobre o vídeo; o `mux` ajusta o áudio à duração exata do vídeo. Você não ouve:
valide por número e peça escuta.

## Fase 6 — prévia, aprovação, final
Prévia 540x960 com **a voz real** (`vedit mux` na prévia). **Portão 2:** entregue a prévia, uma
prancha por cena e a lista de textos; espere o ok. Final (se o texto vier do HyperFrames,
substitua `limpo.mp4` pelo render dele; se o texto for ASS, queime com `vedit burn` antes
do `mux`):
```bash
vedit cut --edl run-anuncio/04-edl.json -o run-anuncio/out/limpo.mp4
vedit mux --video run-anuncio/out/limpo.mp4 --audio run-anuncio/out/mix.wav -o run-anuncio/out/composto.mp4
vedit master run-anuncio/out/composto.mp4 -o run-anuncio/out/final.mp4
vedit verify run-anuncio/out/final.mp4 --platform meta-ads --json
```
Não use `--strict-edges` (há música até o fim). Rode `ve-qc`: zoom no texto de cada cena,
rosto sob texto, card final com ao menos 1,4 s.

## Checklist final
- [ ] Todo número, preço, nota e garantia veio do cliente; nenhuma afirmação proibida.
- [ ] Gancho com prova visual nos primeiros 2 s; uma ação de CTA, fácil, visível.
- [ ] Cada cena dura o que a voz dura; nada parado por mais de ~3 s.
- [ ] Texto na tela é curto e diferente da fala; dentro das áreas seguras.
- [ ] Música audível até o fim, ducking sob a voz, -14 LUFS medido no arquivo final.
- [ ] `verify` com `--platform meta-ads` aprovado; usuário ouviu; sem promessa de resultado.
