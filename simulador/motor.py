"""Laço de simulação: o mecanismo.

O motor avança o relógio de uma em uma unidade (C1), monta o conjunto de
tarefas prontas, cobra a troca de contexto (C4, C5), administra o recurso R e
recalcula a prioridade efetiva sob herança, teto e envelhecimento. Ele não
conhece o critério de escolha: a cada decisão entrega o conjunto de prontas a
política e recebe de volta a tarefa escolhida.

O que acontece em uma unidade de tempo t:

1. Tarefas que chegaram ao início da seção crítica pedem R. Se R está ocupado,
   a tarefa fica suspensa e sai do conjunto de prontas.
2. Sob herança, a detentora de R assume a maior prioridade entre as suspensas
   e a sua própria.
3. O conjunto de prontas é montado: tarefas que já ingressaram, não concluíram
   e não estão suspensas. Se estiver vazio, o relógio salta para o próximo
   ingresso.
4. A política é consultada quando o processador está livre, quando o quantum
   se esgotou ou, nas políticas preemptivas, a cada unidade de tempo.
5. Se a tarefa escolhida é diferente da última que ocupou o processador, há
   troca de contexto: custa ttc unidades, descontadas da fatia (C5). A troca e
   a primeira unidade útil que a segue são indivisíveis: nenhuma decisão é
   tomada durante a troca, para que o custo pago sempre produza trabalho.
6. A tarefa executa uma unidade útil. Ao atingir o início da seção crítica ela
   obtém R (sob teto, assume o teto do recurso); ao atingir o fim, libera R,
   devolve a prioridade e acorda as suspensas.
"""

from .politicas import criar_politica


class Segmento:
    """Um intervalo [inicio, fim) do diagrama de tempo, de um dado tipo."""

    __slots__ = ("tarefa", "inicio", "fim", "tipo")

    def __init__(self, tarefa, inicio, fim, tipo):
        self.tarefa = tarefa    # id da tarefa
        self.inicio = inicio
        self.fim = fim
        self.tipo = tipo        # "execucao" | "troca" | "bloqueio" | "recurso"

    def __repr__(self):
        return f"t{self.tarefa}[{self.inicio},{self.fim}) {self.tipo}"


class Resultado:
    """Tudo o que uma simulação produz."""

    def __init__(self, tarefas, parametros):
        self.tarefas = tarefas              # lista de Tarefa, já com o estado final
        self.parametros = parametros
        self.segmentos = []                 # lista de Segmento
        self.eventos = []                   # (instante, texto)
        self.trocas = 0
        self.instante_final = 0
        self.bloqueio_direto = {}           # id -> unidades esperando pela detentora de R
        self.inversao = {}                  # id -> unidades esperando por terceiras

    def sequencia(self):
        """Sequência de execução no formato do enunciado: t1[0,2) t4[2,3) ..."""
        return " ".join(f"t{s.tarefa}[{s.inicio},{s.fim})"
                        for s in self.segmentos if s.tipo == "execucao")

    def _acrescentar(self, tarefa, t, tipo):
        for s in reversed(self.segmentos):
            if s.tarefa == tarefa and s.tipo == tipo:
                if s.fim == t:
                    s.fim = t + 1
                    return
                break
        self.segmentos.append(Segmento(tarefa, t, t + 1, tipo))

    def _registrar(self, t, texto):
        self.eventos.append((t, texto))


