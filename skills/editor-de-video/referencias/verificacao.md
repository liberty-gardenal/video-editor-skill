> **Leia quando** terminar um render e precisar decidir se o vídeo pode ir ao humano ou à plataforma: que inspeção pega que defeito, o que `vedit verify` significa e como fechar o ciclo de autoavaliação.
> **Princípio:** cada classe de bug só aparece com **um tipo** de inspeção. Rode todos os tipos; "o render existe" não é "o render está certo".

# Verificação

## 1. Qual inspeção pega qual bug

| Inspeção | Pega | Como (exemplo) |
|---|---|---|
| **Prancha por trecho**: quadro 0 + primeiro, meio e último de cada trecho, miniaturas ~180x320 | legenda sobre o rosto, texto fora da zona segura, trecho em layout errado, motion cobrindo a boca | `vedit sheet final.mp4 -o prancha.jpg --every 2 --cols 9 --guides zona.json` |
| **Zoom recortado nas bordas de composição** (borda do cartão, recorte de cabeça, ~700x240 px, 6 quadros) | faixa clara no cabelo, "fantasma" do encosto, halo de matte, spill | `ffmpeg -i final.mp4 -vf "select='eq(n\,a)+eq(n\,b)',crop=700:240:150:1060,tile=2x3" -frames:v 1 zoom.png` |
| **Medição no stem/arquivo final** | junções de silêncio, pausas, LUFS, true peak, cauda de música, duração dos stems | `vedit loudness`, `vedit silences`, `vedit edges`, RMS de janelas de 10 ms no stem |
| **Contagem de quadros** | trecho sem máscara, render curto, duplicação de quadro | `ffprobe -count_frames` x `round(dur*fps)` |
| **Quadro no meio de movimento rápido x quadro parado** | motion blur ausente ou persistente | o do meio deve estar borrado, o parado, nítido |
| **Pico do SFX x movimento** | SFX fora do tempo | pico a poucos ms do meio do movimento; riser acaba na junção (último sample não nulo) |
| **MD5 do áudio** (`ffmpeg -i x.mp4 -map 0:a -f md5 -`) | motion/master que tocou no áudio congelado | igual ao da fonte quando o áudio não deve mudar |
| **Bitrate por trecho** | plano explodindo (grão incompressível) | ver `motion.md` |

- Miniatura **não** mostra defeito de poucos pixels (o humano achou a faixa no cabelo assistindo). Faça zoom em todas as regiões de composição.
- Defeitos de máscara: varra **todos** os quadros (resíduo ao lado da cabeça, "cabeça perdida" = alfa > 0,6 no original e < 0,3 no limpo), não amostras.
- Pranchas com `fps=1` a partir de `-ss` deslocam 1-2 s; use `fps=2` ou `fps=4` na janela quando o ponto exato importa. `tile=8x1` pega os 8 **primeiros** quadros; distribua com `select='not(mod(n\,N))'`.

## 2. `vedit verify` (obrigatório antes de entregar)

`vedit verify final.mp4 --platform reels|tiktok|shorts|meta-ads --source bruto.mp4 --json`. Sai com código != 0 se reprovar. O que cada falha significa:

| Falha | Significa | Ação |
|---|---|---|
| resolução/aspecto != 1080x1920 | export errado ou crop faltando | reexportar; ver `plataformas.md` |
| fps variável ou != do plano | EDL em fps diferente do fonte, ou VFR | normalizar com `fps=` e conferir `avg_frame_rate` |
| codec/pix_fmt != H.264 `yuv420p` | player/plataforma pode recusar | reencodar |
| sem `faststart` | início lento/falha em upload | remuxar com `-movflags +faststart` |
| duração fora do limite da plataforma | passa do teto ou do mínimo do formato | encurtar ou escolher outro destino |
| LUFS/true peak fora (alvo -14 / -1,5) | mix errado ou `loudnorm` sem `aresample` | `vedit master` (ver `audio.md`) |
| som nas bordas do áudio | aviso no `verify`: palavra truncada (fala) ou só música até o fim (normal). `--strict-edges` o torna falha; use em fala sem música | ajustar in/out; `vedit edges` |
| quadros pretos ou congelados | falha de composição, cena sem máscara, clone de fim | achar o intervalo, corrigir fonte |
| A/V com durações diferentes | stem curto/longo (ex.: música acabou antes) | `vedit mux` (ajusta o áudio à duração exata do vídeo) |

`verify` não vê o que é editorial (rosto cortado, legenda errada, sentido alterado). Esses defeitos só saem com os olhos (seção 1).

## 3. Autoavaliação no arquivo final (nunca na fonte)

