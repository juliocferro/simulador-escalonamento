"""Métricas por tarefa e em média (R3) e eficiência do escalonador (R4).

    tt  tempo de execução      = conclusão - ingresso
    tp  tempo de processamento = dado de entrada
    tw  tempo de espera        = tt - tp  (fila, suspensão em R e troca de contexto, C8)
    primeira execução          = instante do primeiro despacho - ingresso

A eficiência E = tq / (tq + ttc) é propriedade da configuração do escalonador
e só está definida quando há quantum, isto é, sob Round-Robin. Nos demais
algoritmos ela é reportada como indefinida.
"""


class MetricaTarefa:
    __slots__ = ("id", "ingresso", "tp", "conclusao", "tt", "tw", "primeira_execucao")

    def __init__(self, tarefa):
        self.id = tarefa.id
        self.ingresso = tarefa.ingresso
        self.tp = tarefa.tp
        self.conclusao = tarefa.conclusao
        self.tt = tarefa.conclusao - tarefa.ingresso
        self.tw = self.tt - tarefa.tp
        self.primeira_execucao = tarefa.primeiro_despacho - tarefa.ingresso


class Metricas:
    """Tabela de métricas de um Resultado, com as médias."""

    def __init__(self, resultado):
        self.por_tarefa = [MetricaTarefa(t) for t in sorted(resultado.tarefas, key=lambda x: x.id)]
        n = len(self.por_tarefa)
        self.tt_medio = sum(m.tt for m in self.por_tarefa) / n
        self.tp_medio = sum(m.tp for m in self.por_tarefa) / n
        self.tw_medio = sum(m.tw for m in self.por_tarefa) / n
        self.primeira_execucao_media = sum(m.primeira_execucao for m in self.por_tarefa) / n
        self.trocas = resultado.trocas
        self.eficiencia = eficiencia(resultado.parametros)

    def linhas(self):
        """Linhas (id, ingresso, tp, conclusão, tt, tw, 1ª exec) para exibição."""
        return [(m.id, m.ingresso, m.tp, m.conclusao, m.tt, m.tw, m.primeira_execucao)
                for m in self.por_tarefa]


def eficiencia(parametros):
    """E = tq / (tq + ttc) sob Round-Robin; None quando não há quantum."""
    if parametros.algoritmo != "RR":
        return None
    return parametros.quantum / (parametros.quantum + parametros.custo_troca)


def formatar_eficiencia(valor):
    if valor is None:
        return "não definida (sem quantum)"
    return f"{valor:.3f}"
