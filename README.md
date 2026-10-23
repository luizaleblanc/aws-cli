# aws-cli — Disparos de e-mail com templates no Amazon SES v2

Provisiona e testa templates de e-mail no Amazon SES (API v2) via AWS CLI, para disparo automatizado.

## Pré-requisitos
- AWS CLI v2 ≥ 2.32.0 (`aws --version`)
- Autenticação: `aws login` (recomendado) ou `aws configure`
- Região: `us-east-2`
- Identidades verificadas no SES (us-east-2): domínio `grupoatalhos.com.br` (DKIM) e MAIL FROM `envio.grupoatalhos.com.br`
- Permissões IAM: `ses:CreateEmailTemplate`, `ses:GetEmailTemplate`, `ses:UpdateEmailTemplate`, `ses:TestRenderEmailTemplate`, `ses:SendEmail`, `ses:GetAccount`, `ses:CreateContactList`; para o disparo automático, também IAM, Lambda, EventBridge Scheduler e S3
- Sem AWS CLI logado no computador: os comandos rodam no **AWS CloudShell** (arquivos enviados por *Ações → Carregar arquivo*)
- Produção: conta fora do sandbox. Em sandbox, o destinatário de teste também precisa estar verificado.

Checar a configuração:
```bash
aws sts get-caller-identity
aws sesv2 get-account --region us-east-2
```

## Estrutura
```
README.md
.gitignore
assets/
  logo-ad-preta.png                     # logo do header (hospedada no S3)
bases/
  oduarte.example.csv                   # base de teste (fictícia)
templates/
  andreia-fim-de-ano.json               # payload CreateEmailTemplate
  andreia-fim-de-ano.data.example.json  # exemplo de TemplateData (dados fictícios)
  andreia-fim-de-ano.data.neutro.example.json  # TemplateData sem nome (saudação neutra)
  send-test.json                        # payload do send-email de teste
  smoke-test.json                       # teste simples sem template
  send-oduarte-test.json                # teste da marca o Duarte
  contact-list.json                     # lista de contatos do SES (descadastro por marca)
scripts/send-base.sh                    # envio manual por base de leads (lote 1, testes)
infra/disparo-diario/                   # disparo diário automático (Lambda + EventBridge Scheduler)
  lambda_function.py                    # código da Lambda
  env.json                              # variáveis da campanha
  estado-inicial.json                   # posição inicial na base
  trust-*.json, policy-*.json           # funções e políticas IAM
docs/plano-sdd-andreia.md               # plano de ação SDD
.claude/agents/                         # subagentes SDLC
```

## Como funciona o disparo
1. **Template:** fica salvo no SES com assunto, HTML e texto contendo variáveis `{{nome}}`.
2. **Envio:** cada `send-email` informa o nome do template e um `TemplateData` (string JSON) com os valores daquele destinatário. O SES substitui as variáveis e entrega.
3. **Personalização:** acontece no `TemplateData`; não exige locatários (tenants).

## Passo a passo
> Comandos válidos em PowerShell e Bash: todo JSON é passado via `file://`. Troque `DESTINATARIO_TESTE` pelo e-mail de teste.

```bash
# 0. (Opcional) Teste simples de entrega, sem template
aws sesv2 send-email --from-email-address "Grupo Atalhos Digitais <comercial@grupoatalhos.com.br>" --destination ToAddresses=DESTINATARIO_TESTE --content file://templates/smoke-test.json --region us-east-2
# 1. Criar
aws sesv2 create-email-template --cli-input-json file://templates/andreia-fim-de-ano.json --region us-east-2
# 2. Verificar
aws sesv2 get-email-template --template-name andreia-fim-de-ano --region us-east-2
# 3. Pré-visualizar a renderização
aws sesv2 test-render-email-template --template-name andreia-fim-de-ano --template-data file://templates/andreia-fim-de-ano.data.example.json --region us-east-2
# 4. Enviar teste
aws sesv2 send-email --from-email-address "Grupo Atalhos Digitais <comercial@grupoatalhos.com.br>" --destination ToAddresses=DESTINATARIO_TESTE --content file://templates/send-test.json --region us-east-2
```

