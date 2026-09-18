"""Ponto de entrada do simulador.

Abre a janela do programa. Não recebe argumentos de linha de comando: toda a
interação acontece dentro da janela depois de aberta.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulador.interface import iniciar   # noqa: E402

if __name__ == "__main__":
    iniciar()
