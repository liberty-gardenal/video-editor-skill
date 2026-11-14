> **Leia quando** for escrever ou ler `words.json`, uma EDL, o JSON de `--guides`, ou precisar lembrar a pasta da run e a sintaxe de um subcomando. Esta é a referência de formatos da skill: ela vale mesmo quando a skill é instalada sem o resto do repositório. Para opções exatas de um comando, rode `vedit <comando> --help`.

# Formatos e comandos

## 1. `words.json` (saída de `vedit transcribe`)

```json
{"language": "pt", "duration": 123.4,
 "words": [{"w": "palavra", "t": 12.28, "e": 12.54}]}
```

`t` = início e `e` = fim da palavra, em segundos **da mídia transcrita** (não do clipe final; `vedit captions --edl` remapeia). Numa EDL com várias fontes, `captions` só põe palavras nos clipes da fonte transcrita (o `source` do topo da EDL, senão o do primeiro clipe; um `source` gravado no `words.json` tem prioridade); clipes de outras fontes e imagens ficam sem legenda. O loop principal não lê este arquivo: use `vedit digest`.

## 2. EDL (`edl.json`)

A EDL é a fonte única de verdade do corte. **Uma EDL = um vídeo entregável**: `vedit cut --edl X.json -o saida.mp4` sempre renderiza **um** arquivo com todos os clipes da EDL concatenados, na ordem. Para N shorts de um vídeo longo, escreva N EDLs (`edl/<id>.json`) e renderize cada uma para `out/<id>/corte.mp4`.

### Campos de topo

| Campo | Significado |
|---|---|
| `source` | arquivo de vídeo (ou imagem) padrão. **Opcional** se todo clipe tiver o próprio `source`. Caminho relativo ao arquivo da EDL |
| `fps` | taxa de saída (30 por padrão). Fronteiras viram quadro inteiro: `round(t*fps)` |
| `output` | `{"width": 1080, "height": 1920}` |
| `clips` | lista de clipes, na ordem de saída |
| `overlays` | opcional: b-roll sobre a timeline (ver abaixo) |

### Campos de cada clipe

| Campo | Significado |
|---|---|
| `id` | rótulo livre (`c1`, `gancho`...) |
| `source` | fonte só deste clipe (relativa ao arquivo da EDL); sobrepõe o `source` de topo. **Imagem é fonte válida**: vira um still mostrado por `out − in` segundos, sem áudio |
| `in`, `out` | segundos da fonte. Em imagem, só a diferença importa |
| `speed` | 0,25 a 4,0 (padrão 1). A duração na saída é `(out − in) / speed` |
| `layout` | `cover` (crop 9:16 em torno de `crop_x`), `split` (quadro inteiro em cima + crop fechado embaixo; recusa fonte já vertical), `fit` (sem crop, barras desfocadas), `lower` (locutor em cover embaixo, de `split_at` até o fim; em cima, cópia desfocada e escurecida; feito para ficar sob overlay `top`) |
| `split_at` | só `lower`: fração da altura onde o locutor começa, 0,25 a 0,6 (padrão 0,45) |
| `caption_y` | opcional, 0 a 1: posição vertical da legenda neste clipe |
| `crop_x` | **centro** do crop como fração da largura da fonte (0 a 1). Número fixo, ou keyframes `[{"t": 0.0, "x": 0.4}, {"t": 2.5, "x": 0.6}]` com `t` em segundos **a partir do início do clipe**. Os keyframes são constantes por trecho: o crop salta no `t` listado, **não desliza**. O crop nunca sai do quadro |
| `zoom` | número fixo (>= 1, padrão 1; fecha o crop) ou rampa linear `{"from": 1.0, "to": 1.10}` ao longo do clipe. Não há outra curva |

### Exemplo completo: montagem com várias fontes

`edl/montagem.json`, com os arquivos em `../clipes/` e `../fotos/`:

