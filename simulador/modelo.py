"""Estrutura de uma tarefa e de um cenário.

Uma tarefa é descrita por identificador, instante de ingresso, tempo de
processamento (tp), prioridade e, opcionalmente, uma seção crítica sobre o
recurso R. A seção crítica é medida no tempo de execução própria da tarefa
(convenção C7): início 1 e duração 4 significam que a tarefa obtém R depois de
executar 1 unidade útil e o mantém até ter executado 5.

Um cenário reúne a lista de tarefas e os parâmetros com que ela foi simulada,
para que possa ser gravado em JSON e recarregado depois.
"""

import json
from dataclasses import dataclass, field, asdict


ALGORITMOS = ("FCFS", "SJF", "SRTF", "RR", "PRIOc", "PRIOp")
PROTOCOLOS = ("nenhum", "heranca", "teto")


class EntradaInvalida(ValueError):
    """Valor de entrada fora da faixa aceita. A mensagem descreve o motivo."""


@dataclass
class Tarefa:
    id: int
    ingresso: int
    tp: int
    prioridade: int
    uso_de_r: tuple | None = None   # (inicio, duracao) ou None

    # Estado de execução. Preenchido pelo motor e reiniciado a cada simulação.
    executado: int = field(default=0, compare=False)
    conclusao: int | None = field(default=None, compare=False)
    primeiro_despacho: int | None = field(default=None, compare=False)
    ultimo_despacho: int | None = field(default=None, compare=False)
    prioridade_elevada: int | None = field(default=None, compare=False)
    detem_r: bool = field(default=False, compare=False)
    bloqueada: bool = field(default=False, compare=False)

    def __post_init__(self):
        validar_tarefa(self.id, self.ingresso, self.tp, self.prioridade, self.uso_de_r)
        if self.uso_de_r is not None:
            self.uso_de_r = (int(self.uso_de_r[0]), int(self.uso_de_r[1]))

    @property
    def nome(self):
        return f"t{self.id}"

    @property
    def restante(self):
        return self.tp - self.executado

    @property
    def concluida(self):
        return self.executado >= self.tp

    @property
    def inicio_secao(self):
        return None if self.uso_de_r is None else self.uso_de_r[0]

    @property
    def fim_secao(self):
        return None if self.uso_de_r is None else self.uso_de_r[0] + self.uso_de_r[1]

    def reiniciar(self):
        self.executado = 0
        self.conclusao = None
        self.primeiro_despacho = None
        self.ultimo_despacho = None
        self.prioridade_elevada = None
        self.detem_r = False
        self.bloqueada = False

    def copia(self):
        return Tarefa(self.id, self.ingresso, self.tp, self.prioridade, self.uso_de_r)

    def para_dict(self):
        d = {"id": self.id, "ingresso": self.ingresso, "tp": self.tp,
             "prioridade": self.prioridade}
        if self.uso_de_r is not None:
            d["uso_de_r"] = list(self.uso_de_r)
        return d

    @staticmethod
    def de_dict(d):
        uso = d.get("uso_de_r")
        return Tarefa(int(d["id"]), int(d["ingresso"]), int(d["tp"]),
                      int(d["prioridade"]), tuple(uso) if uso else None)


def validar_tarefa(id, ingresso, tp, prioridade, uso_de_r):
    """Confere as faixas válidas de uma tarefa e levanta EntradaInvalida."""
    if id < 1:
        raise EntradaInvalida(f"Identificador da tarefa deve ser positivo (recebido {id}).")
    if ingresso < 0:
        raise EntradaInvalida(f"Tarefa t{id}: instante de ingresso não pode ser negativo (recebido {ingresso}).")
    if tp <= 0:
        raise EntradaInvalida(f"Tarefa t{id}: tempo de processamento deve ser positivo (recebido {tp}).")
    if prioridade < 0:
        raise EntradaInvalida(f"Tarefa t{id}: prioridade não pode ser negativa (recebido {prioridade}).")
    if uso_de_r is not None:
        inicio, duracao = uso_de_r
        if inicio < 0:
            raise EntradaInvalida(f"Tarefa t{id}: início da seção crítica não pode ser negativo (recebido {inicio}).")
        if duracao <= 0:
            raise EntradaInvalida(f"Tarefa t{id}: duração da seção crítica deve ser positiva (recebido {duracao}).")
        if inicio + duracao > tp:
            raise EntradaInvalida(
                f"Tarefa t{id}: seção crítica [{inicio}, {inicio + duracao}) ultrapassa o tempo de "
                f"processamento {tp}. Ela precisa caber dentro da tarefa.")


