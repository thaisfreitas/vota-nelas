#!/usr/bin/env python3
"""Extrai as fotos oficiais das candidatas do site a partir dos zips do TSE.

Uso:
    python3 scripts/tse_fotos.py dados-tse/fotos

Os zips são os itens "XX - Fotos de candidatos" de
https://dadosabertos.tse.jus.br/dataset/candidatos-2026 (foto_cand2026_XX_div.zip).
Só entram as fotos das candidatas que já estão em site/dados/ (mulheres aptas).
As fotos do TSE já são pequenas (cerca de 161x225 px): as que cabem em 160 px são
copiadas sem nenhuma alteração; só as maiores são reduzidas com o sips do macOS,
sem corte nem retoque. O recorte redondo é feito só na exibição, pelo CSS.

Depois de extrair, marca em site/dados/{UF}.json quem tem foto (5º campo de cada
candidata: 1 com foto, 0 sem) e mostra quantas candidatas de cada cargo têm foto.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

RAIZ = os.path.join(os.path.dirname(__file__), "..")
DADOS = os.path.join(RAIZ, "site", "dados")
FOTOS = os.path.join(RAIZ, "site", "fotos")
EXTENSOES = (".jpg", ".jpeg", ".png")
LADO = 160


def arquivos_de_dados():
    return sorted(p for p in glob.glob(os.path.join(DADOS, "*.json")) if os.path.basename(p) != "votacoes.json")


def candidatas_do_site():
    """SQ_CANDIDATO de todas as candidatas que o site mostra."""
    sqs = set()
    for p in arquivos_de_dados():
        with open(p, encoding="utf-8") as f:
            for chave, lista in json.load(f).items():
                if isinstance(lista, list):
                    sqs |= {c[3] for c in lista}
    return sqs


def medidas(caminho):
    saida = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", caminho],
                           capture_output=True, text=True, check=True).stdout
    return [int(l.split()[-1]) for l in saida.splitlines() if "pixel" in l]


def reduzir(origem, destino):
    """Copia a foto como está se já cabe em LADO px; se não, reduz (nunca amplia)."""
    if origem.lower().endswith((".jpg", ".jpeg")) and max(medidas(origem)) <= LADO + 1:
        shutil.copyfile(origem, destino)
        return
    subprocess.run(["sips", "-Z", str(LADO), "-s", "format", "jpeg", "-s", "formatOptions", "80",
                    origem, "--out", destino], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def marcar_fotos():
    """Atualiza o 5º campo (tem foto) em site/dados/{UF}.json e devolve a cobertura por cargo."""
    cobertura = {}
    for p in arquivos_de_dados():
        with open(p, encoding="utf-8") as f:
            dados = json.load(f)
        for chave, lista in dados.items():
            if not isinstance(lista, list):
                continue
            for c in lista:
                tem = 1 if os.path.exists(os.path.join(FOTOS, f"{c[3]}.jpg")) else 0
                c[4:] = [tem]
                total, com = cobertura.get(chave, (0, 0))
                cobertura[chave] = (total + 1, com + tem)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))
    return cobertura


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    zips = sorted(glob.glob(os.path.join(sys.argv[1], "*.zip")))
    if not zips:
        sys.exit(f"Nenhum zip em {sys.argv[1]}. Baixe os itens 'XX - Fotos de candidatos' do TSE.")

    sqs = candidatas_do_site()
    os.makedirs(FOTOS, exist_ok=True)
    extraidas = set()
    with tempfile.TemporaryDirectory() as tmp:
        for caminho in zips:
            n = 0
            with zipfile.ZipFile(caminho) as zf:
                for nome in zf.namelist():
                    if not nome.lower().endswith(EXTENSOES):
                        continue
                    # o nome do arquivo traz o SQ_CANDIDATO (ex.: FAC10002532485_div.jpg)
                    m = re.search(r"(\d{9,})", os.path.basename(nome))
                    if not m or m.group(1) not in sqs:
                        continue
                    sq = m.group(1)
                    origem = os.path.join(tmp, os.path.basename(nome))
                    with zf.open(nome) as src, open(origem, "wb") as dst:
                        dst.write(src.read())
                    reduzir(origem, os.path.join(FOTOS, f"{sq}.jpg"))
                    os.remove(origem)
                    extraidas.add(sq)
                    n += 1
            print(f"{os.path.basename(caminho)}: {n} fotos")

    # fotos de quem saiu dos dados (candidatura que deixou de ser apta) são apagadas
    for p in glob.glob(os.path.join(FOTOS, "*.jpg")):
        if os.path.basename(p)[:-4] not in sqs:
            os.remove(p)

    print("\nCandidatas com foto, por cargo:")
    for cargo, (total, com) in sorted(marcar_fotos().items()):
        print(f"  {cargo}: {com} de {total} ({100 * com / total:.0f}%)")


if __name__ == "__main__":
    main()
