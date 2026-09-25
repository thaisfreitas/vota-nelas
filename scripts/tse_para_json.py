#!/usr/bin/env python3
"""Converte o consulta_cand_2026.zip do TSE nos arquivos que o site carrega.

Uso:
    python3 scripts/tse_para_json.py dados-tse/consulta_cand_2026.zip \
        --complementar dados-tse/consulta_cand_complementar_2026.zip

Gera site/dados/{UF}.json (deputadas, senadoras e governadoras de cada estado)
e site/dados/BR.json (presidentas). Mantém só candidaturas de mulheres aptas
(inclui as que aguardam julgamento, que aparecem na urna).

Desde 2024 a situação da candidatura não vem no consulta_cand (fica #NE);
ela está no arquivo "Candidatos - complementar" do mesmo conjunto de dados.
Rode de novo sempre que o TSE atualizar os arquivos.
"""
import argparse
import csv
import io
import json
import re
import os
import sys
import unicodedata
import zipfile

SAIDA = os.path.join(os.path.dirname(__file__), "..", "site", "dados")
FOTOS = os.path.join(os.path.dirname(__file__), "..", "site", "fotos")

# DS_CARGO do TSE -> chave usada no site (distrital entra como "est")
CARGOS = {
    "DEPUTADO FEDERAL": "fed",
    "DEPUTADO ESTADUAL": "est",
    "DEPUTADO DISTRITAL": "est",
    "SENADOR": "sen",
    "GOVERNADOR": "gov",
    "PRESIDENTE": "pres",
}
UFS = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
MINUSCULAS = {"da", "de", "do", "das", "dos", "e", "di", "du", "del", "van", "von"}


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").upper().strip()


def nome_bonito(nome):
    """MARIA DA SILVA -> Maria da Silva (o TSE publica tudo em maiúsculas)."""
    partes = []
    for i, p in enumerate(nome.split()):
        low = p.lower()
        if i > 0 and low in MINUSCULAS:
            partes.append(low)
        else:
            partes.append(re.sub(r"(^|[-'’])(\w)", lambda m: m.group(1) + m.group(2).upper(), low))
    return " ".join(partes)


def arquivos_csv(zf):
    """Usa o arquivo _BRASIL quando existe; senão, junta os arquivos por UF (sem duplicar)."""
    nomes = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    brasil = [n for n in nomes if "_BRASIL" in n.upper()]
    return brasil or nomes


# Apta = nome consta da urna (ST_CANDIDATO_INSERIDO_URNA = SIM), não foi substituída por outra candidatura
# (ST_SUBSTITUIDO = S; a substituta herda o número) e a situação não é definitiva contra (renúncia,
# indeferimento sem recurso...). Conferido contra o campo candidatoApto do DivulgaCand em 24/09/2026.
SITUACOES_APTAS = {"DEFERIDO", "DEFERIDO COM RECURSO", "INDEFERIDO EM PRAZO RECURSAL OU COM RECURSO",
                   "PENDENTE DE JULGAMENTO", "#NULO"}  # #NULO = ainda sem julgamento
SITUACOES_INAPTAS = {"INDEFERIDO", "RENUNCIA", "CANCELADO", "FALECIDO", "CASSADO", "NAO CONHECIMENTO DO PEDIDO"}


def situacoes(caminho_zip):
    """SQ_CANDIDATO -> True/False (apta) lido do consulta_cand_complementar."""
    aptas, desconhecidas = {}, {}
    for l in ler(caminho_zip):
        if not {"ST_CANDIDATO_INSERIDO_URNA", "DS_SITUACAO_CANDIDATO_TOT", "ST_SUBSTITUIDO"} <= set(l):
            sys.exit("O arquivo complementar mudou de formato. Colunas:\n" + ", ".join(l))
        situacao = sem_acento(l["DS_SITUACAO_CANDIDATO_TOT"])
        if situacao not in SITUACOES_APTAS and situacao not in SITUACOES_INAPTAS:
            desconhecidas[situacao] = desconhecidas.get(situacao, 0) + 1
        aptas[l["SQ_CANDIDATO"].strip()] = (
            sem_acento(l["ST_CANDIDATO_INSERIDO_URNA"]) == "SIM"
            and sem_acento(l["ST_SUBSTITUIDO"]) != "S"
            and situacao in SITUACOES_APTAS)
    for situacao, n in desconhecidas.items():
        print(f"ATENÇÃO: situação nova no TSE, tratada como inapta: {situacao} ({n} candidaturas). "
              "Confira e ajuste SITUACOES_APTAS no script.")
    return aptas


