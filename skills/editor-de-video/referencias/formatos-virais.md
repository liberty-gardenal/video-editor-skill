> **Leia quando** o pedido for "nesse estilo", "como esses vídeos", ou quando for escolher o formato de um vertical (apresentador com b-roll, corte de podcast, narração sobre imagens, opinião com montagem) e montar layout, legenda, manchete e inserts.
> **Comandos:** `vedit analyze`, `vedit cut` (EDL com `lower` e `overlays`), `vedit captions` (`--mode`, `--case`, `--emphasis`, `--headline`...), `vedit burn`. Estilos animados ficam no HyperFrames.
> **Evidência:** tudo aqui é **prática observada** em vídeos publicados, não causa comprovada de retenção. Detalhes na seção 1.

# Formatos virais observados (receitas)

## 1. De onde vem e o que isso vale

Fonte: desmontagem de 12 verticais em pt-BR (quadros, detecção de cortes, loudness; o áudio **não** foi ouvido; **não** há dado de desempenho). Duração de 11 a 179 s, cinco entre 100 e 180 s. Logo:

- Leia "observado em N de 12 referências" como **o que se vê em vídeos que circularam**, nunca como "isto causa retenção". Quem publicou pode ter acertado por outro motivo (tema, rosto, distribuição).
- 12 vídeos não dão estatística. Use como repertório de receitas, escolha por **função** (o que o recurso resolve neste conteúdo) e valide publicando, como em `psicologia-do-feed.md`.
- Nada aqui revoga as regras de `cortes-e-ritmo.md` e `motion.md` ("todo corte serve a uma batida"). As receitas são formas de cumpri-las, não substitutos.
- Estudar o estilo não é reusar o material: copie a **técnica** (layout, cadência, tipografia), nunca imagens, falas, marcas ou rostos alheios.

## 2. Frequência (n de 12)

| Item observado | n |
|---|---|
| **Janela de b-roll** no topo (~45% da altura), fala embaixo (~55%), central no vídeo | 5 |
| Formato "apresentador com b-roll em janela" (subconjunto da linha acima) | 3 |
| Corte de podcast/entrevista (punch-in alternado) | 4 |
| Talking head longo sem corte (40-60 s) | 2 |
| Narração sem rosto sobre imagens/memes/filmes | 1 |
| Explicador totalmente animado, sem cortes | 1 |
| Opinião com montagem de b-roll e faixa fixa | 1 |
| Selfie de 11 s na mão com whip-pans | 1 |
| Manchete/faixa fixa na tela | 6 |
| Manchete já no quadro 0 | 7 |
| Legenda com posição que segue o layout | 7 |
| Legenda de 1 palavra por bloco (caixa alta, troca a cada 0,3-0,5 s) | 3 |
| Legenda com salto de **tamanho** em número/frase-chave | 3 |
| Legenda com palavra ativa acesa (karaoke) | 1 |
| Legenda sem nenhum destaque | 5 |
| Legenda em frase/minúscula | 6 (caixa alta: 5) |
| Montagem de b-roll em tela cheia como gancho (3+ trocas nos 3 s) | 2 |
| Cartão de prova (print/estatística) | 1 com ~9 cartões; 1 com cartão de referência no gancho |
| Sem CTA nem cartão final | 9 |
| CTA verbal por palavra-chave nos comentários | 1 |
| Cartão final com QR/logo | 1 |
| Marca d'água pequena persistente | 1 |
| Conteúdo 3:4 em tela preta 9:16 | 1 |
| Loudness entre -13,2 e -17,1 LUFS (sete dentro de ±0,5 de -14) | 12 |
| True peak acima de -1 dBTP (um em +0,2) | 6 |

Mediana de plano nas peças editadas: ~1,7 a 3,2 s. Fala de 2,5 a 4,0 palavras/s. Cortes concentrados nos 5 primeiros segundos em 3 vídeos.

## 3. Receitas

Cada receita: quando usar, layout, legenda, cadência de inserts, gancho, como montar no `vedit`, o que exige HyperFrames.

### 3.1 Apresentador com janela de b-roll (5 de 12)