```json
{
  "fps": 30,
  "output": {"width": 1080, "height": 1920},
  "clips": [
    {"id": "gancho", "source": "../clipes/praia-a.mp4", "in": 4.20, "out": 7.00,
     "layout": "cover", "crop_x": 0.62, "zoom": {"from": 1.0, "to": 1.10}},
    {"id": "foto-fachada", "source": "../fotos/fachada.jpg", "in": 0, "out": 1.5,
     "layout": "cover", "crop_x": 0.5, "zoom": {"from": 1.0, "to": 1.06}},
    {"id": "camera-lenta", "source": "../clipes/praia-b.mp4", "in": 12.0, "out": 14.0,
     "speed": 0.5, "layout": "cover",
     "crop_x": [{"t": 0.0, "x": 0.35}, {"t": 2.0, "x": 0.65}]},
    {"id": "tela", "source": "../clipes/gravacao-tela.mp4", "in": 0.0, "out": 3.0,
     "layout": "fit"},
    {"id": "fecho", "source": "../clipes/praia-a.mp4", "in": 4.20, "out": 6.0,
     "layout": "cover", "crop_x": 0.62, "zoom": 1.0}
  ]
}
```

Neste exemplo, `camera-lenta` ocupa 4 s na saída (2 s de fonte a 0,5x) e o `crop_x` salta de 0,35 para 0,65 aos 2,0 s do clipe. Os tempos de fonte são reais da mídia: confira cada `in`/`out` na transcrição, na prancha ou no `probe`.

### Overlays (b-roll)

Lista no topo da EDL, aplicada pelo `cut` depois de montar a timeline (um passe). Só vídeo: o áudio do overlay nunca entra; o áudio da base não muda. Corte seco.

| Campo | Significado |
|---|---|
| `source` | vídeo ou imagem (relativo ao arquivo da EDL) |
| `at`, `dur` | início e duração em segundos da **timeline de saída** (depois dos cortes). Sem sobreposição entre overlays; `at + dur` <= fim |
| `region` | `full` (cover no quadro todo), `top` (cover na parte de cima), `card` (mantém a proporção, como cartão de prova; base escurecida/dessaturada/desfocada) |
| `in` | só vídeo: início na fonte (padrão 0). Vídeo curto congela o último quadro |
| `height`, `feather` | `top`: fração da altura (0,2 a 0,7; padrão 0,45) e px de esmaecimento da borda de baixo (padrão 60 a 1920; 0 = seca) |
| `width`, `y` | `card`: fração da largura (padrão 0,78) e centro vertical (padrão 0,36) |
| `zoom`, `crop_x` | número ou `{"from","to"}` (padrão: imagem 1.0→1.08, vídeo 1.0); centro do cover 0 a 1 (padrão 0,5) |

Avisos: clipe `lower` com trecho sem overlay `top`; overlay `top` sobre clipe que não é `lower`.

```json
{"source": "fala.mp4", "fps": 30,
 "clips": [{"id": "c1", "in": 1.0, "out": 9.0, "layout": "lower", "crop_x": 0.5},
           {"id": "c2", "in": 13.3, "out": 25.3, "layout": "cover"}],
 "overlays": [{"source": "praia.mp4", "at": 1.0, "dur": 2.5, "region": "top"},
              {"source": "grafico.jpg", "at": 4.0, "dur": 2.0, "region": "top"},
              {"source": "cena.mp4", "at": 9.0, "dur": 1.5, "region": "full"},
              {"source": "print.png", "at": 13.0, "dur": 3.5, "region": "card"}]}
```

### O que a EDL e o `vedit` NÃO fazem

- **J-cut e L-cut** (áudio e vídeo cortados no mesmo quadro, com micro-fade nas junções): não existe deslocamento de áudio em relação à imagem. É conhecimento de ofício; faça no HyperFrames ou em ffmpeg manual.
- **Pan animado** entre keyframes de `crop_x`: o crop salta. Só `zoom` tem rampa.
- **Transições, texto animado, keying**: os `overlays` entram e saem em corte seco, sem fade. Isso e gráficos são do HyperFrames.
- **Legenda animada**: o `vedit captions` + `burn` entregam legenda estática por bloco. Animada é do HyperFrames.

## 3. JSON de `--guides` (`vedit sheet --guides zona.json`)

Lista de retângulos em **frações do quadro (0 a 1)**: `x`, `y` (canto superior esquerdo), `w`, `h`, e `color` opcional (nome de cor do ffmpeg, como `red`, `yellow`, ou hexadecimal `0xFF8800`; padrão `red`). Também é aceito um objeto `{"rects": [...]}` (ou `{"guides": [...]}`) com a mesma lista. Cada retângulo vira uma caixa de 3 px sobre cada quadro da prancha.

```json
[
  {"x": 0.0, "y": 0.0,  "w": 1.0,  "h": 0.14, "color": "yellow"},
  {"x": 0.0, "y": 0.65, "w": 1.0,  "h": 0.35, "color": "yellow"},
  {"x": 0.08, "y": 0.62, "w": 0.84, "h": 0.07, "color": "red"},
  {"x": 0.30, "y": 0.18, "w": 0.40, "h": 0.22, "color": "0x00FF00"}
]
```

