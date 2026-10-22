-- ============================================================
-- Dados iniciais do jogo: itens, adversários e missões.
-- "INSERT OR IGNORE" evita duplicados se for executado de novo
-- ============================================================

-- ------------------------------------------------------------
-- ITENS (name, description, type, price, stock, effect_type, effect_value)
-- ------------------------------------------------------------
INSERT OR IGNORE INTO items (name, description, type, price, stock, effect_type, effect_value) VALUES
('Pocao de Vida',      'Recupera 50 pontos de vida.',            'pocao',      50,  50, 'curar',        50),
('Pocao de Vida Maior','Recupera 120 pontos de vida.',           'pocao',      110, 30, 'curar',        120),
('Pocao de Energia',   'Recupera 40 pontos de energia.',         'pocao',      40,  50, 'energia',      40),
('Espada de Ferro',    'Espada simples. Aumenta o ataque em 4.', 'arma',       120, 10, 'bonus_ataque',  4),
('Cajado Arcano',      'Cajado mágico. Aumenta o ataque em 7.',  'arma',       300, 5,  'bonus_ataque',  7),
('Escudo de Madeira',  'Escudo leve. Aumenta a defesa em 3.',    'armadura',   100, 10, 'bonus_defesa',  3),
('Armadura de Couro',  'Proteção leve. Aumenta a defesa em 5.',  'armadura',   220, 8,  'bonus_defesa',  5),
('Kit de Ferramentas', 'Ferramentas diversas de sobrevivência.', 'ferramenta', 60,  20, 'nenhum',       0),
('Amuleto Antigo',     'Objeto raro, valioso para colecionadores.','especial', 500, 3,  'nenhum',       0);

-- ------------------------------------------------------------
-- ADVERSÁRIOS
-- (name, level, health, attack, defense, reward_money, reward_xp, dodge, crit)
-- ------------------------------------------------------------
INSERT OR IGNORE INTO enemies (name, level, health, attack, defense, reward_money, reward_xp, dodge_chance, crit_chance) VALUES
('Rato Gigante', 1,  30,  6,  2,  15,  30, 0.05, 0.03),
('Goblin',       2,  45,  9,  4,  25,  50, 0.08, 0.05),
('Lobo Selvagem',3,  70,  13, 6,  40,  80, 0.10, 0.08),
('Bandido',      4,  90,  16, 9,  60,  120, 0.08, 0.10),
('Orc',          6,  140, 22, 13, 100, 200, 0.05, 0.10),
('Troll',        8,  220, 28, 18, 180, 350, 0.03, 0.12);

-- ------------------------------------------------------------
-- MISSÕES
-- (name, description, difficulty, min_level, reward_money, reward_xp,
--  objective_type, objective_target_id, objective_amount)
-- O id do adversário vai buscar-se por nome, em vez de escrever o número.
-- ------------------------------------------------------------
INSERT OR IGNORE INTO missions
(name, description, difficulty, min_level, reward_money, reward_xp, objective_type, objective_target_id, objective_amount) VALUES
('Primeiras Compras', 'Compra 1 item na loja.',                          1, 1, 30,  40,  'buy_items',      NULL, 1),
('Caçador de Goblins','Derrota 3 Goblins.',                              1, 1, 80,  100, 'defeat_enemies', (SELECT id FROM enemies WHERE name = 'Goblin'), 3),
('Aprendiz',          'Atinge o nível 3.',                               2, 1, 100, 120, 'reach_level',    NULL, 3),
('Praga das Cavernas','Derrota 5 Lobos Selvagens.',                      3, 3, 200, 250, 'defeat_enemies', (SELECT id FROM enemies WHERE name = 'Lobo Selvagem'), 5),
('Campeão da Arena',  'Vence 10 combates contra qualquer adversário.',   4, 4, 400, 500, 'win_combats',    NULL, 10);