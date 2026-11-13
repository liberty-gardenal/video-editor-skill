> **Leia quando** for montar a linha do tempo de um vídeo curto: onde cortar, quando mudar a imagem, como abrir, quanto de pausa remover, ritmo por tipo de vídeo e montagem em grade de batida.
> **Comandos:** `vedit silences`, `vedit edges`, `vedit cut --edl`, `vedit metrics`, `vedit sheet`. A edição inteira vive em `edl.json`.

# Cortes e ritmo

## 1. EDL como fonte única de verdade

- Um único `edl.json`; todo o resto (áudio, legendas, motion, relatório) é **derivado dele por script**. Uma correção na EDL se propaga sem edição manual.
- Fronteiras em **quadro inteiro**: `round(t * fps)` em todos os scripts. Bug real: um script comparava `t >= inicio - 1e-9` e outro `1e-6`; com o início gravado com 6 casas, um quadro caiu em layouts diferentes e ficou sem máscara.
- Vídeo e áudio de um clipe usam o mesmo deslocamento; o `vedit cut` corta os dois no mesmo quadro, então a boca nunca dessincroniza.
- Correção cirúrgica com render pronto: se a mudança só **desloca** trechos seguintes sem mudar a duração deles, reaproveite os renders caros (gráficos, máscaras indexadas pelo quadro da fonte) e apare o trecho afetado.
- Palavra que o ASR data **dentro de um silêncio removido** pertence ao clipe seguinte (o ASR adianta o início das palavras).
- **Sempre reencode** (`vedit cut` nunca usa `-c copy`): `-c copy` corta no keyframe e o in/out não bate com o transcrito.

## 2. Edição por beat: o que justifica uma mudança visual

Unidade de edição = beat semântico ou emocional, não "um corte a cada X s". Mude a imagem quando houver:

| Justificativa | Exemplo |
|---|---|
| nova ideia | passa do problema para a causa |
| número importante | punch-in ou card no número |
| mudança de pessoa | troca de locutor |
| contraste ou virada | "mas aí..." |
| prova | mostrar o objeto, a tela, o resultado |
| reação | rosto de quem ouve, só se reagiu àquilo |
| passagem de tempo ou objeto citado | corte para o objeto |
| retomada após highlight | volta ao início do trecho |

Sem uma dessas razões, não mude. Corte, zoom ou efeito "para estimular" não é critério (ver `psicologia-do-feed.md`).

## 3. Quadro de abertura

- O 1º quadro tem pelo menos uma âncora: rosto expressivo (em movimento > neutro), objeto relevante, texto específico, número, ação em andamento.
- Evite: fade-in, logo longo, silêncio não intencional, plano vazio, frase começando no meio, texto abstrato ("VOCÊ PRECISA VER ISSO").
- Antes de fechar o início, olhe os quadros: o bruto costuma ter card de título, tela, reação ou inserto que dá gancho de graça; **não corte imediatamente antes dele**.

## 4. Highlight de abertura e retorno

Quando o melhor momento vem depois: `HIGHLIGHT -> corte claro de retorno -> contexto mínimo -> continuação após o trecho já usado -> payoff`. O retorno precisa ser compreensível, não chamativo: corte seco, card curto ou mudança de enquadramento. Regra: o hook não pode ocupar mais de 50% do clipe; se ocupar, faça linear.

## 5. Remoção de pausas

| Situação | Ação | Por quê |
|---|---|---|
| silêncio técnico, hesitação sem função, repetição de palavra, ar entre frases independentes | remover | tempo morto |
| silêncio sem função > ~0,4-0,55 s | encolher para ~0,15-0,2 s; **não zerar** | zerar vira locução de robô |
| 0,25-0,55 s | só com razão editorial | pode ser respiração natural |
| pausa antes da revelação, timing de piada, reação, emoção, mudança de decisão | **preservar** | é o conteúdo |
| respiração curta dentro da frase | preservar | cortar soa artificial |

Se a soma removida passar de ~15% da duração, o problema provavelmente é o in/out: devolva à seleção em vez de costurar. Use `vedit silences --noise -35 --min 0.25` sobre a voz **já tratada** (ver `audio.md`: limiares só valem sobre sinal tratado e normalizado). Meça junções no **stem final**: fade e limitador derrubam a cauda abaixo do limiar mais cedo (junções projetadas com 130 ms mediram 160-180 ms); projete com folga (~100 ms de gap) e meça logo após montar a voz.

## 6. Emendas no meio da frase

