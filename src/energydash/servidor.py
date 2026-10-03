"""Servidor HTTP local com http.server (biblioteca padrao).
Local HTTP server using http.server (stdlib).

Rotas:
Routes:

- ``/``          pagina do painel (HTML com dados embutidos)
- ``/api/resumo`` payload JSON
- ``/saude``     verificacao de vida ({"status": "ok"})

O servidor e iniciado em ``127.0.0.1`` so para uso local. O modo de
primeiro plano (``main``) fica bloqueado ate Ctrl+C; para gerar artefato
sem bloquear, use o comando ``exportar``.
The server is bound to ``127.0.0.1`` for local use only. The foreground
mode (``main``) blocks until Ctrl+C; to generate an artifact without
blocking, use the ``exportar`` command.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

HOST_PADRAO = "127.0.0.1"
PORTA_PADRAO = 8000


def _handler(resumo_json: str, template: str):
    """Montar a classe de handler com os dados fechados por escopo.
    Build the handler class with the data closed over by scope.
    """

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args, **kwargs) -> None:
            # Silencia o log por linha: saida deterministica no terminal.
            # Silence per-request logging: deterministic terminal output.
            return

        def _enviar(self, status: int, tipo: str, corpo: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self) -> None:  # noqa: N802 - nome exigido pelo http.server
            if self.path == "/":
                corpo = template.replace("__DADOS__", resumo_json)
                self._enviar(
                    200, "text/html; charset=utf-8", corpo.encode("utf-8")
                )
            elif self.path == "/api/resumo":
                self._enviar(
                    200,
                    "application/json; charset=utf-8",
                    resumo_json.encode("utf-8"),
                )
            elif self.path == "/saude":
                self._enviar(
                    200, "application/json; charset=utf-8", b'{"status": "ok"}'
                )
            else:
                msg = json.dumps(
                    {"erro": "rota nao encontrada / route not found"},
                    ensure_ascii=True,
                ).encode("utf-8")
                self._enviar(404, "application/json; charset=utf-8", msg)

    return Handler


def criar_servidor(
    resumo_json: str,
    template: str,
    porta: int = PORTA_PADRAO,
    host: str = HOST_PADRAO,
) -> ThreadingHTTPServer:
    """Criar o ThreadingHTTPServer sem dar inicio ao loop.
    Create the ThreadingHTTPServer without starting the loop.
    """
    return ThreadingHTTPServer((host, porta), _handler(resumo_json, template))


def iniciar_em_thread(
    resumo_json: str,
    template: str,
    porta: int = 0,
    host: str = HOST_PADRAO,
) -> tuple[ThreadingHTTPServer, threading.Thread]:
    """Saber o servidor em thread daemon e devolver (servidor, thread).
    Start the server on a daemon thread and return (server, thread).

    Com ``porta=0`` o sistema escolhe uma porta livre; a porta efetiva
    aparece em ``servidor.server_address[1]``.
    With ``porta=0`` the OS picks a free port; the effective port is in
    ``servidor.server_address[1]``.
    """
    server = criar_servidor(resumo_json, template, porta=porta, host=host)
    thread = threading.Thread(
        target=server.serve_forever, daemon=True, name="energydash-http"
    )
    thread.start()
    return server, thread


def main(
    porta: int,
    resumo_json: str,
    template: str,
    host: str = HOST_PADRAO,
) -> int:
    """Rodar o servidor no primeiro plano ate Ctrl+C.
    Run the server in the foreground until Ctrl+C.
    """
    try:
        server = criar_servidor(resumo_json, template, porta=porta, host=host)
    except OSError as exc:
        print(
            f"ERRO: nao foi possivel abrir {host}:{porta} ({exc}) "
            f"/ could not bind {host}:{porta}",
        )
        return 1
    print(f"Servidor em http://{host}:{porta} / Server at http://{host}:{porta}")
    print("Encerrar com Ctrl+C / Stop with Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    print("Servidor encerrado / Server stopped")
    return 0
