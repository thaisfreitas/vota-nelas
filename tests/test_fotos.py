"""Testa scripts/tse_fotos.py com um zip de fotos falso, no formato do TSE."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

RAIZ = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import tse_fotos  # noqa: E402


@unittest.skipUnless(shutil.which("sips"), "tse_fotos.py usa o sips do macOS")
class TestFotos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dados = os.path.join(self.tmp.name, "dados")
        self.fotos = os.path.join(self.tmp.name, "fotos")
        os.makedirs(self.dados)
        with open(os.path.join(self.dados, "AC.json"), "w", encoding="utf-8") as f:
            json.dump({"gerado": "x", "fed": [["Maria", "1234", "PT", "10000000001", 0],
                                              ["Ana", "1235", "PT", "10000000002", 0]]}, f)
        # imagem de exemplo: a og.png do site, maior que o tamanho final
        zips = os.path.join(self.tmp.name, "zips")
        os.makedirs(zips)
        with zipfile.ZipFile(os.path.join(zips, "foto_cand2026_AC_div.zip"), "w") as z:
            z.write(os.path.join(RAIZ, "site", "og.png"), "FAC10000000001_div.png")
            z.write(os.path.join(RAIZ, "site", "og.png"), "FAC99999999999_div.png")  # não é candidata do site
            z.writestr("FAC10000000002_div.jpg", self.foto_pequena())
        self.zips = zips
        self.antigos = (tse_fotos.DADOS, tse_fotos.FOTOS)
        tse_fotos.DADOS, tse_fotos.FOTOS = self.dados, self.fotos

    def foto_pequena(self):
        """JPEG de 111x155, do tamanho das fotos do TSE."""
        caminho = os.path.join(self.tmp.name, "pequena.jpg")
        subprocess.run(["sips", "-z", "155", "111", "-s", "format", "jpeg", os.path.join(RAIZ, "site", "og.png"),
                        "--out", caminho], check=True, capture_output=True)
        with open(caminho, "rb") as f:
            return f.read()

    def tearDown(self):
        tse_fotos.DADOS, tse_fotos.FOTOS = self.antigos
        self.tmp.cleanup()

    def test_extrai_so_fotos_do_site_reduzidas_e_marca_nos_dados(self):
        sys.argv = ["tse_fotos.py", self.zips]
        tse_fotos.main()
        self.assertEqual(sorted(os.listdir(self.fotos)), ["10000000001.jpg", "10000000002.jpg"])
        # a foto pequena é copiada sem alteração
        with open(os.path.join(self.fotos, "10000000002.jpg"), "rb") as f:
            self.assertEqual(f.read(), self.foto_pequena())
        largura = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", os.path.join(self.fotos, "10000000001.jpg")],
                                 capture_output=True, text=True).stdout
        medidas = [int(l.split()[-1]) for l in largura.splitlines() if "pixel" in l]
        self.assertEqual(max(medidas), tse_fotos.LADO)
        with open(os.path.join(self.dados, "AC.json"), encoding="utf-8") as f:
            fed = json.load(f)["fed"]
        self.assertEqual([c[4] for c in fed], [1, 1])


if __name__ == "__main__":
    unittest.main()
