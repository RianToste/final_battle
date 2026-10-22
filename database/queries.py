"""
Todas as consultas SQL do projeto ficam neste ficheiro.

Regras:
  - Cada função recebe uma 'connection' (ligação à BD) como primeiro
    argumento. Quem decide quando fazer COMMIT/ROLLBACK é o serviço que
    chama (ver transaction() em connection.py).
  - NUNCA se junta texto do utilizador ao SQL. Usamos sempre "?" e passamos
    os valores à parte (queries parametrizadas), o que impede SQL Injection.
  - Aqui não há regras de jogo: só ler e escrever dados.
"""

import config

# ============================================================
# UTILIZADORES
# ============================================================


def insert_user(connection, username, password_hash, password_salt, role):
    """Cria um utilizador e devolve o id novo."""
    cursor = connection.execute(
        "INSERT INTO users (username, password_hash, password_salt, role) "
        "VALUES (?, ?, ?, ?)",
        (username, password_hash, password_salt, role),
    )
    return cursor.lastrowid


def get_user_by_id(connection, user_id):
    """Devolve a linha do utilizador (sem o hash) ou None."""
    return connection.execute(
        "SELECT id, username, role, status, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


def get_user_credentials(connection, username):
    """Devolve a linha COM hash e salt (só para o login) ou None."""
    return connection.execute(
        "SELECT id, username, password_hash, password_salt, role, status, created_at "
        "FROM users WHERE username = ?",
        (username,),
    ).fetchone()


def get_user_credentials_by_id(connection, user_id):
    """Como a anterior, mas pesquisa por id (para confirmar a password atual)."""
    return connection.execute(
        "SELECT id, username, password_hash, password_salt FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


def update_username(connection, user_id, new_username):
    """Muda o username de um utilizador."""
    connection.execute(
        "UPDATE users SET username = ? WHERE id = ?", (new_username, user_id)
    )


def update_password(connection, user_id, password_hash, password_salt):
    """Guarda um novo hash/salt de password."""
    connection.execute(
        "UPDATE users SET password_hash = ?, password_salt = ? WHERE id = ?",
        (password_hash, password_salt, user_id),
    )


def update_user_status(connection, user_id, status):
    """Bloqueia ('bloqueado') ou desbloqueia ('ativo') um utilizador."""
    connection.execute(
        "UPDATE users SET status = ? WHERE id = ?", (status, user_id)
    )


def list_users_with_characters(connection):
    """
    Lista todos os utilizadores e, quando existe, o nome e nível da
    personagem. LEFT JOIN: utilizadores sem personagem também aparecem.
    """
    return connection.execute(
        "SELECT u.id, u.username, u.role, u.status, u.created_at, "
        "       c.name AS character_name, c.level AS character_level "
        "FROM users u LEFT JOIN characters c ON c.user_id = u.id "
        "ORDER BY u.id"
    ).fetchall()


# ============================================================
# PERSONAGENS
# ============================================================


def insert_character(connection, user_id, name, class_name, stats):
    """
    Cria uma personagem e devolve o id novo.
    'stats' é um dicionário com health, attack, defense e agility.
    """
    cursor = connection.execute(
        "INSERT INTO characters "
        "(user_id, name, class, health, max_health, energy, money, attack, defense, agility) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user_id, name, class_name,
            stats["health"], stats["health"],
            config.STARTING_ENERGY, config.STARTING_MONEY,
            stats["attack"], stats["defense"], stats["agility"],
        ),
    )
    return cursor.lastrowid


def get_character_by_user_id(connection, user_id):
    """Devolve a linha da personagem de um utilizador (ou None)."""
    return connection.execute(
        "SELECT * FROM characters WHERE user_id = ?", (user_id,)
    ).fetchone()


def get_character_by_id(connection, character_id):
    """Devolve a linha da personagem com este id (ou None)."""
    return connection.execute(
        "SELECT * FROM characters WHERE id = ?", (character_id,)
    ).fetchone()


def save_character(connection, character):
    """Grava na BD todos os valores que mudam durante o jogo."""
    connection.execute(
        "UPDATE characters SET level = ?, experience = ?, health = ?, max_health = ?, "
        "energy = ?, money = ?, attack = ?, defense = ?, agility = ?, "
        "wins = ?, losses = ? WHERE id = ?",
        (
            character.level, character.experience, character.health,
            character.max_health, character.energy, character.money,
            character.attack, character.defense, character.agility,
            character.wins, character.losses, character.id,
        ),
    )


# ============================================================
# OBJETOS (CATÁLOGO DA LOJA)
# ============================================================

# Colunas que o administrador pode escrever. Servem de "lista branca":
# como os NOMES de colunas não podem ser parametrizados com "?", só
# aceitamos nomes que estejam nestas listas.
ITEM_COLUMNS = ("name", "description", "type", "price", "stock", "effect_type", "effect_value")
ENEMY_COLUMNS = ("name", "level", "health", "attack", "defense", "reward_money",
                 "reward_xp", "dodge_chance", "crit_chance")
MISSION_COLUMNS = ("name", "description", "difficulty", "min_level", "reward_money",
                   "reward_xp", "objective_type", "objective_target_id", "objective_amount")


def _insert_row(connection, table, allowed_columns, data):
    """Insere uma linha numa tabela, só com colunas permitidas."""
    columns = [column for column in data if column in allowed_columns]
    if len(columns) != len(data):
        raise ValueError("Coluna não permitida.")
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    return connection.execute(sql, [data[column] for column in columns]).lastrowid


def _update_row(connection, table, allowed_columns, row_id, changes):
    """Atualiza apenas as colunas indicadas (e permitidas) de uma linha."""
    columns = [column for column in changes if column in allowed_columns]
    if not columns or len(columns) != len(changes):
        raise ValueError("Colunas inválidas.")
    assignments = ", ".join(f"{column} = ?" for column in columns)
    sql = f"UPDATE {table} SET {assignments} WHERE id = ?"
    connection.execute(sql, [changes[column] for column in columns] + [row_id])


def list_items(connection):
    """Todos os objetos do catálogo, por tipo e nome."""
    return connection.execute("SELECT * FROM items ORDER BY type, name").fetchall()


def get_item_by_id(connection, item_id):
    """Um objeto pelo id (ou None)."""
    return connection.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()


def insert_item(connection, data):
    """Cria um objeto. 'data' é um dicionário coluna -> valor."""
    return _insert_row(connection, "items", ITEM_COLUMNS, data)


def update_item(connection, item_id, changes):
    """Edita campos de um objeto."""
    _update_row(connection, "items", ITEM_COLUMNS, item_id, changes)


def change_item_stock(connection, item_id, delta):
    """Soma 'delta' (positivo ou negativo) ao stock da loja."""
    connection.execute("UPDATE items SET stock = stock + ? WHERE id = ?", (delta, item_id))


def delete_item(connection, item_id):
    """Apaga um objeto do catálogo."""
    connection.execute("DELETE FROM items WHERE id = ?", (item_id,))


def item_is_referenced(connection, item_id):
    """
    True se o objeto já aparece em algum inventário ou transação.
    Nesse caso não pode ser apagado (chave estrangeira).
    """
    row = connection.execute(
        "SELECT (SELECT COUNT(*) FROM inventory WHERE item_id = ?) + "
        "       (SELECT COUNT(*) FROM transactions WHERE item_id = ?) AS total",
        (item_id, item_id),
    ).fetchone()
    return row["total"] > 0


# ============================================================
# INVENTÁRIO
# ============================================================


def list_inventory(connection, character_id):
    """Inventário da personagem: junta 'inventory' com 'items' (JOIN)."""
    return connection.execute(
        "SELECT i.*, inv.quantity "
        "FROM inventory inv JOIN items i ON i.id = inv.item_id "
        "WHERE inv.character_id = ? "
        "ORDER BY i.type, i.name",
        (character_id,),
    ).fetchall()


def get_inventory_quantity(connection, character_id, item_id):
    """Quantas unidades deste objeto a personagem tem (0 se nenhuma)."""
    row = connection.execute(
        "SELECT quantity FROM inventory WHERE character_id = ? AND item_id = ?",
        (character_id, item_id),
    ).fetchone()
    return row["quantity"] if row else 0


def add_to_inventory(connection, character_id, item_id, quantity):
    """
    Junta unidades ao inventário. Se a personagem ainda não tinha o objeto,
    cria a linha; se já tinha, soma (UPSERT = INSERT ... ON CONFLICT UPDATE).
    """
    connection.execute(
        "INSERT INTO inventory (character_id, item_id, quantity) VALUES (?, ?, ?) "
        "ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity",
        (character_id, item_id, quantity),
    )


def remove_from_inventory(connection, character_id, item_id, quantity):
    """
    Tira unidades do inventário. A tabela não aceita quantidade 0, por isso
    quando não sobra nenhuma unidade a linha é apagada em vez de atualizada.
    """
    current = get_inventory_quantity(connection, character_id, item_id)

    if current <= quantity:
        connection.execute(
            "DELETE FROM inventory WHERE character_id = ? AND item_id = ?",
            (character_id, item_id),
        )
    else:
        connection.execute(
            "UPDATE inventory SET quantity = quantity - ? "
            "WHERE character_id = ? AND item_id = ?",
            (quantity, character_id, item_id),
        )


def get_equipment_bonuses(connection, character_id):
    """
    Devolve (bónus de ataque, bónus de defesa) do equipamento da personagem.
    Conta-se apenas o MELHOR objeto de cada tipo (MAX), para os bónus não
    se acumularem sem limite.
    """
    row = connection.execute(
        "SELECT "
        "  COALESCE(MAX(CASE WHEN i.effect_type = 'bonus_ataque' THEN i.effect_value END), 0) AS attack_bonus, "
        "  COALESCE(MAX(CASE WHEN i.effect_type = 'bonus_defesa' THEN i.effect_value END), 0) AS defense_bonus "
        "FROM inventory inv JOIN items i ON i.id = inv.item_id "
        "WHERE inv.character_id = ?",
        (character_id,),
    ).fetchone()
    return row["attack_bonus"], row["defense_bonus"]


# ============================================================
# TRANSAÇÕES (compras e vendas)
# ============================================================


def insert_transaction(connection, character_id, item_id, kind, quantity,
                       unit_price, total, balance_before, balance_after):
    """Regista uma compra ou venda, com o saldo antes e depois."""
    connection.execute(
        "INSERT INTO transactions "
        "(character_id, item_id, type, quantity, unit_price, total, balance_before, balance_after) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (character_id, item_id, kind, quantity, unit_price, total,
         balance_before, balance_after),
    )


