# `vedit` — referência da CLI

Contrato único entre a skill (que decide) e os scripts (que medem e renderizam).
O modelo nunca estima um valor que um comando daqui calcula.

Lançador: `bin/vedit <subcomando>` (bash; resolve o Python ≥ 3.10 nesta ordem: venv em
`$CLAUDE_PLUGIN_DATA/venv` (se a variável existir), venv `.venv/` do repositório, Python do
sistema; `vedit doctor` mostra qual está em uso). Código em `lib/vedit/` (pacote Python, `python -m vedit`).
Núcleo só com biblioteca padrão + `ffmpeg`/`ffprobe`. Opcionais, importados sob demanda
com erro claro e instrução de instalação: `faster-whisper` (transcribe), `Pillow` + `numpy`
(legenda sem libass), `opencv-python` (reframe).

Variáveis de ambiente: `CLAUDE_PLUGIN_DATA` (onde `setup` cria a venv: `$CLAUDE_PLUGIN_DATA/venv`);
`VEDIT_DEBUG=1` mostra o traceback de erros inesperados; `VEDIT_FFMPEG` / `VEDIT_FFPROBE` escolhem os binários; sem elas,
usa o `ffmpeg` do PATH (se houver vários, prefere o que tem libass). Logs longos ficam ao lado
da saída (`<saida>.ffmpeg.log`); em falha do ffmpeg mostram-se as últimas 30 linhas.

Todo comando: sai com código 0 em sucesso e ≠ 0 em falha; aceita `--json` para saída
de máquina (nos que já imprimem JSON — `probe`, `silences`, `metrics`, `reframe` — é um
no-op; `digest --json` embrulha o texto em `{"digest": ...}`); nunca decodifica o vídeo inteiro
se uma janela (`--start/--end`) resolve. Erros previstos (EDL malformada, tempo inválido, fonte
inexistente) viram uma única mensagem em pt-BR com código 1; erro inesperado imprime uma
linha curta e "rode com VEDIT_DEBUG=1 para o traceback".

Toda mídia que o `vedit` escreve (`cut`, `burn`, `master`, `mux`) sai com o áudio do mesmo
comprimento do vídeo (diferença < 40 ms, no máximo um quadro de áudio AAC): o áudio é
preenchido/cortado para a duração exata do vídeo (`apad`/`atrim`, `-t`).

## Formatos

**words.json**
```json
{"language": "pt", "duration": 123.4,
 "words": [{"w": "palavra", "t": 12.28, "e": 12.54}]}
```
Tempos em segundos da mídia transcrita.

**edl.json** — fonte única de verdade do corte
```json
{"source": "bruto.mp4", "fps": "30000/1001",
 "output": {"width": 1080, "height": 1920},
 "clips": [{"id": "c1", "in": 12.30, "out": 25.10,
            "layout": "cover", "crop_x": 0.5, "zoom": {"from": 1.0, "to": 1.10}},
           {"id": "foto", "source": "capa.jpg", "in": 0, "out": 2},
           {"id": "c2", "source": "outra.mp4", "in": 3, "out": 7, "speed": 0.5}]}
```
- `fps`: número (`25`, `29.97`) ou fração (`"30000/1001"`); as duas formas valem em todo
  lugar. Sem `fps`, usa o fps real da primeira fonte de vídeo (probe). `init --source` grava o
  fps real (fração para NTSC). `cut`, `captions`, `metrics` e `reframe` usam o mesmo resolvedor.
- `in`/`out` em segundos da fonte do clipe; o render arredonda para quadro inteiro
  (`round(t*fps)`) e valida `in` e `out` contra a duração da fonte (erro em pt-BR com o `id`).
- `source` por clipe sobrescreve o `source` do topo, que fica opcional se todo clipe tiver o
  seu. Caminhos relativos valem a partir da pasta do arquivo da EDL. Resoluções e fps
  diferentes são normalizados para o fps e o tamanho de saída da EDL.
  - Imagem (`.jpg .jpeg .png .webp .heic`; HEIC só se o ffmpeg decodificar) vira um still
    repetido por `out − in` segundos, com áudio silencioso. Fonte sem áudio também recebe
    áudio silencioso.
  - Legendas: as palavras do `words.json` valem só para a fonte transcrita (o `source` do
    topo, ou o do primeiro clipe, ou o `source` gravado no `words.json`); clipes de outra
    fonte ou imagens ficam sem legenda.
- `speed` 0.25–4.0 (padrão 1): vídeo por `setpts`, áudio por `atempo` encadeado (tom
  preservado); a duração do clipe na saída é `(out − in) / speed`, arredondada para quadros.
