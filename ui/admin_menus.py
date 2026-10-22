"""
Menus da área de administração.

Todas as operações passam pelo serviço services/admin.py, que volta a
verificar se o utilizador é mesmo administrador. Assim a segurança não
depende só de este menu estar escondido.
"""

from services import admin
from ui import messages
from ui.input_helpers import ask_choice, ask_int, ask_list_choice, ask_text, ask_yes_no
from ui.navigation import run_menu
from utils.formatting import format_datetime, format_money, format_table


# ------------------------------------------------------------
# Auxiliares para formulários (criar / editar)
# ------------------------------------------------------------

def _ask_field(spec):
    """
    Pergunta o valor de um campo. A validação é feita pelo serviço
    (admin.validate_field), por isso a pergunta repete até o valor ser válido.
    Para campos com opções fixas, mostra-as primeiro.
    """
    if spec.kind == "choice":
        messages.print_info(f"Opções: {', '.join(spec.choices)}")
    return ask_text(f"{spec.label}: ", lambda text: admin.validate_field(spec, text))


def _ask_all_fields(fields):
    """Pergunta todos os campos de uma lista e devolve {coluna: valor}."""
    return {spec.column: _ask_field(spec) for spec in fields}


def _print_fields(fields, row):
    """Mostra a lista numerada de campos com o valor atual de cada um."""
    for number, spec in enumerate(fields, start=1):
        print(f"  {number}. {spec.label}: {row[spec.column]}")


def _edit_flow(fields, current_row, update_function):
    """
    Fluxo de edição genérico: o administrador escolhe UM campo, vê o valor
    atual e escreve o novo. Repete enquanto quiser editar mais campos.

    - fields:          lista de FieldSpec (os campos editáveis)
    - current_row:     dicionário com os valores atuais
    - update_function: função que grava as alterações, recebe {coluna: valor}
    """
    while True:
        print("\nQue campo quer editar?")
        _print_fields(fields, current_row)
        spec = ask_list_choice("Número do campo (0 para terminar): ", fields)
        if spec is None:
            return

        new_value = _ask_field(spec)
        update_function({spec.column: new_value})
        current_row[spec.column] = new_value     # para a lista mostrar o valor novo
        messages.print_success(f"{spec.label} atualizado.")


# ------------------------------------------------------------
# Menu principal da administração
# ------------------------------------------------------------

def admin_menu(admin_user):
    """Menu principal do administrador."""
    options = [
        ("Utilizadores", lambda: users_menu(admin_user)),
        ("Objetos", lambda: items_menu(admin_user)),
        ("Adversários", lambda: enemies_menu(admin_user)),
        ("Missões", lambda: missions_admin_menu(admin_user)),
        ("Consultar partidas (combates)", lambda: show_combats(admin_user)),
        ("Estatísticas do sistema", lambda: show_statistics(admin_user)),
        ("Logs de atividade", lambda: show_logs(admin_user)),
    ]
    run_menu(f"ADMINISTRAÇÃO - {admin_user.username}", options,
             back_label="Terminar sessão", pause_after=False)


# ------------------------------------------------------------
# Utilizadores
# ------------------------------------------------------------

def users_menu(admin_user):
    """Consultar, bloquear e desbloquear utilizadores."""
    options = [
        ("Listar utilizadores", lambda: list_users(admin_user)),
        ("Bloquear utilizador", lambda: change_block(admin_user, True)),
        ("Desbloquear utilizador", lambda: change_block(admin_user, False)),
    ]
    run_menu("UTILIZADORES", options)


def _users_table(users):
    rows = [
        [u["id"], u["username"], u["role"], u["status"],
         u["character_name"] or "-", u["character_level"] or "-",
         format_datetime(u["created_at"])]
        for u in users
    ]
    return format_table(
        ["ID", "Username", "Tipo", "Estado", "Personagem", "Nível", "Criado em"], rows
    )


def list_users(admin_user):
    print(_users_table(admin.list_users(admin_user)))