def ler(caminho_zip):
    vistos = set()
    with zipfile.ZipFile(caminho_zip) as zf:
        for nome in arquivos_csv(zf):
            with zf.open(nome) as f:
                leitor = csv.DictReader(io.TextIOWrapper(f, encoding="latin-1", newline=""), delimiter=";")
                for linha in leitor:
                    sq = linha.get("SQ_CANDIDATO", "")
                    if not sq or sq in vistos:
                        continue
                    vistos.add(sq)
                    yield linha


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cand", help="consulta_cand_2026.zip")
    ap.add_argument("--complementar", help="consulta_cand_complementar_2026.zip (traz a situação da candidatura)")
    ap.add_argument("--saida", default=SAIDA, help="pasta de saída (padrão: site/dados)")
    ap.add_argument("--fotos", default=FOTOS, help="pasta das fotos extraídas por scripts/tse_fotos.py (padrão: site/fotos)")
    ap.add_argument("--sem-situacao", action="store_true",
                    help="só para conferir: não filtra por situação (NÃO publicar assim)")
    args = ap.parse_args()
    saida = args.saida
    for caminho, nome in ((args.cand, "Candidatos"), (args.complementar, "Candidatos - complementar")):
        if caminho and not os.path.isfile(caminho):
            sys.exit(f"Arquivo não encontrado: {caminho}\n"
                     f"Baixe '{nome}' em https://dadosabertos.tse.jus.br/dataset/candidatos-2026 "
                     "e salve nesse caminho.")
    sit = situacoes(args.complementar) if args.complementar else None
    if sit is None and not args.sem_situacao:
        sys.exit("Falta o arquivo complementar (--complementar), que traz a situação das candidaturas.\n"
                 "Para só conferir os números sem esse filtro, use --sem-situacao (não publique o resultado).")
    por_uf = {uf: {"fed": [], "est": [], "sen": [], "gov": []} for uf in UFS}
    br = {"pres": []}
    gerado = ""
    total = 0

    for l in ler(args.cand):
        gerado = gerado or f'{l.get("DT_GERACAO", "")} {l.get("HH_GERACAO", "")}'.strip()
        if sem_acento(l.get("DS_GENERO", "")) != "FEMININO":
            continue
        if sit is not None and not sit.get(l["SQ_CANDIDATO"].strip()):
            continue
        if l.get("NR_TURNO", "1").strip() not in ("", "1"):
            continue
        cargo = CARGOS.get(sem_acento(l.get("DS_CARGO", "")))
        if not cargo:
            continue  # vices e suplentes
        uf = l.get("SG_UF", "").strip()
        item = [
            nome_bonito(l["NM_URNA_CANDIDATO"].strip()),
            l["NR_CANDIDATO"].strip(),
            l["SG_PARTIDO"].strip(),
            l["SQ_CANDIDATO"].strip(),
        ]
        # 5º campo: 1 se a foto oficial já foi extraída (scripts/tse_fotos.py), 0 se não
        item.append(1 if os.path.exists(os.path.join(args.fotos, f"{item[3]}.jpg")) else 0)
        if cargo == "pres":
            br["pres"].append(item)
        elif uf in por_uf:
            por_uf[uf][cargo].append(item)
        else:
            continue
        total += 1

    if not total:
        sys.exit("Nenhuma candidata encontrada. Confira se o arquivo é o consulta_cand_2026.zip.")

    os.makedirs(saida, exist_ok=True)
    meta = {"gerado": gerado}

    def gravar(nome, dados):
        for lista in dados.values():
            lista.sort(key=lambda x: x[1])  # ordem estável; o site sorteia a cada visita
        with open(os.path.join(saida, nome), "w", encoding="utf-8") as f:
            json.dump({**meta, **dados}, f, ensure_ascii=False, separators=(",", ":"))

    for uf, dados in por_uf.items():
        gravar(f"{uf}.json", dados)
    gravar("BR.json", br)

    tipo = "aptas" if sit is not None else "(PRÉVIA, sem filtro de situação: não publique)"
    print(f"{total} candidatas {tipo} · arquivo do TSE gerado em {gerado}")
    print("Presidenta:", len(br["pres"]))
    for uf in UFS:
        d = por_uf[uf]
        vazios = [k for k, v in d.items() if not v]
        aviso = f"  (sem mulheres: {', '.join(vazios)})" if vazios else ""
        print(f"{uf}: fed {len(d['fed'])}, est {len(d['est'])}, sen {len(d['sen'])}, gov {len(d['gov'])}{aviso}")


if __name__ == "__main__":
    main()
