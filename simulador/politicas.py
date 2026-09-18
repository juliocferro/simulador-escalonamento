"""Os seis algoritmos de escalonamento: a política.

Cada política responde a uma única pergunta: dado o conjunto de tarefas
prontas, qual delas recebe o processador? Ela não conhece o relógio, não cobra
troca de contexto e não sabe da existência do recurso R. Tudo isso é trabalho
do motor (motor.py), que monta o conjunto de prontas e entrega a política.

O desempate entre tarefas equivalentes segue a convenção C3: menor instante de
ingresso e, persistindo o empate, menor identificador. Por isso toda chave de
ordenação termina com (ingresso, id).

A política recebe também um contexto, com o método prioridade_efetiva(tarefa),
para que as políticas de prioridade enxerguem herança, teto e envelhecimento
sem precisar saber como esses valores foram calculados.
"""


def _desempate(tarefa):
    return (tarefa.ingresso, tarefa.id)


class Politica:
    """Base comum. As subclasses definem escolher() e os três atributos abaixo."""

    sigla = ""
    nome = ""
    preemptiva = False      # a decisão é reavaliada a cada unidade de tempo
    usa_quantum = False     # a tarefa perde o processador ao esgotar a fatia
    usa_prioridade = False  # a escolha depende da prioridade (efetiva)

    def escolher(self, prontas, contexto):
        raise NotImplementedError

    def quantum_esgotado(self, tarefa):
        """Avisa que a tarefa esgotou a fatia. Só o Round-Robin se importa."""

    def reiniciar(self):
        """Limpa qualquer estado interno antes de uma nova simulação."""


class FCFS(Politica):
    sigla = "FCFS"
    nome = "First-Come, First-Served"

    def escolher(self, prontas, contexto):
        return min(prontas, key=_desempate)


class SJF(Politica):
    sigla = "SJF"
    nome = "Shortest Job First"

    def escolher(self, prontas, contexto):
        return min(prontas, key=lambda t: (t.tp,) + _desempate(t))


class SRTF(Politica):
    sigla = "SRTF"
    nome = "Shortest Remaining Time First"
    preemptiva = True

    def escolher(self, prontas, contexto):
        return min(prontas, key=lambda t: (t.restante,) + _desempate(t))


class RoundRobin(Politica):
    """Fila circular.

    A fila é mantida na ordem de chegada ao conjunto de prontas. Uma tarefa que
    esgota o quantum volta à cauda depois das que ingressaram naquele mesmo
    instante (convenção C6): o motor chama quantum_esgotado() e, na próxima
    escolha, as recém-chegadas são enfileiradas antes da tarefa reposicionada.
    """

    sigla = "RR"
    nome = "Round-Robin"
    usa_quantum = True

    def __init__(self):
        self.fila = []
        self._reposicionar = None

    def reiniciar(self):
        self.fila = []
        self._reposicionar = None

    def escolher(self, prontas, contexto):
        prontas_ordenadas = sorted(prontas, key=_desempate)
        presentes = set(id(t) for t in prontas)
        self.fila = [t for t in self.fila if id(t) in presentes]
        na_fila = set(id(t) for t in self.fila)
        for t in prontas_ordenadas:
            if id(t) not in na_fila:
                self.fila.append(t)
        if self._reposicionar is not None:
            t = self._reposicionar
            self._reposicionar = None
            if t in self.fila:
                self.fila.remove(t)
                self.fila.append(t)
        return self.fila[0]

    def quantum_esgotado(self, tarefa):
        self._reposicionar = tarefa


class PrioridadeCooperativa(Politica):
    sigla = "PRIOc"
    nome = "Prioridade cooperativa"
    usa_prioridade = True

    def escolher(self, prontas, contexto):
        return min(prontas, key=lambda t: (-contexto.prioridade_efetiva(t),) + _desempate(t))


class PrioridadePreemptiva(PrioridadeCooperativa):
    sigla = "PRIOp"
    nome = "Prioridade preemptiva"
    preemptiva = True


POLITICAS = {p.sigla: p for p in (FCFS, SJF, SRTF, RoundRobin,
                                  PrioridadeCooperativa, PrioridadePreemptiva)}


def criar_politica(sigla):
    try:
        return POLITICAS[sigla]()
    except KeyError:
        raise ValueError(f"Algoritmo desconhecido: {sigla}") from None