- `layout`: `cover` (crop 9:16 ancorado em `crop_x`, 0–1), `split` (quadro inteiro em cima +
  crop fechado embaixo), `fit` (sem crop, barras desfocadas) ou `lower` (o locutor em cover na
  parte de baixo, de `split_at` até o fim, respeitando `crop_x`/`zoom`; em cima, cópia
  desfocada e escurecida do mesmo plano, nunca preto; feito para ficar sob um overlay `top`).
  `split` recusa fonte já vertical.
- `split_at` (só `lower`): fração da altura onde o locutor começa, 0.25–0.6 (padrão 0.45).
  `caption_y` (opcional, 0–1): posição vertical sugerida da legenda neste clipe (lida pelo `captions`).
- `crop_x` é a posição do **centro** do crop como fração da largura da fonte (0–1); o crop
  nunca sai do quadro (é limitado nas bordas). Pode ser lista `[{"t": 0.0, "x": 0.4}, ...]`
  (todo item precisa de `t` e `x`), com `t` em segundos **a partir do início do clipe**; vale
  constante por trecho e só muda nos tempos listados (sem pan animado entre os keyframes).
- `zoom` ≥ 1 (até 4): número = crop estático (no `split` aperta o crop de baixo); ou
  `{"from": 1.0, "to": 1.10}` = rampa linear ao longo do clipe, suave (frame redimensionado a
  2× e `zoompan` com expressão por quadro). Vale onde há crop: `cover` e a metade de baixo do
  `split`; no `fit` é ignorado.

**`overlays`** (topo da EDL) — camada de b-roll sobre a timeline já montada, no mesmo `cut`
(um único passe de encode, sem geração extra). Só vídeo: o áudio do overlay nunca é usado e o
áudio/duração da base não mudam. Entrada/saída em corte seco.
```json
{"overlays": [{"source": "b.mp4", "at": 3.2, "dur": 2.4, "region": "top",
               "in": 0, "height": 0.45, "feather": 60, "zoom": 1.0, "crop_x": 0.5},
              {"source": "print.png", "at": 14, "dur": 3.5, "region": "card",
               "width": 0.78, "y": 0.36}]}
```
- `source` (vídeo ou imagem; caminho relativo como o dos clipes), `at` (segundos da timeline
  de saída, já com cortes), `dur`. `region`: `full` (cover no quadro todo), `top` (cover na parte
  de cima, `height` = fração, padrão 0.45, 0.2–0.7, borda de baixo esmaecida por `feather` px a
  1920 de altura, padrão 60, 0 = borda seca) ou `card` (mantém a proporção da fonte, `width` =
  fração da largura, padrão 0.78; centro em `y`, padrão 0.36; a base fica escurecida, dessaturada e
  desfocada durante o overlay).
- `in` (só vídeo, padrão 0); vídeo mais curto que `dur` congela o último quadro. `zoom`: número
  ou `{"from","to"}` ao longo do overlay (padrão: still 1.0→1.08, vídeo 1.0); `crop_x` 0–1 (padrão 0.5).
- Overlays não se sobrepõem no tempo (erro nomeando os dois) e `at + dur` não passa do fim da
  timeline. Avisos (não falham): clipe `lower` com trechos sem overlay `top`; overlay `top` sobre
  clipe que não é `lower` (cobre o rosto). Cada overlay encarece o render (30 funcionam).

## Subcomandos