> Se um configuration set usar click tracking, o SES reescreve os links (o redirecionamento continua funcionando).

## Descadastro (gerenciado pelo SES)
O rodapé do template tem `{{amazonSESUnsubscribeUrl}}`. Quando o envio informa `--list-management-options`, o SES troca o placeholder pelo link de cada destinatário, adiciona os cabeçalhos `List-Unsubscribe` (um clique) e bloqueia novos envios para quem saiu. Cada marca é um tópico da lista `grupoatalhos-leads`.

```bash
# Uma vez: criar a lista com o tópico da marca
aws sesv2 create-contact-list --cli-input-json file://templates/contact-list.json --region us-east-2
# Quem se descadastrou
aws sesv2 list-contacts --contact-list-name grupoatalhos-leads --filter FilteredStatus=OPT_OUT,TopicFilter={TopicName=oduarte} --region us-east-2
```
Nova marca: acrescentar um tópico com `aws sesv2 update-contact-list`. Doc: https://docs.aws.amazon.com/ses/latest/dg/sending-email-subscription-management.html

## Bases de leads por marca e persona do remetente
Cada marca tem sua própria base de leads. O disparo usa o mesmo template e o mesmo e-mail, mas o nome exibido do remetente segue a marca da base:

| Marca (base) | `--from-email-address` |
|---|---|
| o Duarte | `"o Duarte do Grupo Atalhos <comercial@grupoatalhos.com.br>"` |

- Bases reais ficam fora do git (`bases/*.csv`); no repo só há exemplos fictícios (`bases/*.example.csv`).
- Formato da base: `email,nome` (o `nome` alimenta `{{nome}}` no template).
- Rastreio por marca: `--email-tags Name=marca,Value=NOME_DA_MARCA`.
- Não usa Locatários do SES; a persona é definida por envio.
- Foto do remetente: não é controlada pelo SES. O Gmail exibe a foto do perfil Google Workspace do **endereço** remetente (vale para todos os e-mails desse endereço). Configuração da foto: responsabilidade do Thiago (Admin do Workspace).
- Foto específica por marca exige endereço próprio da marca (ex.: `oduarte@grupoatalhos.com.br`, usuário no Workspace com a foto), mantendo `--reply-to-addresses comercial@grupoatalhos.com.br` para as respostas. O domínio já verificado no SES cobre o novo endereço.
- O `send-base.sh` envia com `--list-management-options ContactListName=grupoatalhos-leads,TopicName=TAG_MARCA`, ativando o descadastro.

Teste da marca o Duarte:
```bash
aws sesv2 send-email --from-email-address "o Duarte do Grupo Atalhos <comercial@grupoatalhos.com.br>" --destination ToAddresses=DESTINATARIO_TESTE --content file://templates/send-oduarte-test.json --email-tags Name=marca,Value=oduarte --region us-east-2
```

Envio por base — o primeiro nome vem da coluna `nome` (1ª palavra). Na higiene da base, o nome só é tirado do e-mail quando é inequívoco (`luizaa.fq@` → Luiza); senão a coluna fica vazia e o template usa a saudação neutra (assunto "Ouvi dizer que…", corpo "Oi!"). E-mails genéricos sem nome são pulados:
```bash
scripts/send-base.sh bases/oduarte.csv "o Duarte" oduarte            # simulação
scripts/send-base.sh bases/oduarte.csv "o Duarte" oduarte --enviar   # envio real
```

## Operação de disparos em massa
Limites da conta (us-east-2): **50.000 e-mails / 24 h** e **14 e-mails/s**.

- **Origem da base:** a planilha da campanha é exportada como CSV (`email,nome`) para `bases/<marca>.csv`, que fica fora do git. Use uma base por marca.
- **Aquecimento do domínio:** mesmo cabendo na cota, a base não é enviada de uma vez. Lotes diários: **1k → 2k → 3k → 4k**; cada lote só sai se o anterior estiver saudável.
- **Taxa:** no máximo ~10 envios/s, abaixo do limite de 14/s.
- **Critérios de pausa:** bounce > 3% ou reclamação > 0,05%. A AWS coloca a conta em revisão a partir de 5% de bounce ou 0,1% de reclamação.

