"""Atalho de duplo clique para quem tem Python instalado.

No Windows, arquivos .pyw abrem com o pythonw, sem janela de console. Este
arquivo apenas chama o ponto de entrada em main.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulador.interface import iniciar   # noqa: E402

iniciar()
