"""Janela do simulador (tkinter, biblioteca padrão do Python).

A interface le os dados digitados, valida cada campo e entrega ao motor. Um
valor inválido é recusado com uma mensagem e o foco volta ao campo, para que
o valor seja corrigido; o programa nunca fecha por causa de uma entrada
errada. Erros inesperados também são mostrados em janela, nunca no console.
"""

import os
import sys
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .modelo import Tarefa, Parametros, Cenario, EntradaInvalida, ALGORITMOS
from .politicas import POLITICAS
from .motor import simular
from .metricas import Metricas, formatar_eficiencia
from .gerador import FaixasSorteio, sortear_tarefas, comparar_em_lote
from .exemplos import EXEMPLOS, exemplo_inicial

MAX_TAREFAS = 30

CORES = ["#4e79a7", "#f28e2b", "#59a14f", "#e15759", "#b07aa1", "#76b7b2",
         "#edc948", "#ff9da7", "#9c755f", "#bab0ac"]
COR_TROCA = "#9e9e9e"
COR_BLOQUEIO = "#d62728"
COR_RECURSO = "#222222"


def pasta_base():
    """Pasta onde o programa esta: ao lado do .exe ou a raiz do repositório."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pasta_cenarios():
    p = os.path.join(pasta_base(), "cenarios")
    return p if os.path.isdir(p) else pasta_base()


def ler_inteiro(entrada, rotulo, minimo=None, maximo=None):
    """Le um inteiro de um Entry. Em caso de erro, foca o campo e levanta EntradaInvalida."""
    texto = entrada.get().strip()
    try:
        valor = int(texto)
    except ValueError:
        entrada.focus_set()
        entrada.selection_range(0, tk.END)
        raise EntradaInvalida(f"{rotulo}: informe um número inteiro (recebido '{texto}').")
    if minimo is not None and valor < minimo:
        entrada.focus_set()
        entrada.selection_range(0, tk.END)
        raise EntradaInvalida(f"{rotulo}: o valor mínimo é {minimo} (recebido {valor}).")
    if maximo is not None and valor > maximo:
        entrada.focus_set()
        entrada.selection_range(0, tk.END)
        raise EntradaInvalida(f"{rotulo}: o valor máximo é {maximo} (recebido {valor}).")
    return valor


class LinhaTarefa:
    """Os campos de entrada de uma tarefa na tabela."""

    def __init__(self, pai, numero, linha):
        self.numero = numero
        self.rotulo = ttk.Label(pai, text=f"t{numero}", width=5, anchor="center")
        self.ingresso = ttk.Entry(pai, width=8, justify="center")
        self.tp = ttk.Entry(pai, width=8, justify="center")
        self.prioridade = ttk.Entry(pai, width=9, justify="center")
        self.usa_r = tk.BooleanVar(value=False)
        self.check = ttk.Checkbutton(pai, variable=self.usa_r, command=self._alternar_r)
        self.inicio_r = ttk.Entry(pai, width=8, justify="center")
        self.duracao_r = ttk.Entry(pai, width=8, justify="center")
        widgets = (self.rotulo, self.ingresso, self.tp, self.prioridade,
                   self.check, self.inicio_r, self.duracao_r)
        for col, w in enumerate(widgets):
            w.grid(row=linha + 1, column=col, padx=2, pady=1)
        self.widgets = widgets
        self.definir(Tarefa(numero, 0, 1, 1))
        self._alternar_r()

    def _alternar_r(self):
        estado = "normal" if self.usa_r.get() else "disabled"
        self.inicio_r.configure(state=estado)
        self.duracao_r.configure(state=estado)

    def definir(self, tarefa):
        for entrada, valor in ((self.ingresso, tarefa.ingresso), (self.tp, tarefa.tp),
                               (self.prioridade, tarefa.prioridade)):
            entrada.delete(0, tk.END)
            entrada.insert(0, str(valor))
        self.usa_r.set(tarefa.uso_de_r is not None)
        for entrada in (self.inicio_r, self.duracao_r):
            entrada.configure(state="normal")
            entrada.delete(0, tk.END)
        if tarefa.uso_de_r is not None:
            self.inicio_r.insert(0, str(tarefa.uso_de_r[0]))
            self.duracao_r.insert(0, str(tarefa.uso_de_r[1]))
        else:
            self.inicio_r.insert(0, "0")
            self.duracao_r.insert(0, "1")
        self._alternar_r()

    def ler(self):
        n = self.numero
        ingresso = ler_inteiro(self.ingresso, f"Tarefa t{n}, ingresso", minimo=0)
        tp = ler_inteiro(self.tp, f"Tarefa t{n}, tempo de processamento", minimo=1)
        prioridade = ler_inteiro(self.prioridade, f"Tarefa t{n}, prioridade", minimo=0)
        uso = None
        if self.usa_r.get():
            inicio = ler_inteiro(self.inicio_r, f"Tarefa t{n}, início da seção crítica", minimo=0)
            duracao = ler_inteiro(self.duracao_r, f"Tarefa t{n}, duração da seção crítica", minimo=1)
            if inicio + duracao > tp:
                self.duracao_r.focus_set()
                self.duracao_r.selection_range(0, tk.END)
                raise EntradaInvalida(
                    f"Tarefa t{n}: a seção crítica [{inicio}, {inicio + duracao}) ultrapassa o tempo "
                    f"de processamento {tp}. Ela precisa caber dentro da tarefa.")
            uso = (inicio, duracao)
        return Tarefa(n, ingresso, tp, prioridade, uso)

    def destruir(self):
        for w in self.widgets:
            w.destroy()


class Aplicacao(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulador de Escalonamento de Tarefas")
        self.minsize(1100, 700)
        self.geometry("1280x760")
        self.report_callback_exception = self._erro_inesperado
        self.linhas = []
        self.ultimo_resultado = None
        self._estilo()
        self._montar()
        self.carregar_cenario(exemplo_inicial())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # ---- construcao ---------------------------------------------------------

    def _estilo(self):
        estilo = ttk.Style(self)
        if "vista" in estilo.theme_names():
            estilo.theme_use("vista")
        elif "clam" in estilo.theme_names():
            estilo.theme_use("clam")
        estilo.configure("Titulo.TLabel", font=("TkDefaultFont", 10, "bold"))
        estilo.configure("Acao.TButton", font=("TkDefaultFont", 10, "bold"))

    def _montar(self):
        painel = ttk.PanedWindow(self, orient="horizontal")
        painel.pack(fill="both", expand=True, padx=6, pady=6)
        esquerda = ttk.Frame(painel)
        direita = ttk.Frame(painel)
        painel.add(esquerda, weight=0)
        painel.add(direita, weight=1)
        self._montar_tarefas(esquerda)
        self._montar_parametros(esquerda)
        self._montar_lote(esquerda)
        self._montar_resultados(direita)

    def _montar_tarefas(self, pai):
        quadro = ttk.LabelFrame(pai, text=" Conjunto de tarefas ")
        quadro.pack(fill="x", padx=4, pady=4)

        topo = ttk.Frame(quadro)
        topo.pack(fill="x", padx=4, pady=(4, 2))
        ttk.Label(topo, text="Número de tarefas:").pack(side="left")
        self.qtd_tarefas = ttk.Spinbox(topo, from_=1, to=MAX_TAREFAS, width=4, justify="center")
        self.qtd_tarefas.pack(side="left", padx=4)
        self.qtd_tarefas.set("5")
        ttk.Button(topo, text="Aplicar", command=self.aplicar_quantidade).pack(side="left", padx=2)
        ttk.Button(topo, text="Sortear", command=self.sortear).pack(side="left", padx=2)
        self.menu_exemplos = ttk.Menubutton(topo, text="Exemplos")
        menu = tk.Menu(self.menu_exemplos, tearoff=False)
        for rotulo, _, fabrica in EXEMPLOS:
            menu.add_command(label=rotulo, command=lambda f=fabrica: self.carregar_cenario(f()))
        self.menu_exemplos.configure(menu=menu)
        self.menu_exemplos.pack(side="left", padx=2)

        self.canvas_tabela = tk.Canvas(quadro, height=190, highlightthickness=0)
        barra = ttk.Scrollbar(quadro, orient="vertical", command=self.canvas_tabela.yview)
        self.canvas_tabela.configure(yscrollcommand=barra.set)
        self.canvas_tabela.pack(side="left", fill="both", expand=True, padx=(4, 0))
        barra.pack(side="left", fill="y", padx=(0, 4))
        self.tabela = ttk.Frame(self.canvas_tabela)
        self.canvas_tabela.create_window((0, 0), window=self.tabela, anchor="nw")
        for col, texto in enumerate(("Tarefa", "Ingresso", "tp", "Prioridade", "Usa R",
                                     "Início SC", "Duração SC")):
            ttk.Label(self.tabela, text=texto, anchor="center", style="Titulo.TLabel").grid(
                row=0, column=col, padx=2, pady=(0, 2))
        self.tabela.bind("<Configure>",
                         lambda e: self.canvas_tabela.configure(scrollregion=self.canvas_tabela.bbox("all")))

        rodape = ttk.Frame(pai)
        rodape.pack(fill="x", padx=4)
        ttk.Button(rodape, text="Gravar cenário...", command=self.gravar).pack(side="left", padx=2)
        ttk.Button(rodape, text="Carregar cenário...", command=self.carregar).pack(side="left", padx=2)
        self.rotulo_cenario = ttk.Label(rodape, text="", foreground="#555555")
        self.rotulo_cenario.pack(side="left", padx=8)

    def _montar_parametros(self, pai):
        quadro = ttk.LabelFrame(pai, text=" Parâmetros do escalonador ")
        quadro.pack(fill="x", padx=4, pady=4)
        grade = ttk.Frame(quadro)
        grade.pack(fill="x", padx=4, pady=4)

        ttk.Label(grade, text="Algoritmo:").grid(row=0, column=0, sticky="w", pady=2)
        self.algoritmo = ttk.Combobox(grade, state="readonly", width=34,
                                      values=[f"{s} - {POLITICAS[s].nome}" for s in ALGORITMOS])
        self.algoritmo.current(0)
        self.algoritmo.grid(row=0, column=1, columnspan=3, sticky="w", pady=2)
        self.algoritmo.bind("<<ComboboxSelected>>", lambda e: self._atualizar_estado_campos())

        ttk.Label(grade, text="Quantum tq:").grid(row=1, column=0, sticky="w", pady=2)
        self.quantum = ttk.Entry(grade, width=6, justify="center")
        self.quantum.insert(0, "2")
        self.quantum.grid(row=1, column=1, sticky="w", pady=2)
        ttk.Label(grade, text="Custo da troca ttc:").grid(row=1, column=2, sticky="w", padx=(12, 0))
        self.custo_troca = ttk.Entry(grade, width=6, justify="center")
        self.custo_troca.insert(0, "0")
        self.custo_troca.grid(row=1, column=3, sticky="w")

        ttk.Label(grade, text="Protocolo para R:").grid(row=2, column=0, sticky="w", pady=2)
        self.protocolo = tk.StringVar(value="nenhum")
        caixa = ttk.Frame(grade)
        caixa.grid(row=2, column=1, columnspan=3, sticky="w")
        for valor, texto in (("nenhum", "nenhum"), ("heranca", "herança de prioridade"),
                             ("teto", "teto de prioridade")):
            ttk.Radiobutton(caixa, text=texto, value=valor, variable=self.protocolo).pack(side="left", padx=(0, 8))

        ttk.Label(grade, text="Envelhecimento (alfa):").grid(row=3, column=0, sticky="w", pady=2)
        self.envelhecimento = ttk.Entry(grade, width=6, justify="center")
        self.envelhecimento.insert(0, "0")
        self.envelhecimento.grid(row=3, column=1, sticky="w", pady=2)
        ttk.Label(grade, text="(0 desliga)", foreground="#555555").grid(row=3, column=2, sticky="w", padx=(12, 0))

        ttk.Button(quadro, text="Simular", style="Acao.TButton", command=self.simular).pack(
            fill="x", padx=4, pady=(2, 6))
        self._atualizar_estado_campos()

    def _montar_lote(self, pai):
        quadro = ttk.LabelFrame(pai, text=" Sorteio e comparação em lote ")
        quadro.pack(fill="x", padx=4, pady=4)
        grade = ttk.Frame(quadro)
        grade.pack(fill="x", padx=4, pady=4)
        self.faixa_ingresso = self._campo(grade, 0, 0, "Ingresso máximo:", "8")
        self.faixa_tp = self._campo(grade, 0, 2, "tp máximo:", "6")
        self.faixa_prioridade = self._campo(grade, 1, 0, "Prioridade máxima:", "5")
        self.amostras = self._campo(grade, 1, 2, "Cenários no lote:", "50")
        self.sortear_r = tk.BooleanVar(value=False)
        ttk.Checkbutton(grade, text="sortear seções críticas em parte das tarefas",
                        variable=self.sortear_r).grid(row=2, column=0, columnspan=4, sticky="w", pady=2)
        ttk.Label(quadro, text="O sorteio usa o número de tarefas e as faixas acima. O lote sorteia\n"
                               "vários cenários e compara os seis algoritmos com o quantum e o custo\n"
                               "de troca informados nos parâmetros.",
                  foreground="#555555", justify="left").pack(anchor="w", padx=6)
        ttk.Button(quadro, text="Comparar os seis algoritmos em lote",
                   command=self.comparar_lote).pack(fill="x", padx=4, pady=(4, 6))

    def _campo(self, grade, linha, coluna, rotulo, valor):
        ttk.Label(grade, text=rotulo).grid(row=linha, column=coluna, sticky="w", pady=2,
                                           padx=(0 if coluna == 0 else 12, 0))
        entrada = ttk.Entry(grade, width=6, justify="center")
        entrada.insert(0, valor)
        entrada.grid(row=linha, column=coluna + 1, sticky="w", pady=2)
        return entrada

    def _montar_resultados(self, pai):
        self.abas = ttk.Notebook(pai)
        self.abas.pack(fill="both", expand=True, padx=4, pady=4)

        aba = ttk.Frame(self.abas)
        self.abas.add(aba, text="  Métricas  ")
        self.resumo = ttk.Label(aba, text="Preencha as tarefas e clique em Simular.", justify="left")
        self.resumo.pack(anchor="w", padx=6, pady=(6, 2))
        colunas = ("tarefa", "ingresso", "tp", "conclusao", "tt", "tw", "primeira")
        self.arvore = ttk.Treeview(aba, columns=colunas, show="headings", height=12)
        for c, texto, largura in (("tarefa", "Tarefa", 60), ("ingresso", "Ingresso", 70),
                                  ("tp", "tp", 55), ("conclusao", "Conclusão", 80),
                                  ("tt", "tt (execução)", 95), ("tw", "tw (espera)", 95),
                                  ("primeira", "1ª execução", 95)):
            self.arvore.heading(c, text=texto)
            self.arvore.column(c, width=largura, anchor="center", stretch=True)
        self.arvore.tag_configure("media", font=("TkDefaultFont", 9, "bold"), background="#eef2f7")
        self.arvore.pack(fill="x", padx=6, pady=4)
        self.detalhes = tk.Text(aba, height=9, wrap="word", state="disabled",
                                font=("TkFixedFont", 9), relief="flat", background="#f7f7f7")
        self.detalhes.pack(fill="both", expand=True, padx=6, pady=(2, 6))

        aba = ttk.Frame(self.abas)
        self.abas.add(aba, text="  Diagrama de tempo  ")
        self.canvas = tk.Canvas(aba, background="white", highlightthickness=0)
        bx = ttk.Scrollbar(aba, orient="horizontal", command=self.canvas.xview)
        by = ttk.Scrollbar(aba, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=bx.set, yscrollcommand=by.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        by.grid(row=0, column=1, sticky="ns")
        bx.grid(row=1, column=0, sticky="ew")
        aba.rowconfigure(0, weight=1)
        aba.columnconfigure(0, weight=1)

        aba = ttk.Frame(self.abas)
        self.abas.add(aba, text="  Eventos  ")
        self.eventos = tk.Text(aba, wrap="word", state="disabled", font=("TkFixedFont", 9))
        be = ttk.Scrollbar(aba, orient="vertical", command=self.eventos.yview)
        self.eventos.configure(yscrollcommand=be.set)
        self.eventos.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        be.pack(side="left", fill="y", pady=6)

        aba = ttk.Frame(self.abas)
        self.abas.add(aba, text="  Comparação em lote  ")
        self.resumo_lote = ttk.Label(aba, text="Clique em \"Comparar os seis algoritmos em lote\".",
                                     justify="left")
        self.resumo_lote.pack(anchor="w", padx=6, pady=(6, 2))
        colunas = ("algoritmo", "tt", "tw", "primeira")
        self.arvore_lote = ttk.Treeview(aba, columns=colunas, show="headings", height=6)
        for c, texto in (("algoritmo", "Algoritmo"), ("tt", "Tt médio"), ("tw", "Tw médio"),
                         ("primeira", "1ª execução média")):
            self.arvore_lote.heading(c, text=texto)
            self.arvore_lote.column(c, width=140, anchor="center")
        self.arvore_lote.pack(fill="x", padx=6, pady=4)
        self.detalhes_lote = ttk.Label(aba, text="", justify="left")
        self.detalhes_lote.pack(anchor="w", padx=6, pady=4)

    # ---- leitura e escrita dos campos --------------------------------------

    def _atualizar_estado_campos(self):
        sigla = self.sigla_algoritmo()
        self.quantum.configure(state="normal" if sigla == "RR" else "disabled")
        usa_prio = POLITICAS[sigla].usa_prioridade
        self.envelhecimento.configure(state="normal" if usa_prio else "disabled")

    def sigla_algoritmo(self):
        return self.algoritmo.get().split(" ")[0]

    def aplicar_quantidade(self):
        try:
            n = ler_inteiro(self.qtd_tarefas, "Número de tarefas", 1, MAX_TAREFAS)
        except EntradaInvalida as e:
            return self._recusar(e)
        self._definir_linhas(n)

    def _definir_linhas(self, n):
        while len(self.linhas) > n:
            self.linhas.pop().destruir()
        while len(self.linhas) < n:
            self.linhas.append(LinhaTarefa(self.tabela, len(self.linhas) + 1, len(self.linhas)))
        self.qtd_tarefas.set(str(n))

    def ler_tarefas(self):
        return [linha.ler() for linha in self.linhas]

    def ler_parametros(self):
        sigla = self.sigla_algoritmo()
        quantum = 1
        if sigla == "RR":
            quantum = ler_inteiro(self.quantum, "Quantum", minimo=1)
        custo = ler_inteiro(self.custo_troca, "Custo da troca de contexto", minimo=0)
        alfa = 0
        if POLITICAS[sigla].usa_prioridade:
            alfa = ler_inteiro(self.envelhecimento, "Passo do envelhecimento", minimo=0)
        p = Parametros(sigla, quantum, custo, self.protocolo.get(), alfa)
        try:
            p.validar()
        except EntradaInvalida:
            self.quantum.focus_set()
            self.quantum.selection_range(0, tk.END)
            raise
        return p

    def ler_faixas(self):
        return FaixasSorteio(
            quantidade=ler_inteiro(self.qtd_tarefas, "Número de tarefas", 1, MAX_TAREFAS),
            ingresso_max=ler_inteiro(self.faixa_ingresso, "Ingresso máximo", minimo=0),
            tp_max=ler_inteiro(self.faixa_tp, "tp máximo", minimo=1),
            prioridade_max=ler_inteiro(self.faixa_prioridade, "Prioridade máxima", minimo=1),
            com_recurso=self.sortear_r.get())

    def carregar_cenario(self, cenario):
        cenario.validar()
        self._definir_linhas(len(cenario.tarefas))
        for linha, tarefa in zip(self.linhas, sorted(cenario.tarefas, key=lambda t: t.id)):
            linha.definir(tarefa)
        p = cenario.parametros
        self.algoritmo.current(ALGORITMOS.index(p.algoritmo))
        for entrada, valor in ((self.quantum, p.quantum), (self.custo_troca, p.custo_troca),
                               (self.envelhecimento, p.envelhecimento)):
            entrada.configure(state="normal")
            entrada.delete(0, tk.END)
            entrada.insert(0, str(valor))
        self.protocolo.set(p.protocolo)
        self._atualizar_estado_campos()
        self.rotulo_cenario.configure(text=cenario.nome)

    # ---- acoes ----------------------------------------------------------------

    def _recusar(self, erro):
        messagebox.showerror("Valor inválido", str(erro), parent=self)

    def _erro_inesperado(self, tipo, valor, tb):
        texto = "".join(traceback.format_exception(tipo, valor, tb))
        messagebox.showerror("Erro inesperado",
                             "O simulador encontrou um erro e continua aberto.\n\n" + texto, parent=self)

    def sortear(self):
        try:
            tarefas = sortear_tarefas(self.ler_faixas())
        except EntradaInvalida as e:
            return self._recusar(e)
        self._definir_linhas(len(tarefas))
        for linha, tarefa in zip(self.linhas, tarefas):
            linha.definir(tarefa)
        self.rotulo_cenario.configure(text="cenário sorteado")

    def simular(self):
        try:
            tarefas = self.ler_tarefas()
            parametros = self.ler_parametros()
            resultado = simular(tarefas, parametros)
        except EntradaInvalida as e:
            return self._recusar(e)
        self.ultimo_resultado = resultado
        self.mostrar_resultado(resultado)
        self.abas.select(0)

    def comparar_lote(self):
        try:
            faixas = self.ler_faixas()
            amostras = ler_inteiro(self.amostras, "Cenários no lote", minimo=1, maximo=100000)
            base = self.ler_parametros_para_lote()
            medias = comparar_em_lote(faixas, amostras, base)
        except EntradaInvalida as e:
            return self._recusar(e)
        self.mostrar_lote(medias, amostras, faixas, base)
        self.abas.select(3)

    def ler_parametros_para_lote(self):
        """No lote o quantum é sempre necessário, porque o Round-Robin faz parte da comparação."""
        self.quantum.configure(state="normal")
        try:
            quantum = ler_inteiro(self.quantum, "Quantum", minimo=1)
        finally:
            self._atualizar_estado_campos()
        custo = ler_inteiro(self.custo_troca, "Custo da troca de contexto", minimo=0)
        self.envelhecimento.configure(state="normal")
        try:
            alfa = ler_inteiro(self.envelhecimento, "Passo do envelhecimento", minimo=0)
        finally:
            self._atualizar_estado_campos()
        p = Parametros("RR", quantum, custo, self.protocolo.get(), alfa)
        try:
            p.validar()
        except EntradaInvalida:
            self.quantum.configure(state="normal")
            self.quantum.focus_set()
            self.quantum.selection_range(0, tk.END)
            raise
        return p

    def gravar(self):
        try:
            cenario = Cenario(self.ler_tarefas(), self.ler_parametros(), self.rotulo_cenario.cget("text"))
        except EntradaInvalida as e:
            return self._recusar(e)
        caminho = filedialog.asksaveasfilename(
            parent=self, title="Gravar cenário", initialdir=pasta_cenarios(),
            defaultextension=".json", filetypes=[("Cenário JSON", "*.json")])
        if not caminho:
            return
        cenario.nome = os.path.splitext(os.path.basename(caminho))[0]
        try:
            cenario.gravar(caminho)
        except OSError as e:
            return messagebox.showerror("Não foi possível gravar", str(e), parent=self)
        self.rotulo_cenario.configure(text=cenario.nome)
        messagebox.showinfo("Cenário gravado", f"Cenário gravado em:\n{caminho}", parent=self)

    def carregar(self):
        caminho = filedialog.askopenfilename(
            parent=self, title="Carregar cenário", initialdir=pasta_cenarios(),
            filetypes=[("Cenário JSON", "*.json"), ("Todos os arquivos", "*.*")])
        if not caminho:
            return
        try:
            cenario = Cenario.carregar(caminho)
            if len(cenario.tarefas) > MAX_TAREFAS:
                raise EntradaInvalida(f"O cenário tem {len(cenario.tarefas)} tarefas; o máximo é {MAX_TAREFAS}.")
            if not cenario.nome:
                cenario.nome = os.path.splitext(os.path.basename(caminho))[0]
            self.carregar_cenario(cenario)
        except (EntradaInvalida, OSError) as e:
            return messagebox.showerror("Não foi possível carregar", str(e), parent=self)

    # ---- apresentacao ----------------------------------------------------------

    def mostrar_resultado(self, r):
        m = Metricas(r)
        p = r.parametros
        self.arvore.delete(*self.arvore.get_children())
        for linha in m.linhas():
            self.arvore.insert("", "end", values=(f"t{linha[0]}",) + tuple(linha[1:]))
        self.arvore.insert("", "end", tags=("media",), values=(
            "Média", "", f"{m.tp_medio:.2f}", "", f"{m.tt_medio:.2f}", f"{m.tw_medio:.2f}",
            f"{m.primeira_execucao_media:.2f}"))

        descricao = f"{p.algoritmo} - {POLITICAS[p.algoritmo].nome}"
        if p.algoritmo == "RR":
            descricao += f"   |   quantum tq = {p.quantum}"
        descricao += f"   |   custo da troca ttc = {p.custo_troca}"
        if POLITICAS[p.algoritmo].usa_prioridade:
            descricao += f"   |   protocolo: {p.protocolo}   |   envelhecimento alfa = {p.envelhecimento}"
        self.resumo.configure(text=descricao)

        texto = [f"Tt médio = {m.tt_medio:.2f}    Tw médio = {m.tw_medio:.2f}    "
                 f"1ª execução média = {m.primeira_execucao_media:.2f}",
                 f"Trocas de contexto: {m.trocas}    Eficiência E = tq/(tq+ttc): {formatar_eficiencia(m.eficiencia)}",
                 f"Instante final: {r.instante_final}",
                 "",
                 "Sequência de execução:",
                 "  " + r.sequencia()]
        esperas = sorted(set(r.bloqueio_direto) | set(r.inversao))
        if esperas:
            texto.append("")
            texto.append("Espera pelo recurso R:")
            for i in esperas:
                direto = r.bloqueio_direto.get(i, 0)
                inv = r.inversao.get(i, 0)
                texto.append(f"  t{i}: {direto} unidade(s) de bloqueio direto (esperando a detentora de R) e "
                             f"{inv} unidade(s) de inversão de prioridades (esperando terceiras).")
        self._escrever(self.detalhes, "\n".join(texto))
        self._escrever(self.eventos, "\n".join(f"t = {t:>3}   {msg}" for t, msg in r.eventos))
        self.desenhar_diagrama(r)

    def _escrever(self, widget, texto):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", texto)
        widget.configure(state="disabled")

    def desenhar_diagrama(self, r):
        c = self.canvas
        c.delete("all")
        tarefas = sorted(r.tarefas, key=lambda t: t.id)
        fim = max(r.instante_final, 1)
        x0, y0, altura, passo = 60, 44, 26, 44
        disponivel = max(c.winfo_width() - x0 - 40, 360)
        escala = max(14, min(40, disponivel // fim))
        largura = x0 + fim * escala + 40

        p = r.parametros
        titulo = f"{p.algoritmo}"
        if p.algoritmo == "RR":
            titulo += f", tq = {p.quantum}"
        titulo += f", ttc = {p.custo_troca}"
        if POLITICAS[p.algoritmo].usa_prioridade:
            titulo += f", protocolo {p.protocolo}, alfa = {p.envelhecimento}"
        c.create_text(x0, 14, text=titulo, anchor="w", font=("TkDefaultFont", 9, "bold"))
        for i, t in enumerate(tarefas):
            y = y0 + i * passo
            c.create_text(x0 - 10, y + altura / 2, text=t.nome, anchor="e", font=("TkDefaultFont", 10, "bold"))
            c.create_line(x0, y + altura, x0 + fim * escala, y + altura, fill="#cccccc")
        for u in range(fim + 1):
            x = x0 + u * escala
            c.create_line(x, y0 - 6, x, y0 + len(tarefas) * passo - passo + altura, fill="#eeeeee")
            if escala >= 22 or u % 2 == 0 or u == fim:
                c.create_text(x, y0 + len(tarefas) * passo - passo + altura + 12, text=str(u),
                              font=("TkDefaultFont", 8))
        indice = {t.id: i for i, t in enumerate(tarefas)}
        for s in r.segmentos:
            i = indice[s.tarefa]
            y = y0 + i * passo
            xa, xb = x0 + s.inicio * escala, x0 + s.fim * escala
            if s.tipo == "execucao":
                c.create_rectangle(xa, y, xb, y + altura, fill=CORES[i % len(CORES)], outline="white")
            elif s.tipo == "troca":
                c.create_rectangle(xa, y, xb, y + altura, fill=COR_TROCA, outline="white", stipple="gray50")
            elif s.tipo == "bloqueio":
                c.create_rectangle(xa, y + 4, xb, y + altura - 4, fill=COR_BLOQUEIO, outline=COR_BLOQUEIO,
                                   stipple="gray25")
            elif s.tipo == "recurso" and s.fim > s.inicio:
                c.create_line(xa, y - 5, xb, y - 5, fill=COR_RECURSO, width=3)
                c.create_text((xa + xb) / 2, y - 12, text="R", font=("TkDefaultFont", 7, "bold"))

        ly = y0 + len(tarefas) * passo + 18
        legenda = (("execução", CORES[0], None), ("troca de contexto", COR_TROCA, "gray50"),
                   ("suspensa à espera de R", COR_BLOQUEIO, "gray25"), ("posse do recurso R", None, None))
        lx = x0
        for texto, cor, stipple in legenda:
            if cor is None:
                c.create_line(lx, ly + 6, lx + 18, ly + 6, fill=COR_RECURSO, width=3)
            elif stipple is None:
                c.create_rectangle(lx, ly, lx + 18, ly + 12, fill=cor, outline="white")
            else:
                c.create_rectangle(lx, ly, lx + 18, ly + 12, fill=cor, outline=cor, stipple=stipple)
            c.create_text(lx + 24, ly + 6, text=texto, anchor="w", font=("TkDefaultFont", 8))
            lx += 24 + 7 * len(texto) + 16
            if lx > x0 + max(fim * escala, 300) - 120:
                lx = x0
                ly += 18
        ly += 18
        c.configure(scrollregion=(0, 0, largura, ly + 30))

    def mostrar_lote(self, medias, amostras, faixas, base):
        self.arvore_lote.delete(*self.arvore_lote.get_children())
        for m in medias:
            self.arvore_lote.insert("", "end", values=(
                m.algoritmo, f"{m.tt:.2f}", f"{m.tw:.2f}", f"{m.primeira_execucao:.2f}"))
        menor_tw = min(medias, key=lambda m: m.tw)
        menor_pe = min(medias, key=lambda m: m.primeira_execucao)
        self.resumo_lote.configure(text=(
            f"Médias sobre {amostras} cenários sorteados de {faixas.quantidade} tarefas "
            f"(ingresso até {faixas.ingresso_max}, tp até {faixas.tp_max}, prioridade até "
            f"{faixas.prioridade_max}), quantum {base.quantum}, custo de troca {base.custo_troca}."))
        self.detalhes_lote.configure(text=(
            f"Menor Tw médio: {menor_tw.algoritmo} ({menor_tw.tw:.2f}).\n"
            f"Menor tempo médio até a primeira execução: {menor_pe.algoritmo} "
            f"({menor_pe.primeira_execucao:.2f}).\n"
            "Cada execução sorteia outros cenários: os valores mudam, a ordenação se mantém."))


def iniciar():
    try:
        app = Aplicacao()
    except Exception:
        # Sem janela principal não há para onde mandar o erro: mostra-o em uma caixa avulsa.
        raiz = tk.Tk()
        raiz.withdraw()
        messagebox.showerror("Erro ao abrir o simulador", traceback.format_exc())
        raiz.destroy()
        return
    app.mainloop()