| Comando | Faz |
|---|---|
| `doctor [--json]` | Mostra o interpretador/venv em uso. Confere ffmpeg/ffprobe (e se há filtros `ass`/`subtitles`, `drawtext`, `loudnorm`, `arnndn`), Python, opcionais, Node/npx, HyperFrames (`npx hyperframes --version` ou plugin do Claude Code instalado), Chrome. Para cada falta, imprime o comando de correção por sistema (macOS/Linux/Windows-WSL). Sem `zscale`, avisa que vídeo HDR será convertido sem tone mapping adequado (imagem lavada/contrastada) e como corrigir (ffmpeg com libzimg). Código ≠ 0 só se faltar algo obrigatório (Python ≥ 3.10, ffmpeg, ffprobe); filtros, opcionais, HyperFrames e Chrome ausentes são apenas avisos. |
| `setup [--all]` | Cria a venv (`$CLAUDE_PLUGIN_DATA/venv` se a variável existir, senão `.venv/`) e instala Pillow e numpy (os leves, para uma venv existente nunca esconder os pacotes do sistema); `--all` acrescenta faster-whisper e opencv-python. |
| `init <workspace> [--source midia]` | Cria a pasta da run (com `--source`, grava `00-probe.json` e preenche a EDL com o caminho relativo à pasta e o fps real): `00-probe.json 01-words.json 02-digest.md 03-moments.json 04-edl.json out/ qc/`. |
| `probe <midia>` | JSON: largura, altura, rotação, `avg_frame_rate` real (não a base de tempo), nb_frames, duração, codec, pix_fmt, HDR (transfer `arib-std-b67`/`smpte2084`), canais de áudio, correlação L/R, loudness integrado e true peak. `--no-audio` pula as medições de áudio; `--count-frames` conta quadros decodificando. |
| `sheet <video> -o prancha.jpg [--every 5] [--start s --end s] [--cols 4] [--width 480] [--guides zona.json]` | Prancha de quadros (contact sheet) com timestamp; `--guides` (lista JSON de `{x,y,w,h,color?}` em frações 0–1) desenha safe zones/faixa de legenda. O timestamp só aparece se o ffmpeg tiver `drawtext`. |
| `analyze <video> -o pasta [--scene 0.3] [--region Y0:Y1]... [--merge 0.15] [--hook-seconds 6] [--words words.json] [--transcribe] [--json]` | Teardown de um vídeo de referência. Grava `analise.json` (ficha técnica, `cuts` por `select=gt(scene,T)`, estatísticas de plano, loudness/true peak/LRA e, com `--words` ou `--transcribe`, palavras/s, maior pausa, primeiras palavras e se a fala começa em até 0,5 s), `gancho.jpg` (primeiros `--hook-seconds` a cada 0,5 s), `completo.jpg` (vídeo inteiro, ~40–64 quadros, passo mínimo 1 s) e `analise.md` com checklist do que a métrica não mede (legenda, layout, título fixo, inserts, final). `--merge` (padrão 0.15 s; 0 desliga) funde detecções próximas (flash/blur de ~0,1 s contam em dobro) em um evento e `shots` traz `raw_detections` ao lado de `cuts`. `--region` (repetível, frações da altura, ex. `0:0.48`) roda a mesma detecção num recorte da faixa e grava `regions: [{y0, y1, cuts, shots}]`; em layout empilhado a tela cheia fica cega a cortes só da janela de cima. Sem `--region` e com menos de 1 corte a cada 20 s, testa sozinho metade de cima (0:0.5) e de baixo (0.5:1). Não abaixe `--scene` de 0.3: gera falsos cortes de zoom/gesto. A detecção de cena é um limite inferior: não vê dissolvências, whip-pans nem motion graphics contínuos. |
| `transcribe <midia> -o words.json [--model] [--lang pt] [--vad]` | faster-whisper com `word_timestamps`; modelo padrão `large-v3` até 10 min de mídia, senão `small`; refina o início das palavras por energia. |
| `digest <words.json> [-o digest.md] [--windows "a-b,c-d"] [--every 15]` | Texto compacto com carimbo de tempo por linha para o modelo ler (nunca o JSON cru). |
| `silences <midia> [--noise -35] [--min 0.25] [--start s --end s]` | Lista de silêncios (JSON). |
| `edges <clipe> [--noise -35] [--ms 80] [--json]` | Confere se os primeiros e últimos 80 ms ficam abaixo de −35 dB RMS (palavra truncada = falha, código 1; use para decidir pelo ouvido se é fala ou só música/ambiente). |
| `cut --edl edl.json -o saida.mp4 [--preview]` | Renderiza a EDL: recodifica sempre (nunca `-c copy`), várias fontes/imagens/`speed`/rampa de `zoom`, micro-fades de áudio nas junções (10 ms, mesmo quadro no áudio e no vídeo), crop/layout vertical, HDR→SDR automático, `--preview` em 540x960. Valida `in`/`out` contra a fonte. |
| `reframe --edl edl.json [--write]` | **(experimental)** (opcional, OpenCV) amostra a 3 fps (na fonte de cada clipe; imagens ficam em 0.5), detecta rostos e locutor ativo por correlação boca×energia do áudio; grava `crop_x` por subsegmento na EDL. |
| `captions <words.json> --edl edl.json -o legenda.ass [--srt] [--style viral\|limpo] [--max-words N] [--y 0.62] [--font Arial] [--highlight "p1,p2"] [--accent "#FFD400"] [--mode bloco\|palavra\|karaoke] [--case upper\|lower\|sentence\|keep] [--emphasis "p1,p2"] [--keep-under-cards] [--headline "L1\|L2"] [--headline-y 0.12] [--headline-start 0] [--headline-end S] [--headline-box "#RRGGBB"] [--headline-color "#FFFFFF"]` | Agrupa por pontuação/sentido, remapeia os tempos para o clipe final, sem sobreposição e sem bloco atravessando corte. `--max-words` padrão: 3 (`viral`) ou 6 (`limpo`); `--srt` grava `<saida>.srt` ao lado. `--y` padrão 0.62 nos dois estilos. `--highlight` pinta na cor `--accent` (padrão `#FFD400`) as palavras listadas (sem diferenciar caixa nem acento, palavra inteira, pontuação ignorada), por tags de override ASS em linha (cores ASS são BGR; o comando converte). O SRT não leva cor.`--mode`: `bloco` (padrão), `palavra` (uma palavra por bloco) ou `karaoke` (o bloco fica na tela e a palavra falada ganha a cor `--accent`; `--highlight` não pinta nesse modo). `--case`: padrão `upper` no `viral` e `keep` no `limpo`; `sentence` capitaliza só o início de cada frase. `--emphasis` desenha as palavras listadas a ~130% (soma-se ao `--highlight`; mesma regra de correspondência). Na EDL, um clipe com `caption_y` (0–1) usa essa posição no lugar de `--y`; com `layout: "lower"` e sem `caption_y`, usa o `split_at` do clipe (padrão 0.45). Overlays `region: "card"` da EDL silenciam a legenda enquanto estão na tela (`--keep-under-cards` desliga isso). `--headline` fixa uma manchete (`\|` quebra linha) em estilo próprio, maior que a legenda, em `--headline-y` (padrão 0.12) de `--headline-start` (padrão 0) até `--headline-end` (padrão: vídeo inteiro); `--headline-box` põe uma caixa opaca atrás de cada linha, sem ela leva contorno; linhas longas encolhem/quebram para caber nas margens laterais. Sem libass o `burn` desenha tudo isso via Pillow (tamanho de palavra enfatizada e caixa incluídos; alinhamento tipográfico fino pode diferir levemente). |
| `burn <video> <legenda.ass> -o saida.mp4 [--fallback] [--font]` | Queima a legenda: libass se houver; senão, fallback Pillow + overlay (fluxo de PNGs transparentes via demuxer `concat`, um único `overlay`). `--fallback` força o caminho Pillow. O fallback também pinta só a palavra destacada (lê as tags `\c` do `.ass`). O áudio é copiado e cortado no comprimento do vídeo. |
| `loudness <midia>` | LUFS integrado, true peak, LRA. |
| `master <video> -o saida.mp4 [--lufs -14] [--tp -1.5]` | `loudnorm` em duas passadas + `aresample=48000`, vídeo copiado; áudio ajustado ao comprimento exato do vídeo. |
| `extract-audio <video> -o voz.wav [--start s --end s]` | Extrai o áudio em WAV PCM 24 bits, 48 kHz, mantendo os canais da fonte (estéreo continua estéreo); janela opcional. |
| `mux --video V --audio A -o saida.mp4` | Copia o vídeo, codifica o áudio em AAC 48 kHz 192k, preenche/corta o áudio para a duração exata do vídeo, `+faststart`. Fecha o fluxo voz → `mix` → `mux` → `master`. |
| `mix --voice v.wav --music m.wav -o mix.wav [--music-lufs -27] [--duck]` | Música sob a voz com ducking por sidechain, stems alinhados em 48 kHz e duração exata. |
| `metrics --edl edl.json [--words words.json]` | Palavras/s, cortes/min, maior trecho sem corte, duração; com `overlays`: quantidade, por minuto e por 10 s, e o maior trecho sem mudança visual (corte ou início/fim de overlay). |
| `verify <final.mp4> [--platform reels\|tiktok\|shorts\|meta-ads] [--source bruto] [--strict-edges] [--json]` | QC final: resolução, fps, codec, pix_fmt, faststart, duração × limites da plataforma, LUFS/true peak, bordas de áudio, quadros pretos/congelados, A/V com mesma duração (falha acima de 80 ms). Som alto nas bordas é **aviso** (música/ambiente na borda é aceitável; palavra truncada não); `--strict-edges` transforma em FALHA. Relatório em pt-BR (`--json` para máquina). Sai com 1 se houver FALHA; avisos saem com 0. Limites por plataforma em `lib/vedit/platforms.py` (padrões, confirme na plataforma): Reels até 180 s, TikTok até 500 MB. |

Especificações de entrega padrão: 1080x1920, H.264 high, yuv420p, `+faststart`,
AAC 48 kHz 192k, −14 LUFS / −1,5 dBTP.

## O que o `vedit` não faz

- **J-cut / L-cut**: não há. Áudio e vídeo são cortados no mesmo quadro, com micro-fade de
  10 ms em cada junção.
- **Pan animado entre keyframes de `crop_x`**: não há. O crop é constante por trecho e só
  muda nos tempos listados (a rampa existe apenas para `zoom`).
- **Transições (fades, wipes), texto animado, keying/recorte de fundo**: não há; os overlays
  entram e saem em corte seco. Isso, e composição além de `overlays`, é do HyperFrames
  (`docs/hyperframes.md`).
