"""Simulador de escalonamento de tarefas em um processador.

Pacote organizado em torno da separação entre política e mecanismo:

- modelo.py     estrutura de uma tarefa e de um cenário, leitura e gravação em JSON
- politicas.py  os seis algoritmos de escalonamento (a política)
- motor.py      laço de simulação, recurso exclusivo, herança, teto e envelhecimento (o mecanismo)
- metricas.py   cálculo de tt, tp, tw, tempo até a primeira execução e eficiência
- gerador.py    sorteio de cenários e comparação em lote
- interface.py  janela do programa (tkinter)
"""

VERSAO = "1.0"
