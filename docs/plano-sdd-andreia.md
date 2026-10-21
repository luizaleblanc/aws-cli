# Plano de Ação SDD — Template Andréia no Amazon SES v2

## 1. Spec
- **Objetivo:** cadastrar o template `andreia-fim-de-ano` no SES v2 e validar o disparo.
- **Variável:** `{{nome}}`. **CTA:** https://forms.gle/uvVygZWyP7AonX1s6
- **Restrições:** região `us-east-2` explícita em todo comando; JSON sempre via `file://`.
- **Fonte da verdade:** https://docs.aws.amazon.com/pt_br/ses/latest/APIReference-V2/API_CreateEmailTemplate.html
- **Critérios de aceite:**
  - [ ] AC1: `get-email-template` retorna TemplateName e TemplateContent (Subject/Html/Text) iguais ao arquivo.
  - [ ] AC2: `test-render-email-template` renderiza `{{nome}}` sem placeholders sobrando.
  - [ ] AC3: e-mail de teste entregue; layout correto; o link redireciona ao formulário (a URL pode estar reescrita por click tracking).

## 2. Plan
| Fase | Subagente (Sonnet) | Entregável | Gate |
|---|---|---|---|
| Setup | Executor (principal) | `.gitignore`, `.claude/agents/*.md` | Diff aprovado |
| Requisitos | analyst | Copy final + variáveis | Copy aprovada |
| Design | template-designer | Diff de `templates/*.json` | Diff do JSON aprovado |
| Implementação | cli-runner | `create-email-template` | Comando aprovado |
| Testes | qa | Saídas do get, do test-render e do send | AC1–AC3 |
| Revisão/Docs | reviewer | README + bloco de commit | Árvore limpa |

## 3. Tasks
0. [x] Regras locais e subagentes definidos.
1. [x] Copy completa da Andréia recebida (mantida como original).
2. [x] Remetente: `comercial@grupoatalhos.com.br` (verificado). Produção habilitada (50.000/24h, 14/s) — 21/10/2026.
   2.1 [x] Identidade `grupoatalhos.com.br` criada (Easy DKIM); 3 CNAMEs publicados; DKIM SUCCESS.
   2.2 [x] MAIL FROM `envio.grupoatalhos.com.br` (fallback USE_DEFAULT_VALUE); MX + TXT publicados.
   [ ] Confirmar permissões IAM do usuário da CLI (ses:CreateEmailTemplate, GetEmailTemplate, UpdateEmailTemplate, TestRenderEmailTemplate, SendEmail, GetAccount).
3. [x] Arquivos do template gerados em `templates/`.
3.1 [x] Teste simples (sem template) para `contato@grupoatalhos.com.br` — entregue; autenticado após DKIM.
4. [x] `aws sesv2 create-email-template --cli-input-json file://templates/andreia-fim-de-ano.json --region us-east-2`
5. [x] `aws sesv2 get-email-template --template-name andreia-fim-de-ano --region us-east-2`
6. [x] `aws sesv2 test-render-email-template --template-name andreia-fim-de-ano --template-data file://templates/andreia-fim-de-ano.data.example.json --region us-east-2`
7. [ ] `aws sesv2 send-email --from-email-address "Grupo Atalhos Digitais <comercial@grupoatalhos.com.br>" --destination ToAddresses=DESTINATARIO_TESTE --content file://templates/send-test.json --region us-east-2`
7.1 [x] Teste por marca — o Duarte: From "o Duarte do Grupo Atalhos <comercial@grupoatalhos.com.br>", base de teste `bases/oduarte.example.csv` (contato@), tag `marca=oduarte`.
7.2 [ ] Receber bases reais por marca (Thiago) — fora do git.
7.3 [x] Script `scripts/send-base.sh`: primeiro nome da base (ou do e-mail); simulação por padrão. Teste real para luiza.leblanc@ enviado.
7.4 [x] Header preto com logo (S3 `email/logo-ad-preta.png`, HTTP 200).
7.5 [ ] `update-email-template` no SES + reenvio de teste com header.
   7.6 [ ] Foto do remetente da marca o Duarte (Thiago — Google Workspace).
8. [ ] README atualizado e bloco de commit entregue.
9. [ ] **Antes do disparo real (bloqueante):** definir e incluir o link de descadastro (destino e tratamento: formulário, resposta por e-mail ou lista de supressão do SES), com aprovação da Andréia.

## 4. Rollback
- `aws sesv2 delete-email-template --template-name andreia-fim-de-ano --region us-east-2` (irreversível; só com aprovação).
- Ajustes: `aws sesv2 update-email-template --cli-input-json file://templates/andreia-fim-de-ano.json --region us-east-2` (com novo diff).
