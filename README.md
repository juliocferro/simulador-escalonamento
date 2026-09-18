# Simulador de Escalonamento de Tarefas — Grupo 4

Projeto prático da disciplina de **Sistemas Operacionais**, 8º semestre do curso de Engenharia da Computação da Faculdade Engenheiro Salvador Arena, ministrada pelo Prof. Vinícius S. Borges. Semestre 2026/2.

## Integrantes

| Nome | RA | GitHub |
|---|---|---|
| Felipe de Carvalho Medeiros | 081230026 | [FelipeMedeiros068](https://github.com/FelipeMedeiros068) |
| Júlio César Caberlino Ferro | 081230003 | [juliocferro](https://github.com/juliocferro) |
| Matheus Mitsuo Sato Silva | 081230046 | — |
| Nicolas Gomes Lima | 081230048 | [nicolas-optio](https://github.com/nicolas-optio) |

## Como executar

Clique duas vezes em **`Simulador.exe`**.

Não é necessário instalar nada. O programa abre já com o cenário da Aula 5 carregado; clique em **Simular** para ver o primeiro resultado.

Quem tiver Python 3.10 ou superior instalado pode, em vez disso, dar dois cliques em `Simulador.pyw` (sem console) ou executar `python main.py`. Nenhuma biblioteca externa é necessária: o programa usa apenas a biblioteca padrão, incluindo o `tkinter`.

## Descrição

O simulador reproduz, em tempo discreto, o escalonamento de um conjunto de tarefas em um processador. Implementa os seis algoritmos estudados em aula (FCFS, SJF, SRTF, Round-Robin e prioridade cooperativa e preemptiva), cobra o custo da troca de contexto, calcula as métricas por tarefa e em média (tempo de execução, tempo de processamento, tempo de espera e tempo até a primeira execução) e desenha o diagrama de tempo no formato usado em sala, com uma linha por tarefa.

Uma tarefa pode declarar uma seção crítica sobre o recurso de uso exclusivo R. Com isso o simulador reproduz a inversão de prioridades, distingue bloqueio direto de inversão, e aplica os dois protocolos de correção, herança e teto de prioridade, além do envelhecimento para eliminar a inanição. Um gerador sorteia conjuntos de tarefas, para observação individual ou para comparar os seis algoritmos sobre um lote, e qualquer cenário pode ser gravado em JSON e recarregado depois. O código separa o mecanismo (o laço de simulação, único) da política (cada algoritmo em poucas linhas).

## Estrutura do repositório

```
simulador-escalonamento/
├── README.md                    este arquivo
├── Simulador.exe                programa pronto: abre com dois cliques
├── Simulador.pyw                mesmo programa, para quem tem Python (dois cliques, sem console)
├── main.py                      ponto de entrada do código-fonte
├── gerar_executavel.bat         gera o Simulador.exe em uma máquina Windows
├── simulador/                   código-fonte do simulador
├── cenarios/                    cenários de referência gravados em JSON
├── testes/                      testes que reproduzem os cenários de validação do enunciado
├── docs/                        tutoriais e documentação técnica (PDF e Markdown)
│   └── imagens/                 capturas de tela e diagrama de módulos
├── documentos/                  enunciado e guias distribuídos pelo professor
└── .github/workflows/           geração automática do executável no GitHub Actions
```

## Arquivos de código

- `main.py` — ponto de entrada; abre a janela do programa.
- `Simulador.pyw` — mesmo ponto de entrada, associado ao `pythonw` no Windows para abrir sem console.
- `simulador/modelo.py` — estrutura de uma tarefa (`Tarefa`), dos parâmetros do escalonador (`Parametros`) e de um cenário (`Cenario`); validação das faixas de entrada; gravação e leitura em JSON.
- `simulador/politicas.py` — os seis algoritmos de escalonamento (a política): cada um é uma classe pequena com o método `escolher(prontas, contexto)`.
- `simulador/motor.py` — laço de simulação (o mecanismo): relógio, conjunto de prontas, troca de contexto, recurso R com suspensão, herança, teto, envelhecimento e o `Resultado` com segmentos e eventos.
- `simulador/metricas.py` — cálculo de tt, tp, tw, tempo até a primeira execução, médias, trocas e eficiência.
- `simulador/gerador.py` — sorteio de conjuntos de tarefas e comparação dos seis algoritmos em lote.
- `simulador/exemplos.py` — cenários de referência do enunciado, oferecidos pelo botão **Exemplos**.
- `simulador/interface.py` — janela do programa em tkinter: tabela de tarefas, parâmetros, métricas, diagrama de tempo, eventos e comparação em lote.
- `testes/test_referencia.py` — reprodução automática dos cenários de validação do enunciado (`python -m unittest discover -s testes -v`).

## Funcionalidades

| O que faz | Requisito | Onde |
|---|---|---|
| Os seis algoritmos (FCFS, SJF, SRTF, RR, PRIOc, PRIOp) | R1 | `simulador/politicas.py` |
| Entrada de tarefas digitada, com recusa de valores inválidos | R2 | `simulador/interface.py`, `simulador/modelo.py` |
| Gravar e recarregar um cenário (JSON) | R2 | `simulador/modelo.py`, `simulador/interface.py` |
| Métricas por tarefa e em média: tt, tp, tw, 1ª execução | R3 | `simulador/metricas.py` |
| Quantum, custo da troca e eficiência tq/(tq+ttc); recusa de tq ≤ ttc | R4 | `simulador/motor.py`, `simulador/metricas.py`, `simulador/modelo.py` |
| Recurso exclusivo R, suspensão, bloqueio direto e inversão | R5 | `simulador/motor.py` |
| Herança de prioridade | R6 | `simulador/motor.py` |
| Teto de prioridade | R7 | `simulador/motor.py` |
| Envelhecimento com passo α | R8 | `simulador/motor.py` |
| Sorteio de cenários e comparação em lote | R9 | `simulador/gerador.py` |
| Diagrama de tempo, uma linha por tarefa | R9 | `simulador/interface.py` |
| Programa que abre com dois cliques, sem argumentos | R10 | `Simulador.exe`, `Simulador.pyw`, `main.py` |
| Cenários de referência prontos para carregar | — | `simulador/exemplos.py`, `cenarios/` |

## Requisitos de ambiente

- `Simulador.exe`: Windows 10 ou 11, 64 bits. Nada a instalar.
- Código-fonte: Python 3.10 ou superior com `tkinter` (incluído no instalador oficial do Python). Nenhuma biblioteca externa.
- Geração do executável: PyInstaller, no Windows (`gerar_executavel.bat`) ou pelo GitHub Actions (`.github/workflows/gerar_executavel.yml`).

## Documentação

- [Tutorial de execução](./docs/tutorial_execucao.pdf) — pré-requisitos, qual arquivo abrir, primeira tela, execução mínima e resultado esperado.
- [Tutorial de uso](./docs/tutorial_uso.pdf) — cada função do programa, passo a passo, com capturas de tela e um resultado conhecido para conferência.
- [Documentação técnica](./docs/documentacao_projeto.pdf) — separação entre política e mecanismo, diagrama de módulos, estrutura de uma tarefa, interface dos módulos, parâmetros, funcionamento interno e convenções de simulação.

Os três documentos também estão em Markdown na pasta `docs/`.

## Por onde começar

1. Abra o programa e siga o [tutorial de execução](./docs/tutorial_execucao.pdf).
2. Reproduza um cenário de exemplo pelo [tutorial de uso](./docs/tutorial_uso.pdf).
3. Consulte a [documentação técnica](./docs/documentacao_projeto.pdf) para entender o código.

## Cenários de referência

Valores obtidos pelo simulador no cenário da Aula 5, com custo de troca nulo:

| Algoritmo | Tt | Tw | 1ª exec. | Trocas |
|---|---|---|---|---|
| FCFS | 8,0 | 5,2 | 5,2 | 5 |
| RR (q = 2) | 8,4 | 5,6 | 2,8 | 8 |
| SJF | 5,8 | 3,0 | 3,0 | 5 |
| SRTF | 5,4 | 2,6 | 2,4 | 6 |
| PRIOc | 6,6 | 3,8 | 3,8 | 5 |
| PRIOp | 5,6 | 2,8 | 2,2 | 7 |

Com custo de troca 1: FCFS Tt = 11,0 e Tw = 8,2; RR (q = 4) Tt = 13,4, Tw = 10,6 e E = 0,800. Aula 6: inversão Tt = 9,75 e Tw = 5,75; herança e teto Tt = 9,50 e Tw = 5,50. Todos são verificados por `testes/test_referencia.py`.

## Uso de assistentes de programação

<!-- Preencher: declarar se foram usados e em quais partes. -->