| # | Etapa | Bloqueia se… |
|---|---|---|
| 0 | Lista de contatos criada (descadastro) e configuration set com métricas de reputação | a lista não existir |
| 1 | Higiene da base: normalizar, remover duplicados, inválidos e a lista de supressão do SES | sobrar menos de 90% de e-mails válidos |
| 2 | Simulação (`send-base.sh` sem `--enviar`): conferir nomes e pulados | houver nomes errados |
| 3 | Envio-semente para ~5 caixas internas (Gmail/Outlook) | cair no spam |
| 4 | Envio do lote do dia | — |
| 5 | Após 24 h: conferir bounce e reclamação (`aws sesv2 get-account --region us-east-2`) | ultrapassar os critérios de pausa |
| 6 | Próximo lote, retomando de onde parou | — |

As etapas 4 a 6 são feitas pelo disparo diário automático (seção abaixo). O lote 1 pode sair à mão pelo `send-base.sh`.

> **Pendente:** configuration set com eventos por e-mail (entrega, abertura, clique) e script de higiene da base no repositório.

### Campanha o Duarte (out/2026)
| Lote | Data | E-mails | Como |
|---|---|---|---|
| 1 | 22/10 | 1.000 | manual: 34 bounces (3,4%), 1 reclamação (0,1%) → pausado em 23/10 |
| 2 | 24/10 | 500 | automático, 10h (retomada aceitando o lote 1) |
| 3 | 25/10 | 1.000 | automático, se o lote anterior ficar abaixo dos limites |
| 4 | 26/10 | 1.500 | idem |
| 5 | 27/10 | 2.000 | idem |
| 6 | 28/10 | 2.500 | idem |
| 7 | 29/10 | 1.659 (resto) | idem |

Base: 10.159 e-mails válidos (de 10.275), 9.085 com nome e 1.074 com saudação neutra. Ao terminar: apagar o agendamento e o bucket `grupoatalhos-disparos-024378233621` (dados reais).

### Acompanhar os envios (CloudShell)
```bash
aws sesv2 get-account --region us-east-2 --query '{Status:EnforcementStatus,Enviados24h:SendQuota.SentLast24Hours}'
aws logs tail /aws/lambda/disparo-diario --since 1h --region us-east-2
aws sesv2 list-suppressed-destinations --region us-east-2
```

## Disparo diário automático (`infra/disparo-diario/`)
EventBridge Scheduler (todo dia, 10h de Brasília) → Lambda `disparo-diario`:
1. Confere o lote anterior inteiro (desde o início dele, em `inicio_lote`); se bounce ≥ 3% ou reclamação ≥ 0,05%, não envia, grava `pausado: true` e avisa. Pausado, não volta sozinho.
2. Lê a base e a posição em `s3://grupoatalhos-disparos-024378233621/<marca>/` (bucket privado; a base nunca entra no git).
3. Envia o lote do dia (tamanhos em `LOTES`), com descadastro, e salva a nova posição em `estado.json`.
4. Manda um resumo para `comercial@` e `luiza.leblanc@`.

| Arquivo | Uso |
|---|---|
| `lambda_function.py` | código da Lambda (Python 3.12) |
| `env.json` | variáveis: marca, tag, template, lista, lotes, destinatários do resumo |
| `estado-inicial.json` | posição inicial na base (ex.: lote 1 já enviado à mão → `posicao: 1000`) |
| `trust-*.json`, `policy-*.json` | funções IAM da Lambda e do agendador |