def change_block(admin_user, blocked):
    """Bloqueia ou desbloqueia, conforme o parâmetro."""
    users = admin.list_users(admin_user)
    print(_users_table(users))
    user_id = ask_int("ID do utilizador (0 para cancelar): ", minimum=0)
    if user_id == 0:
        return
    admin.set_user_blocked(admin_user, user_id, blocked)
    messages.print_success("Utilizador bloqueado." if blocked else "Utilizador desbloqueado.")


# ------------------------------------------------------------
# Objetos
# ------------------------------------------------------------

def items_menu(admin_user):
    """Criar, editar e remover objetos."""
    options = [
        ("Listar objetos", lambda: list_items(admin_user)),
        ("Criar objeto", lambda: create_item(admin_user)),
        ("Editar objeto", lambda: edit_item(admin_user)),
        ("Remover objeto", lambda: delete_item(admin_user)),
    ]
    run_menu("OBJETOS", options)


def _items_table(items):
    rows = [
        [n, i["name"], i["type"], format_money(i["price"]), i["stock"],
         i["effect_type"], i["effect_value"]]
        for n, i in enumerate(items, start=1)
    ]
    return format_table(["Nº", "Nome", "Tipo", "Preço", "Stock", "Efeito", "Valor"], rows)


def list_items(admin_user):
    print(_items_table(admin.list_items(admin_user)))


def create_item(admin_user):
    data = _ask_all_fields(admin.ITEM_FIELDS)
    admin.create_item(admin_user, data)
    messages.print_success("Objeto criado.")


def edit_item(admin_user):
    items = admin.list_items(admin_user)
    print(_items_table(items))
    item = ask_list_choice("Número do objeto a editar (0 para cancelar): ", items)
    if item is None:
        return
    _edit_flow(admin.ITEM_FIELDS, item,
               lambda changes: admin.update_item(admin_user, item["id"], changes))


def delete_item(admin_user):
    items = admin.list_items(admin_user)
    print(_items_table(items))
    item = ask_list_choice("Número do objeto a remover (0 para cancelar): ", items)
    if item is None:
        return
    if ask_yes_no(f"Remover '{item['name']}' definitivamente"):
        admin.delete_item(admin_user, item["id"])
        messages.print_success("Objeto removido.")


# ------------------------------------------------------------
# Adversários
# ------------------------------------------------------------

def enemies_menu(admin_user):
    """Criar e editar adversários."""
    options = [
        ("Listar adversários", lambda: list_enemies(admin_user)),
        ("Criar adversário", lambda: create_enemy(admin_user)),
        ("Editar adversário", lambda: edit_enemy(admin_user)),
    ]
    run_menu("ADVERSÁRIOS", options)


def _enemies_table(enemies):
    rows = [
        [n, e["name"], e["level"], e["health"], e["attack"], e["defense"],
         e["reward_money"], e["reward_xp"], e["dodge_chance"], e["crit_chance"]]
        for n, e in enumerate(enemies, start=1)
    ]
    return format_table(
        ["Nº", "Nome", "Nível", "Vida", "Atq", "Def", "Dinheiro", "XP", "Esquiva", "Crítico"],
        rows,
    )


def list_enemies(admin_user):
    print(_enemies_table(admin.list_enemies(admin_user)))


def create_enemy(admin_user):
    data = _ask_all_fields(admin.ENEMY_FIELDS)
    admin.create_enemy(admin_user, data)
    messages.print_success("Adversário criado.")


def edit_enemy(admin_user):
    enemies = admin.list_enemies(admin_user)
    print(_enemies_table(enemies))
    enemy = ask_list_choice("Número do adversário a editar (0 para cancelar): ", enemies)
    if enemy is None:
        return
    _edit_flow(admin.ENEMY_FIELDS, enemy,
               lambda changes: admin.update_enemy(admin_user, enemy["id"], changes))


# ------------------------------------------------------------
# Missões
# ------------------------------------------------------------

