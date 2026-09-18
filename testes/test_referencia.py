"""Cenarios de validacao da secao 4 do enunciado.

Executar a partir da raiz do repositorio:

    python -m unittest discover -s testes -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from simulador.modelo import Tarefa, Parametros, EntradaInvalida, Cenario   # noqa: E402
from simulador.motor import simular                                          # noqa: E402
from simulador.metricas import Metricas, eficiencia                          # noqa: E402
from simulador.gerador import FaixasSorteio, comparar_em_lote                # noqa: E402


def aula5():
    return [Tarefa(1, 0, 5, 2), Tarefa(2, 0, 2, 3), Tarefa(3, 1, 4, 1),
            Tarefa(4, 3, 1, 4), Tarefa(5, 5, 2, 5)]


def aula6():
    return [Tarefa(1, 0, 6, 1, (1, 4)), Tarefa(2, 4, 4, 2), Tarefa(3, 6, 3, 3),
            Tarefa(4, 2, 3, 4, (1, 1))]


def inanicao():
    return [Tarefa(1, 0, 4, 1), Tarefa(2, 0, 2, 5), Tarefa(3, 2, 2, 5),
            Tarefa(4, 4, 2, 5), Tarefa(5, 6, 2, 5), Tarefa(6, 8, 2, 5)]


class Aula5(unittest.TestCase):
    esperado = {
        "FCFS": (8.0, 5.2, 5.2, 5),
        "RR": (8.4, 5.6, 2.8, 8),
        "SJF": (5.8, 3.0, 3.0, 5),
        "SRTF": (5.4, 2.6, 2.4, 6),
        "PRIOc": (6.6, 3.8, 3.8, 5),
        "PRIOp": (5.6, 2.8, 2.2, 7),
    }

    def test_seis_algoritmos(self):
        for alg, (tt, tw, pe, trocas) in self.esperado.items():
            with self.subTest(alg=alg):
                m = Metricas(simular(aula5(), Parametros(alg, quantum=2)))
                self.assertAlmostEqual(m.tt_medio, tt)
                self.assertAlmostEqual(m.tw_medio, tw)
                self.assertAlmostEqual(m.primeira_execucao_media, pe)
                self.assertEqual(m.trocas, trocas)

    def test_custo_de_troca(self):
        m = Metricas(simular(aula5(), Parametros("FCFS", custo_troca=1)))
        self.assertAlmostEqual(m.tt_medio, 11.0)
        self.assertAlmostEqual(m.tw_medio, 8.2)
        self.assertIsNone(m.eficiencia)
        m = Metricas(simular(aula5(), Parametros("RR", quantum=4, custo_troca=1)))
        self.assertAlmostEqual(m.tt_medio, 13.4)
        self.assertAlmostEqual(m.tw_medio, 10.6)
        self.assertAlmostEqual(m.eficiencia, 0.8)

    def test_quantum_menor_que_custo_e_recusado(self):
        with self.assertRaises(EntradaInvalida):
            Parametros("RR", quantum=1, custo_troca=1).validar()
        Parametros("FCFS", quantum=1, custo_troca=1).validar()


class Aula6(unittest.TestCase):
    def conferir(self, r, conclusoes, tt_medio, tw_medio):
        m = Metricas(r)
        self.assertEqual([x.conclusao for x in m.por_tarefa], conclusoes)
        self.assertAlmostEqual(m.tt_medio, tt_medio)
        self.assertAlmostEqual(m.tw_medio, tw_medio)

    def test_inversao(self):
        r = simular(aula6(), Parametros("PRIOp"))
        self.assertEqual(r.sequencia(),
                         "t1[0,2) t4[2,3) t1[3,4) t2[4,6) t3[6,9) t2[9,11) t1[11,13) t4[13,15) t1[15,16)")
        self.conferir(r, [16, 11, 9, 15], 9.75, 5.75)
        self.assertEqual(r.bloqueio_direto.get(4, 0), 3)
        self.assertEqual(r.inversao.get(4, 0), 7)

    def test_heranca(self):
        r = simular(aula6(), Parametros("PRIOp", protocolo="heranca"))
        self.assertEqual(r.sequencia(), "t1[0,2) t4[2,3) t1[3,6) t4[6,8) t3[8,11) t2[11,15) t1[15,16)")
        self.conferir(r, [16, 15, 11, 8], 9.5, 5.5)
        self.assertEqual(r.bloqueio_direto.get(4, 0), 3)
        self.assertEqual(r.inversao.get(4, 0), 0)

    def test_teto(self):
        r = simular(aula6(), Parametros("PRIOp", protocolo="teto"))
        self.assertEqual(r.sequencia(), "t1[0,5) t4[5,8) t3[8,11) t2[11,15) t1[15,16)")
        self.conferir(r, [16, 15, 11, 8], 9.5, 5.5)
        self.assertEqual(r.bloqueio_direto.get(4, 0), 0)

    def test_preco_do_teto_sem_disputa(self):
        tarefas = [Tarefa(1, 0, 6, 1, (1, 4)), Tarefa(2, 2, 3, 2), Tarefa(4, 12, 2, 4, (0, 1))]
        r = simular(tarefas, Parametros("PRIOp", protocolo="heranca"))
        self.assertEqual(r.sequencia(), "t1[0,2) t2[2,5) t1[5,9) t4[12,14)")
        self.assertAlmostEqual(Metricas(r).tw_medio, 1.0)
        r = simular(tarefas, Parametros("PRIOp", protocolo="teto"))
        self.assertEqual(r.sequencia(), "t1[0,5) t2[5,8) t1[8,9) t4[12,14)")
        self.assertAlmostEqual(Metricas(r).tw_medio, 2.0)


class Envelhecimento(unittest.TestCase):
    def test_sem_envelhecimento(self):
        r = simular(inanicao(), Parametros("PRIOc"))
        self.assertEqual(r.sequencia(), "t2[0,2) t3[2,4) t4[4,6) t5[6,8) t6[8,10) t1[10,14)")
        self.assertAlmostEqual(Metricas(r).tw_medio, 10 / 6)

    def test_alfa_1(self):
        r = simular(inanicao(), Parametros("PRIOc", envelhecimento=1))
        self.assertEqual(r.sequencia(), "t2[0,2) t3[2,4) t1[4,8) t4[8,10) t5[10,12) t6[12,14)")
        self.assertAlmostEqual(Metricas(r).tw_medio, 16 / 6)

    def test_alfa_2(self):
        r = simular(inanicao(), Parametros("PRIOc", envelhecimento=2))
        self.assertEqual(r.sequencia(), "t2[0,2) t1[2,6) t3[6,8) t4[8,10) t5[10,12) t6[12,14)")
        self.assertAlmostEqual(Metricas(r).tw_medio, 3.0)


class Lote(unittest.TestCase):
    def test_ordenacao_se_mantem(self):
        medias = comparar_em_lote(FaixasSorteio(), 60, Parametros("RR", quantum=2))
        por_alg = {m.algoritmo: m for m in medias}
        menor_tw = min(medias, key=lambda m: m.tw).algoritmo
        menor_pe = min(medias, key=lambda m: m.primeira_execucao).algoritmo
        self.assertEqual(menor_tw, "SRTF")
        self.assertEqual(menor_pe, "RR")
        self.assertLess(por_alg["SJF"].tw, por_alg["FCFS"].tw)


class Persistencia(unittest.TestCase):
    def test_gravar_e_recarregar(self):
        import tempfile
        c = Cenario(aula6(), Parametros("PRIOp", protocolo="heranca"), "aula 6")
        with tempfile.TemporaryDirectory() as d:
            caminho = os.path.join(d, "c.json")
            c.gravar(caminho)
            c2 = Cenario.carregar(caminho)
        self.assertEqual(c2.tarefas, c.tarefas)
        self.assertEqual(c2.parametros, c.parametros)
        self.assertEqual(c2.nome, "aula 6")

    def test_valores_invalidos(self):
        with self.assertRaises(EntradaInvalida):
            Tarefa(1, -1, 2, 1)
        with self.assertRaises(EntradaInvalida):
            Tarefa(1, 0, 0, 1)
        with self.assertRaises(EntradaInvalida):
            Tarefa(1, 0, 3, 1, (2, 2))


class Ociosidade(unittest.TestCase):
    def test_salto_do_relogio(self):
        tarefas = [Tarefa(1, 0, 2, 1), Tarefa(2, 10, 3, 1)]
        r = simular(tarefas, Parametros("FCFS"))
        self.assertEqual(r.sequencia(), "t1[0,2) t2[10,13)")
        m = Metricas(r)
        self.assertAlmostEqual(m.tw_medio, 0.0)

    def test_eficiencia(self):
        self.assertIsNone(eficiencia(Parametros("SJF", quantum=2, custo_troca=1)))
        self.assertAlmostEqual(eficiencia(Parametros("RR", quantum=4, custo_troca=1)), 0.8)


if __name__ == "__main__":
    unittest.main()