> Em teste real com fonte de podcast, esta receita feita só no `vedit` (janela desfocada
> esperando b-roll, manchete em caixinha) foi reprovada. Para podcast/entrevista, o padrão
> aprovado é tela cheia + punch-in + trilha de motion: `padrao-excelencia.md`.

- **Quando**: alguém explica, opina ou narra coisas **nomeáveis** (pessoas, lugares, produtos, telas, números). Sem coisa a mostrar, não use: janela com imagem genérica é o "filler" da seção 4.
- **Layout**: janela de b-roll em cima (~45% da altura), apresentador no ~55% de baixo, costura em degradê suave (~0,45 da altura). Alterna com apresentador em tela cheia nos cortes; cobertura da janela de 40 a 100% do tempo.
- **Cadência**: o conteúdo da janela troca a cada 1,5-3 s (4 a 6 trocas por 10 s nos trechos densos). Cada imagem **aparece quando a coisa é nomeada** (gatilho por palavra-chave, mesma âncora ±3 quadros de `motion.md`, seção 2).
- **Legenda**: em cima da costura (y ≈ 0,43-0,50) enquanto o layout é empilhado; `vedit captions` já assume a costura nos clipes `lower`.
- **Gancho**: manchete no quadro 0 (7 de 12 têm) ou b-roll já na primeira frase.
- **No `vedit`**: clipes `lower` + lista `overlays` com `region: "top"`. Exemplo na seção 5.1.
- **HyperFrames**: cantos arredondados, sombra, entradas animadas, picture-in-picture com chips.

### 3.2 Corte de podcast/entrevista com punch-in alternado (4 de 12)

- **Quando**: dois ou mais falantes, fala densa. Corte por fala, não por contagem de segundos.
- **Layout**: `cover`; alterna enquadramento normal e punch-in de ≈1,2-1,3x a cada ~2,5-4 s. Em `cortes-e-ritmo.md` o padrão continua 1,05-1,15 e "só com razão"; o 1,2-1,3x é o que se vê em podcast onde o plano é aberto e o rosto pequeno. Alterne nas fronteiras de turno ou frase.
- **Legenda**: bloco de 2-4 palavras, y padrão (0,62) ou abaixo do queixo; manchete fixa no topo ou na costura.
- **Gancho**: manchete no quadro 0 + a frase mais forte primeiro (ver `psicologia-do-feed.md`, seção 5).
- **No `vedit`**: clipes alternando `zoom` 1,0 e 1,25 (cada troca é um clipe), `--headline`. Exemplo na seção 5.2.
- **HyperFrames**: manchete animada (digitada palavra a palavra), troca de cor por falante.

### 3.3 Narração sem rosto sobre imagens (1 de 12)

- **Quando**: roteiro/narração seu, material de imagem licenciado ou próprio. Playbook: `motion-de-narracao.md` (ou `montagem-na-batida.md` sem fala).
- **Layout**: tela cheia, trocas curtas (0,7-2 s por imagem), cada imagem ilustra a palavra dita.
- **Legenda**: bloco ou palavra, caixa alta é comum; y 0,62-0,78.
- **No `vedit`**: EDL com stills como fonte (`source` imagem) + `captions`. Memes e trechos de filme são material de terceiros: confirme direitos antes.

### 3.4 Explicador totalmente animado, sem cortes (1 de 12)

HyperFrames (`/hyperframes:faceless-explainer`, `/hyperframes:motion-graphics`). O `vedit` entra só no master e no `verify`. Aqui o "ritmo" vem de movimento dentro da cena, não de corte; transições radiais e linhas de velocidade também são HyperFrames.

### 3.5 Opinião com montagem de b-roll e faixa fixa (1 de 12)

- **Layout**: tela cheia, montagem de palavras-chave (inserts de 0,7-2 s) sobre a fala; faixa/manchete fixa o vídeo todo.
- **Gancho**: 3 ou mais trocas de imagem nos 3 primeiros segundos (observado em 2 de 12; dos 12, só estes dois usam o b-roll em tela cheia como gancho).
- **No `vedit`**: `overlays` com `region: "full"`, `--headline` com `--headline-start 0` e sem `--headline-end`.

### 3.6 Talking head longo sem corte (2 de 12)

