> **Leia quando** for exportar ou publicar: resolução, duração máxima, codec, zonas seguras, loudness e capa por plataforma (Reels, TikTok, Shorts, anúncios Meta e TikTok).
> **Regra:** todo número abaixo foi **conferido em 2026-11** na fonte indicada ou marcado como não confirmado. Especificações mudam; confirme na documentação da plataforma antes de publicar. Onde as fontes divergem, vale o valor **conservador**.

# Plataformas

## 1. Especificação de entrega padrão (master)

| Item | Valor | Por quê |
|---|---|---|
| Resolução / aspecto | **1080x1920, 9:16** | formato nativo e aceito em todas as plataformas; TikTok exige >= 540x960 e recomenda >= 720p; YouTube serve Shorts a no máximo 1080p |
| Vídeo | H.264 High, `yuv420p`, BT.709, fps constante (30; 24-60 aceitos) | compatibilidade; a API do TikTok aceita 23-60 fps |
| Contêiner | MP4 com `+faststart` | início imediato; sem *edit lists* (a Meta pede) |
| Áudio | AAC, 48 kHz, estéreo, ~192 kbps (Meta pede >= 128 kbps) | |
| Loudness | **-14 LUFS integrado, true peak <= -1,5 dBTP** | convenção de produção; nenhuma das plataformas abaixo publica um alvo obrigatório para Reels/TikTok/Shorts; confirme |
| Bitrate | ~8-12 Mbps é um default prático; TikTok exige >= 516 kbps em anúncios | plataforma recomprime; evite grão (ver `motion.md`) |
| Tamanho | abaixo de 500 MB (limite do arquivo TikTok que o `verify` aplica) | |

`vedit verify --platform reels|tiktok|shorts|meta-ads` aplica estas checagens (limites do `verify`: Reels 180 s, arquivo TikTok 500 MB; padrões conservadores, confirme na plataforma). Som nos primeiros/últimos instantes é aviso; `--strict-edges` o torna falha (use em fala sem música).

## 2. Resumo por plataforma (conferido em 2026-11)

| | Instagram Reels (orgânico) | TikTok (orgânico) | YouTube Shorts | Meta Ads (Reels) | TikTok Ads (In-Feed) |
|---|---|---|---|---|---|
| Aspecto | 9:16 | 9:16 | vertical ou quadrado | 9:16 (anúncio de Reels) | 9:16 recomendado; 1:1 e 16:9 aceitos |
| Resolução | 1080x1920 (padrão prático) | 1080x1920; aceita 360-4096 px por lado (API) | até 1080p servido | **1440x2560 recomendado** (imagens: 1440x2560, largura mín. 500 px); 1080x1920 comum | mín. 540x960 (9:16); >= 720p recomendado |
| Duração máx. | até 3 min publicáveis; páginas de ajuda mais antigas citam 20 min, e acima de 3 min não é recomendado a novos públicos (**divergente: confirme**) | 3 min para todos; alguns criadores 5 ou 10 min (API); app pode permitir mais | **até 3 min** (desde 15/10/2024), só quadrado/vertical; no feed de anúncios só os 60 s iniciais | página de vídeo consultada não listou Reels; feed: 1 s a 241 min | página oficial atual: **até 10 min**; outras fontes citam 5-60 s (divergente: use <= 60 s, 9-15 s para conversão) |
| Arquivo | MP4/MOV (confirme limite) | MP4 recomendado, MOV, WebM; até 4 GB (API) | confirme no upload | MP4/MOV; feed até 4 GB | MP4, MOV, MPEG, 3GP, AVI; <= 500 MB |

Divergências relevantes: (a) limite de duração do Reels e do anúncio no TikTok variam por fonte e por data; (b) Meta recomenda 1440x2560 mas 1080x1920 é aceito e é o master padrão (suba o master 1080x1920; se quiser ganho, exporte também 1440x2560 sem upscale artificial: só se a fonte tiver resolução).

## 3. Zonas seguras (1080x1920)

