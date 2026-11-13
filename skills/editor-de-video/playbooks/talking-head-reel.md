# Playbook: talking head -> Reel polido

Objetivo: uma gravação curta de uma pessoa falando vira um Reel 9:16 enxuto, com ritmo
visual, legenda, capa e trilha. Ordem pensada para **nunca refazer etapa cara**:
decisões baratas primeiro, geometria travada antes do render, motion por último.

Referências: `cortes-e-ritmo.md`, `enquadramento-vertical.md`, `legendas.md`, `audio.md`,
`motion.md` (se houver gráficos), `verificacao.md`, `armadilhas.md`.

## Fase 0 — entradas (minutos, decide o vídeo inteiro)
```bash
vedit init ./run-reel
vedit probe take.mp4 > run-reel/00-probe.json
vedit sheet take.mp4 -o run-reel/qc/entrada.jpg --every 5 --cols 4 --width 480
```
Pergunte-se: os canais estéreo são a mesma fonte? (a correlação L/R está no probe). Há
áudio limpo separado? Onde está o rosto, a pessoa olha para a lente ou de lado? A prancha
responde isso antes de qualquer decisão. Sem segunda fonte de áudio, a voz é o áudio da
câmera tratado; registre a decisão e siga.

## Fase 1 — transcrever e ler (barato)
```bash
vedit transcribe take.mp4 -o run-reel/01-words.json --lang pt
vedit digest run-reel/01-words.json -o run-reel/02-digest.md
vedit silences take.mp4 --noise -35 --min 0.25 > run-reel/silences.json
```
Leia o digest inteiro. Marque: o gancho (a frase mais forte que pode abrir), tomadas
repetidas (retakes: fique com a melhor), vícios e hesitações, o fechamento.
**Portão 1:** apresente o roteiro editado em texto (o que fica, o que sai, ordem) e
espere o ok. Não reordene frases se isso mudar o sentido.

## Fase 2 — EDL
Monte `run-reel/04-edl.json` com um clipe por trecho mantido (formato em `referencias/formatos.md`; um Reel = uma EDL).
- Silêncio entre frases: deixe de 80 a 150 ms; pausa dramática intencional pode ficar.
- Emenda no meio de frase só no vale de energia entre palavras; se a fala é contínua, não emende.
- J-cut/L-cut **não estão disponíveis no `vedit`** (áudio e imagem cortam no mesmo quadro, com micro-fade); se o usuário quiser, faça no HyperFrames ou em ffmpeg manual.
- Todas as fronteiras em quadro inteiro (`round(t*fps)`).
```bash
vedit metrics --edl run-reel/04-edl.json --words run-reel/01-words.json
vedit cut --edl run-reel/04-edl.json -o run-reel/out/previa.mp4 --preview
vedit edges run-reel/out/previa.mp4
```
Alvo de referência: maior trecho sem mudança visual entre 4 e 8 s. Palavra truncada é falha.
**Portão 2:** mostre a prévia seca (só cortes) e espere o ok.

## Fase 3 — geometria (o retrabalho mais caro mora aqui)
Trave **juntos** o enquadramento e a faixa de legenda. Desenhe, sobre um quadro real, o
rosto, a borda de qualquer cartão e a faixa da legenda; elas não podem se cruzar.
- `layout: cover` com `crop_x` centrado na pessoa (não no centro geométrico do quadro).
- Variação visual a cada poucos segundos com **propósito**: punch-in de 5 a 10% em ênfase
  ou virada, feito como **clipe separado** (divida o trecho no vale entre palavras) com
  `zoom` estático diferente (ex.: 1,0 -> 1,08), ou uma rampa linear `{"from": 1.0, "to": 1.10}`
  num clipe longo; alternar `cover` e `split` quando houver tela ou objeto a
  mostrar. Nunca dois layouts iguais seguidos sem motivo, nada parado além de ~8 s.
- Cada mudança tem de servir a uma batida da fala. Sem batida, sem mudança.
```bash
vedit sheet run-reel/out/previa.mp4 -o run-reel/qc/geo.jpg --every 2 --cols 6 --width 240 --guides zona.json
```

## Fase 4 — áudio (antes do render caro)
Meça a voz já no arquivo da prévia: `vedit loudness run-reel/out/previa.mp4`. Se a sala
for ruim (eco, ruído), trate a voz antes de decidir cortes por silêncio (ver `audio.md`:
cada tipo de gravação tem um redutor diferente; redutor errado deixa a voz "suja").
Sem música, não há o que fazer aqui: o áudio do `cut` já é a voz. Com música (livre de
direitos, sintetizada ou licença que o usuário confirme; `musica.wav` vem dele), a cadeia
roda depois do corte limpo, na Fase 8: `extract-audio` -> `mix` -> `mux`.