- Corte no **vale de energia entre o meio de uma palavra e o meio da seguinte**; o tempo do ASR erra a fronteira por dezenas de ms.
- Valide com a energia no ponto exato (< -24 dB). Se a fala é contínua e não há vale, **descarte a emenda**.
- Micro-fade de áudio (~30 ms) em toda junção, senão estala (`vedit cut` já aplica).
- Folga de 30-200 ms em toda borda; o ASR deriva 50-100 ms.
- Emendas dentro de frase são o ponto mais arriscado de fontes longas; prefira blocos que já têm gancho -> lista -> fechamento.

## 7. J-cut e L-cut (conhecimento de ofício; **não disponível no `vedit`**; faça no HyperFrames ou em ffmpeg manual)

O `vedit cut` corta áudio e vídeo no mesmo quadro, com micro-fade nas junções. Não há deslocamento de áudio em relação à imagem.

| Tipo | O que faz | Use em |
|---|---|---|
| J-cut | áudio da cena nova entra ~50-250 ms antes da imagem | suavizar emenda de fala; mostrar o objeto citado |
| L-cut | áudio da cena anterior continua sobre a imagem nova | mostrar reação ou prova enquanto a frase termina |

Motivo do ofício: o ouvido antecipa, o olho segue; cortar áudio e imagem no mesmo quadro lê como corte mecânico. No `vedit`, o remédio é cortar no vale de energia entre palavras (seção 6), onde o micro-fade esconde a emenda.

## 8. Ética do jump cut

Pode: remover tempo morto, condensar contexto, separar beats, ganhar clareza. **Não pode:** fazer a pessoa dizer o que não disse, apagar qualificações importantes, transformar dúvida em certeza, quebrar continuidade emocional. Em dúvida, mostre a emenda ao humano.

## 9. Corte em ação e regra dos seis (Murch)

- Corte **durante** o movimento (gesto, virada de cabeça, passo) mascara a emenda; corte em quadro parado com troca de ângulo pequeno parece erro (jump).
- Murch ordena o que um bom corte satisfaz: emoção (51%), história (23%), ritmo (10%), trilha do olhar (7%), plano 2D/eixo (5%), espaço 3D (4%). Os percentuais são o peso aproximado dado por ele, não medição; o uso prático é a **ordem de sacrifício**: abra mão primeiro da continuidade espacial, depois do eixo, trilha do olhar e ritmo; nunca da emoção ou da história.
- Para vídeo falado, "trilha do olhar" = rosto e boca no mesmo terço do quadro antes e depois do corte, para o olho não procurar.

## 10. Punch-in

Defaults: escala 1,05-1,15; duração mínima ~1,2 s; não alternar sem motivo; evitar em toda frase. Use em número, confissão, reação, mudança de argumento, prova. No `vedit`, o punch-in é um **clipe separado** na EDL com `zoom` estático diferente (o salto cai na fronteira do clipe, de preferência num corte de câmera, que o esconde), ou uma rampa linear `{"from": 1.0, "to": 1.10}` dentro de um clipe. Não existe outra curva (sem ease, sem pan animado). Em cortes de podcast observados (4 de 12 referências), o plano alterna enquadramento normal e punch-in de **≈1,2-1,3x a cada ~2,5-4 s**, em fronteiras de frase ou turno; é mais forte que o 1,05-1,15 acima porque o plano é aberto e o rosto pequeno. Use quando o formato for esse e cada alternância cair numa frase; é prática observada, não causa comprovada de retenção, e vira tique se for mecânica. Exemplo de EDL em `formatos-virais.md`. Zoom contínuo lento (+6-14% ao longo do plano) pela rampa serve de gancho sem cortar. Zoom com easing ou "punch" que assenta em poucos quadros: HyperFrames.

## 11. Transições

Padrão: **corte seco** (domina nas 12 referências observadas). Transição especial só para volta no tempo, mudança de lugar, mudança de capítulo, antes/depois, mudança de fonte visual. Sem flash branco, whip-pan nem glitch como muleta (ver `motion.md`). **Whip-pan é técnica de câmera**: uma referência de 11 s usa whip-pans gravados na mão; o `vedit` não os simula, e o que já está no bruto você preserva. Dissolve, glitch e rajadas radiais, quando pedidos, são do HyperFrames.

### Plano longo sem corte

Dois talking heads observados seguram 40-60 s sem corte (outra peça de 63 s tem um só), com o movimento vindo da legenda e do gesto. Cortar menos é válido quando a **entrega** carrega (história, emoção, humor, argumento em construção) e a legenda dá o ritmo. Isso convive com a referência de 4-8 s sem mudança visual do playbook de talking head, que é alvo para falas sem essa carga. Se mantiver o plano longo, sustente com legenda bem segmentada, manchete fixa ou um punch-in lento em rampa; se a entrega for fraca, corte. Mediana de plano das peças editadas observadas: ~1,7-3,2 s; em 3 delas os cortes se concentram nos 5 primeiros segundos.

