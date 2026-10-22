# Disparo diário: confere a saúde do dia anterior, envia o lote do dia e manda um resumo.
# Estado (posição na base e lote atual) fica em S3; a base nunca entra no repositório.
import csv, io, json, os, time
from datetime import datetime, timedelta, timezone

import boto3

s3 = boto3.client("s3")
ses = boto3.client("sesv2")
cw = boto3.client("cloudwatch")

BUCKET = os.environ["BUCKET"]
PREFIXO = os.environ["PREFIXO"]                      # ex.: oduarte/
MARCA = os.environ["MARCA"]                          # ex.: o Duarte
TAG = os.environ["TAG"]                              # ex.: oduarte (tag e tópico da lista)
TEMPLATE = os.environ["TEMPLATE"]
LISTA = os.environ["LISTA"]
LOTES = [int(x) for x in os.environ["LOTES"].split(",")]   # tamanho de cada lote, em ordem
RESUMO_PARA = os.environ["RESUMO_PARA"].split(",")
REMETENTE = "comercial@grupoatalhos.com.br"
FROM = f"{MARCA} do Grupo Atalhos <{REMETENTE}>"
MAX_BOUNCE, MAX_COMPLAINT = 0.03, 0.0005
GENERICOS = {"contato", "comercial", "atendimento", "vendas", "suporte", "financeiro",
             "rh", "noreply", "no-reply", "admin", "info"}


def ler(key):
    return s3.get_object(Bucket=BUCKET, Key=PREFIXO + key)["Body"].read().decode("utf-8")


def gravar(key, texto):
    s3.put_object(Bucket=BUCKET, Key=PREFIXO + key, Body=texto.encode("utf-8"))


def soma(metrica, inicio, fim):
    r = cw.get_metric_statistics(Namespace="AWS/SES", MetricName=metrica, StartTime=inicio,
                                 EndTime=fim, Period=86400 * 2, Statistics=["Sum"])
    return sum(p["Sum"] for p in r["Datapoints"])


def resumo(assunto, linhas):
    ses.send_email(FromEmailAddress=FROM, Destination={"ToAddresses": RESUMO_PARA},
                   Content={"Simple": {"Subject": {"Data": f"[Disparo {MARCA}] {assunto}"},
                                       "Body": {"Text": {"Data": "\n".join(linhas)}}}})


def primeiro_nome(nome):
    n = (nome or "").strip().split(" ")[0]
    return n[:1].upper() + n[1:].lower() if n else ""


def lambda_handler(event, context):
    estado = json.loads(ler("estado.json"))
    hoje = datetime.now(timezone(timedelta(hours=-3))).date().isoformat()
    if estado.get("ultimo_dia") == hoje:
        return {"status": "ja_enviado_hoje"}

    base = list(csv.DictReader(io.StringIO(ler("base.csv"))))
    pos, lote = estado["posicao"], estado["lote"]
    if pos >= len(base):
        resumo("concluído", [f"Base inteira enviada ({len(base)} e-mails). Desative o agendamento."])
        return {"status": "concluido"}

    # Saúde das últimas 24 h antes de enviar mais.
    fim = datetime.now(timezone.utc); inicio = fim - timedelta(hours=24)
    env, bnc, cpl = soma("Send", inicio, fim), soma("Bounce", inicio, fim), soma("Complaint", inicio, fim)
    tx_b, tx_c = (bnc / env, cpl / env) if env else (0.0, 0.0)
    saude = [f"Últimas 24 h: {env:.0f} enviados, {bnc:.0f} bounces ({tx_b:.2%}), "
             f"{cpl:.0f} reclamações ({tx_c:.3%})."]
    if tx_b >= MAX_BOUNCE or tx_c >= MAX_COMPLAINT:
        resumo("PAUSADO", saude + ["Acima do limite (bounce 3% / reclamação 0,05%). Nada foi enviado hoje.",
                                   f"Próximo lote começa na linha {pos + 1}."])
        return {"status": "pausado"}

    tamanho = LOTES[min(lote, len(LOTES) - 1)]
    fatia = base[pos:pos + tamanho]
    enviados, pulados, erros = 0, 0, []
    for i, linha in enumerate(fatia):
        email = linha["email"].strip()
        pn = primeiro_nome(linha.get("nome"))
        if not pn and email.split("@")[0].split(".")[0].lower() in GENERICOS:
            pulados += 1
            continue
        try:
            ses.send_email(
                FromEmailAddress=FROM, Destination={"ToAddresses": [email]},
                Content={"Template": {"TemplateName": TEMPLATE, "TemplateData": json.dumps({"nome": pn})}},
                EmailTags=[{"Name": "marca", "Value": TAG}],
                ListManagementOptions={"ContactListName": LISTA, "TopicName": TAG})
            enviados += 1
        except ses.exceptions.MessageRejected as e:
            erros.append(f"{email}: {e}")
        except Exception as e:  # erro de conta/permissão: para e salva onde parou
            pos += i
            gravar("estado.json", json.dumps({**estado, "posicao": pos}))
            resumo("ERRO", saude + [f"Parou na linha {pos + 1}: {e}", f"Enviados antes do erro: {enviados}."])
            raise
        time.sleep(0.1)  # ~8-10 envios/s, abaixo do limite de 14/s

    pos += len(fatia)
    gravar("estado.json", json.dumps({"posicao": pos, "lote": lote + 1, "ultimo_dia": hoje}))
    resumo(f"lote {lote + 1} enviado", saude + [
        f"Lote {lote + 1}: {enviados} enviados, {pulados} pulados, {len(erros)} rejeitados.",
        f"Progresso: {pos} de {len(base)}.", *erros[:20]])
    return {"status": "ok", "enviados": enviados, "posicao": pos}
