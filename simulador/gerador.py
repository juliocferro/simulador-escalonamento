"""Sorteio de cenários (R9).

O mesmo gerador serve a dois usos: sortear um único conjunto de tarefas para
observar em detalhe, e sortear um lote de conjuntos para comparar os seis
algoritmos pelas médias de tt, tw e tempo até a primeira execução.

O sorteio não usa semente fixa: cada execução produz conjuntos diferentes. O
que se espera manter entre execuções é a ordenação dos algoritmos, não os
valores absolutos das médias.
"""

import random
from dataclasses import dataclass

from .modelo import Tarefa, Parametros, EntradaInvalida, ALGORITMOS
from .motor import simular
from .metricas import Metricas


@dataclass
class FaixasSorteio:
    """Limites do sorteio. Os valores padrão são os da seção 4.7 do enunciado."""
    quantidade: int = 5
    ingresso_max: int = 8
    tp_max: int = 6
    prioridade_max: int = 5
    com_recurso: bool = False       # sorteia seções críticas em parte das tarefas
    fracao_com_recurso: float = 0.4

    def validar(self):
        if self.quantidade < 1:
            raise EntradaInvalida(f"Quantidade de tarefas deve ser ao menos 1 (recebido {self.quantidade}).")
        if self.ingresso_max < 0:
            raise EntradaInvalida("Ingresso máximo não pode ser negativo.")
        if self.tp_max < 1:
            raise EntradaInvalida("Tempo de processamento máximo deve ser ao menos 1.")
        if self.prioridade_max < 1:
            raise EntradaInvalida("Prioridade máxima deve ser ao menos 1.")
        return self


def sortear_tarefas(faixas):
    """Sorteia um conjunto de tarefas dentro das faixas informadas."""
    faixas.validar()
    tarefas = []
    for i in range(1, faixas.quantidade + 1):
        tp = random.randint(1, faixas.tp_max)
        uso = None
        if faixas.com_recurso and random.random() < faixas.fracao_com_recurso:
            inicio = random.randint(0, tp - 1)
            duracao = random.randint(1, tp - inicio)
            uso = (inicio, duracao)
        tarefas.append(Tarefa(i, random.randint(0, faixas.ingresso_max), tp,
                              random.randint(1, faixas.prioridade_max), uso))
    return tarefas


@dataclass
class MediaAlgoritmo:
    algoritmo: str
    tt: float
    tw: float
    primeira_execucao: float


def comparar_em_lote(faixas, amostras, parametros_base):
    """Sorteia `amostras` cenários e simula cada um sob os seis algoritmos.

    Devolve a lista de MediaAlgoritmo, na ordem de ALGORITMOS, com as médias
    de tt, tw e tempo até a primeira execução sobre todos os cenários.
    """
    if amostras < 1:
        raise EntradaInvalida(f"Número de amostras deve ser ao menos 1 (recebido {amostras}).")
    soma = {a: [0.0, 0.0, 0.0] for a in ALGORITMOS}
    for _ in range(amostras):
        tarefas = sortear_tarefas(faixas)
        for alg in ALGORITMOS:
            p = Parametros(alg, parametros_base.quantum, parametros_base.custo_troca,
                           parametros_base.protocolo, parametros_base.envelhecimento)
            m = Metricas(simular(tarefas, p))
            soma[alg][0] += m.tt_medio
            soma[alg][1] += m.tw_medio
            soma[alg][2] += m.primeira_execucao_media
    return [MediaAlgoritmo(a, soma[a][0] / amostras, soma[a][1] / amostras, soma[a][2] / amostras)
            for a in ALGORITMOS]
