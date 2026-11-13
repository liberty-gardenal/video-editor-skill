> **Leia quando** tiver um vídeo longo (podcast, aula, entrevista, live) e precisar decidir quais trechos viram clipes, ou quando for pontuar, ranquear ou reprovar candidatos.
> **Regra de ordem:** a seleção roda inteira sobre transcrição com tempo por palavra (`vedit transcribe`, `vedit digest`); o vídeo só é aberto para cortar e para olhar as janelas já escolhidas.

# Seleção e scoring de clipes

## 1. Pré-requisito: hook, desenvolvimento, payoff

Antes de existir candidato, responda por escrito, só com o texto:

| Parte | Pergunta | Sem isso |
|---|---|---|
| **Hook** | Qual frase ou fato prende sem contexto externo? | volta para o texto, não vira candidato |
| **Desenvolvimento** | O que sustenta entre hook e payoff (mecanismo, prova, virada)? | vira opinião solta |
| **Payoff** | O que fecha a promessa? | promessa não paga = reprovado |

Por que texto primeiro: o transcrito inteiro de um episódio longo custa centenas de vezes mais tokens que as janelas candidatas (medido em um caso: ~3 mil tokens de janelas contra mais de 1 milhão do episódio). Use `vedit digest --windows "a-b,c-d"` para ler só o que importa. Decodificar o vídeo inteiro antes de selecionar travou uma execução de 3 h; nada visual é necessário para escolher.

## 2. Dois portões

| Portão | O clipe precisa | Falhar impede aprovar |
|---|---|---|
| **Editorial** | ser fiel, compreensível, ter desenvolvimento e payoff, terminar corretamente, não depender do episódio, não duplicar clipe melhor | sim |
| **Feed** | orientar rápido, comunicar promessa/stakes no tempo do perfil, entregar primeiro valor, progredir, manter dívida de contexto aceitável, pagar a promessa | sim |

Média alta não compensa falha crítica em qualquer portão.

## 3. Perfis de clipe e estrutura

| Perfil | Use para | Estrutura preferida |
|---|---|---|
| `fast_answer` (resposta rápida) | pergunta direta, tutorial, definição, opinião com razão clara | resposta/resultado -> motivo -> demonstração -> limite/implicação |
| `contrarian` | quebra de crença comum | crença comum -> quebra -> mecanismo -> prova -> nova regra |
| `money` (dinheiro/número) | número com escala | número/escala -> comparação -> mecanismo -> consequência (número sem escala não basta) |
| `story` | narrativa | consequência/stakes -> contexto mínimo -> obstáculo -> virada -> resolução |
| `humor` | piada, situação | setup mínimo -> expectativa -> ruptura -> reação (não destruir timing com cortes) |
| `transformation` | antes/depois | antes/depois -> ponto de mudança -> processo -> significado |
| `long_clip` | trecho de 90 s+ | capítulos internos, vários beats, valor cumulativo; **não é um Short lento** |

Tempos de orientação/proposta/primeiro valor por perfil estão em `psicologia-do-feed.md`, seção 4.

## 4. Dimensões de score (0-10)

`orientation`, `hook`, `proposition_clarity`, `first_value_speed`, `context_efficiency` (dívida de contexto baixa), `stakes`, `curiosity_integrity` (a lacuna é específica e paga), `progression`, `payoff`, `closure`, `self_contained`, `shareability`, `visual_opportunity`, `novelty`, `editability`, `truthfulness`.

- `truthfulness` **não entra na média**: é portão. Montagem que muda sentido, número alterado ou texto de tela que o áudio não sustenta reprova.
- O modelo julga as dimensões; o script mede tempos. Nunca digite à mão um valor que `vedit` calcula.

## 5. Métricas de tempo (marcadas pelo modelo, calculadas por script)

`orientation_latency`, `proposition_latency`, `first_value_latency`, `first_turn_latency`, `payoff_latency`, `maximum_seconds_without_new_value`. Reporte em segundos com 1 casa.

## 6. Hard fails (impedem "aprovado", sem exceção por média)

1. Assunto central não pode ser entendido.
2. Promessa não é paga.
3. Primeira frase depende claramente de algo dito antes.
4. Montagem altera significado, causalidade ou cronologia relevante.
5. Highlight reaparece no corpo sem propósito declarado.
6. Mais de 50% do clipe duplica uma versão melhor.
7. Final corta a resolução ou trunca a última palavra.
8. Trecho-chave da transcrição não foi confirmado no áudio.
9. Dívida de contexto crítica.
10. Sem primeiro valor até o limite máximo do perfil, sem justificativa.
11. Opinião sem razão, consequência ou tensão.
12. Suspense genérico que poderia ser trocado por promessa específica.
13. Texto de tela afirma algo que o áudio não sustenta.
14. O sentido depende de um recurso visual que não existe.

## 7. Ranking (só depois dos portões)