class Motor:
    """Executa um cenário sob uma política. Uma instância por simulação."""

    def __init__(self, tarefas, parametros):
        parametros.validar()
        self.tarefas = [t.copia() for t in sorted(tarefas, key=lambda x: (x.ingresso, x.id))]
        self.p = parametros
        self.politica = criar_politica(parametros.algoritmo)
        self.resultado = Resultado(self.tarefas, parametros)
        self.t = 0
        self.atual = None            # tarefa que ocupa o processador
        self.ultima = None           # última tarefa que ocupou o processador
        self.troca_restante = 0
        self.fatia_restante = 0
        self.detentora_r = None
        self.teto_r = self._calcular_teto()

    # ---- prioridade efetiva -------------------------------------------------

    def prioridade_efetiva(self, tarefa):
        """Prioridade usada pela política: base, envelhecimento e elevação."""
        base = tarefa.prioridade
        if self.p.envelhecimento > 0 and tarefa is not self.atual:
            referencia = tarefa.ingresso if tarefa.ultimo_despacho is None else tarefa.ultimo_despacho
            base += self.p.envelhecimento * (self.t - referencia)
        if tarefa.prioridade_elevada is not None:
            return max(base, tarefa.prioridade_elevada)
        return base

    def _calcular_teto(self):
        """Teto de R: maior prioridade entre as tarefas que declaram seção crítica (C9)."""
        usuarias = [t.prioridade for t in self.tarefas if t.uso_de_r is not None]
        return max(usuarias) if usuarias else None

    # ---- laço principal -----------------------------------------------------

    def executar(self, limite=100000):
        r = self.resultado
        self.politica.reiniciar()
        while any(not t.concluida for t in self.tarefas):
            if self.t > limite:
                raise RuntimeError("A simulação ultrapassou o limite de tempo.")
            self._tratar_pedidos_de_recurso()
            self._aplicar_heranca()
            prontas = [t for t in self.tarefas
                       if t.ingresso <= self.t and not t.concluida and not t.bloqueada]
            if not prontas:
                self._saltar_relogio()
                continue
            escolhida = self._decidir(prontas)
            if escolhida is not self.ultima:
                self._trocar_contexto(escolhida)
                while self.troca_restante > 0:
                    self._unidade_de_troca()
            elif escolhida is not self.atual:
                self._despachar(escolhida)
            self._unidade_de_execucao()
        r.instante_final = self.t
        return r

    def _decidir(self, prontas):
        precisa_decidir = (self.atual is None or self.politica.preemptiva
                           or (self.politica.usa_quantum and self.fatia_restante <= 0))
        if not precisa_decidir:
            return self.atual
        if self.politica.usa_quantum and self.atual is not None and self.fatia_restante <= 0:
            self.politica.quantum_esgotado(self.atual)
            self.atual = None
        escolhida = self.politica.escolher(prontas, self)
        if self.atual is not None and escolhida is not self.atual:
            self.resultado._registrar(self.t, f"t{self.atual.id} é preemptada por t{escolhida.id}")
        return escolhida

    def _despachar(self, tarefa):
        """A tarefa recebe o processador (com ou sem troca de contexto)."""
        self.atual = tarefa
        self.fatia_restante = self.p.quantum if self.politica.usa_quantum else 0
        if tarefa.primeiro_despacho is None:
            tarefa.primeiro_despacho = self.t
        tarefa.ultimo_despacho = self.t

    def _trocar_contexto(self, tarefa):
        self.resultado.trocas += 1
        self.ultima = tarefa
        self._despachar(tarefa)
        self.troca_restante = self.p.custo_troca

    def _unidade_de_troca(self):
        self.resultado._acrescentar(self.atual.id, self.t, "troca")
        self._registrar_espera()
        self.troca_restante -= 1
        self.fatia_restante -= 1
        self.t += 1

    def _unidade_de_execucao(self):
        tarefa = self.atual
        r = self.resultado
        if tarefa.uso_de_r is not None and not tarefa.detem_r and tarefa.executado == tarefa.inicio_secao:
            self._obter_recurso(tarefa)
        r._acrescentar(tarefa.id, self.t, "execucao")
        self._registrar_espera()
        tarefa.executado += 1
        self.fatia_restante -= 1
        self.t += 1
        if tarefa.detem_r and tarefa.executado == tarefa.fim_secao:
            self._liberar_recurso(tarefa)
        if tarefa.concluida:
            tarefa.conclusao = self.t
            r._registrar(self.t, f"t{tarefa.id} conclui")
            self.atual = None

    def _saltar_relogio(self):
        futuros = [t.ingresso for t in self.tarefas if not t.concluida and t.ingresso > self.t]
        if not futuros:
            raise RuntimeError("Nenhuma tarefa pronta e nenhum ingresso futuro: impasse no recurso.")
        proximo = min(futuros)
        self.resultado._registrar(self.t, f"processador ocioso até {proximo}")
        self.t = proximo
        self.atual = None

    # ---- recurso R ----------------------------------------------------------

    def _tratar_pedidos_de_recurso(self):
        """Tarefas no início da seção crítica pedem R; se ocupado, suspendem."""
        for t in self.tarefas:
            if t.uso_de_r is None or t.detem_r or t.concluida or t.ingresso > self.t:
                continue
            if t.executado != t.inicio_secao:
                continue
            if self.detentora_r is not None and self.detentora_r is not t:
                if not t.bloqueada:
                    t.bloqueada = True
                    self.resultado._registrar(
                        self.t, f"t{t.id} solicita R, ocupado por t{self.detentora_r.id}, e fica suspensa")
                    if self.atual is t:
                        self.atual = None
            else:
                t.bloqueada = False

    def _obter_recurso(self, tarefa):
        tarefa.detem_r = True
        self.detentora_r = tarefa
        texto = f"t{tarefa.id} obtém R"
        if self.p.protocolo == "teto" and self.teto_r is not None and self.teto_r > tarefa.prioridade:
            tarefa.prioridade_elevada = self.teto_r
            texto += f" e assume o teto {self.teto_r}"
        self.resultado._registrar(self.t, texto)
        self.resultado.segmentos.append(Segmento(tarefa.id, self.t, self.t, "recurso"))

    def _liberar_recurso(self, tarefa):
        tarefa.detem_r = False
        self.detentora_r = None
        texto = f"t{tarefa.id} libera R"
        if tarefa.prioridade_elevada is not None:
            texto += f" e volta a prioridade {tarefa.prioridade}"
            tarefa.prioridade_elevada = None
        for s in reversed(self.resultado.segmentos):
            if s.tipo == "recurso" and s.tarefa == tarefa.id:
                s.fim = self.t
                break
        acordadas = [t for t in self.tarefas if t.bloqueada]
        for t in acordadas:
            t.bloqueada = False
        if acordadas:
            texto += "; " + ", ".join(f"t{t.id}" for t in acordadas) + " volta(m) ao conjunto de prontas"
        self.resultado._registrar(self.t, texto)

    def _aplicar_heranca(self):
        if self.p.protocolo != "heranca" or self.detentora_r is None:
            return
        d = self.detentora_r
        suspensas = [t for t in self.tarefas if t.bloqueada]
        if not suspensas:
            return
        maior = max(t.prioridade for t in suspensas)
        if maior > d.prioridade and d.prioridade_elevada != maior:
            d.prioridade_elevada = maior
            self.resultado._registrar(self.t, f"t{d.id} herda a prioridade {maior}")

    def _registrar_espera(self):
        """Classifica cada unidade de espera das tarefas suspensas (R5)."""
        r = self.resultado
        for t in self.tarefas:
            if not t.bloqueada:
                continue
            r._acrescentar(t.id, self.t, "bloqueio")
            if self.atual is self.detentora_r:
                r.bloqueio_direto[t.id] = r.bloqueio_direto.get(t.id, 0) + 1
            else:
                r.inversao[t.id] = r.inversao.get(t.id, 0) + 1


def simular(tarefas, parametros):
    """Atalho: cria o motor, executa e devolve o Resultado."""
    return Motor(tarefas, parametros).executar()