def list_transactions(connection, character_id, limit):
    """Últimas transações da personagem (mais recentes primeiro)."""
    return connection.execute(
        "SELECT t.*, i.name AS item_name "
        "FROM transactions t JOIN items i ON i.id = t.item_id "
        "WHERE t.character_id = ? ORDER BY t.id DESC LIMIT ?",
        (character_id, limit),
    ).fetchall()


# ============================================================
# ADVERSÁRIOS E COMBATES
# ============================================================


def list_enemies(connection):
    """Todos os adversários, do mais fraco para o mais forte."""
    return connection.execute("SELECT * FROM enemies ORDER BY level, name").fetchall()


def get_enemy_by_id(connection, enemy_id):
    """Um adversário pelo id (ou None)."""
    return connection.execute("SELECT * FROM enemies WHERE id = ?", (enemy_id,)).fetchone()


def insert_enemy(connection, data):
    """Cria um adversário."""
    return _insert_row(connection, "enemies", ENEMY_COLUMNS, data)


def update_enemy(connection, enemy_id, changes):
    """Edita campos de um adversário."""
    _update_row(connection, "enemies", ENEMY_COLUMNS, enemy_id, changes)


def insert_combat(connection, character_id, enemy_id, result, turns,
                  damage_dealt, damage_taken, xp_gained, money_gained):
    """Guarda o resultado de um combate."""
    connection.execute(
        "INSERT INTO combats "
        "(character_id, enemy_id, result, turns, damage_dealt, damage_taken, xp_gained, money_gained) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (character_id, enemy_id, result, turns, damage_dealt, damage_taken,
         xp_gained, money_gained),
    )