Leitura do exemplo: faixas amarelas = topo 14% e base 35% (zona da interface da plataforma); retângulo vermelho = onde cairá a legenda; verde = onde está o rosto (meça no pior quadro). Se vermelho e verde se cruzam, mexa na legenda (`--y`) ou no enquadramento antes do render.

A conversão de `--y` para pixel: a legenda é centrada na altura `y × 1920` (0,62 é cerca de y 1190 em 1080x1920).

## 4. Pasta da run (`vedit init <pasta>`)

```
<pasta>/
  00-probe.json    # {}; com `init --source <midia>` já vem com o probe; senão: vedit probe <midia> > <pasta>/00-probe.json
  01-words.json    # esqueleto vazio; vedit transcribe -o sobrescreve
  02-digest.md     # vazio; vedit digest -o preenche
  03-moments.json  # {"moments": []}; saída do ve-clip-hunter
  04-edl.json      # EDL vazia (1080x1920, clips: []; fps 30, ou o real da mídia com --source, que também preenche o `source`); uso de um único entregável
  out/             # renders
  qc/              # pranchas e relatórios
```

`vedit init` só cria o que não existe e nunca sobrescreve. Para vários shorts do mesmo vídeo longo, crie `edl/` na run e escreva uma EDL por short (`edl/<id>.json`), com saídas em `out/<id>/` (`corte.mp4`, `leg.ass`, `final.mp4`). `04-edl.json` fica como molde ou para o caso de um entregável só.

## 5. Subcomandos

Todos aceitam `--json` (saída de máquina) e saem com código 0 em sucesso, diferente de 0 em falha.

