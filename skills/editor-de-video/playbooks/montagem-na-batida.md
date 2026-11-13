# Playbook: montagem na batida (vários clipes de celular, sem narração)

Objetivo: um Reel de cerca de 30 s feito de gravações reais (evento, bastidores,
passeio), com planos cortados em múltiplos de batida, rótulos de personagem, **um** momento
de fala original, e final que volta ao começo (loop).

```
pranchas + transcrição -> gancho, personagens, 1 momento de fala -> tabela de planos em
batidas -> textos -> trilha no mesmo grid -> prévia 540x960 -> aprovação -> final
```

Referências: `cortes-e-ritmo.md`, `enquadramento-vertical.md`, `legendas.md`, `audio.md`,
`plataformas.md`, `verificacao.md`, `armadilhas.md`. HyperFrames só se o usuário quiser
gráficos animados; a base aqui é vídeo real, então `vedit` + legenda ASS bastam. Formatos (EDL,
`--guides`) em `formatos.md`.

## Fase 0 — mapear tudo antes de cortar
```bash
vedit init ./run-batida
for f in clipes/*.mp4; do vedit probe "$f" > "run-batida/probe-$(basename "$f").json"; done
vedit sheet clipes/a.mp4 -o run-batida/qc/a.jpg --every 4 --cols 4 --width 360
vedit transcribe clipes/a.mp4 -o run-batida/a-words.json --lang pt
vedit digest run-batida/a-words.json -o run-batida/a-digest.md
```
Repita por arquivo (a prancha de um clipe longo pode ir a um subagente para o loop
principal não carregar dezenas de imagens). Conferir no probe de cada um: `avg_frame_rate`
real (o "120 fps" costuma ser só a base de tempo), altura que varia entre arquivos, rotação
e **HDR** (celular grava HLG/BT.2020).
Prancha com `--every` grande desloca um ou dois segundos: para escolher entradas exatas,
refine com `--start/--end` e `--every 0.5`.

## Fase 1 — escolher o fio
Decida, com a prancha e o texto:
- **Gancho:** o plano mais estranho ou que encara a câmera, com frase de curiosidade em até 2 linhas.
- **Personagens:** quem aparece e o rótulo curto de cada um (ex.: "O MOTORISTA").
- **Um momento de fala** original, limpo (sem palavrão, sem música com direitos ao fundo).
- **Fim em loop:** volta ao plano do gancho.
**Portão 1:** mostre a tabela de planos (arquivo, tempo, o que é) e a ideia de abertura/fim.

## Fase 2 — grid de batida
Escolha o BPM da trilha (por exemplo 110 a 140). Duração da batida = 60 / BPM. Cada plano
dura um múltiplo de batida (4 ou 8 é o comum); o momento de fala é a exceção e pode ter duração livre.
Tabela de planos (a fonte única de verdade, vira a EDL):

| Plano | Arquivo (`source`) | Entrada (`in`) | Batidas | `speed` | `crop_x` | `zoom` | Rótulo |
|---|---|---|---|---|---|---|---|

Estrutura de referência (~30 s): gancho 8 batidas; apresentação de cada personagem 4;
chegada 8 (câmera lenta leve); situação engraçada 8; fala ~11; respiro irônico 4; fim 8.
Converta para `04-edl.json`: **cada plano é um clipe com o próprio `source`** (caminho relativo
ao arquivo da EDL; o `source` de topo pode ficar de fora). `out − in` é em segundos da fonte e,
com `speed` (0,25 a 4), a duração na saída é `(out − in) / speed`: para um plano de N
batidas a `speed` 0,5, use `out = in + N × 60/BPM × 0,5`. Foto ou imagem também é fonte
válida (still de `out − in` segundos, sem áudio), útil para o gancho ou o respiro. Zoom por
clipe: número fixo (empurrão estático) ou rampa linear `{"from": 1.0, "to": 1.10}` (zoom
lento no gancho). O "punch" que assenta em poucos quadros **não existe** como curva: faça-o
como um clipe curto separado com `zoom` mais alto. Sem batida, sem zoom. `crop_x` fixo por
clipe; keyframes `[{"t","x"}]` trocam por salto, não deslizam. Exemplo multi-fonte completo
em `formatos.md`, seção 2.

