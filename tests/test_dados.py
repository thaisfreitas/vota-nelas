"""Confere os arquivos de site/dados/ antes de publicar.

Um número errado aqui vai parar na colinha que a pessoa leva para a urna,
então os dados publicados precisam estar completos e no formato certo.
"""
import json
import os
import re
import unittest

DADOS = os.path.join(os.path.dirname(__file__), "..", "site", "dados")
UFS = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
# dígitos do número na urna por cargo
DIGITOS = {"fed": 4, "est": 5, "sen": 3, "gov": 2, "pres": 2}


def carregar(nome):
    with open(os.path.join(DADOS, nome), encoding="utf-8") as f:
        return json.load(f)


class TestDados(unittest.TestCase):
    def test_existe_um_arquivo_por_estado_e_um_nacional(self):
        esperados = {f"{uf}.json" for uf in UFS} | {"BR.json"}
        self.assertEqual(set(os.listdir(DADOS)), esperados)

    def test_estados_tem_todos_os_cargos(self):
        for uf in UFS:
            with self.subTest(uf=uf):
                d = carregar(f"{uf}.json")
                self.assertTrue(d.get("gerado"), "falta a data de geração")
                for cargo in ("fed", "est", "sen", "gov"):
                    self.assertIsInstance(d.get(cargo), list, cargo)
                # todo estado tem mulheres concorrendo à Câmara e à Assembleia
                self.assertTrue(d["fed"], "nenhuma deputada federal")
                self.assertTrue(d["est"], "nenhuma deputada estadual/distrital")

    def test_candidatas_no_formato_certo(self):
        arquivos = [(f"{uf}.json", ("fed", "est", "sen", "gov")) for uf in UFS] + [("BR.json", ("pres",))]
        for nome, cargos in arquivos:
            d = carregar(nome)
            for cargo in cargos:
                for c in d[cargo]:
                    with self.subTest(arquivo=nome, cargo=cargo, candidata=c):
                        self.assertEqual(len(c), 4, "esperado [nome, número, partido, SQ_CANDIDATO]")
                        nome_urna, numero, partido, sq = c
                        self.assertTrue(nome_urna.strip())
                        self.assertNotEqual(nome_urna, nome_urna.upper(), "nome deveria estar formatado, não em maiúsculas")
                        self.assertRegex(numero, rf"^\d{{{DIGITOS[cargo]}}}$")
                        self.assertTrue(partido.strip())
                        self.assertRegex(sq, r"^\d+$")

    def test_sem_numeros_nem_candidatas_repetidas(self):
        todos_sq = []
        for uf in UFS:
            d = carregar(f"{uf}.json")
            for cargo in ("fed", "est", "sen", "gov"):
                with self.subTest(uf=uf, cargo=cargo):
                    numeros = [c[1] for c in d[cargo]]
                    self.assertEqual(len(numeros), len(set(numeros)), "número repetido no mesmo cargo")
                todos_sq += [c[3] for c in d[cargo]]
        pres = carregar("BR.json")["pres"]
        todos_sq += [c[3] for c in pres]
        self.assertEqual(len(todos_sq), len(set(todos_sq)), "a mesma candidatura aparece duas vezes")

    def test_data_de_geracao_valida(self):
        for nome in [f"{uf}.json" for uf in UFS] + ["BR.json"]:
            with self.subTest(arquivo=nome):
                self.assertRegex(carregar(nome)["gerado"], r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$")
        # todos os arquivos precisam vir da mesma extração do TSE
        datas = {carregar(n)["gerado"] for n in [f"{uf}.json" for uf in UFS] + ["BR.json"]}
        self.assertEqual(len(datas), 1, f"arquivos de extrações diferentes: {datas}")


if __name__ == "__main__":
    unittest.main()