| Comando | Para quê e opções principais |
|---|---|
| `doctor` | confere ffmpeg/ffprobe e filtros, Python, opcionais, Node, HyperFrames, Chrome; imprime o comando de correção de cada falta |
| `setup [--all]` | cria a `.venv` do pack e instala Pillow + numpy; `--all` inclui faster-whisper e opencv-python |
| `init <pasta> [--source midia]` | cria a pasta da run (seção 4). Com `--source`, faz o probe da mídia, grava `00-probe.json` e preenche `source` (relativo à pasta) e `fps` da EDL |
| `probe <midia> [--no-audio] [--count-frames]` | largura, altura, rotação, fps real, duração, codec, HDR, canais, correlação L/R, loudness e true peak |
| `sheet <video> -o prancha.jpg [--every s] [--start s --end s] [--cols n] [--width px] [--guides zona.json]` | prancha de quadros com carimbo de tempo (se o ffmpeg tem `drawtext`) e retângulos-guia |
| `analyze <video> -o pasta [--scene 0.3] [--region Y0:Y1] [--merge 0.15] [--hook-seconds 6] [--words w.json] [--transcribe]` | teardown de referência: `analise.json`/`analise.md` (cortes, tamanho de plano, loudness, ritmo de fala), `gancho.jpg` e `completo.jpg`; `--region` detecta cortes numa faixa (layout empilhado), `--merge` funde flashes de ~0,1 s; cena detectada é limite inferior |
| `transcribe <midia> -o words.json [--model m] [--lang pt] [--vad]` | faster-whisper com tempo por palavra |
| `digest <words.json> [-o digest.md] [--windows "a-b,c-d"] [--every s]` | texto compacto com carimbo de tempo para o modelo ler |
| `silences <midia> [--noise -35] [--min 0.25] [--start s --end s]` | lista de silêncios |
| `edges <clipe> [--noise -35] [--ms 80]` | falha se os primeiros/últimos 80 ms têm som acima do limiar (palavra truncada) |
| `cut --edl X.json -o saida.mp4 [--preview]` | renderiza UM arquivo com todos os clipes da EDL; `--preview` em 540x960 |
| `reframe --edl X.json [--write]` | **experimental** (exige OpenCV): sugere `crop_x` por locutor ativo; confira na prancha |
| `captions <words.json> --edl X.json -o leg.ass [--srt] [--style viral\|limpo] [--max-words n] [--y 0.62] [--font f] [--highlight "a,b"] [--accent "#FFD400"] [--mode bloco\|palavra\|karaoke] [--case upper\|lower\|sentence\|keep] [--emphasis "a,b"] [--keep-under-cards] [--headline "L1\|L2"] [--headline-y 0.12] [--headline-start 0] [--headline-end S] [--headline-box "#RRGGBB"] [--headline-color "#FFF"] [--keep-punct] [--mute "a-b,c-d"] [--size N] [--outline N] [--shadow N] [--no-bridge]` | legenda ASS com tempos remapeados para o clipe final. `--mode karaoke` pinta a palavra falada; `--emphasis` aumenta palavras (~130%); `caption_y`/`layout: lower` por clipe mudam o `--y`; overlays `card` silenciam a legenda; `--headline` fixa manchete (com `--headline-box` opcional). `--highlight` pinta só as palavras que **você** listar, com a cor de `--accent`. Sem deslocamento automático de tempo. Por padrão remove `.` e `,` do texto exibido (mantém `?` `!` `%` e decimais como `2,5`; `.` final ainda quebra o bloco); `--keep-punct` mantém. `--mute` tira a legenda das janelas dadas (segundos do vídeo final, ex.: onde um motion mostra a frase); `--size/--outline/--shadow` sobrescrevem o estilo; lacunas de menos de 0.35 s entre blocos são fechadas (`--no-bridge` desliga) |
| `burn <video> <leg.ass> -o saida.mp4 [--fallback] [--font f] [--fontsdir DIR]` | queima a legenda (libass, ou fallback Pillow); recodifica o vídeo. `--fontsdir` aponta uma pasta de fontes extras para o libass. Se o ffmpeg do PATH não tem libass, usa automaticamente outro que tenha (`~/.local/bin`, `/opt/homebrew/bin`, `/usr/local/bin`); `VEDIT_FFMPEG` tem prioridade |
| `composite --video base.mp4 --overlay motion.mov [--subs leg.ass] [--fontsdir DIR] [--sfx sfx.wav] [--sfx-gain DB] -o saida.mov\|mp4` | põe a trilha de motion transparente (ProRes 4444 / VP9 alpha, mesma resolução e duração do base) sobre o vídeo, queima a legenda POR CIMA do motion, mistura o SFX ao áudio (`amix normalize=0`) e grava H.264 yuv420p crf 17 com a duração do base (.mov com áudio PCM, .mp4 com AAC). Erro se o overlay não tem alpha ou a resolução difere. Depois: `master` e `verify` |
| `loudness <midia>` | LUFS integrado, true peak, LRA |
| `master <video> -o saida.mp4 [--lufs -14] [--tp -1.5]` | `loudnorm` em duas passadas, 48 kHz, vídeo copiado |
| `extract-audio <video> -o voz.wav` | extrai o áudio de um render para WAV |
| `mix --voice voz.wav --music musica.wav -o mix.wav [--music-lufs -27] [--duck]` | música sob a voz, com ducking por sidechain |
| `mux --video V --audio A -o saida.mp4` | troca o áudio do vídeo: vídeo copiado, áudio ajustado à duração exata do vídeo |
| `metrics --edl X.json [--words words.json]` | palavras/s, cortes/min, maior trecho sem corte |
| `verify <final.mp4> [--platform reels\|tiktok\|shorts\|meta-ads] [--source bruto] [--strict-edges]` | QC final. Som nos primeiros/últimos instantes é **aviso** (música até o fim é normal); `--strict-edges` o transforma em falha, para fala sem música. Limites: Reels 180 s, arquivo TikTok 500 MB |

### Cadeia de áudio padrão (música, ou voz própria)

```bash
vedit cut --edl X.json -o out/corte.mp4                      # vídeo com o áudio da fonte
vedit extract-audio out/corte.mp4 -o out/voz.wav             # a voz exatamente na duração do corte
vedit mix --voice out/voz.wav --music musica.wav -o out/mix.wav --music-lufs -27 --duck
vedit captions words.json --edl X.json -o out/leg.ass --srt
vedit burn out/corte.mp4 out/leg.ass -o out/com-leg.mp4      # burn recodifica o vídeo: faça antes do mux
vedit mux --video out/com-leg.mp4 --audio out/mix.wav -o out/composto.mp4
vedit master out/composto.mp4 -o out/final.mp4
vedit verify out/final.mp4 --platform reels --json           # fala só: acrescente --strict-edges
```

Sem música, pule `extract-audio`, `mix` e `mux`: `cut` → `burn` → `master` → `verify`. Se a narração é um arquivo próprio (anúncio), ela entra no `mix` como `--voice` e o áudio do footage é descartado.