@dataclass
class Parametros:
    """Parâmetros do escalonador informados por quem executa o simulador."""
    algoritmo: str = "FCFS"
    quantum: int = 2
    custo_troca: int = 0
    protocolo: str = "nenhum"      # nenhum | herança | teto
    envelhecimento: int = 0        # passo alfa; 0 desliga

    def validar(self):
        if self.algoritmo not in ALGORITMOS:
            raise EntradaInvalida(f"Algoritmo desconhecido: {self.algoritmo}.")
        if self.protocolo not in PROTOCOLOS:
            raise EntradaInvalida(f"Protocolo desconhecido: {self.protocolo}.")
        if self.custo_troca < 0:
            raise EntradaInvalida(f"Custo da troca de contexto não pode ser negativo (recebido {self.custo_troca}).")
        if self.envelhecimento < 0:
            raise EntradaInvalida(f"Passo do envelhecimento não pode ser negativo (recebido {self.envelhecimento}).")
        if self.algoritmo == "RR":
            if self.quantum <= 0:
                raise EntradaInvalida(f"Quantum deve ser positivo (recebido {self.quantum}).")
            if self.quantum <= self.custo_troca:
                raise EntradaInvalida(
                    f"Quantum ({self.quantum}) precisa ser maior que o custo da troca de contexto "
                    f"({self.custo_troca}): se a troca consumisse a fatia inteira, nenhum trabalho "
                    f"útil seria realizado.")
        return self

    def para_dict(self):
        return asdict(self)

    @staticmethod
    def de_dict(d):
        p = Parametros()
        for chave in ("algoritmo", "quantum", "custo_troca", "protocolo", "envelhecimento"):
            if chave in d:
                setattr(p, chave, d[chave])
        p.quantum = int(p.quantum)
        p.custo_troca = int(p.custo_troca)
        p.envelhecimento = int(p.envelhecimento)
        return p


@dataclass
class Cenario:
    tarefas: list
    parametros: Parametros = field(default_factory=Parametros)
    nome: str = ""

    def validar(self):
        ids = [t.id for t in self.tarefas]
        if not ids:
            raise EntradaInvalida("O cenário precisa ter ao menos uma tarefa.")
        if len(ids) != len(set(ids)):
            raise EntradaInvalida("Identificadores de tarefa repetidos.")
        self.parametros.validar()
        return self

    def para_dict(self):
        return {"nome": self.nome,
                "parametros": self.parametros.para_dict(),
                "tarefas": [t.para_dict() for t in self.tarefas]}

    @staticmethod
    def de_dict(d):
        tarefas = [Tarefa.de_dict(x) for x in d.get("tarefas", [])]
        params = Parametros.de_dict(d.get("parametros", {}))
        return Cenario(tarefas, params, d.get("nome", ""))

    def gravar(self, caminho):
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(self.para_dict(), f, indent=2, ensure_ascii=False)

    @staticmethod
    def carregar(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            try:
                dados = json.load(f)
            except json.JSONDecodeError as e:
                raise EntradaInvalida(f"O arquivo não está em formato JSON válido: {e}") from e
        try:
            return Cenario.de_dict(dados)
        except (KeyError, TypeError, ValueError) as e:
            raise EntradaInvalida(f"O arquivo não descreve um cenário válido: {e}") from e