def missions_admin_menu(admin_user):
    """Criar e editar missões."""
    options = [
        ("Listar missões", lambda: list_missions(admin_user)),
        ("Criar missão", lambda: create_mission(admin_user)),
        ("Editar missão", lambda: edit_mission(admin_user)),
    ]
    run_menu("MISSÕES (ADMIN)", options)


def _missions_table(missions):
    rows = [
        [n, m["name"], m["difficulty"], m["min_level"], m["objective_type"],
         m["target_name"] or "-", m["objective_amount"],
         f"{m['reward_money']} € + {m['reward_xp']} XP"]
        for n, m in enumerate(missions, start=1)
    ]
    return format_table(
        ["Nº", "Nome", "Dific.", "Nível", "Objetivo", "Alvo", "Qtd", "Recompensa"], rows
    )


def list_missions(admin_user):
    print(_missions_table(admin.list_missions(admin_user)))


def create_mission(admin_user):
    data = _ask_all_fields(admin.MISSION_FIELDS)

    messages.print_info("Tipo de objetivo:")
    objective_type = ask_choice("Escolha: ", list(admin.OBJECTIVE_TYPE_FIELD.choices))

    target_id = None
    if objective_type == "defeat_enemies":
        enemies = admin.list_enemies(admin_user)
        print(_enemies_table(enemies))
        target = ask_list_choice("Adversário-alvo (0 para cancelar): ", enemies)
        if target is None:
            return
        target_id = target["id"]

    admin.create_mission(admin_user, data, objective_type, target_id)
    messages.print_success("Missão criada.")


def edit_mission(admin_user):
    missions = admin.list_missions(admin_user)
    print(_missions_table(missions))
    mission = ask_list_choice("Número da missão a editar (0 para cancelar): ", missions)
    if mission is None:
        return
    _edit_flow(admin.MISSION_FIELDS, mission,
               lambda changes: admin.update_mission(admin_user, mission["id"], changes))


# ------------------------------------------------------------
# Combates, estatísticas e logs
# ------------------------------------------------------------

def show_combats(admin_user):
    combats = admin.list_combats(admin_user)
    rows = [
        [format_datetime(c["created_at"]), c["character_name"], c["enemy_name"],
         c["result"], c["turns"], c["xp_gained"], c["money_gained"]]
        for c in combats
    ]
    print(format_table(["Data", "Personagem", "Adversário", "Resultado", "Turnos", "XP", "Dinheiro"], rows))


def show_statistics(admin_user):
    stats = admin.get_system_statistics(admin_user)

    messages.print_section("Utilizadores")
    for row in stats["users_by_status"]:
        messages.print_info(f"{row['status']}: {row['total']}")

    chars = stats["characters"]
    messages.print_section("Personagens")
    messages.print_info(f"Total: {chars['total']}")
    messages.print_info(f"Nível médio: {chars['average_level']:.1f}    Nível máximo: {chars['max_level']}")
    messages.print_info(f"Dinheiro em circulação: {format_money(chars['total_money'])}")

    messages.print_section("Combates por resultado")
    for row in stats["combats_by_result"] or [{"result": "(nenhum)", "total": 0}]:
        messages.print_info(f"{row['result']}: {row['total']}")

    messages.print_section("Objetos mais comprados")
    for row in stats["best_selling_items"] or [{"name": "(nenhum)", "total": 0}]:
        messages.print_info(f"{row['name']}: {row['total']} unid.")

    messages.print_section("Missões concluídas")
    for row in stats["missions_completed"] or [{"name": "(nenhuma)", "total": 0}]:
        messages.print_info(f"{row['name']}: {row['total']}x")


def show_logs(admin_user):
    limit = ask_int("Quantos registos quer ver? (1-200): ", minimum=1, maximum=200)
    logs = admin.list_logs(admin_user, limit)
    rows = [
        [format_datetime(l["created_at"]), l["username"] or "-", l["action"], l["description"]]
        for l in reversed(logs)
    ]
    print(format_table(["Data", "Utilizador", "Ação", "Descrição"], rows))
