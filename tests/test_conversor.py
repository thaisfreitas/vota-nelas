"""Testa scripts/tse_para_json.py com arquivos do TSE falsos, no mesmo formato dos reais."""
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

RAIZ = os.path.join(os.path.dirname(__file__), "..")
SCRIPT = os.path.join(RAIZ, "scripts", "tse_para_json.py")

COLS_CAND = ["DT_GERACAO", "HH_GERACAO", "NR_TURNO", "CD_ELEICAO", "SG_UF", "SG_UE", "DS_CARGO",
             "SQ_CANDIDATO", "NR_CANDIDATO", "NM_URNA_CANDIDATO", "DS_SITUACAO_CANDIDATURA",
             "SG_PARTIDO", "DS_GENERO"]
COLS_COMP = ["SQ_CANDIDATO", "ST_CANDIDATO_INSERIDO_URNA", "DS_SITUACAO_CANDIDATO_TOT", "ST_SUBSTITUIDO"]


def zip_csv(caminho, nome_csv, colunas, linhas):
    buf = io.StringIO()
    w = csv.DictWriter(buf, colunas, delimiter=";", quoting=csv.QUOTE_ALL)
    w.writeheader()
    w.writerows(linhas)
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr(nome_csv, buf.getvalue().encode("latin-1"))


class TestConversor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cand, self.comp = [], []
        self.sq = 0

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, nome, cargo="DEPUTADO FEDERAL", uf="SP", num="1234", genero="FEMININO",
            urna="SIM", situacao="DEFERIDO", substituido="N", partido="PT"):
        self.sq += 1
        sq = str(250000000000 + self.sq)
        self.cand.append(dict(DT_GERACAO="24/09/2026", HH_GERACAO="19:31:08", NR_TURNO="1", CD_ELEICAO="6259",
                              SG_UF=uf, SG_UE=uf, DS_CARGO=cargo, SQ_CANDIDATO=sq, NR_CANDIDATO=num,
                              NM_URNA_CANDIDATO=nome, DS_SITUACAO_CANDIDATURA="#NE", SG_PARTIDO=partido,
                              DS_GENERO=genero))
        self.comp.append(dict(SQ_CANDIDATO=sq, ST_CANDIDATO_INSERIDO_URNA=urna,
                              DS_SITUACAO_CANDIDATO_TOT=situacao, ST_SUBSTITUIDO=substituido))
        return sq

    def converter(self, *extra, complementar=True):
        cand = os.path.join(self.tmp.name, "consulta_cand_2026.zip")
        comp = os.path.join(self.tmp.name, "consulta_cand_complementar_2026.zip")
        saida = os.path.join(self.tmp.name, "dados")
        zip_csv(cand, "consulta_cand_2026_BRASIL.csv", COLS_CAND, self.cand)
        zip_csv(comp, "consulta_cand_complementar_2026_BRASIL.csv", COLS_COMP, self.comp)
        args = [sys.executable, SCRIPT, cand, "--saida", saida, *extra]
        if complementar:
            args += ["--complementar", comp]
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
        return r, saida

    def json(self, saida, nome):
        with open(os.path.join(saida, nome), encoding="utf-8") as f:
            return json.load(f)

    def test_so_entram_mulheres_aptas(self):
        apta = self.add("MARIA APTA")
        self.add("JOAO", genero="MASCULINO")
        self.add("FORA DA URNA", urna="NÃO", situacao="#NULO")
        self.add("RENUNCIOU", situacao="RENÚNCIA")
        self.add("INDEFERIDA", situacao="INDEFERIDO")
        recurso = self.add("COM RECURSO", situacao="INDEFERIDO EM PRAZO RECURSAL OU COM RECURSO")
        pendente = self.add("SEM JULGAMENTO", situacao="#NULO")
        r, saida = self.converter()
        self.assertEqual(r.returncode, 0, r.stderr)
        sqs = {c[3] for c in self.json(saida, "SP.json")["fed"]}
        self.assertEqual(sqs, {apta, recurso, pendente})

    def test_candidatura_substituida_sai_e_substituta_fica_com_o_numero(self):
        # caso real de 24/09/2026: a substituta herda o número da substituída
        self.add("MARIA HELENA", num="3660", situacao="INDEFERIDO EM PRAZO RECURSAL OU COM RECURSO", substituido="S")
        nova = self.add("POLÍCIAL EDJANE", num="3660", situacao="#NULO")
        r, saida = self.converter()
        self.assertEqual(r.returncode, 0, r.stderr)
        fed = self.json(saida, "SP.json")["fed"]
        self.assertEqual([(c[1], c[3]) for c in fed], [("3660", nova)])

    def test_vices_e_suplentes_ficam_de_fora(self):
        self.add("VICE", cargo="VICE-GOVERNADOR", num="13")
        self.add("SUPLENTE", cargo="1º SUPLENTE", num="131")
        gov = self.add("GOVERNADORA", cargo="GOVERNADOR", num="13")
        r, saida = self.converter()
        self.assertEqual(r.returncode, 0, r.stderr)
        d = self.json(saida, "SP.json")
        self.assertEqual([c[3] for c in d["gov"]], [gov])
        self.assertEqual(d["sen"], [])

    def test_cargos_vao_para_os_arquivos_certos(self):
        self.add("DISTRITAL", cargo="DEPUTADO DISTRITAL", uf="DF", num="13123")
        self.add("PRESIDENTA", cargo="PRESIDENTE", uf="BR", num="80")
        self.add("SENADORA", cargo="SENADOR", uf="RJ", num="131")
        r, saida = self.converter()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.json(saida, "DF.json")["est"][0][1], "13123")
        self.assertEqual(self.json(saida, "BR.json")["pres"][0][1], "80")
        self.assertEqual(self.json(saida, "RJ.json")["sen"][0][1], "131")
        self.assertEqual(len(os.listdir(saida)), 28)

    def test_nomes_formatados(self):
        for nome in ["MARIA DA SILVA", "JOANA D'ARC", "TÂNIA-MARA LIMA", "DRA. ANA DOS SANTOS"]:
            self.add(nome)
        r, saida = self.converter()
        self.assertEqual(r.returncode, 0, r.stderr)
        nomes = {c[0] for c in self.json(saida, "SP.json")["fed"]}
        self.assertEqual(nomes, {"Maria da Silva", "Joana D'Arc", "Tânia-Mara Lima", "Dra. Ana dos Santos"})

    def test_situacao_desconhecida_avisa_e_fica_de_fora(self):
        self.add("NOVIDADE", situacao="ALGUMA SITUACAO NOVA")
        self.add("MARIA")
        r, saida = self.converter()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ATENÇÃO", r.stdout)
        self.assertEqual(len(self.json(saida, "SP.json")["fed"]), 1)

    def test_exige_arquivo_complementar(self):
        self.add("MARIA")
        r, saida = self.converter(complementar=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("complementar", r.stderr)
        self.assertFalse(os.path.exists(saida))


if __name__ == "__main__":
    unittest.main()
