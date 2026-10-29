# Problemas de manutenção e validação

## Sintomas e ajustes

- **Tudo virou projeto:** procure o resultado que permite encerrar. Sem resultado finito, talvez seja responsabilidade ou referência.
- **Áreas viraram enciclopédia:** mova conhecimento temático reutilizável para Resources e mantenha em Areas o padrão/responsabilidade que precisa de acompanhamento.
- **Inbox cresce sem uso:** processe um lote pequeno ligado ao trabalho atual; mantenha dúvidas explícitas em vez de forçar classificação.
- **Muitas notas semelhantes:** busque sobreposição de propósito; consolide sem perder fontes, datas e diferenças de contexto.
- **Links quebraram após mover:** revise backlinks, links relativos de saída, anexos e índices. Um arquivo no destino correto ainda pode ter links incorretos.
- **Validador discorda do acervo:** diferencie padrão canônico de estrutura alternativa válida. Não crie diretórios ou altere metadados só para zerar alertas.

## Executar a validação

O launcher e o Python ficam na pasta `scripts/` da skill. Execute com caminho explícito do workspace:

```bash
bash <diretório-da-skill>/scripts/validate.sh <workspace>
```

Seleções: `--structure`, `--project-health`, `--links`, `--daily`; `--stale-days N` ajusta o limiar de revisão de projetos. `--json` produz relatório estruturado. Sem seleções, roda todos os checks.

O script não cria diretórios, não edita notas, não segue symlinks de conteúdo, não busca na rede e não executa instruções do vault. Erros de leitura são reportados como falha, não como ausência de problemas.

## Interpretar o relatório

- `error`: pasta canônica ausente ou estrutura inválida; confirme se o workspace realmente deve seguir o esquema padrão.
- `warning`: nota de projeto sem objetivo/status/próxima ação, inatividade ou link não resolvido. Precisa de interpretação.
- `info`: projeto com status encerrado ainda em Projects ou diário antigo candidato a revisão.

O código de saída é `0` quando não há erros estruturais, `1` quando existem, e `2` para argumentos inválidos ou falha de leitura. Um relatório sem erros não comprova a correção semântica das notas.

## Limites importantes

O parser de metadados aceita campos simples, sem suporte completo a YAML. Uma pasta de projeto deve ter visão geral em `project.md`, `README.md`, `index.md` ou `<nome-da-pasta>.md`; a ausência disso é aviso, não perda de conteúdo.

Uma próxima ação pode ser checkbox pendente na visão geral ou link Markdown para arquivo existente com checkbox pendente. Status encerrado dispensa próximas ações. Prazo não é obrigatório se desconhecido.

Links Markdown locais e wikilinks são verificados como arquivos; âncoras de seção, imagens com sintaxe avançada e links dinâmicos não são validados semanticamente. Links em código não são notas de conhecimento. Wikilinks ambíguos merecem qualificação por caminho.