def list_combats(connection, limit):
    """Últimos combates de todos os jogadores (para a administração)."""
    return connection.execute(
        "SELECT cb.id, cb.created_at, c.name AS character_name, e.name AS enemy_name, "
        "       cb.result, cb.turns, cb.xp_gained, cb.money_gained "
        "FROM combats cb "
        "JOIN characters c ON c.id = cb.character_id "
        "JOIN enemies e ON e.id = cb.enemy_id "
        "ORDER BY cb.id DESC LIMIT ?",
        (limit,),
    ).fetchall()


def get_combat_summary(connection, character_id):
    """
    Resumo dos combates de uma personagem, agrupado por resultado.
    GROUP BY + funções de agregação (COUNT, SUM).
    """
    return connection.execute(
        "SELECT result, COUNT(*) AS total, "
        "       COALESCE(SUM(xp_gained), 0) AS xp, "
        "       COALESCE(SUM(money_gained), 0) AS money "
        "FROM combats WHERE character_id = ? GROUP BY result",
        (character_id,),
    ).fetchall()


# ============================================================
# MISSÕES
# ============================================================

# SELECT base das missões "vistas" por uma personagem: junta o catálogo
# com o estado dessa personagem (LEFT JOIN) e com o nome do adversário-alvo.
_MISSIONS_FOR_CHARACTER_SQL = (
    "SELECT m.*, cm.status AS status, cm.progress AS progress, e.name AS target_name "
    "FROM missions m "
    "LEFT JOIN character_missions cm ON cm.mission_id = m.id AND cm.character_id = ? "
    "LEFT JOIN enemies e ON e.id = m.objective_target_id "
)


