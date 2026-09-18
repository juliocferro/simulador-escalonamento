"""Cenários de referência do enunciado, prontos para carregar pela interface.

Os mesmos conjuntos estão gravados em JSON na pasta cenarios/ do repositório.
Mantê-los aqui também permite que o executável os ofereça sem depender de
arquivos externos.
"""

from .modelo import Tarefa, Parametros, Cenario


def _aula5():
    return [Tarefa(1, 0, 5, 2), Tarefa(2, 0, 2, 3), Tarefa(3, 1, 4, 1),
            Tarefa(4, 3, 1, 4), Tarefa(5, 5, 2, 5)]


def _aula6():
    return [Tarefa(1, 0, 6, 1, (1, 4)), Tarefa(2, 4, 4, 2), Tarefa(3, 6, 3, 3),
            Tarefa(4, 2, 3, 4, (1, 1))]


def _inanicao():
    return [Tarefa(1, 0, 4, 1), Tarefa(2, 0, 2, 5), Tarefa(3, 2, 2, 5),
            Tarefa(4, 4, 2, 5), Tarefa(5, 6, 2, 5), Tarefa(6, 8, 2, 5)]


def _teto_sem_disputa():
    return [Tarefa(1, 0, 6, 1, (1, 4)), Tarefa(2, 2, 3, 2), Tarefa(4, 12, 2, 4, (0, 1))]


# (rótulo no menu, nome do arquivo, função que cria o cenário)
EXEMPLOS = [
    ("Aula 5 - cinco tarefas (FCFS)",
     "aula5_cinco_tarefas",
     lambda: Cenario(_aula5(), Parametros("FCFS", quantum=2), "Aula 5 - cinco tarefas")),
    ("Aula 5 - Round-Robin com quantum 2",
     "aula5_round_robin",
     lambda: Cenario(_aula5(), Parametros("RR", quantum=2), "Aula 5 - Round-Robin q=2")),
    ("Aula 5 - Round-Robin q=4 com custo de troca 1",
     "aula5_custo_de_troca",
     lambda: Cenario(_aula5(), Parametros("RR", quantum=4, custo_troca=1), "Aula 5 - q=4, ttc=1")),
    ("Aula 6 - inversão de prioridades",
     "aula6_inversao",
     lambda: Cenario(_aula6(), Parametros("PRIOp"), "Aula 6 - inversão de prioridades")),
    ("Aula 6 - herança de prioridade",
     "aula6_heranca",
     lambda: Cenario(_aula6(), Parametros("PRIOp", protocolo="heranca"), "Aula 6 - herança")),
    ("Aula 6 - teto de prioridade",
     "aula6_teto",
     lambda: Cenario(_aula6(), Parametros("PRIOp", protocolo="teto"), "Aula 6 - teto")),
    ("Teto sem disputa (preço do teto)",
     "teto_sem_disputa",
     lambda: Cenario(_teto_sem_disputa(), Parametros("PRIOp", protocolo="teto"), "Teto sem disputa")),
    ("Inanição sob prioridade cooperativa",
     "inanicao_sem_envelhecimento",
     lambda: Cenario(_inanicao(), Parametros("PRIOc"), "Inanição - sem envelhecimento")),
    ("Envelhecimento com alfa = 1",
     "inanicao_envelhecimento_1",
     lambda: Cenario(_inanicao(), Parametros("PRIOc", envelhecimento=1), "Envelhecimento alfa=1")),
]


def exemplo_inicial():
    return EXEMPLOS[0][2]()