## Fase 5 — legenda
```bash
vedit captions run-reel/01-words.json --edl run-reel/04-edl.json -o run-reel/out/leg.ass --srt --style viral --max-words 3 --y 0.62 --highlight "palavra1,palavra2"
vedit sheet run-reel/out/previa.mp4 -o run-reel/qc/leg.jpg --guides zona.json --every 2
```
`--y 0.62` é o padrão; confira na prancha com `--guides` (formato em `formatos.md`) e mova
só se a faixa cobrir o rosto no pior quadro (talking head com o rosto alto: pode descer;
rosto baixo: suba, nunca sobre os olhos). Grupos de 1 a 3 palavras por pontuação e sentido.
`--highlight` é a lista de palavras-chave que **você** escolheu (uma a cada 3 a 4 s, no
máximo) e **nunca** número ou afirmação que a fonte não sustenta; sem a lista, não há
destaque. Sem libass no ffmpeg, o `vedit burn` usa o fallback com Pillow, mais lento.

## Fase 6 — gráficos e b-roll opcionais (HyperFrames)
Só se o usuário quiser: cartão de número, lower-third, ícone, pergunta na tela. Uma
composição por trecho com a duração exata; entrada na palavra certa lida do `words.json`.
Skill: `/hyperframes:talking-head-recut` (overlays sobre o vídeo da pessoa) ou
`/hyperframes:motion-graphics`. Prévia em fps baixo, prancha, só então render alto. Veja
`motion.md`, seção 15 (handoff). Textos inventados vão numa lista para revisão.

## Fase 6b — janela de b-roll, cartões e manchete (opcional, no `vedit`)
Para o formato "apresentador com janela de b-roll" (receita e exemplo em
`referencias/formatos-virais.md`; é prática observada em vídeos publicados, não causa
comprovada de retenção). Só se houver **coisas nomeadas para mostrar**; sem isso, pule.
- Clipes onde entra b-roll em cima: `layout: "lower"` (`split_at` 0,45); onde não há, `cover`.
- Lista `overlays` na EDL: `region: "top"` (janela, só sobre clipe `lower`), `"full"` (tela cheia, p.ex. montagem de gancho), `"card"` (print ou número, 1,5-3 s). `at` em tempo de **saída**, cada um na palavra que mostra; troca a cada 1,5-3 s; sem sobreposição no tempo.
- Legenda: `--mode`, `--case`, `--emphasis` e a manchete (`--headline "L1|L2" --headline-y 0.12 --headline-start 0`), no máximo 2 linhas, dentro das zonas seguras. A legenda cala sob cartões e fica na costura nos clipes `lower`.
- Confira rosto x costura x legenda numa prancha com `--guides` antes do render caro e liste manchete e rótulos como textos inventados.
Animação, transição e cantos arredondados continuam no HyperFrames (Fase 6).

## Fase 7 — capa
Quadro 0 com título de até 2 linhas curtas, legível em miniatura, dentro da área segura. Se
sair pelo HyperFrames, é um PNG sobreposto só no quadro 0. Mostre ao usuário.

## Fase 8 — render, áudio, master, verificação
```bash
vedit cut --edl run-reel/04-edl.json -o run-reel/out/limpo.mp4
vedit burn run-reel/out/limpo.mp4 run-reel/out/leg.ass -o run-reel/out/com-leg.mp4
vedit master run-reel/out/com-leg.mp4 -o run-reel/out/final.mp4
vedit verify run-reel/out/final.mp4 --platform reels --source take.mp4 --strict-edges --json
```
Com música, insira a cadeia entre o `burn` e o `master` (o `burn` recodifica o vídeo, por
isso vem antes do `mux`) e **tire** o `--strict-edges` (som até o fim é esperado):
```bash
vedit extract-audio run-reel/out/limpo.mp4 -o run-reel/out/voz.wav
vedit mix --voice run-reel/out/voz.wav --music musica.wav -o run-reel/out/mix.wav --music-lufs -27 --duck
vedit mux --video run-reel/out/com-leg.mp4 --audio run-reel/out/mix.wav -o run-reel/out/composto.mp4
vedit master run-reel/out/composto.mp4 -o run-reel/out/final.mp4
```
Se a legenda ou os gráficos saem do HyperFrames, o vídeo-base dele é o `limpo.mp4`, sem
`burn`. Rode o subagente `ve-qc`. **Portão final:** entregue com a lista de textos
inventados e peça ao usuário para ouvir.

## Checklist final
- [ ] Roteiro editado aprovado antes de qualquer render.
- [ ] Nenhuma palavra inventada; sentido preservado; retakes resolvidos.
- [ ] Geometria (rosto, legenda, cartão) travada antes do render caro.
- [ ] Cada punch-in e troca de layout justificado por uma batida.
- [ ] Voz medida no arquivo final; música livre de direitos e abaixo da voz.
- [ ] Capa legível, `verify` aprovado, textos inventados listados.
- [ ] Se houve janela de b-roll: `top` só sobre `lower`, nenhum overlay sobreposto, nada de legenda sob cartão.
