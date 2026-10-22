-- ============================================================
-- Usa "IF NOT EXISTS" para poder ser executado várias vezes sem erro.
--
-- Relações principais:
--   users 1:1 characters           (cada jogador tem uma personagem)
--   characters N:N items           (via tabela inventory)
--   characters N:N missions        (via tabela character_missions)
--   characters N:N enemies         (via tabela combats)
-- ============================================================

-- ------------------------------------------------------------
-- UTILIZADORES: contas de acesso (jogadores e administradores)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,  -- UNIQUE impede duplicados ("Ana" = "ana")
    password_hash TEXT    NOT NULL, 
    password_salt TEXT    NOT NULL,                   -- texto aleatório único por utilizador
    role          TEXT    NOT NULL DEFAULT 'jogador'
                  CHECK (role IN ('jogador', 'administrador')),
    status        TEXT    NOT NULL DEFAULT 'ativo'
                  CHECK (status IN ('ativo', 'bloqueado')),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ------------------------------------------------------------
-- PERSONAGENS: relação 1:1 com users (user_id é UNIQUE)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS characters (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL UNIQUE
                REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    class       TEXT    NOT NULL,
    level       INTEGER NOT NULL DEFAULT 1   CHECK (level >= 1),
    experience  INTEGER NOT NULL DEFAULT 0   CHECK (experience >= 0),
    health      INTEGER NOT NULL             CHECK (health >= 0),
    max_health  INTEGER NOT NULL             CHECK (max_health > 0),
    energy      INTEGER NOT NULL             CHECK (energy >= 0),
    money       INTEGER NOT NULL DEFAULT 0   CHECK (money >= 0),  -- impede saldo negativo
    attack      INTEGER NOT NULL,
    defense     INTEGER NOT NULL,
    agility     INTEGER NOT NULL,
    wins        INTEGER NOT NULL DEFAULT 0,  -- usado no ranking
    losses      INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ------------------------------------------------------------
-- ITENS: catálogo da loja
-- effect_type/effect_value descrevem o que o item faz.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE,
    description  TEXT    NOT NULL,
    type         TEXT    NOT NULL
                 CHECK (type IN ('arma', 'armadura', 'pocao', 'ferramenta', 'especial')),
    price        INTEGER NOT NULL CHECK (price >= 0),
    stock        INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),  -- quantidade disponível na loja
    effect_type  TEXT    NOT NULL DEFAULT 'nenhum'
                 CHECK (effect_type IN ('nenhum', 'curar', 'energia', 'bonus_ataque', 'bonus_defesa')),
    effect_value INTEGER NOT NULL DEFAULT 0
);

-- ------------------------------------------------------------
-- INVENTÁRIO: relação N:N entre characters e items
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventory (
    character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    item_id      INTEGER NOT NULL REFERENCES items(id),
    quantity     INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (character_id, item_id)
);

-- ------------------------------------------------------------
-- TRANSAÇÕES: registo de todas as compras e vendas
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id   INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    item_id        INTEGER NOT NULL REFERENCES items(id),
    type           TEXT    NOT NULL CHECK (type IN ('compra', 'venda')),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    unit_price     INTEGER NOT NULL CHECK (unit_price >= 0),
    total          INTEGER NOT NULL CHECK (total >= 0),
    balance_before INTEGER NOT NULL,
    balance_after  INTEGER NOT NULL,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ------------------------------------------------------------
-- ADVERSÁRIOS: inimigos do combate
-- dodge_chance e crit_chance são as "probabilidades de resultados".
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS enemies (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE,
    level        INTEGER NOT NULL CHECK (level >= 1),
    health       INTEGER NOT NULL CHECK (health > 0),
    attack       INTEGER NOT NULL CHECK (attack >= 0),
    defense      INTEGER NOT NULL CHECK (defense >= 0),
    reward_money INTEGER NOT NULL CHECK (reward_money >= 0),
    reward_xp    INTEGER NOT NULL CHECK (reward_xp >= 0),
    dodge_chance REAL    NOT NULL DEFAULT 0.05 CHECK (dodge_chance BETWEEN 0 AND 1),
    crit_chance  REAL    NOT NULL DEFAULT 0.05 CHECK (crit_chance  BETWEEN 0 AND 1)
);

-- ------------------------------------------------------------
-- COMBATES: histórico de cada combate (alimenta ranking e estatísticas)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS combats (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id  INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    enemy_id      INTEGER NOT NULL REFERENCES enemies(id),
    result        TEXT    NOT NULL CHECK (result IN ('vitoria', 'derrota', 'empate')),
    turns         INTEGER NOT NULL,
    damage_dealt  INTEGER NOT NULL DEFAULT 0,
    damage_taken  INTEGER NOT NULL DEFAULT 0,
    xp_gained     INTEGER NOT NULL DEFAULT 0,
    money_gained  INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ------------------------------------------------------------
-- MISSÕES: catálogo de missões (iguais para todos os jogadores)
-- objective_type diz o que é preciso fazer:
--   defeat_enemies -> derrotar X vezes o adversário objective_target_id
--   win_combats    -> vencer X combates (qualquer adversário)
--   buy_items      -> comprar X itens
--   reach_level    -> atingir o nível X
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS missions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT    NOT NULL UNIQUE,
    description         TEXT    NOT NULL,
    difficulty          INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
    min_level           INTEGER NOT NULL DEFAULT 1,
    reward_money        INTEGER NOT NULL DEFAULT 0 CHECK (reward_money >= 0),
    reward_xp           INTEGER NOT NULL DEFAULT 0 CHECK (reward_xp >= 0),
    objective_type      TEXT    NOT NULL
                        CHECK (objective_type IN ('defeat_enemies', 'win_combats', 'buy_items', 'reach_level')),
    objective_target_id INTEGER REFERENCES enemies(id),   -- só usado em defeat_enemies
    objective_amount    INTEGER NOT NULL CHECK (objective_amount > 0)
);

-- ------------------------------------------------------------
-- MISSÕES DA PERSONAGEM: estado de cada missão POR jogador (N:N)
-- Se não existir linha, a missão está "disponível" para esse jogador.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS character_missions (
    character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    mission_id   INTEGER NOT NULL REFERENCES missions(id),
    status       TEXT    NOT NULL DEFAULT 'em_curso'
                 CHECK (status IN ('disponivel', 'em_curso', 'concluida', 'falhada')),
    progress     INTEGER NOT NULL DEFAULT 0,
    accepted_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    finished_at  TEXT,
    PRIMARY KEY (character_id, mission_id)
);

-- ------------------------------------------------------------
-- LOGS: histórico de atividade (jogador e administração)
-- ON DELETE SET NULL: se o utilizador for apagado, o log mantém-se.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_logs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    character_id INTEGER REFERENCES characters(id) ON DELETE SET NULL,
    action       TEXT NOT NULL,      -- código curto, ex.: "COMPRA", "COMBATE", "LOGIN"
    description  TEXT NOT NULL,      -- frase legível para o histórico
    created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- ------------------------------------------------------------
-- ÍNDICES: aceleram as consultas mais frequentes
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_logs_character   ON activity_logs(character_id, created_at);
CREATE INDEX IF NOT EXISTS idx_combats_char     ON combats(character_id);
CREATE INDEX IF NOT EXISTS idx_transactions_chr ON transactions(character_id);
CREATE INDEX IF NOT EXISTS idx_characters_rank  ON characters(level DESC, experience DESC);