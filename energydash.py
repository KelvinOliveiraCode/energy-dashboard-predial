"""Raiz: shim para ``python -m energydash`` sem instalacao.
Root: shim for ``python -m energydash`` without installation.

O pacote de verdade vive em ``src/energydash`` (layout src/). Este arquivo
e um **modulo** (nao um pacote), entao ``os.path.isdir("energydash")``
nao e True e o coverage (``--cov=energydash``) mede o pacote de ``src/``,
neste arquivo. Ele existe so para que ``python -m energydash`` funcione a
partir da raiz do repositorio, sem instalar o pacote: adiciona ``src`` ao
sys.path e delega para a CLI em ``src/energydash``.
The real package lives in ``src/energydash`` (src/ layout). This file is a
**module** (not a package), so ``os.path.isdir("energydash")`` is not True
and coverage (``--cov=energydash``) measures the package in ``src/``, not
this file. It exists only so that ``python -m energydash`` works from the
repository root without installing the package: it adds ``src`` to
sys.path and delegates to the CLI in ``src/energydash``.
"""

import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

if __name__ == "__main__":
    # Garante que o pacote em src seja o 'energydash' importado, mesmo que
    # este shim ja tenha sido registrado em sys.modules com o mesmo nome.
    # Ensures the package in src is the imported 'energydash', even if this
    # shim was already registered in sys.modules under the same name.
    sys.modules.pop("energydash", None)
    from energydash.cli import main

    sys.exit(main())