Dois vídeos seguram 40-60 s (um de 63 s com um único corte) só com legenda e gesto. Serve quando a **entrega** carrega (história, emoção, humor): não corte por reflexo. Sem entrega forte, use 3.1 ou 3.2. Compatível com `cortes-e-ritmo.md` (pausa com tensão é conteúdo).

### 3.7 Selfie curta com whip-pans (1 de 12)

Whip-pan aqui é **técnica de câmera** (o gesto de virar o celular na gravação), não efeito de pós. `motion.md` continua proibindo whip-pan como transição de pós. Se o material já vem assim, mantenha; não simule.

### 3.8 Cartões de prova (1 de 12 com ~9; outro com cartão de referência no gancho)

- **Quando**: você afirma algo que tem print, documento, estatística ou manchete. Mostra a prova quando ela é dita.
- **Forma observada**: cartão ~75% da largura, centro em y ≈ 0,30-0,36, base escurecida, em cinza e desfocada; 1,5-3 s por cartão; às vezes número circulado.
- **No `vedit`**: `overlays` com `region: "card"` (`width`, `y`); o `captions` cala os blocos sob o cartão. A base escurecida/cinza/desfocada, número circulado, cantos arredondados e sombra **não** são do `vedit`: HyperFrames.
- **Texto do cartão é de terceiros ou seu?** Print de página real: confirme que pode usar e que o dado está certo (`motion.md` pede número verificável).
- **Defeito observado**: a legenda corrida colidindo com o texto do próprio cartão. Por isso o `captions` cala sob cartões; mantenha assim.

## 4. O que NÃO copiar

| Observado | Por que não |
|---|---|
| Picos de true peak acima de -1 dBTP (6 de 12; um em +0,2) | clip no AAC e reprovação no `verify`; mantenha -14 LUFS e -1,5 dBTP (`audio.md`) |
| Legenda sobre o texto do cartão de prova | duas tipografias brigam (`legendas.md`, seção 8; armadilha 46) |
| Imagem de enchimento ocupando meia tela | meia tela sem informação; ver `enquadramento-vertical.md` (nunca meia tela vazia) |
| Erro de transcrição queimado na legenda | falha de QC; confira cada texto contra o áudio |
| Parar no meio do pensamento como padrão (9 de 12 sem CTA, vários cortam seco) | observado, mas fechamento é critério de `psicologia-do-feed.md`; só pare assim por escolha editorial declarada |
| Texto ocluído atrás do sujeito por máscara | efeito de composição; `vedit` não faz, HyperFrames faria com matte |
| Marca d'água de terceiros, rosto ou clipe de famoso | direitos e imagem; estude a técnica, não reuse |
| Letterbox 3:4 em tela preta | só se a fonte for realmente 3:4 e o resultado for pedido; padrão da skill é preencher o 9:16 |

## 5. Montagem no `vedit`

Estas receitas dependem de campos de EDL e flags de `captions`. Confira em `vedit cut --help`, `vedit captions --help` e em `formatos.md`.

Campos úteis:

- Clipe `layout: "lower"` com `split_at` (padrão 0,45): o apresentador fica na região de baixo, a de cima fica livre para `overlays`. `caption_y` por clipe; nos clipes `lower` o padrão da legenda é a costura.
- `overlays` (topo da EDL): `[{"source", "at", "dur", "region": "full"|"top"|"card", "in", "height", "feather", "zoom", "crop_x", "width", "y"}]`. `at` é tempo de **saída**; é camada só de vídeo sobre a linha do tempo montada; o áudio base não é tocado; **overlays não podem se sobrepor no tempo**. Renderizado pelo `vedit cut`.
- `region: "top"` só sobre clipe `lower` (senão cobre o rosto); `"full"` cobre tudo; `"card"` é o cartão de prova.

### 5.1 Apresentador com janela de b-roll