def list_missions_for_character(connection, character_id):
    """Todas as missões, com o estado e o progresso desta personagem."""
    return connection.execute(
        _MISSIONS_FOR_CHARACTER_SQL + "ORDER BY m.difficulty, m.name",
        (character_id,),
    ).fetchall()


def get_mission_for_character(connection, character_id, mission_id):
    """Uma missão, com o estado e o progresso desta personagem (ou None)."""
    return connection.execute(
        _MISSIONS_FOR_CHARACTER_SQL + "WHERE m.id = ?",
        (character_id, mission_id),
    ).fetchone()


def list_active_missions(connection, character_id, objective_type):
    """Missões 'em curso' desta personagem com um determinado tipo de objetivo."""
    return connection.execute(
        _MISSIONS_FOR_CHARACTER_SQL
        + "WHERE cm.status = ? AND m.objective_type = ?",
        (character_id, config.MISSION_IN_PROGRESS, objective_type),
    ).fetchall()


def start_mission(connection, character_id, mission_id):
    """
    Coloca a missão 'em curso' com progresso 0. Se já existia uma linha
    (missão falhada), é reiniciada.
    """
    connection.execute(
        "INSERT INTO character_missions (character_id, mission_id, status, progress) "
        "VALUES (?, ?, ?, 0) "
        "ON CONFLICT(character_id, mission_id) DO UPDATE SET "
        "  status = excluded.status, progress = 0, "
        "  accepted_at = datetime('now', 'localtime'), finished_at = NULL",
        (character_id, mission_id, config.MISSION_IN_PROGRESS),
    )


def set_mission_progress(connection, character_id, mission_id, progress):
    """Atualiza o progresso de uma missão em curso."""
    connection.execute(
        "UPDATE character_missions SET progress = ? "
        "WHERE character_id = ? AND mission_id = ?",
        (progress, character_id, mission_id),
    )


def finish_mission(connection, character_id, mission_id, status, progress):
    """Termina a missão ('concluida' ou 'falhada') e guarda a data."""
    connection.execute(
        "UPDATE character_missions SET status = ?, progress = ?, "
        "finished_at = datetime('now', 'localtime') "
        "WHERE character_id = ? AND mission_id = ?",
        (status, progress, character_id, mission_id),
    )


def count_completed_missions(connection, character_id):
    """Quantas missões esta personagem já concluiu."""
    row = connection.execute(
        "SELECT COUNT(*) AS total FROM character_missions "
        "WHERE character_id = ? AND status = 'concluida'",
        (character_id,),
    ).fetchone()
    return row["total"]


def list_missions(connection):
    """Catálogo completo de missões (para a administração)."""
    return connection.execute(
        "SELECT m.*, e.name AS target_name "
        "FROM missions m LEFT JOIN enemies e ON e.id = m.objective_target_id "
        "ORDER BY m.difficulty, m.name"
    ).fetchall()


def get_mission_by_id(connection, mission_id):
    """Uma missão do catálogo pelo id (ou None)."""
    return connection.execute(
        "SELECT m.*, e.name AS target_name "
        "FROM missions m LEFT JOIN enemies e ON e.id = m.objective_target_id "
        "WHERE m.id = ?",
        (mission_id,),
    ).fetchone()


def insert_mission(connection, data):
    """Cria uma missão."""
    return _insert_row(connection, "missions", MISSION_COLUMNS, data)


def update_mission(connection, mission_id, changes):
    """Edita campos de uma missão."""
    _update_row(connection, "missions", MISSION_COLUMNS, mission_id, changes)


# ============================================================
# LOGS (HISTÓRICO DE ATIVIDADE)
# ============================================================


def insert_log(connection, action, description, user_id=None, character_id=None):
    """Regista uma entrada no histórico de atividade."""
    connection.execute(
        "INSERT INTO activity_logs (user_id, character_id, action, description) "
        "VALUES (?, ?, ?, ?)",
        (user_id, character_id, action, description),
    )