| Plataforma | Regra oficial | Em pixels | Observação |
|---|---|---|---|
| Meta (Reels e Stories, anúncios) | manter texto, logos e elementos-chave fora de ~**14% topo, ~35% base, ~6% cada lado** | topo ~270, base ~670 (conteúdo até y ~1250), lados ~65 | números da Ads Guide de Reels (aberta em 2026-11); a ajuda de "zona segura" não abriu na consulta; relatos secundários de unificação Stories/Reels em 2026: não confirmado. Ative o guardrail "Safe zone" no Ads Manager |
| TikTok (anúncios) | sem pixels fixos: depende de orientação, comprimento da legenda e formatos adicionais; baixar o arquivo de safe zone do Ads Manager | sem número oficial; fontes secundárias citam ~35-40% da base | use o gabarito oficial da conta; a página aberta orienta usar os arquivos (LTR; RTL para árabe; versão com *anchors*) |
| Reels orgânico / Shorts / TikTok orgânico | não há tabela oficial pública consultada | use o **conservador**: esq. 90, dir. 170, topo 160, base 310 px, sem texto crítico em y > ~1250 e à direita dos botões | a interface muda; teste em prévia real |

Leitura prática (todas as plataformas): conteúdo importante entre y ~290 e ~1000; faixa de legenda y ~1040-1220 (ou 1270-1540 em talking head com o rosto acima); nada crítico na coluna direita (botões) nem sob a descrição/CTA.

## 4. Faixa de legenda recomendada

- Default do `vedit captions`: `--y 0.62` (centro do texto em y ~1190, faixa ~1040-1220) com layout "gráfico em cima + cartão embaixo" ou conteúdo acima. Em fala direta à câmera com o rosto alto, desça para `--y` 0.70 a 0.78 (faixa ~1270-1540), depois de conferir. Em ambos, margem lateral >= 90 px e coluna direita livre.
- Mova o `--y` só se a prancha mostrar conflito. Confirme **sempre** com `vedit sheet --guides` (formato em `formatos.md`) num quadro real (ver `enquadramento-vertical.md`). Meta e TikTok podem sobrepor a descrição e o CTA ao rodapé em anúncios.

## 5. 4:5 a partir do master 9:16

Quando o posicionamento exige 4:5 (feed): `crop=1080:1350:0:285` sobre o 1080x1920, **sem refazer layout**, desde que o conteúdo importante esteja entre y 340 e 1000 e a legenda entre 1040 e 1220 **dentro do recorte** (285 + 1350 = 1635; o recorte cobre y 285-1635). Se a legenda cai fora, recompor. O anúncio de feed da Meta usa 4:5 a 1440x1800. 1:1 (1080x1080): recorte central e legenda dentro dele.

## 6. Capa e miniatura

| Plataforma | Nota |
|---|---|
| Instagram Reels | escolha do quadro/foto de capa na publicação; o perfil recorta a capa na grade (hoje 3:4; confirme). Texto da capa no terço central |
| TikTok | capa escolhida entre quadros do vídeo ou imagem; quadro 0 forte ajuda |
| YouTube Shorts | miniatura em Shorts é limitada; o quadro inicial importa; confirme as opções atuais |
| Anúncios | sem capa própria: o primeiro quadro e os 3 primeiros segundos fazem o trabalho |

Aplique texto de capa **só no quadro 0** quando o 1º quadro serve de capa (ver `legendas.md`).

## 7. Diretrizes de criativo pago (oficiais, resumidas)

- **TikTok:** gancho nos 6 primeiros segundos; proposta em 3 s; usar som/música; legendas/overlays com ~5-10 palavras por segundo; vertical 9:16, >= 720p; CTA claro; estilo nativo/menos polido; testar 3-5 criativos por grupo e renovar quando o desempenho cai.
- **Meta (Reels):** marca e mensagem nos 5 primeiros segundos (marca); em resposta direta, gancho com visual e som; combinar fala e música; entregar a mensagem por áudio e visual; incluir CTA visual ou falado; produto mais de uma vez; presença de marca <= 25% da duração em resposta direta; feito para ser nativo da plataforma, não reaproveitado. São correlações do estudo da Meta, não garantias.
- **YouTube Shorts (anúncios):** 9:16 melhor; vídeos até 3 min mas só os 60 s iniciais tocam no feed; 10-30 s para ação; usar som; parecer orgânico; testar vários criativos; rotular conteúdo editado/criado por IA onde exigido.

## 8. Tabela: o que conferir na plataforma antes de publicar

Marque cada item com a data da conferência (ex.: "conferido em 2026-11").

