"""Servidor estático de site/ para os testes do Playwright.

Igual ao `python3 -m http.server`, mas com fila de conexões maior: o padrão
(5) recusava conexões quando vários navegadores rodavam em paralelo.
"""
import functools
import http.server
import os
import sys

PASTA = os.path.join(os.path.dirname(__file__), "..", "site")


class Servidor(http.server.ThreadingHTTPServer):
    request_queue_size = 128


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass  # sem log de cada requisição na saída dos testes


if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 4173
    Servidor(("", porta), functools.partial(Handler, directory=PASTA)).serve_forever()