Pesos default (somam 1,0): hook 0,10; proposition_clarity 0,10; first_value_speed 0,09; context_efficiency 0,10; curiosity_integrity 0,08; progression 0,10; payoff 0,13; self_contained 0,10; shareability 0,08; visual_opportunity 0,04; novelty 0,04; editability 0,04.

```text
critical_floor = min(proposition_clarity, payoff, self_contained, truthfulness)
ajustado = média_ponderada * (0,70 + 0,30 * critical_floor / 10)
```

Por que o piso: uma média de 8 com `payoff` 3 mostra 8 e esconde o defeito que importa; o fator derruba para ~6,2. Mesmo assim, um hard fail reprova independentemente da nota. Pesos são ponto de partida; ajuste por conta/nicho e registre a mudança.

## 8. Sinais em frases (candidatos, não garantias)

| Bons sinais | Sinais de risco |
|---|---|
| número concreto; comparação inesperada | "isso", "ele", "aquilo" sem referente |
| "porque" com causalidade real | "como eu falei" (depende de trecho anterior) |
| mudança de decisão; confissão específica | lista longa de nomes próprios |
| conflito; antes/depois | opinião circular; frase forte sem explicação |
| pergunta respondida; detalhe visual verificável | resposta que depende de gráfico não mostrado |
| regra prática aplicável | conclusão fora do intervalo; exagero que o resto suaviza |
|  | contexto que começa antes do trecho detectado |

## 9. Duração, bordas e recortes

| Item | Default | Motivo |
|---|---|---|
| Alvo de duração | definido pelo perfil (tabela de psicologia); clipes de 35-75 s são comuns em cortes de podcast | depende do valor, não do relógio |
| Teto sem justificativa | 90 s; acima, tentar versão curta antes | retenção cai com enrolação |
| Início | 0,2-0,3 s antes da 1ª palavra | timing do ASR adianta ou atrasa 50-100 ms |
| Fim | 0,3-0,5 s depois da última sílaba, +1-2 s se a reação faz parte do payoff | evita corte amputado |
| Hook x clipe | se o hook ocupa mais de 50% do clipe, faça versão linear | vira montagem sem corpo |
| Sobreposição entre clipes | < 30% | senão é o mesmo clipe |
| Não abrir em | "mas", "então", "aí", "e", "porque", "uhum", "olha só", "agora" | conector depende do que veio antes |

Procure uma janela apertada dentro de um bloco antes de descartá-lo (um bloco de 55 s pode conter uma janela de 25 s autossuficiente). Use `vedit edges` em todo candidato.

## 10. Deduplicação e contenção

- Compare intervalos de tempo (interseção e contenção) por script e, depois, equivalência semântica entre clipes com pouca sobreposição temporal (a mesma ideia dita em dois momentos).
- Dois clipes com um contido no outro: publique só o melhor. Mantenha o de melhor combinação de independência, velocidade, payoff e editabilidade.
- Replay do highlight no corpo só com função narrativa declarada.

## 11. Quantidade

`max_clips` é **teto**, nunca meta. Retornar **zero aprovados** é resultado válido; relate o motivo de cada rejeição. Nunca crie clipe para encher a cota.

## 12. Erros reais, generalizados

| Erro | Correção |
|---|---|
| 4-6 s de preâmbulo antes do número | abrir **no** número |
| Tese ("a lição é X") antes do loop de curiosidade | pergunta primeiro; a moral vira payoff |
| Hook ocupando ~70% do clipe | reprovar como hook; fazer linear |
| Última palavra truncada ("muito gran-") | `vedit edges` e folga de saída |
| Abrir em "Uhum" ou outro marcador de escuta | mover o início para a imagem/frase forte |
| Dois cortes publicados, um contido no outro | checar contenção antes de cortar |
| Descartar bloco inteiro sem procurar janela interna | varrer janelas de 20-30 s |
| Revisor que só confirma | instruir a tentar derrubar; revisão cega recebe apenas transcrição, duração e descrição visual, sem scores nem justificativas |

## 13. Fluxo mínimo recomendado

`vedit transcribe` -> `vedit digest` -> candidatos com hook/desenvolvimento/payoff -> auditoria (tempos, contenção, bordas) -> revisão cega -> dedupe -> corte de pré-visualização horizontal para o humano aprovar -> só então vertical (`enquadramento-vertical.md`). Pare e mostre quando o humano precisa decidir; renderizar 20 verticais para descobrir que 12 não servem é o custo que o portão evita.

## Fontes
- TikTok, "Creative best practices for performance ads", https://ads.tiktok.com/resources/help/article/creative-best-practices?lang=en (aberta em 2026-11; proposta em 3 s, gancho em 6 s).
- Meta, "Reels creative strategies", https://www.facebook.com/business/news/reels-creative-strategies (aberta em 2026-11).
- Pesos, perfis e hard fails: consolidação própria a partir de uso operacional; são defaults a calibrar, não resultado de estudo publicado.
