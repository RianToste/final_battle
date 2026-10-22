# Jogo de Gestão e Estratégia em Python

Projeto de LPRO — jogo de consola com personagens, loja, missões, combates e ranking,
com persistência numa base de dados relacional (SQLite).

## 1. Elementos do grupo

| Nome | Nº | Responsabilidades |
|------|----|-------------------|
| Rian Toste | 7 | Código |
| Fábio Ferreira | 3 | Documentação |

## 2. Descrição do jogo

Cada jogador cria uma **conta** e uma **personagem** (Guerreiro, Mago ou Ladrão) e evolui-a:

- **Combate** por turnos contra adversários guardados na base de dados. O resultado depende das
  estatísticas (ataque, defesa, agilidade, equipamento) e de probabilidades de esquiva/crítico —
  não é aleatório sem regras. Antes de lutar, o jogo mostra a **probabilidade estimada de vitória**.
- **Níveis e experiência**: ao atingir o XP necessário (`100 × nível^1.5`) a personagem sobe de
  nível e ganha vida, ataque, defesa e agilidade.
- **Loja e economia**: comprar e vender objetos (poções, armas, armaduras...). Cada transação
  regista o saldo anterior e o saldo atual.
- **Inventário**: poções gastam-se ao usar; armas e armaduras aplicam o bónus sozinhas
  em combate (conta o melhor de cada tipo).
- **Missões**: derrotar adversários, vencer combates, comprar objetos ou atingir um nível.
  Estados: Disponível, Em curso, Concluída, Falhada (ao abandonar).
- **Energia**: combates e missões gastam energia; recupera-se com poções ou a descansar.
- **Ranking** por nível, dinheiro, vitórias ou missões concluídas.
- **Histórico** de todas as ações relevantes.
- **Administração**: gerir utilizadores, objetos, adversários, missões, e consultar combates,
  estatísticas e logs.

### Regras principais

| Regra | Valor |
|-------|-------|
| Dano de um ataque | `ataque × 100 / (100 + defesa)`, ±20 % de variação, crítico +50 % |
| Quem ataca primeiro | A personagem |
| Combate sem vencedor | Empate ao fim de 30 turnos |
| Derrota | Perde 10 % do dinheiro e fica com 1 de vida |
| Venda de objetos | A loja paga 50 % do preço |
| Descansar | Custa até 20 € (menos se não tiver dinheiro) e recupera vida e energia |

Todos estes valores estão em `config.py` e podem ser ajustados para equilibrar o jogo.

## 3. Requisitos

- Python **3.9 ou superior** (testado em 3.12) — SQLite já vem incluído no Python.
- `pytest` (opcional: só para correr os testes com pytest; também correm com `unittest`).

## 4. Instalação

```bash
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux / macOS

# 2. instalar dependências
pip install -r requirements.txt

# 3. criar o ficheiro de configuração
copy .env.example .env         # Windows
cp .env.example .env           # Linux / macOS
```

Abra o `.env` e **mude a password do administrador** (`ADMIN_PASSWORD`).
O `.env` não vai para o Git (está no `.gitignore`), por isso as credenciais não ficam no código.

## 5. Execução

```bash
python main.py
```

Na primeira execução a base de dados (`game.db`) é criada automaticamente, com
itens, adversários e missões de exemplo. Para recomeçar do zero, apague o `game.db`.

Para correr os testes:

```bash
python -m unittest discover -s tests -t .     # biblioteca padrão
pytest                                        # alternativa
```

## 6. Utilizadores de teste

| Tipo | Username | Password |
|------|----------|----------|
| Administrador | `admin` (ou o valor de `ADMIN_USERNAME`) | a de `ADMIN_PASSWORD` no `.env` |
| Jogador | _crie um em "Registar nova conta"_ | mínimo 8 caracteres, com letra e número |

## 7. Estrutura do projeto

```
projeto_jogo/
├── main.py                  # ponto de entrada
├── config.py                # TODAS as constantes do jogo + leitura do .env
├── requirements.txt
├── .env.example             # modelo do ficheiro de configuração
│
├── database/
│   ├── connection.py        # abrir ligações e transações (COMMIT/ROLLBACK)
│   ├── init_db.py           # cria tabelas, dados iniciais e conta admin
│   ├── queries.py           # TODO o SQL do projeto (parametrizado)
│   ├── schema.sql           # criação das tabelas
│   └── seed.sql             # dados iniciais (itens, adversários, missões)
│
├── models/                  # classes que representam os dados
│   ├── user.py  character.py  item.py  enemy.py  mission.py
│
├── services/                # regras do jogo (não imprimem nada)
│   ├── authentication.py    # registo, login, permissões
│   ├── character_service.py # criar personagem, experiência, descanso
│   ├── shop.py              # comprar, vender, usar objetos
│   ├── combat.py            # simulação e resultado dos combates
│   ├── missions.py          # aceitar, progresso e conclusão
│   ├── ranking.py
│   ├── history.py           # registo de atividade
│   └── admin.py             # operações de administração
│
├── ui/                      # interface de consola (só pergunta e mostra)
│   ├── menus.py             # menu inicial, login, registo
│   ├── game_menus.py        # menus do jogador
│   ├── admin_menus.py       # menus do administrador
│   ├── navigation.py        # run_menu e tratamento de erros
│   ├── input_helpers.py     # ask_int, ask_text... (validam e repetem)
│   └── messages.py          # formatação do que se mostra
│
├── utils/
│   ├── validators.py  security.py  exceptions.py  formatting.py
│
├── tests/                   # 125 testes automáticos
└── docs/                    # diagrama entidade-relação
```