Criação (CloudShell, na pasta com os arquivos de `infra/disparo-diario/`):
```bash
B=grupoatalhos-disparos-024378233621
aws s3api create-bucket --bucket $B --region us-east-2 --create-bucket-configuration LocationConstraint=us-east-2
aws s3api put-public-access-block --bucket $B --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true --region us-east-2
aws s3 cp BASE.csv s3://$B/oduarte/base.csv --region us-east-2
aws s3 cp estado-inicial.json s3://$B/oduarte/estado.json --region us-east-2
aws iam create-role --role-name disparo-diario-lambda --assume-role-policy-document file://trust-lambda.json
aws iam put-role-policy --role-name disparo-diario-lambda --policy-name disparo-diario --policy-document file://policy-lambda.json
aws iam create-role --role-name disparo-diario-scheduler --assume-role-policy-document file://trust-scheduler.json
aws iam put-role-policy --role-name disparo-diario-scheduler --policy-name invocar-lambda --policy-document file://policy-scheduler.json
zip -q funcao.zip lambda_function.py && sleep 15
aws lambda create-function --function-name disparo-diario --runtime python3.12 --handler lambda_function.lambda_handler --role arn:aws:iam::024378233621:role/disparo-diario-lambda --zip-file fileb://funcao.zip --timeout 900 --memory-size 256 --environment file://env.json --region us-east-2
aws scheduler create-schedule --name disparo-diario-oduarte --region us-east-2 --schedule-expression "cron(0 10 * * ? *)" --schedule-expression-timezone America/Sao_Paulo --flexible-time-window Mode=OFF --target '{"Arn":"arn:aws:lambda:us-east-2:024378233621:function:disparo-diario","RoleArn":"arn:aws:iam::024378233621:role/disparo-diario-scheduler","RetryPolicy":{"MaximumRetryAttempts":0}}'
```
`MaximumRetryAttempts: 0` evita reenvio duplicado se a Lambda falhar. A Lambda também não envia duas vezes no mesmo dia (`ultimo_dia` em `estado.json`).

Rodar agora (fora do horário): `aws lambda invoke --function-name disparo-diario --region us-east-2 out.json` — envia o próximo lote, se ainda não houve envio hoje.
Pausar/encerrar: `aws scheduler delete-schedule --name disparo-diario-oduarte --region us-east-2`. Quando a base termina, a Lambda manda "concluído" e não envia mais nada.
Retomar após pausa (aceitando o lote anterior): gravar um estado novo com `pausado: false` e `inicio_lote` vazio, mantendo `posicao`:
```bash
aws s3 cp s3://grupoatalhos-disparos-024378233621/oduarte/estado.json - --region us-east-2   # ver posição atual
```
Limpeza ao final: `aws s3 rb s3://grupoatalhos-disparos-024378233621 --force --region us-east-2`.

## DNS do domínio (GoDaddy)
- 3 CNAMEs DKIM `*._domainkey` → `*.dkim.amazonses.com` (publicados).
- MX `envio` → `10 feedback-smtp.us-east-2.amazonses.com`; TXT `envio` → `v=spf1 include:amazonses.com ~all` (publicados).
- DMARC existente: `p=quarantine` (alinhamento relaxado).

## Imagens do e-mail (S3)
- Bucket `grupoatalhos-email-assets-024378233621` (us-east-2); leitura pública apenas em `email/*`.
- Logo do header: `https://grupoatalhos-email-assets-024378233621.s3.us-east-2.amazonaws.com/email/logo-ad-preta.png` (fonte: `assets/logo-ad-preta.png`).
- Após alterar o template: `aws sesv2 update-email-template --cli-input-json file://templates/andreia-fim-de-ano.json --region us-east-2`.

## Atualizar / remover
```bash
aws sesv2 update-email-template --cli-input-json file://templates/andreia-fim-de-ano.json --region us-east-2
# IRREVERSÍVEL: só com aprovação
aws sesv2 delete-email-template --template-name andreia-fim-de-ano --region us-east-2
```

## Fonte da verdade
- https://docs.aws.amazon.com/pt_br/ses/latest/APIReference-V2/API_CreateEmailTemplate.html
- https://awscli.amazonaws.com/v2/documentation/api/latest/reference/sesv2/index.html

## Regras do projeto
- O push é manual e feito pela mantenedora.
- O README precisa estar atualizado antes de cada push.
- Credenciais e dados reais de destinatários nunca são versionados.
