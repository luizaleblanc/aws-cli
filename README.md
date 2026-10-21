# aws-cli — Disparos de e-mail com templates no Amazon SES v2

Provisiona e testa templates de e-mail no Amazon SES (API v2) via AWS CLI, para disparo automatizado.

## Pré-requisitos
- AWS CLI v2 ≥ 2.32.0 (`aws --version`)
- Autenticação: `aws login` (recomendado) ou `aws configure`
- Região: `us-east-2`
- Identidade verificada no SES: domínio `grupoatalhos.com.br` (DKIM)
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
templates/
  andreia-fim-de-ano.json               # payload CreateEmailTemplate
  andreia-fim-de-ano.data.example.json  # exemplo de TemplateData (dados fictícios)
  send-test.json                        # payload do send-email de teste
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
