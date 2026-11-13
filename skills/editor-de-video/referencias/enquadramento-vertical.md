> **Leia quando** for converter vídeo horizontal (ou de câmera aberta) em 9:16: escolher crop, layout, quem enquadrar, como rastrear, ou compor cartões e recortes de cabeça.
> **Comandos:** `vedit probe`, `vedit sheet --guides`, `vedit reframe`, `vedit cut` (layouts `cover`/`split`/`fit`). Decida geometria e faixa de legenda **juntas**, num quadro real, antes de qualquer etapa cara.

# Enquadramento vertical

## 1. Ordem de preferência

1. Rosto ou objeto principal rastreado (locutor ativo).
2. Composição de duas ou três pessoas (`split`).
3. `crop_x` definido à mão por segmento.
4. Centro, último recurso (declare no plano que é manual).

Antes de tudo: `vedit probe` (rotação, `avg_frame_rate` real, HDR, canais) e `vedit sheet` (1 quadro a cada ~5 s, 4 colunas, ~480 px). A prancha revela enquadramento, perfil x olhar para a lente e onde o rosto está; em um caso, mudou toda a regra de contato visual.

## 2. Locutor ativo

- Critério: **correlação entre movimento da boca e energia do áudio**, com histerese para não "pingar" entre pessoas. `vedit reframe` faz isso (amostra ~3 fps, detecta rostos, grava `crop_x` por subsegmento).
- **Nunca o maior rosto**: em plano aberto quem está mais perto da câmera tem o maior rosto e frequentemente não é quem fala.
- **Nunca só movimento de boca**: em monólogo, o ouvinte que ajeita a mão, mastiga ou reage pode ter mais movimento que quem fala (medido: 17,5 vs 16,2). Correlação com o áudio separa o locutor do ouvinte inquieto.
- Bug clássico: o detector devolve a caixa do rosto com jitter de 1-2 px; comparar recortes da boca por igualdade de shape falha e o movimento sai 0,00 justamente para quem mais aparece. **Redimensione o recorte a tamanho fixo antes de comparar.**
- Rostos pequenos (plano aberto, 2-3 pessoas) caem em confiança < 0,2 em passe único: fatie o quadro em tiras verticais sobrepostas, amplie 2x, soma coordenadas de volta, deduplique por centro.
- Trilhas fragmentadas competem consigo mesmas: agrupe trilhas com `cx` médio a menos de ~220 px antes de pontuar.
- Sem locutor detectável: caia para `crop_x` do segmento, depois centro.

## 3. Câmera que zoom dentro do plano

Ausência de corte de câmera não significa enquadramento estático. Olhe a largura necessária por balde de tempo; se variar mais de ~25% entre baldes, use enquadramento por subsegmento (`crop_x` como lista `[{"t":..,"x":..}]`, com `t` em segundos desde o início do clipe, e `zoom`). Os keyframes são **constantes por trecho**: o crop salta no `t` listado, não desliza (**pan animado não é suportado**; se precisar de pan suave, faça no HyperFrames). `zoom` aceita número fixo ou rampa linear `{"from","to"}`; mais que isso (easing, curva) também não. Caso real: punch-in contínuo do operador fez o grupo ir de ~810 a ~1400 px de largura em 39 s; crop fixo cortava gente na segunda metade.

## 4. Layouts e geometria (saída 1080x1920)

| Layout | Quando | Geometria |
|---|---|---|
| `cover` | uma pessoa, ou locutor cabe sozinho no 9:16 | crop 9:16 ancorado em `crop_x` (0-1) sobre a altura da fonte: `w = floor(altura*9/16)` (par) |
| `split` | 2-3 pessoas no mesmo plano que não cabem num crop estreito | metade de cima = **quadro inteiro sem crop em altura natural**; baixo = crop fechado em quem fala |
| `fit` | conteúdo que não pode ser cortado (tela, gráfico) | quadro inteiro centralizado, barras com fundo desfocado |

- `split` com fonte 1920x1080: o quadro inteiro escalado a 1080 de largura tem 608 px de altura; sobram 1312 px para o crop fechado. A altura natural é o que impede distorção e metade preta.
- Nunca deixe metade do `split` preta ou vazia; sem conteúdo extra, repita o mesmo plano mais aberto, nunca cor sólida. Fonte já vertical **não aceita** `split` (degenerado): recuse.
- A altura varia entre arquivos do mesmo celular (ex.: 1840 vs 1824): calcule o crop pela altura de cada arquivo.
- Nunca corte um rosto na borda do crop. O recorte 9:16 do layout A fica **centrado no sujeito**, não no centro geométrico.
- Não aplique saturação, sharpen ou glow automáticos no enquadramento.

## 5. Quando trocar o enquadramento

Salto de crop só onde já existe **corte de câmera ou fronteira de turno de fala**; nunca no meio de uma palavra. Troca fora disso lê como erro e quebra a continuidade da boca.

## 6. Rastrear sujeito em movimento

- Amostre **2-5 fps** (basta para câmera e pessoa em cortes de 30-90 s; processar todo quadro é caro e não muda a decisão). Em passe de segmentação, ~5 fps em ~320 px de entrada.
- Suavize com gaussiana de ~0,7 s e **reinicie a suavização em cada corte** (senão o crop "arrasta" do plano anterior).
- Armadilha da **mão levantada**: o ponto mais alto da silhueta pode ser a mão. Se `|cabeça - centro do corpo| > 0,12` (fração da largura), use o centro do corpo.
- Limite de pan (vale para quem faz pan no HyperFrames ou em ffmpeg manual; o `vedit` não anima pan): um push de N% dá só `N/2 %` da largura de folga lateral; `pan_max = (escala - 1) * largura / 2`. Push 6% com pan de 70 px puxou borda preta para dentro do quadro.
- Pessoa falando para a plateia (não para a lente): contato visual vira "rosto visível ou ação relevante".