## Fase 3 — render dos planos
```bash
vedit cut --edl run-batida/04-edl.json -o run-batida/out/previa.mp4 --preview
vedit sheet run-batida/out/previa.mp4 -o run-batida/qc/previa.jpg --every 1 --cols 6 --width 240
```
O `vedit cut` já converte HDR para SDR; **sem o filtro `zscale` no ffmpeg a conversão sai sem
tone mapping** (o `vedit doctor` avisa). Confira as cores fortes (laranja, vermelho) na
prancha: se saírem avermelhadas ou lavadas, avise o usuário. `speed` abaixo de 1 é só
mudança de velocidade, sem interpolação de quadros: use em planos curtos.

## Fase 4 — textos
Rótulos e frases em ASS. `vedit captions` cobre a fala (com `--highlight` para as poucas
palavras que você quer em cor); rótulos extras vão num `.ass` seu (`rotulos.ass`), um
evento por palavra quando precisar acender palavra a palavra. O rótulo "bate" na batida
(escala 135% -> 100% em ~0,14 s) **só** num `.ass` escrito à mão com `\t`; animação
mais rica é do HyperFrames. O texto nunca cobre o rosto: confira na prancha com `--guides`.
Posição padrão da legenda de fala: `--y 0.62`; mova só se cobrir o rosto.
```bash
vedit captions run-batida/a-words.json --edl run-batida/04-edl.json -o run-batida/out/leg.ass --y 0.62
```
(`a-words.json` é a transcrição do arquivo que contém a fala. O `captions` lê só **um**
`words.json` e remapeia as palavras pelas janelas `in`/`out` dos clipes **da fonte
transcrita** (o `source` do topo da EDL; sem ele, o do primeiro clipe). Clipes de outras
fontes e imagens ficam sem legenda, mesmo que a janela coincida em tempo. Por isso o `source`
do topo ou o primeiro clipe deve ser o arquivo da fala; confira na prancha. Fala em dois
arquivos: uma legenda por arquivo, cada uma com sua EDL, e junte os `.ass` na mão.)
Sem libass no ffmpeg ou texto que precisa de CSS (pílula, gradiente): crie o texto como
PNG transparente pelo HyperFrames ou HTML e sobreponha lá. Fonte em ASS costuma sair menor
que o esperado: teste o tamanho em 1080x1920.
**Portão 2:** prévia com texto, mostre e liste os textos inventados.

## Fase 5 — trilha, fala, loudness, final
Trilha original (sintetizada por código) ou música sem direitos, **no mesmo grid** do BPM
(`musica.wav`, fornecida pelo usuário ou gerada por você; nenhum comando do `vedit` cria
música). A cadeia, depois do ok da prévia:
```bash
vedit cut --edl run-batida/04-edl.json -o run-batida/out/corte.mp4
vedit extract-audio run-batida/out/corte.mp4 -o run-batida/out/voz.wav
vedit mix --voice run-batida/out/voz.wav --music run-batida/musica.wav -o run-batida/out/mix.wav --music-lufs -27 --duck
vedit burn run-batida/out/corte.mp4 run-batida/out/leg.ass -o run-batida/out/com-texto.mp4
vedit mux --video run-batida/out/com-texto.mp4 --audio run-batida/out/mix.wav -o run-batida/out/composto.mp4
vedit master run-batida/out/composto.mp4 -o run-batida/out/final.mp4
vedit verify run-batida/out/final.mp4 --platform reels --json
```
`voz.wav` é o som original de todos os planos do corte; o `mix` o põe **sob** a duração da
música com ducking. O `vedit` não silencia um plano individual: stills não têm áudio, mas
um plano de vídeo traz o som dele. Se algum plano tem música com direitos ou palavrão ao
fundo, troque o plano, ou trate o áudio fora do `vedit` (ffmpeg manual, gerando um
`voz.wav` próprio só com a fala escolhida, e passe esse arquivo ao `--voice`). `burn`
recodifica o vídeo, por isso vem **antes** do `mux`. Não use `--strict-edges`: a trilha toca
até o fim e som nas bordas é esperado (vira só aviso).
Rode `ve-qc` (rosto inteiro no crop, texto sobre rosto, loop sem salto de imagem).

## Checklist final
- [ ] Tabela de planos fechada em batidas; fronteiras em quadro inteiro.
- [ ] HDR convertido sem avermelhar cores fortes; `avg_frame_rate` real conferido.
- [ ] Gancho nos primeiros 2 s; um único momento de fala, limpo, com legenda.
- [ ] Nenhum áudio com direitos nem palavrão; trilha no grid; loudness medido no final.
- [ ] Texto fora do rosto e da área segura; textos inventados listados.
- [ ] Final volta ao plano do gancho; `verify` aprovado; usuário ouviu.