```json
{
  "fps": 30,
  "output": {"width": 1080, "height": 1920},
  "source": "../apresentador.mp4",
  "clips": [
    {"id": "abre", "in": 2.10, "out": 5.60, "layout": "cover", "crop_x": 0.50},
    {"id": "explica", "in": 5.60, "out": 14.20, "layout": "lower", "split_at": 0.45, "crop_x": 0.50}
  ],
  "overlays": [
    {"source": "../b-roll/produto.mp4", "at": 3.5, "dur": 2.0, "region": "full"},
    {"source": "../b-roll/loja.mp4", "at": 5.8, "dur": 2.0, "region": "top", "feather": 0.06},
    {"source": "../b-roll/grafico.png", "at": 7.9, "dur": 1.8, "region": "top", "feather": 0.06},
    {"source": "../b-roll/print.png", "at": 11.0, "dur": 2.4, "region": "card", "width": 0.75, "y": 0.33}
  ]
}
```

```bash
vedit cut --edl edl/abre-explica.json -o out/limpo.mp4
vedit captions 01-words.json --edl edl/abre-explica.json -o out/leg.ass --srt --style viral --max-words 3 --mode bloco --case sentence --headline "O QUE NINGUÉM CONTA|SOBRE ESSE PRODUTO" --headline-y 0.12 --headline-start 0 --headline-box "#D00000" --headline-color "#FFFFFF"
vedit burn out/limpo.mp4 out/leg.ass -o out/com-leg.mp4
vedit master out/com-leg.mp4 -o out/final.mp4
vedit verify out/final.mp4 --platform reels --json
```

Regras: cada `at`/`dur` cai em palavra dita (use `vedit digest --windows`); troque de imagem a cada 1,5-3 s nos trechos densos, nunca sem que algo nomeado justifique; a manchete tem no máximo 2 linhas.

### 5.2 Corte de podcast com manchete fixa e punch-in alternado

```json
{
  "fps": 30,
  "output": {"width": 1080, "height": 1920},
  "source": "../podcast.mp4",
  "clips": [
    {"id": "a", "in": 612.40, "out": 615.30, "layout": "cover", "crop_x": 0.30, "zoom": 1.0},
    {"id": "b", "in": 615.30, "out": 618.60, "layout": "cover", "crop_x": 0.30, "zoom": 1.25},
    {"id": "c", "in": 618.60, "out": 621.40, "layout": "cover", "crop_x": 0.68, "zoom": 1.0},
    {"id": "d", "in": 621.40, "out": 625.00, "layout": "cover", "crop_x": 0.68, "zoom": 1.25}
  ]
}
```

```bash
vedit cut --edl edl/podcast-c1.json -o out/c1/limpo.mp4
vedit captions 01-words.json --edl edl/podcast-c1.json -o out/c1/leg.ass --srt --style viral --max-words 3 --mode bloco --case upper --emphasis "milhões,dobrou" --headline "A REGRA QUE QUEBRA|TODO NEGÓCIO" --headline-y 0.12 --headline-start 0 --headline-box "#FFD400" --headline-color "#000000"
vedit burn out/c1/limpo.mp4 out/c1/leg.ass -o out/c1/com-leg.mp4
```

Alternância de zoom só nas emendas de frase ou turno; troca de `crop_x` só na fronteira de quem fala (o crop salta, não desliza). Se a manchete é só o título do assunto, mantenha-a até o fim ou apague aos ~3 s, conforme a seção de manchete fixa de `legendas.md`.

## 6. O que exige HyperFrames

Texto animado ou digitado, transições (dissolve, glitch, whip, rajada radial), máscara/oclusão do texto atrás do sujeito, cantos arredondados e sombra em cartões, trilha bilíngue, cor por falante, picture-in-picture com etiquetas, explicador animado. O `vedit` entrega o vertical limpo, as janelas de b-roll, os cartões básicos, a legenda estática e a manchete fixa. Handoff em `motion.md`, seção 15.

## 7. Checklist

- [ ] Receita escolhida por função, com o motivo escrito no plano
- [ ] Cada insert cai na palavra que ele mostra (±3 quadros)
- [ ] `top` só sobre clipe `lower`; nenhum overlay sobreposto a outro
- [ ] Legenda calada sob cartões; manchete dentro das zonas seguras
- [ ] Loudness no alvo da skill, não o da referência
- [ ] Nenhuma imagem, fala, marca ou rosto de referência reutilizados
- [ ] Texto queimado conferido contra o áudio (sem erro de transcrição)
