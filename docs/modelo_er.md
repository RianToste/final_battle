# Modelo Entidade-Relação

Imagem: [`modelo_er.png`](modelo_er.png) / [`modelo_er.svg`](modelo_er.svg)
(gerada com Graphviz a partir de [`modelo_er.dot`](modelo_er.dot): `dot -Tpng modelo_er.dot -o modelo_er.png`).

O mesmo diagrama em Mermaid (o GitHub desenha-o automaticamente):

```mermaid
erDiagram
    users ||--o| characters : "tem (1:1)"
    characters ||--o{ inventory : possui
    items ||--o{ inventory : "aparece em"
    characters ||--o{ transactions : realiza
    items ||--o{ transactions : "é comprado/vendido"
    characters ||--o{ combats : luta
    enemies ||--o{ combats : "é enfrentado"
    characters ||--o{ character_missions : aceita
    missions ||--o{ character_missions : "é aceite"
    enemies |o--o{ missions : "é alvo de"
    users ||--o{ activity_logs : gera
    characters |o--o{ activity_logs : "é referida em"

    users {
        int id PK
        text username UK
        text password_hash
        text password_salt
        text role
        text status
        text created_at
    }
    characters {
        int id PK
        int user_id FK
        text name UK
        text class
        int level
        int experience
        int health
        int max_health
        int energy
        int money
        int attack
        int defense
        int agility
        int wins
        int losses
    }
    items {
        int id PK
        text name UK
        text type
        int price
        int stock
        text effect_type
        int effect_value
    }
    inventory {
        int character_id PK
        int item_id PK
        int quantity
    }
    transactions {
        int id PK
        int character_id FK
        int item_id FK
        text type
        int quantity
        int total
        int balance_before
        int balance_after
    }
    enemies {
        int id PK
        text name UK
        int level
        int health
        int attack
        int defense
        real dodge_chance
        real crit_chance
    }
    combats {
        int id PK
        int character_id FK
        int enemy_id FK
        text result
        int turns
        int xp_gained
        int money_gained
    }
    missions {
        int id PK
        text name UK
        int difficulty
        int min_level
        text objective_type
        int objective_target_id FK
        int objective_amount
    }
    character_missions {
        int character_id PK
        int mission_id PK
        text status
        int progress
    }
    activity_logs {
        int id PK
        int user_id FK
        int character_id FK
        text action
        text description
        text created_at
    }
```

## Relações

| Tipo | Tabelas |
|------|---------|
| 1:1  | `users` — `characters` (`user_id` é `UNIQUE`) |
| 1:N  | `characters` — `transactions`, `characters` — `combats`, `users` — `activity_logs`, `enemies` — `missions` (alvo) |
| N:N  | `characters` — `items` (tabela `inventory`), `characters` — `missions` (tabela `character_missions`) |

## Restrições de integridade principais

- `CHECK (money >= 0)`: nunca existe saldo negativo.
- `CHECK (quantity > 0)` no inventário: linhas vazias são apagadas.
- `UNIQUE` em `users.username` e `characters.name` (sem distinção de maiúsculas).
- `CHECK (...)` nos tipos/estados (`role`, `status`, `type`, `result`...).
- Chaves estrangeiras ativas (`PRAGMA foreign_keys = ON`).
