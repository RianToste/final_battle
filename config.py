"""
Configurações centrais do projeto.

Aqui ficam TODOS os valores do jogo (custos de energia,
fórmulas de XP, classes, limites de validação...). Assim, para equilibrar
o jogo, só é preciso mexer neste ficheiro e não no resto do código.

Também lê as variáveis sensíveis (caminho da BD, conta de admin)
do ficheiro .env, para não as escrever diretamente no código.
"""

import os

# ============================================================
# 1. LEITURA DO FICHEIRO .env
# ============================================================

def _load_env_file(path=".env"):
    """
    Lê um ficheiro .env simples (linhas no formato CHAVE=VALOR) e
    coloca os valores nas variáveis de ambiente do programa.
    """
    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()

            # Ignora linhas vazias e comentários (que começam por #)
            if not line or line.startswith("#"):
                continue

            # Ignora linhas mal formadas (sem o sinal de =)
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            # setdefault: não sobrescreve variáveis que já existam no sistema
            os.environ.setdefault(key.strip(), value.strip())


# Executa a leitura assim que o módulo é importado
_load_env_file()

# ============================================================
# 2. BASE DE DADOS E CONTA DE ADMIN (vêm do .env)
# ============================================================

# Ficheiro da base de dados SQLite. Se não houver .env, usa "game.db".
DATABASE_PATH = os.getenv("DATABASE_PATH", "game.db")

# Credenciais do administrador criado na inicialização da BD
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
# NÃO existe valor por defeito para a password: as credenciais não devem
# ficar escritas no código. Se faltar no .env, a aplicação avisa (ver main.py).
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# ============================================================
# 3. TIPOS DE UTILIZADOR E ESTADOS
# ============================================================

ROLE_PLAYER = "jogador"
ROLE_ADMIN = "administrador"

# Estado de uma conta
STATUS_ACTIVE = "ativo"
STATUS_BLOCKED = "bloqueado"

# Estados possíveis de uma missão
MISSION_AVAILABLE = "disponivel"
MISSION_IN_PROGRESS = "em_curso"
MISSION_COMPLETED = "concluida"
MISSION_FAILED = "falhada"


TRANSACTION_BUY = "compra"
TRANSACTION_SELL = "venda"

# ============================================================
# 4. REGRAS DE VALIDAÇÃO DE DADOS
# ============================================================

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 20

PASSWORD_MIN_LENGTH = 8

CHARACTER_NAME_MIN_LENGTH = 3
CHARACTER_NAME_MAX_LENGTH = 20

# ============================================================
# 5. SEGURANÇA (hashing de passwords)
# ============================================================

# Número de repetições do algoritmo PBKDF2. Quanto maior, mais lento
# (e mais difícil) é para um atacante adivinhar passwords por força bruta.
PASSWORD_HASH_ITERATIONS = 200_000

# Tamanho do "salt" (texto aleatório único por utilizador), em bytes
PASSWORD_SALT_BYTES = 16

# ============================================================
# 6. CLASSES DE PERSONAGEM
# ============================================================

CHARACTER_CLASSES = {
    "Guerreiro": {"health": 120, "attack": 12, "defense": 10, "agility": 5},
    "Feiticeiro":      {"health": 80,  "attack": 16, "defense": 4,  "agility": 7},
    "Bandido":    {"health": 90,  "attack": 11, "defense": 6,  "agility": 12},
}

# ============================================================
# 7. ECONOMIA E ENERGIA
# ============================================================

STARTING_MONEY = 200
STARTING_ENERGY = 100
MAX_ENERGY = 100

# Ao vender, o jogador recebe esta fração do preço de compra (50%)
SELL_PRICE_RATIO = 0.5

# Energia gasta por cada ação
ENERGY_COST_COMBAT = 10
ENERGY_COST_MISSION = 15

# ============================================================
# 8. EVOLUÇÃO (NÍVEIS E EXPERIÊNCIA)
#
# Fórmula do XP necessário para passar do nível N para o N+1:
#     xp_necessário = XP_BASE * (N ** XP_EXPONENT)
# Exemplo com os valores abaixo: nível 1 -> 100 XP, nível 2 -> ~282 XP...
# A experiência da personagem é o XP acumulado DENTRO do nível atual:
# ao subir, o XP gasto é descontado e o excedente fica para o nível seguinte.
# ============================================================

XP_BASE = 100
XP_EXPONENT = 1.5
MAX_LEVEL = 50

# Bónus recebidos em cada subida de nível
LEVEL_UP_HEALTH_BONUS = 10
LEVEL_UP_ATTACK_BONUS = 2
LEVEL_UP_DEFENSE_BONUS = 1
LEVEL_UP_AGILITY_BONUS = 1

# ============================================================
# 9. COMBATE
# ============================================================

# Variação aleatória do dano (±20%). Evita resultados sempre iguais.
COMBAT_DAMAGE_VARIATION = 0.2

# Dano mínimo garantido, mesmo que a defesa seja maior que o ataque
COMBAT_MIN_DAMAGE = 1

# Probabilidade base de acerto crítico (e bónus por ponto de agilidade)
COMBAT_BASE_CRIT_CHANCE = 0.05
COMBAT_CRIT_CHANCE_PER_AGILITY = 0.005
COMBAT_CRIT_MULTIPLIER = 1.5

COMBAT_DEFEAT_MONEY_PENALTY = 0.10

COMBAT_MAX_TURNS = 30


RANKING_TOP_N = 10
HISTORY_DEFAULT_LIMIT = 20

# ============================================================
# 10. LISTAS DE VALORES PERMITIDOS (usadas na área de administração)
# Têm de estar de acordo com os CHECK(...) do schema.sql.
# ============================================================

ITEM_TYPES = ["arma", "armadura", "pocao", "ferramenta", "especial"]
ITEM_EFFECT_TYPES = ["nenhum", "curar", "energia", "bonus_ataque", "bonus_defesa"]
OBJECTIVE_TYPES = ["defeat_enemies", "win_combats", "buy_items", "reach_level"]

# Tamanho máximo de textos livres (nomes de objetos, descrições...)
MAX_TEXT_LENGTH = 200

# ============================================================
# 11. COMBATE (parâmetros adicionais)
#
# Dano = ataque * 100 / (100 + defesa)  (depois: variação e crítico)
# Quanto maior a defesa, menos dano se sofre, mas nunca se fica imune.
# ============================================================

COMBAT_DEFENSE_SCALE = 100

# A personagem esquiva-se com (agilidade * valor), até ao máximo indicado
COMBAT_DODGE_CHANCE_PER_AGILITY = 0.005
COMBAT_MAX_DODGE_CHANCE = 0.40

# Vida com que a personagem fica depois de perder um combate
COMBAT_DEFEAT_HEALTH = 1

# Nº de combates simulados para estimar a probabilidade de vitória
COMBAT_WIN_ESTIMATE_SIMULATIONS = 300

# ============================================================
# 12. DESCANSO E REGISTO DE ERROS
# ============================================================

# Descansar recupera vida e energia ao máximo. Custa até este valor
# (se o jogador tiver menos dinheiro, paga só o que tem: nunca fica bloqueado).
REST_COST = 20

# Ficheiro onde se guardam os erros inesperados (para o programador ver)
LOG_FILE = "game_errors.log"