## 7. Layouts de cartão e recorte de cabeça (composição)

Padrão: gráfico no topo, **cartão de câmera embaixo** com cantos arredondados (superelipse) e a cabeça recortada passando por cima da borda do cartão.

- Calcule a máscara **só nos quadros únicos da fonte** realmente usados no layout (centenas em vez de ~1000 a 60 fps) e **indexe pelo quadro da fonte**: o mesmo índice sempre tem a mesma máscara, mesmo que a EDL mude de lugar.
- A **cor da cabeça vem do quadro do cartão**; do recorte só se usa o alfa. Assim cabeça e corpo não se descolam em movimento rápido.
- Recorte só a região da cabeça (janela ao redor), não o quadro inteiro; cache incremental quando a janela não muda.
- **Feathering da máscara fica inteiro dentro do cartão.** Se a suavização de 40 px for centrada na borda, acima dela a cabeça fica semitransparente e o fundo claro do gráfico aparece como faixa no cabelo. Acima da borda o alfa é 1; a rampa mora onde o fundo é o mesmo vídeo.
- Encosto de cadeira/fundo que entra na máscara: separar por componente conectada falha (tocam a cabeça). Abordagem geométrica: contorno superior da silhueta, pico = topo da cabeça, andar até o vale ou fim da silhueta sólida, cortar com rampa de ~10 px, zerar alfa < 0,08. Valide por varredura em **todos** os quadros (resíduo à esquerda x cabeça perdida), não em amostras.
- Ordem de camadas: gráfico -> sombra do cartão (gaussiana, sigma = desfoque CSS/2) -> vídeo dentro da máscara -> cabeça.
- O vídeo do cartão precisa cobrir até o fim do quadro (y=1920); com sujeito pequeno, escale e reposicione.
- Inspecione sempre com zoom na borda (ver `verificacao.md`).

## 8. HDR (HLG/PQ) para SDR

- Celular grava HLG/BT.2020 por padrão em muitos modelos; sem conversão a imagem sai lavada em players SDR. `vedit probe` acusa transfer `arib-std-b67` (HLG) ou `smpte2084` (PQ); `vedit cut` converte automaticamente. **Sem o filtro `zscale` no ffmpeg a conversão sai sem tone mapping** (cores podem ficar lavadas ou deslocadas): confira num quadro e avise o usuário.
- Tonemap (`zscale` + `mobius`/`hable`) pode deslocar cores saturadas (um laranja virou vermelho). Alternativa que preservou cor em teste: `colorspace=all=bt709:iall=bt2020:itrc=bt709:fast=1` + ajuste leve `eq=contrast=1.1:saturation=1.12:gamma=0.95`. Confira cores fortes (laranja, vermelho, pele) num quadro antes de renderizar tudo.
- Saída: H.264 `yuv420p`, BT.709, sem metadados HDR.

## 9. Geometria + legenda, decididas juntas

Retrabalho mais caro registrado: escalar a fonte para o rosto ficar acima do cartão e só depois ver que a faixa de legenda caiu **sobre os olhos**. Procedimento:

1. Pegue um quadro real (o mais crítico: rosto mais baixo/alto).
2. Desenhe (`vedit sheet --guides zona.json`, formato em `formatos.md`) a posição do rosto, a borda do cartão, as zonas seguras da plataforma (`plataformas.md`) e a faixa de legenda (padrão `--y 0.62`, centro em y ~1190).
3. Rosto e faixa de legenda **não se cruzam** em nenhum quadro da janela (meça o pior quadro, não o do meio: a pessoa se mexe).
4. Só então rode máscara, render ou motion.

Se o texto precisa ir onde há rosto, desloque abaixo do queixo mais baixo da janela; energia de borda baixa não prova espaço livre (pele lisa em close dá o menor ruído do quadro).

## 10b. Decisões rápidas

| Situação | Decisão | Motivo |
|---|---|---|
| Uma pessoa, câmera fixa, cabe no 9:16 | `cover`, `crop_x` no rosto, `zoom` 1,0 | menor risco |
| Dois falantes lado a lado, turnos curtos | `cover` com troca de `crop_x` só nas fronteiras de turno | segue quem fala sem pingar |
| Três pessoas numa mesa | `split` (contexto em cima, fechado embaixo) | ninguém sai do quadro |
| Tela compartilhada ou gráfico com texto | `fit` ou `split` com a tela inteira em cima | cortar texto da tela destrói o conteúdo |
| Fonte já vertical | `cover` sem crop; recuse `split` | `split` degenera |
| Entrevistado se levanta ou anda | rastreio com suavização reiniciada nos cortes | evita arrasto |
| Rosto sob a faixa de legenda | mover a faixa ou reenquadrar; nunca ignorar | retrabalho caro depois do render |

## 10. Checklist de saída

- [ ] `vedit probe` conferido (fps real, rotação, HDR, canais)
- [ ] Prancha de enquadramento com zonas seguras aprovada
- [ ] Nenhuma troca de crop dentro de palavra
- [ ] `split` sem metade vazia; `cover` sem rosto cortado
- [ ] Cores fortes ok após HDR->SDR
- [ ] 4:5 (se pedido) sai por crop do master 9:16: `crop=1080:1350:0:285` com conteúdo entre y 340 e 1000 (ver `plataformas.md`)

## Fontes
- Instagram/Meta Ads Guide, "Instagram Reels" (zonas seguras ~14% topo, ~35% base, ~6% lateral), https://www.facebook.com/business/ads-guide/update/image/instagram-reels (aberta em 2026-11).
- Prática operacional (detecção de locutor, rastreamento, máscara): consolidação própria; sem norma publicada.
