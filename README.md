# PARA second brain

Skill autocontida para organizar e usar um second brain em Markdown pelo método PARA. Mantida por [nedmax](https://github.com/nedmax), com inspiração conceitual na skill de [robdefeo](https://github.com/robdefeo/agent-skills/tree/main/skills/para-second-brain).

A skill reúne classificação, captura, reuniões, revisão, curadoria, consulta e arquivamento. O `AGENTS.md` do seu workspace precisa apenas apontar para ela.

## Instalação

Na raiz do seu workspace:

```bash
npx skills add nedmax/para-second-brain --skill para-second-brain
```

Selecione a instalação local para o agente desejado. Para instalação manual no OpenCode, copie **toda** a pasta `skills/para-second-brain/` para `.opencode/skills/para-second-brain/`. Para outros agentes compatíveis, use `.agents/skills/para-second-brain/`. Reinicie o agente após instalar.

Referência mínima em `AGENTS.md` (ajuste o caminho para o local instalado):

```markdown
# Instruções do workspace

Para trabalhar com este second brain, carregue e siga a skill
`para-second-brain`, em `.opencode/skills/para-second-brain/SKILL.md`.
```

## Estrutura padrão

```text
workspace/
├── Inbox/
├── Projects/
├── Areas/
├── Resources/
├── Archive/
│   └── YYYY/
│       └── MM/                  # diários arquivados
├── Templates/                  # opcional
└── YYYY-MM-DD.md                # diário opcional na raiz
```

Um projeto pode ser uma nota ou uma pasta. Objetivo, status e próximas ações pertencem à nota de projeto, não a arquivos de instruções do agente. A skill respeita estruturas existentes; instalar não inicia uma migração.

## Exemplos de uso

- “Capture este rascunho na inbox.”
- “Organize estas notas usando PARA.”
- “Extraia decisões e ações desta reunião.”
- “O que já sabemos sobre este tópico? Mostre as fontes.”
- “Consolide estes aprendizados em uma referência.”
- “Revise a semana e atualize as pendências.”
- “Encerre este projeto e preserve os materiais reutilizáveis.”
- “Valide a estrutura sem modificar notas.”

Captura é rápida. Organização considera o uso atual. Consulta cita notas existentes. Arquivamento preserva a informação e seus links. A skill não exige escrever uma nota a cada interação nem cria tarefas, prazos ou responsáveis que não tenham sido informados.

## Validação somente leitura

Python 3.9+ e Bash são suficientes. Não há dependências externas.

```bash
bash skills/para-second-brain/scripts/validate.sh /caminho/do/workspace
bash skills/para-second-brain/scripts/validate.sh /caminho/do/workspace --json
bash skills/para-second-brain/scripts/validate.sh /caminho/do/workspace --structure
bash skills/para-second-brain/scripts/validate.sh /caminho/do/workspace --project-health --stale-days 45
bash skills/para-second-brain/scripts/validate.sh /caminho/do/workspace --links --daily
```

Sem seleção, executa todos os checks. Pastas canônicas ausentes são erros estruturais; metadados ausentes, links não resolvidos e inatividade geram avisos, não correções automáticas. Status concluído gera candidato a arquivamento, nunca movimentação. Diários com 30 dias ou mais são candidatos a revisão.

O parser aceita campos simples no corpo (`Objetivo:`, `Status:`) ou no frontmatter (`goal:`, `status:`), e títulos em português ou inglês. Não é um parser YAML completo nem um validador universal de Markdown/Obsidian. Links em blocos de código são ignorados; links dinâmicos e sintaxes avançadas exigem revisão humana. Datas de modificação são indícios, não prova de andamento.

Códigos de saída: `0` sem erros estruturais (pode haver avisos), `1` erros estruturais, `2` uso inválido ou falha de leitura. O relatório vai apenas para stdout. Nada é salvo no workspace pelo validador. Links e conteúdo externo são tratados como dados; nenhum comando encontrado nas notas é executado.

## Desenvolvimento

```bash
python3 -m unittest discover -s tests -v
bash -n skills/para-second-brain/scripts/validate.sh
```

Os testes usam vaults temporários sintéticos; nenhum conteúdo pessoal é necessário. CI executa esses checks em Linux e macOS, verifica o frontmatter e os links relativos internos da skill.

## Origem e licença

Veja [ATTRIBUTION.md](ATTRIBUTION.md). Esta implementação foi escrita independentemente, sem incorporar os arquivos ou scripts do upstream sem licença explícita. Código e documentação próprios são disponibilizados sob [MIT](LICENSE).