Regras de correção (quebrar qualquer uma é falha silenciosa):
1. Legenda é a última camada.
2. Fade de ~30 ms em toda emenda de áudio.
3. Nunca cortar dentro de palavra; toda borda toca uma fronteira de palavra.
4. Folga de 30-200 ms em toda borda (o ASR deriva 50-100 ms).
5. Legenda em tempo de **saída**.

Inspeção: em cada emenda (±1,5 s), em 0-2 s, no fim e em 2-3 pontos do meio, procure salto, flash, legenda sobre rosto ou escondida, palavra cortada. Meça o áudio (não presuma). Compare a duração com o plano. Para perfis com gancho: proposta em até 1,5-3 s, nada parado mais de ~8 s, destaque dentro da cadência esperada.

**Laço de correção:** falhou -> corrige -> renderiza -> reavalia. **No máximo 3 passadas**; se sobrar problema, relate em vez de girar em loop. Só mostre o clipe depois de passar (ou diga o que sobrou).

## 4. Revisão cega

Para clipes que serão publicados, use um revisor **sem contexto** do trabalho: recebe só o arquivo (ou a linha do tempo reconstruída), a transcrição do clipe e a duração. Não envie score anterior, justificativa, título promocional nem quem escolheu o trecho. Instrução: **tentar derrubar**, não elogiar. Saída: veredito, problemas ranqueados com timecode e evidência (quadro, nível de áudio), as 5 correções a fazer primeiro. Falha relevante volta à reconstrução.

## 5. "Meça, não estime"

Revisor (humano ou agente) não escreve número que não mediu: nem "parece uns 2 s parado", nem "o áudio está uns -14". Métrica global engana: um rótulo de 270x90 px num quadro 1080x1920 move < 0,2% dos pixels e aparece como "parado" na média; meça **dentro da caixa do elemento**. Estado de módulo/cache pode vazar entre passadas (zere). Rubrica fechada, resposta por escrito, evidência anexada.

## 6. Checklist pré-entrega

- [ ] `vedit verify --platform ...` sem falhas
- [ ] Prancha por trecho vista; zoom nas bordas de composição feito
- [ ] Primeiro e último quadro olhados (`ffmpeg -ss 0.05 -frames:v 1`; o último, ~0,2 s antes do fim)
- [ ] LUFS e true peak medidos no arquivo final; música audível até o fim
- [ ] Contagem de quadros e duração batem com o plano
- [ ] Nenhuma legenda sobre rosto, nada fora das zonas seguras
- [ ] Textos inventados e números listados para o humano revisar
- [ ] Humano **ouviu** o áudio (o agente não ouve)
- [ ] Relatório gerado por script a partir de `edl.json` e logs, com a lista do que o próprio agente reprovaria (lista vazia = não olhou)
- [ ] Arquivos entregues numa pasta com nome descritivo, caminho informado ao humano

## 6b. Snippets de inspeção (quando nenhum `vedit` cobre)

```bash
# silêncio nas bordas de um clipe (precisa haver silêncio nas pontas)
ffmpeg -i clipe.mp4 -af "silencedetect=noise=-35dB:d=0.1" -f null -

# loudness e true peak do arquivo final
ffmpeg -i final.mp4 -af ebur128=peak=true -f null -

# primeiro e último quadro de verdade
ffmpeg -ss 0.05 -i final.mp4 -frames:v 1 ini.jpg
ffmpeg -sseof -0.3 -i final.mp4 -frames:v 1 fim.jpg

# contagem real de quadros e fps médio (não a base de tempo)
ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries stream=nb_read_frames,avg_frame_rate,r_frame_rate -of default=nw=1 final.mp4

# quadros pretos e congelados
ffmpeg -i final.mp4 -vf "blackdetect=d=0.2:pix_th=0.05,freezedetect=n=-60dB:d=0.5" -an -f null -
```

Confira cada comando contra a versão instalada (`vedit doctor`); filtros variam entre builds.

## 7. Relatório de auto-rejeição

Termine toda entrega listando o que **você mesmo** reprovaria: algum corte abre em conector? trunca palavra? passa de 90 s sem tentativa de versão curta? dois cortes com > 30% em comum? legenda perto do rosto? número não verificado na tela? Se nada aparecer, volte a olhar.

## Fontes
- Netflix, "Timed Text Style Guide: General Requirements", https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617 (aberta em 2026-11; base para duração mínima de legenda usada nas checagens).
- Limites de plataforma usados por `vedit verify`: ver `plataformas.md` e as fontes dele.
- Protocolo de inspeção, revisão cega e rubricas: prática operacional própria.
