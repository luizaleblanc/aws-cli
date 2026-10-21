#!/usr/bin/env bash
# Envia o template para cada lead de uma base CSV (email,nome), com a persona da marca.
# Primeiro nome: 1ª palavra da coluna `nome`; se vazia, deriva do e-mail (luiza.leblanc@ -> Luiza).
# E-mails genéricos (contato@, comercial@...) sem nome são pulados.
# Uso: scripts/send-base.sh BASE_CSV "NOME DA MARCA" TAG_MARCA [--enviar]
# Sem --enviar, apenas simula (nada é enviado).
set -euo pipefail
BASE="$1"; MARCA="$2"; TAG="$3"; MODO="${4:-}"
TEMPLATE="andreia-fim-de-ano"; REGION="us-east-2"
FROM="$MARCA do Grupo Atalhos <comercial@grupoatalhos.com.br>"
GENERICOS="contato comercial atendimento vendas suporte financeiro rh noreply no-reply admin info"
TMP=$(mktemp); trap 'rm -f "$TMP"' EXIT
primeiro_nome() {
  local n="${1%% *}"
  if [ -z "$n" ]; then
    n="${2%%@*}"; n="${n%%[._-]*}"; n="${n//[0-9]/}"
    case " $GENERICOS " in *" ${n,,} "*) n="";; esac
  fi
  [ -n "$n" ] && echo "$n" | awk '{print toupper(substr($0,1,1)) tolower(substr($0,2))}'
}
tail -n +2 "$BASE" | tr -d '\r' | while IFS=, read -r email nome; do
  [ -z "$email" ] && continue
  pn=$(primeiro_nome "${nome:-}" "$email" || true)
  if [ -z "$pn" ]; then echo "PULADO (sem nome): $email"; continue; fi
  data=$(jq -cn --arg nome "$pn" '{nome:$nome}')
  jq -cn --arg t "$TEMPLATE" --arg d "$data" '{Template:{TemplateName:$t,TemplateData:$d}}' > "$TMP"
  if [ "$MODO" = "--enviar" ]; then
    id=$(aws sesv2 send-email --from-email-address "$FROM" --destination "ToAddresses=$email" \
      --content "file://$TMP" --email-tags "Name=marca,Value=$TAG" --region "$REGION" --query MessageId --output text)
    echo "ENVIADO $email ($pn) $id"
    sleep 0.1
  else
    echo "SIMULAÇÃO $email -> \"$pn, ouvi dizer...\" / \"Oi, $pn\""
  fi
done
