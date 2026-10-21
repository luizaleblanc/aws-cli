# aws-cli — Disparos de e-mail com templates no Amazon SES v2

Provisiona e testa templates de e-mail no Amazon SES (API v2) via AWS CLI, para disparo automatizado.

## Pré-requisitos
- AWS CLI v2 ≥ 2.32.0 (`aws --version`)
- Autenticação: `aws login` (recomendado) ou `aws configure`
- Região: `us-east-2`
- Identidades verificadas no SES (us-east-2): domínio `grupoatalhos.com.br` (DKIM) e MAIL FROM `envio.grupoatalhos.com.br`
- Permissões IAM: `ses:CreateEmailTemplate`, `ses:GetEmailTemplate`, `ses:UpdateEmailTemplate`, `ses:TestRenderEmailTemplate`, `ses:SendEmail`, `ses:GetAccount`
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
  send-test.json                        # payload do send-email de teste
  smoke-test.json                       # teste simples sem template
  send-oduarte-test.json                # teste da marca o Duarte
scripts/send-base.sh                    # envio por base de leads (primeiro nome)
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

> **Antes do disparo real:** o template precisa de link de descadastro (pendente, ver plano — task 9).

## Bases de leads por marca e persona do remetente
Cada marca tem sua própria base de leads. O disparo usa o mesmo template e o mesmo e-mail, mas o nome exibido do remetente segue a marca da base:

| Marca (base) | `--from-email-address` |
|---|---|
| o Duarte | `"o Duarte do Grupo Atalhos <comercial@grupoatalhos.com.br>"` |

- Bases reais ficam fora do git (`bases/*.csv`); no repo só há exemplos fictícios (`bases/*.example.csv`).
- Formato da base: `email,nome` (o `nome` alimenta `{{nome}}` no template).
- Rastreio por marca: `--email-tags Name=marca,Value=NOME_DA_MARCA`.
- Não usa Locatários do SES; a persona é definida por envio.
- Disparo para base real só após o link de descadastro (task 9 do plano).

Teste da marca o Duarte:
```bash
aws sesv2 send-email --from-email-address "o Duarte do Grupo Atalhos <comercial@grupoatalhos.com.br>" --destination ToAddresses=DESTINATARIO_TESTE --content file://templates/send-oduarte-test.json --email-tags Name=marca,Value=oduarte --region us-east-2
```

Envio por base — o primeiro nome vem da coluna `nome` (1ª palavra) ou, se vazia, do e-mail (`luiza.leblanc@` → Luiza); e-mails genéricos sem nome são pulados:
```bash
scripts/send-base.sh bases/oduarte.csv "o Duarte" oduarte            # simulação
scripts/send-base.sh bases/oduarte.csv "o Duarte" oduarte --enviar   # envio real
```

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