def list_logs_for_user(connection, user_id, limit):
    """Histórico de um utilizador (mais recente primeiro)."""
    return connection.execute(
        "SELECT created_at, action, description FROM activity_logs "
        "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


def list_logs_by_action(connection, character_id, action, limit):
    """Entradas de um certo tipo (ex.: 'NIVEL') de uma personagem."""
    return connection.execute(
        "SELECT created_at, description FROM activity_logs "
        "WHERE character_id = ? AND action = ? ORDER BY id DESC LIMIT ?",
        (character_id, action, limit),
    ).fetchall()


def list_all_logs(connection, limit):
    """Histórico de todos os utilizadores, com o username (para o admin)."""
    return connection.execute(
        "SELECT l.created_at, l.action, l.description, u.username "
        "FROM activity_logs l LEFT JOIN users u ON u.id = l.user_id "
        "ORDER BY l.id DESC LIMIT ?",
        (limit,),
    ).fetchall()


# ============================================================
# RANKING
# ============================================================

# Critérios de ordenação permitidos. O texto do ORDER BY NÃO vem do
# utilizador: escolhemos nós uma destas opções (lista branca).
RANKING_ORDERS = {
    "nivel":    "level DESC, experience DESC, wins DESC, name ASC",
    "dinheiro": "money DESC, level DESC, name ASC",
    "vitorias": "wins DESC, level DESC, name ASC",
    "missoes":  "missions_completed DESC, level DESC, name ASC",
}


def _ranking_sql(criterion):
    """
    Constrói o SQL do ranking para um critério.

    1.º passo (base): uma linha por personagem, com o nº de missões
       concluídas (LEFT JOIN + GROUP BY + COUNT). Jogadores bloqueados
       ficam de fora.
    2.º passo (ranked): acrescenta a posição com ROW_NUMBER().
    """
    order_by = RANKING_ORDERS[criterion]
    return (
        "WITH base AS ( "
        "  SELECT c.id AS character_id, c.name, c.class AS class, c.level, "
        "         c.experience, c.money, c.wins, COUNT(cm.mission_id) AS missions_completed "
        "  FROM characters c "
        "  JOIN users u ON u.id = c.user_id "
        "  LEFT JOIN character_missions cm ON cm.character_id = c.id AND cm.status = 'concluida' "
        "  WHERE u.status = 'ativo' "
        "  GROUP BY c.id "
        "), ranked AS ( "
        f"  SELECT base.*, ROW_NUMBER() OVER (ORDER BY {order_by}) AS position FROM base "
        ") "
    )


def get_ranking(connection, criterion, limit):
    """As melhores 'limit' personagens segundo o critério."""
    return connection.execute(
        _ranking_sql(criterion) + "SELECT * FROM ranked ORDER BY position LIMIT ?",
        (limit,),
    ).fetchall()


def get_ranking_position(connection, criterion, character_id):
    """A linha do ranking de uma personagem (com a sua posição) ou None."""
    return connection.execute(
        _ranking_sql(criterion) + "SELECT * FROM ranked WHERE character_id = ?",
        (character_id,),
    ).fetchone()


# ============================================================
# ESTATÍSTICAS DO SISTEMA (administração)
# ============================================================


def count_users_by_status(connection):
    """Nº de utilizadores por estado (GROUP BY)."""
    return connection.execute(
        "SELECT status, COUNT(*) AS total FROM users GROUP BY status"
    ).fetchall()


def get_character_statistics(connection):
    """Agregados sobre todas as personagens (COUNT, AVG, MAX, SUM)."""
    return connection.execute(
        "SELECT COUNT(*) AS total, "
        "       COALESCE(AVG(level), 0) AS average_level, "
        "       COALESCE(MAX(level), 0) AS max_level, "
        "       COALESCE(SUM(money), 0) AS total_money "
        "FROM characters"
    ).fetchone()


def count_combats_by_result(connection):
    """Nº de combates por resultado (GROUP BY)."""
    return connection.execute(
        "SELECT result, COUNT(*) AS total FROM combats GROUP BY result"
    ).fetchall()


def get_best_selling_items(connection, limit):
    """Objetos mais comprados (JOIN + GROUP BY + SUM + ORDER BY)."""
    return connection.execute(
        "SELECT i.name, SUM(t.quantity) AS total "
        "FROM transactions t JOIN items i ON i.id = t.item_id "
        "WHERE t.type = 'compra' "
        "GROUP BY i.id ORDER BY total DESC LIMIT ?",
        (limit,),
    ).fetchall()


def get_missions_completed_count(connection):
    """Quantas vezes cada missão foi concluída."""
    return connection.execute(
        "SELECT m.name, COUNT(*) AS total "
        "FROM character_missions cm JOIN missions m ON m.id = cm.mission_id "
        "WHERE cm.status = 'concluida' "
        "GROUP BY m.id ORDER BY total DESC"
    ).fetchall()