## 12. Ritmo por perfil

| Perfil | Ritmo |
|---|---|
| resposta rápida | zero tolerância a preâmbulo; cortes ao fim de raciocínio; demonstração cedo |
| história | preservar microexpressões; pausa com tensão; acelera no contexto, desacelera na virada |
| humor | proteger setup e reação; sem SFX que explique a piada; legenda não antecipa o punchline |
| opinião | manter a qualificação; mostrar razão e consequência; não transformar nuance em ataque absoluto |
| anúncio | nada parado mais de ~3 s; fala longa ganha 2 tomadas; 1 SFX por evento visual |

## 13. Métricas de produção são hipóteses

`vedit metrics --edl edl.json --words words.json` entrega palavras/s, cortes/min e maior trecho sem corte. Valores observados em vídeos já feitos: 3,0-4,1 palavras/s e 21-43 mudanças visuais/min (fala pausada de entrevista no extremo baixo). A hipótese ">35 mudanças/min e >3,5 palavras/s retêm melhor" **não foi validada**: registre as métricas de cada vídeo, cruze com retenção em 3 s e tempo médio assistido, e só promova a regra com 5+ vídeos.

## 14. Anúncio de serviço local (estrutura)

| Bloco | Conteúdo | Por quê |
|---|---|---|
| Gancho (0-2 s) | prova visual + número/palavra em caixa alta, ou pergunta de identificação | para o scroll com algo inesperado; som concreto reforça |
| Dor local | 3 palavras curtas na tela | fala do contexto do público, não do serviço |
| Mecanismo | por que o óbvio não resolve | cria a necessidade antes da oferta |
| Prova | antes/depois em tela dividida + "sem filtro" | prova mais forte; responde à desconfiança |
| Humano | dono ou equipe na câmera | confiança, diferencia de franquia |
| Prova social e oferta | nota pública, "a partir de", garantia | reduz risco percebido |
| CTA | cartão final >= 1,4-1,6 s após a última palavra, 1 ação de baixo atrito, telefone legível | uma ação só |

Duração da cena = duração da fala daquela cena + ~0,06 s de entrada + ~0,1 s de saída (cartão final +1,4-1,6 s); o vídeo segue a voz (ver `narracao-tts.md`). Copy sai do site do cliente; nunca use afirmação proibida pelo cliente ou pela política da plataforma ("o mais barato", "100%").

## 15. Montagem em grade de batida (sem fala)

Para vídeo de imagens reais com música (evento, bastidor): fixe o BPM (ex.: 140 bpm -> 0,4286 s por batida), corte planos em **múltiplos de batida**, gere a trilha no mesmo grid.

| Bloco (~30 s) | Batidas | Conteúdo |
|---|---|---|
| Gancho | 8 | plano mais estranho ou direto à câmera, zoom lento, frase de curiosidade em até 2 linhas |
| Apresentação | 4 por personagem | etiqueta que "bate" (escala 135 -> 100% em ~0,14 s; só em `.ass` escrito à mão com `\t` ou no HyperFrames, o `vedit captions` não anima) |
| Situação | 8 | momento engraçado ou de prova |
| Fala original | ~11 | única fala; trilha abaixa ~15 dB |
| Respiro | 4 | ironia ou pausa |
| Fim em loop | 8 | volta ao plano do gancho |

Cuidados: confira `avg_frame_rate` (o "120 fps" do ffprobe pode ser só base de tempo); calcule o crop 9:16 pela altura de cada arquivo (alturas variam); use só áudio sem direitos e sem palavrão. Liste os textos inventados para o humano revisar no preview.

## Fontes
- Netflix, "Timed Text Style Guide: General Requirements", https://partnerhelp.netflixstudios.com/hc/en-us/articles/215758617 (aberta em 2026-11; duração mínima/máxima de legenda).
- No Film School, "6 'Rules' for Good Cutting According to Oscar-Winning Editor Walter Murch", https://nofilmschool.com/2016/11/6-rules-good-cutting-according-oscar-winning-editor-walter-murch (aberta em 2026-11: a página só confirma emoção 51% e a ordem de sacrifício; os demais percentuais vêm de resumos secundários da obra de Murch, *In the Blink of an Eye*; reconfirmar).
- Defaults de pausa, punch-in e ritmo: consolidação operacional própria, não normas publicadas.