**Princípio:** cada camada só conhece a de baixo — `ui → services → database`.
A interface nunca escreve SQL e os serviços nunca fazem `print`.

## 8. Tecnologias utilizadas

Python 3 · SQLite (`sqlite3`) · `hashlib` (PBKDF2-HMAC-SHA256) · `unittest`/`pytest` · Git · Graphviz (diagrama).

## 9. Base de dados

10 tabelas relacionadas: `users`, `characters`, `items`, `inventory`, `transactions`,
`enemies`, `combats`, `missions`, `character_missions`, `activity_logs`.
Diagrama e descrição das relações em **[docs/modelo_er.md](docs/modelo_er.md)**
(imagem: `docs/modelo_er.png`). O script de criação está em `database/schema.sql` e `database/seed.sql`.

Requisitos de SQL do enunciado e onde se encontram em `database/queries.py`:

| Requisito | Exemplo |
|-----------|---------|
| INSERT / UPDATE / DELETE | `insert_user`, `save_character`, `delete_item` |
| SELECT + JOIN | `list_inventory`, `list_combats`, `list_transactions` |
| LEFT JOIN | `list_missions_for_character`, `list_users_with_characters` |
| GROUP BY + agregação | `get_ranking`, `get_combat_summary`, `get_best_selling_items`, `get_character_statistics` |
| ORDER BY | `RANKING_ORDERS` |
| Funções de janela | `ROW_NUMBER()` para a posição no ranking |
| Relações 1:1, 1:N, N:N | ver diagrama |

## 10. Segurança

- Passwords com **PBKDF2-HMAC-SHA256**, 200 000 iterações e *salt* aleatório por utilizador.
- **Queries parametrizadas** em todo o projeto (nomes de colunas dinâmicos só vêm de listas brancas).
- Validação de todos os inputs; o programa **nunca termina** por o utilizador escrever algo inválido.
- Mensagem de login igual para "utilizador inexistente" e "password errada".
- Permissões verificadas **na base de dados** em cada operação de administração.
- Credenciais do admin no `.env`, não no código.
- Transações: compras, vendas e combates fazem *rollback* se algo falhar.
- Erros inesperados vão para `game_errors.log`, sem expor detalhes técnicos ao jogador.

## 11. Exemplos de utilização

```
=========== MENU DO JOGADOR - ana ===========
  1. Ver personagem e evolução   5. Combate
  2. Inventário                  6. Descansar
  3. Loja                        7. Ranking
  4. Missões                     8. Histórico de atividade
```

Compra (recibo):
```
[OK] Jogador comprou: Pocao de Vida (x1)
  Preço unitário: 50 €
  Saldo anterior: 350 €
  Saldo atual: 300 €
```

Arena:
```
Nº | Adversário    | Nível | Vida | Ataque | Defesa | Recompensa    | Prob. vitória
1  | Rato Gigante  | 1     | 30   | 6      | 2      | 15 € + 30 XP  | 100%
4  | Bandido       | 4     | 90   | 16     | 9      | 60 € + 120 XP | 54%
```

Histórico:
```
21/09/2026 10:32 — João iniciou combate contra Goblin
21/09/2026 10:33 — João venceu o combate contra Goblin.
21/09/2026 10:34 — João recebeu 50 XP e 25 €.
21/09/2026 10:35 — João comprou 1x Pocao de Vida por 50 €.
```

## 12. Limitações conhecidas

- Não há recuperação automática de energia ao longo do tempo (só poções ou descanso).
- Os combates são sempre contra adversários controlados pelo sistema (sem jogador contra jogador).
- O administrador não pode apagar missões nem adversários, apenas criá-los e editá-los.
- Não se pode alterar o tipo de objetivo de uma missão depois de criada.
- Não há recuperação de password esquecida (um admin teria de intervir na BD).

## 13. Trabalho futuro

- Interface gráfica (Tkinter) ou API REST (Flask/FastAPI).
- Combate jogador contra jogador, sistema de amigos e chat.