# Contribuindo

Contribuições são bem-vindas: correções, novos playbooks, melhorias de referência, testes.
Idioma da documentação e das skills: português do Brasil. Mensagens de commit em português
ou inglês, curtas e no imperativo.

## Antes de abrir um PR

- Rode `vedit doctor` e a suíte de testes do repositório (veja `tests/` e o CI).
- Rode `claude plugin validate .` para validar `plugin.json` e `marketplace.json`.
- Toda alteração de comando deve atualizar `docs/cli.md`; skills e playbooks só podem citar
  comandos e flags que existem lá.

## Regras do conteúdo

- **Nada pessoal.** Sem caminhos absolutos de máquina, nomes de pessoas, clientes, empresas ou
  projetos reais, e-mails, telefones, chaves ou nomes de arquivos reais. Use exemplos
  inventados e genéricos ("uma clínica", "um curso de inglês").
- **Nada específico de máquina.** Generalize: "macOS Intel", "ffmpeg sem libass".
- **Sem copiar** texto de outras fontes cuja licença não seja clara; reescreva com suas palavras.
- **Sem promessa de desempenho** ("viral garantido", "aumenta conversão em X%").
- Só afirme o que foi verificado. Instalação de terceiros (HyperFrames etc.): confira no README do projeto e, se não der, diga "confira no README".

## Skills, playbooks e agentes

- `SKILL.md` fica enxuto (cerca de 250 linhas) e só roteia; o detalhe vai para playbooks e referências.
- Cada playbook tem passos com comandos exatos, um portão por fase, ordem do mais barato e
  decisivo para o mais caro, e checklist final.
- Subagentes têm frontmatter válido (`name`, `description`, `tools`, `model`), prefixo `ve-`,
  entrada e saída definidas, o que **não** podem receber e a lista de falhas. Prefira ferramentas somente leitura.
- Mantenha os invariantes: transcrição por palavra antes do bruto, EDL como fonte única em
  quadro inteiro, o modelo decide e o script mede, nada aprovado de primeira, `vedit verify`
  antes da entrega.

## Código

Veja a documentação em `docs/cli.md`. Núcleo só com biblioteca padrão e ffmpeg; dependências
pesadas são opcionais e importadas sob demanda com mensagem de instalação clara.

## Licença

Ao contribuir, você concorda que sua contribuição será licenciada sob a MIT.