| Item | Onde conferir | Estado em 2026-11 |
|---|---|---|
| Duração máxima do Reels | ajuda do Instagram / criadores | 3 min na publicação; limites maiores citados em páginas antigas; **confirmar** |
| Duração máxima do TikTok e do anúncio | ajuda do TikTok / página de specs de anúncios | 3 min padrão; anúncio até 10 min na página oficial; outras fontes 5-60 s; **confirmar** |
| Shorts: limite e classificação | YouTube Help "Understand three-minute YouTube Shorts" | até 3 min, quadrado ou vertical, desde 15/10/2024 |
| Resolução recomendada Meta | Meta Ads Guide | 1440x2560 (imagem de Reels); vídeo **confirmar** |
| Zonas seguras Meta | Ads Guide + guardrail do Ads Manager | ~14/35/6% |
| Zonas seguras TikTok | gabarito baixado do Ads Manager | sem px oficiais |
| Loudness | documentação do destino | nenhum alvo obrigatório confirmado; -14 LUFS é convenção |
| Legendas em anúncios TikTok | página In-Feed | legenda de anúncio: fonte branca fixa, sem links, @ ou hashtags |
| Classificação "feito com IA", música e direitos | política da plataforma | rotular quando exigido; voz sintética e música: checar licença |
| Formato da grade do perfil (capa) | app | 3:4 citado por relatos; **confirmar** |

Se qualquer número divergir do que você vê no Ads Manager ou no app, **prevalece a plataforma**; atualize este arquivo e a data.

## 9. Entrega final (checklist)

- [ ] Master 1080x1920 H.264/AAC, `+faststart`, `vedit verify --platform <destino>` limpo
- [ ] Duração dentro do limite do destino (e dentro do recomendado: 9-15 s para conversão em anúncio TikTok, <= 60 s em Shorts de anúncio)
- [ ] Legenda e elementos dentro das zonas seguras (conservador na dúvida)
- [ ] Áudio -14 LUFS / -1,5 dBTP; música e voz com direitos para uso comercial se for anúncio
- [ ] Capa/quadro 0 definidos; descrição, hashtags e CTA conforme a plataforma
- [ ] Variante 4:5 gerada por crop, se necessária

## Fontes
- TikTok, "TikTok Auction In-Feed Ads" (specs), https://ads.tiktok.com/help/article/tiktok-auction-in-feed-ads (aberta em 2026-11: 9:16 mín. 540x960, até 10 min, 500 MB, 516 kbps, legendas de anúncio, orientação de safe zone).
- TikTok, "Creative best practices", https://ads.tiktok.com/resources/help/article/creative-best-practices?lang=en (aberta em 2026-11).
- TikTok for Developers, "Media Transfer Guide", https://developers.tiktok.com/docs/en/content-posting-api-media-transfer-guide (aberta em 2026-11: formatos, 23-60 fps, 360-4096 px, 3/5/10 min, 4 GB).
- Meta, Ads Guide "Instagram Reels" (imagem), https://www.facebook.com/business/ads-guide/update/image/instagram-reels (aberta em 2026-11: 1440x2560, 14/35/6%, largura mín. 500 px).
- Meta, Ads Guide "Video" (Feed), https://www.facebook.com/business/ads-guide/update/video (aberta em 2026-11: 4:5 1440x1800, 1 s a 241 min, 4 GB, AAC >= 128 kbps; sem specs de Reels).
- Meta, "Reels creative strategies", https://www.facebook.com/business/news/reels-creative-strategies (aberta em 2026-11).
- Instagram for Creators, "Finding success on reels in 2025", https://creators.instagram.com/blog/the-latest-with-instagram (aberta em 2026-11: reels de até 3 min nos EUA, 90 s antes).
- YouTube Help, "Understand three-minute YouTube Shorts", https://support.google.com/youtube/answer/15424877?hl=en (aberta em 2026-11).
- YouTube Help, "Upload YouTube Shorts" (resolução máxima 1080p), https://support.google.com/youtube/answer/10059070 (aberta em 2026-11).
- Google Ads Help, "YouTube Shorts ads: Asset specs and best practices", https://support.google.com/google-ads/answer/16041697?hl=en-AU (aberta em 2026-11).
- Não abertas (reconfirmar): páginas de ajuda do Instagram sobre limite de duração do Reels e da Meta sobre "zona segura de texto"; ambas devolveram só o título.
