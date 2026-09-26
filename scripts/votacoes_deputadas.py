#!/usr/bin/env python3
"""Tabela de como votaram, na Câmara, as candidatas de 2026 que já foram deputadas.

Uso:
    python3 scripts/votacoes_deputadas.py dados-tse/consulta_cand_2026.zip \\
        --complementar dados-tse/consulta_cand_complementar_2026.zip

Fontes oficiais: votos nominais do Plenário (API de dados abertos da Câmara) e
candidaturas aptas do TSE. Gera site/dados/votacoes.json (usado no card de cada
candidata e no mapa de calor dos partidos) e, para consulta,
docs/votacoes-deputadas/votacoes.csv, tabela.md e partidos.md.

Uma candidata entra se é mulher, tem candidatura apta em 2026 e votou em pelo
menos uma das votações. O cruzamento é pelo nome civil completo (Câmara) igual
ao nome completo da candidatura (TSE).
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import tse_para_json as tse  # noqa: E402

API = "https://dadosabertos.camara.leg.br/api/v2"
SAIDA = os.path.join(os.path.dirname(__file__), "..", "docs", "votacoes-deputadas")
SITE = os.path.join(os.path.dirname(__file__), "..", "site", "dados", "votacoes.json")

# votação nominal de mérito escolhida para cada tema; "sim" = votar a favor do projeto.
# (tema, id da votação, data, legislatura, descrição, id da proposição na Câmara)
VOTACOES = [
    ("PEC 6x1", "2233802-424", "2026-05-27", 57,
     "PEC 221/2019, 1º turno: Sim = a favor do fim da escala 6x1", 2233802),
    ("Igualdade Salarial", "2351179-51", "2023-05-04", 57,
     "PL 1085/2023: Sim = a favor da igualdade salarial entre mulheres e homens", 2351179),
    ("Misoginia (urgência)", "2636281-8", "2026-07-01", 57,
     "Urgência do PL 896/2023: Sim = a favor de votar com urgência a criminalização da misoginia (o mérito ainda não foi votado)", 2612930),
    ("PL do Veneno", "46249-297", "2022-02-09", 56,
     "PL 6299/2002: Sim = a favor de flexibilizar as regras de agrotóxicos", 46249),
    ("PL da Devastação", "257161-483", "2025-07-16", 57,
     "PL 2159/2021, votação final: Sim = a favor de flexibilizar o licenciamento ambiental", 257161),
]

# voto a favor das mulheres e da sociedade em cada votação (posição editorial do site,
# explicada na seção "Quem vota a favor das mulheres"): Sim nas três primeiras,
# Não nas que flexibilizam agrotóxicos e licenciamento ambiental.
FAVORAVEL = {
    "PEC 6x1": "Sim",
    "Igualdade Salarial": "Sim",
    "Misoginia (urgência)": "Sim",
    "PL do Veneno": "Não",
    "PL da Devastação": "Não",
}
# obstrução é tentar impedir a votação, então conta como voto contra o projeto;
# abstenção e "Artigo 17" (a presidência da Casa não vota) ficam fora da conta
CONTA_COMO = {"Sim": "Sim", "Não": "Não", "Obstrução": "Não"}
# partidos que se fundiram ou mudaram de nome desde a votação -> sigla usada pelo TSE em 2026
SUCESSOR = {"DEM": "UNIÃO", "PSL": "UNIÃO", "PTB": "PRD", "PATRIOTA": "PRD",
            "PROS": "SOLIDARIEDADE", "PSC": "PODE", "PCdoB": "PCDOB"}


def a_favor(tema, voto):
    """True/False para voto registrado; None para ausência, abstenção ou quem não era deputada."""
    v = CONTA_COMO.get(voto)
    return None if v is None else v == FAVORAVEL[tema]


def placar_partidos(votos_partido, partidos_2026):
    """[{sigla, votos: [[a favor, total], ...] por votação}] dos partidos com candidatas em 2026."""
    temas = [t for t, *_ in VOTACOES]
    conta = {}
    for i, tema in enumerate(temas):
        for partido, voto in votos_partido[tema]:
            sigla = SUCESSOR.get(partido, partido)
            fav = a_favor(tema, voto)
            if fav is None or sigla not in partidos_2026:
                continue
            c = conta.setdefault(sigla, [[0, 0] for _ in temas])
            c[i][0] += fav
            c[i][1] += 1
    total = lambda c: sum(a for a, _ in c) / sum(n for _, n in c)
    return sorted(({"sigla": s, "votos": c} for s, c in conta.items()), key=lambda p: (-total(p["votos"]), p["sigla"]))


def get(caminho):
    for tentativa in range(4):
        try:
            req = urllib.request.Request(f"{API}{caminho}", headers={"Accept": "application/json", "User-Agent": "vota-nelas"})
            return json.load(urllib.request.urlopen(req, timeout=40))["dados"]
        except Exception:
            if tentativa == 3:
                raise
            time.sleep(2 * (tentativa + 1))


def todas_paginas(caminho):
    dados, pagina = [], 1
    sep = "&" if "?" in caminho else "?"
    while True:
        d = get(f"{caminho}{sep}itens=100&pagina={pagina}")
        dados += d
        if len(d) < 100:
            return dados
        pagina += 1


def rotulo_voto(tipo):
    return {"Sim": "Sim", "Não": "Não", "Abstenção": "Abstenção", "Obstrução": "Obstrução"}.get(tipo, tipo)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cand")
    ap.add_argument("--complementar", required=True)
    args = ap.parse_args()

    # candidatas aptas em 2026, por nome completo e por nome de urna/nome social
    aptas = tse.situacoes(args.complementar)
    candidatas, por_nome_urna = {}, {}
    for l in tse.ler(args.cand):
        if tse.sem_acento(l.get("DS_GENERO", "")) != "FEMININO" or not aptas.get(l["SQ_CANDIDATO"].strip()):
            continue
        if not tse.CARGOS.get(tse.sem_acento(l["DS_CARGO"])):
            continue
        candidatas.setdefault(tse.sem_acento(l["NM_CANDIDATO"]), []).append(l)
        for campo in ("NM_URNA_CANDIDATO", "NM_SOCIAL_CANDIDATO"):
            if l.get(campo) and not l[campo].startswith("#"):
                por_nome_urna.setdefault(tse.sem_acento(l[campo]), []).append(l)

    # quem exerceu mandato nas legislaturas 56 (2019-2023) e 57 (2023-2027).
    # Sem o filtro de sexo: na legislatura 57 a API da Câmara dá timeout com ele.
    legislaturas = {}
    for leg in (56, 57):
        for d in todas_paginas(f"/deputados?idLegislatura={leg}"):
            legislaturas.setdefault(d["id"], set()).add(leg)

    votos, votos_partido = {}, {}
    for tema, vid, _data, _leg, _desc, _prop in VOTACOES:
        brutos = get(f"/votacoes/{vid}/votos")
        votos[tema] = {v["deputado_"]["id"]: rotulo_voto(v["tipoVoto"]) for v in brutos}
        # partido da deputada ou do deputado no dia da votação
        votos_partido[tema] = [(v["deputado_"]["siglaPartido"], rotulo_voto(v["tipoVoto"])) for v in brutos]
    votantes = sorted(set().union(*votos.values()))
    print(f"{len(votantes)} parlamentares votaram em alguma das votações", file=sys.stderr)

    linhas, nao_encontradas = [], []
    for dep_id in votantes:
        det = get(f"/deputados/{dep_id}")
        if det.get("sexo") != "F":
            continue
        info = {"legislaturas": legislaturas.get(dep_id, set())}
        uf = det["ultimoStatus"]["siglaUf"]
        achadas = candidatas.get(tse.sem_acento(det["nomeCivil"]), [])
        # se houver homônimas, fica a do mesmo estado de onde foi deputada
        achadas = [c for c in achadas if c["SG_UF"] in (uf, "BR")] or achadas
        if not achadas:
            # quem se candidata com nome social (ou outro nome civil) não bate pelo nome civil da Câmara:
            # compara o nome parlamentar com o nome de urna/nome social, exigindo o mesmo estado
            achadas = [c for c in por_nome_urna.get(tse.sem_acento(det["ultimoStatus"]["nome"]), [])
                       if c["SG_UF"] in (uf, "BR")]
        # a mesma candidatura pode aparecer duas vezes (nome de urna igual ao nome social)
        achadas = list({c["SQ_CANDIDATO"]: c for c in achadas}.values())
        if len(achadas) != 1:
            nao_encontradas.append(f'{det["ultimoStatus"]["nome"]} ({det["nomeCivil"]}, {uf}): '
                                   + ("não é candidata apta em 2026" if not achadas else f"{len(achadas)} candidaturas possíveis"))
            continue
        c = achadas[0]
        linha = {
            "nome": tse.nome_bonito(c["NM_URNA_CANDIDATO"]),
            "partido_2026": c["SG_PARTIDO"],
            "cargo_2026": tse.nome_bonito(c["DS_CARGO"]).replace("Deputado", "Deputada").replace("Senador", "Senadora")
                          .replace("Governador", "Governadora").replace("Presidente", "Presidenta"),
            "uf_2026": c["SG_UF"],
            "id_camara": dep_id,
            "sq": c["SQ_CANDIDATO"].strip(),
        }
        for tema, _vid, _data, leg, _desc, _prop in VOTACOES:
            if dep_id in votos[tema]:
                linha[tema] = votos[tema][dep_id]
            elif leg in info["legislaturas"]:
                linha[tema] = "Não votou"
            else:
                linha[tema] = "—"
        linhas.append(linha)

    linhas.sort(key=lambda l: (l["uf_2026"], tse.sem_acento(l["nome"])))
    os.makedirs(SAIDA, exist_ok=True)
    temas = [t for t, *_ in VOTACOES]
    with open(os.path.join(SAIDA, "votacoes.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["nome", "partido_2026", "cargo_2026", "uf_2026", "id_camara", *temas], extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)

    with open(os.path.join(SAIDA, "tabela.md"), "w", encoding="utf-8") as f:
        f.write("# Como votaram na Câmara as candidatas de 2026 que já foram deputadas\n\n")
        f.write("Fonte: votos nominais do Plenário da Câmara dos Deputados (dados abertos) e candidaturas aptas do TSE. ")
        f.write(f"Gerado por `scripts/votacoes_deputadas.py`. {len(linhas)} candidatas.\n\n")
        f.write("## Votações\n\n")
        for tema, vid, data, _leg, desc, _prop in VOTACOES:
            f.write(f"- **{tema}** ({data[8:10]}/{data[5:7]}/{data[:4]}): {desc}. "
                    f"[Votação {vid}](https://dadosabertos.camara.leg.br/api/v2/votacoes/{vid}/votos)\n")
        f.write("\nO PL da Dignidade Menstrual (PL 4968/2019) ficou de fora: a Câmara o aprovou em votação simbólica, sem registro de voto individual.\n\n")
        f.write("**Legenda:** Sim / Não = voto registrado · Não votou = era deputada na legislatura, mas não há voto registrado (ausência, licença ou suplência fora do exercício) · — = não era deputada na época.\n\n")
        f.write("## Tabela\n\n")
        f.write("| Candidata | Partido (2026) | Cargo em 2026 | UF | " + " | ".join(temas) + " |\n")
        f.write("|---|---|---|---|" + "---|" * len(temas) + "\n")
        for l in linhas:
            f.write(f"| {l['nome']} | {l['partido_2026']} | {l['cargo_2026']} | {l['uf_2026']} | "
                    + " | ".join(l[t] for t in temas) + " |\n")
    partidos_2026 = {l["SG_PARTIDO"] for ls in candidatas.values() for l in ls}
    partidos = placar_partidos(votos_partido, partidos_2026)
    sem_deputados = sorted(partidos_2026 - {p["sigla"] for p in partidos})
    with open(os.path.join(SAIDA, "partidos.md"), "w", encoding="utf-8") as f:
        f.write("# Quanto cada partido votou a favor das mulheres nas 5 votações\n\n")
        f.write("Porcentagem dos votos Sim/Não (obstrução conta como Não) das bancadas na Câmara que foram no sentido "
                "a favor das mulheres e da sociedade: " + "; ".join(f"{t}: {v}" for t, v in FAVORAVEL.items()) + ". "
                "Partido no dia da votação; partidos que se fundiram entram na sigla atual ("
                + ", ".join(f"{a} → {b}" for a, b in SUCESSOR.items() if a != "PCdoB") + ").\n\n")
        f.write("| Partido | " + " | ".join(temas) + " | Total |\n|---|" + "---|" * (len(temas) + 1) + "\n")
        for p in partidos:
            cel = [f"{round(100 * a / n)}% ({a}/{n})" if n else "—" for a, n in p["votos"]]
            a, n = sum(a for a, _ in p["votos"]), sum(n for _, n in p["votos"])
            f.write(f"| {p['sigla']} | " + " | ".join(cel) + f" | {round(100 * a / n)}% ({a}/{n}) |\n")
        f.write(f"\nSem deputados nessas votações: {', '.join(sem_deputados)}.\n")

    # para o site: votos de cada candidata pelo SQ_CANDIDATO (mesmo id usado em site/dados/{UF}.json)
    site = {
        "fonte": "Câmara dos Deputados, votos nominais do Plenário (dados abertos)",
        "votacoes": [{"tema": tema, "data": data, "descricao": desc, "favoravel": FAVORAVEL[tema],
                      "link": f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop}",
                      "api": f"https://dadosabertos.camara.leg.br/api/v2/votacoes/{vid}/votos"}
                     for tema, vid, data, _leg, desc, prop in VOTACOES],
        # votos das bancadas: [a favor, total] em cada votação, do partido mais a favor ao mais contra
        "partidos": partidos,
        "sem_deputados": sem_deputados,
        "candidatas": {l["sq"]: {"camara": l["id_camara"], "votos": [l[t] for t in temas]} for l in linhas},
    }
    with open(SITE, "w", encoding="utf-8") as f:
        json.dump(site, f, ensure_ascii=False, separators=(",", ":"))

    with open(os.path.join(SAIDA, "nao_encontradas.txt"), "w", encoding="utf-8") as f:
        f.write("Deputadas que votaram em alguma das votações e não entraram na tabela (conferir à mão):\n\n")
        f.write("\n".join(sorted(nao_encontradas)) + "\n")
    print(f"{len(linhas)} candidatas na tabela; {len(nao_encontradas)} deputadas não encontradas", file=sys.stderr)


if __name__ == "__main__":
    main()
