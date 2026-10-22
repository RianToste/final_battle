"""
Menus do jogador: personagem, inventário, loja, missões, combate,
ranking, histórico e conta.

Este ficheiro só trata de PERGUNTAR e MOSTRAR. As regras do jogo estão em
services/ e as classes em models/.
"""

import config
from services import (
    authentication,
    character_service,
    combat,
    history,
    missions,
    ranking,
    shop,
)
from ui import messages
from ui.input_helpers import (
    ask_int,
    ask_list_choice,
    ask_password,
    ask_text,
    ask_yes_no,
    ask_choice,
    pause,
)
from ui.navigation import run_menu, run_safely
from utils.formatting import format_datetime, format_money, format_table
from utils.exceptions import GameError
from utils.validators import (
    validate_character_name,
    validate_password,
    validate_username,
)


# ============================================================
# PERSONAGEM
# ============================================================

def create_character_flow(user):
    """
    Ecrã de criação da personagem (obrigatório antes de jogar).
    Devolve a Character criada, ou None se o jogador desistir.
    """
    messages.print_title("CRIAR PERSONAGEM")
    messages.print_info("Cada classe tem pontos fortes diferentes:\n")

    rows = [
        [name, stats["health"], stats["attack"], stats["defense"], stats["agility"]]
        for name, stats in config.CHARACTER_CLASSES.items()
    ]
    print(format_table(["Classe", "Vida", "Ataque", "Defesa", "Agilidade"], rows))

    while True:
        # ask_text repete a pergunta até o nome ser válido
        name = ask_text("\nNome da personagem: ", validate_character_name)
        print("Escolha a classe:")
        class_name = ask_choice("Classe: ", list(config.CHARACTER_CLASSES))

        try:
            character = character_service.create_character(user, name, class_name)
        except GameError as error:   # erro previsto (ex.: nome repetido)
            messages.print_error(str(error))
            if not ask_yes_no("Quer tentar novamente"):
                return None
            continue

        messages.print_success(f"{character.name}, o {character.character_class}, está pronto para a aventura!")
        pause()
        return character


def show_profile(user):
    """Ficha da personagem + evolução (subidas de nível, combates, missões)."""
    character = character_service.get_character(user)
    attack_bonus, defense_bonus = character_service.get_equipment_bonuses(character.id)
    messages.print_character(character, attack_bonus, defense_bonus)

    evolution = character_service.get_evolution(character.id)

    messages.print_section("Evolução da personagem")
    if evolution["level_ups"]:
        # As entradas vêm da mais recente para a mais antiga; invertemos
        for entry in reversed(evolution["level_ups"]):
            messages.print_info(f"{format_datetime(entry['created_at'])} - {entry['description']}")
    else:
        messages.print_info("Ainda não subiu de nível.")

    if evolution["combats"]:
        rows = [[c["result"], c["total"], c["xp"], format_money(c["money"])]
                for c in evolution["combats"]]
        print()
        print(format_table(["Resultado", "Combates", "XP ganho", "Dinheiro ganho"], rows))
    messages.print_info(f"\nMissões concluídas: {evolution['missions_completed']}")


def rest_action(user):
    """Descansar: recupera vida e energia."""
    character = character_service.get_character(user)
    cost_preview = min(config.REST_COST, character.money)
    if not ask_yes_no(f"Descansar custa {format_money(cost_preview)}. Continuar"):
        return
    cost = character_service.rest(character.id)
    messages.print_success(f"Descansou. Vida e energia recuperadas (pagou {format_money(cost)}).")


# ============================================================
# INVENTÁRIO
# ============================================================

def _inventory_table(entries):
    """Constrói a tabela de texto do inventário."""
    rows = [
        [number, e.item.name, e.item.type, e.quantity, e.item.effect_text]
        for number, e in enumerate(entries, start=1)
    ]
    return format_table(["Nº", "Objeto", "Tipo", "Qtd", "Efeito"], rows)


def inventory_menu(user):
    """Mostra o inventário e permite usar objetos."""
    character = character_service.get_character(user)

    while True:
        entries = shop.get_inventory(character.id)
        messages.print_title("INVENTÁRIO")
        if not entries:
            messages.print_info("O inventário está vazio. Visite a loja!")
            pause()
            return

        print(_inventory_table(entries))
        messages.print_info("\nArmas e armaduras aplicam o bónus automaticamente em combate.")

        if not ask_yes_no("Quer usar algum objeto"):
            return
        entry = ask_list_choice("Número do objeto (0 para cancelar): ", entries)
        if entry is None:
            continue

        def use():
            result = shop.use_item(character.id, entry.item.id)
            what = "vida" if result.effect_type == "curar" else "energia"
            messages.print_success(f"Usou {result.item_name}: recuperou {result.amount} de {what}.")

        run_safely(use)
        pause()


# ============================================================
# LOJA
# ============================================================

def _shop_table(items):
    """Tabela com os objetos da loja."""
    rows = []
    for number, item in enumerate(items, start=1):
        stock_text = item.stock if item.stock > 0 else "esgotado"
        rows.append([number, item.name, item.type, format_money(item.price),
                     stock_text, item.effect_text])
    return format_table(["Nº", "Objeto", "Tipo", "Preço", "Stock", "Efeito"], rows)


def shop_menu(user):
    """Menu da loja."""
    options = [
        ("Ver loja", lambda: show_shop(user)),
        ("Comprar", lambda: buy_action(user)),
        ("Vender", lambda: sell_action(user)),
        ("Ver as minhas transações", lambda: show_transactions(user)),
    ]
    run_menu("LOJA", options)


def show_shop(user):
    """Lista os objetos à venda e o saldo."""
    character = character_service.get_character(user)
    print(_shop_table(shop.list_shop_items()))
    messages.print_info(f"\nO seu saldo: {format_money(character.money)}")


def buy_action(user):
    """Fluxo de compra: escolher objeto, quantidade e confirmar."""
    character = character_service.get_character(user)
    items = shop.list_shop_items()
    print(_shop_table(items))
    messages.print_info(f"\nO seu saldo: {format_money(character.money)}")

    item = ask_list_choice("Número do objeto a comprar (0 para cancelar): ", items)
    if item is None:
        return
    quantity = ask_int("Quantidade: ", minimum=1)

    receipt = shop.buy_item(character.id, item.id, quantity)
    messages.print_receipt(receipt)
    messages.print_completed_missions(receipt.completed_missions)


def sell_action(user):
    """Fluxo de venda: escolher um objeto do inventário e a quantidade."""
    character = character_service.get_character(user)
    entries = shop.get_inventory(character.id)
    if not entries:
        messages.print_info("Não tem nada para vender.")
        return

    rows = [
        [number, e.item.name, e.quantity, format_money(e.item.sell_price)]
        for number, e in enumerate(entries, start=1)
    ]
    print(format_table(["Nº", "Objeto", "Qtd", "Preço de venda (unid.)"], rows))

    entry = ask_list_choice("Número do objeto a vender (0 para cancelar): ", entries)
    if entry is None:
        return
    quantity = ask_int("Quantidade: ", minimum=1)

    receipt = shop.sell_item(character.id, entry.item.id, quantity)
    messages.print_receipt(receipt)


def show_transactions(user):
    """Histórico de compras e vendas."""
    character = character_service.get_character(user)
    transactions = shop.get_transactions(character.id)
    rows = [
        [format_datetime(t["created_at"]), t["type"], t["item_name"], t["quantity"],
         format_money(t["total"]), format_money(t["balance_after"])]
        for t in transactions
    ]
    print(format_table(["Data", "Tipo", "Objeto", "Qtd", "Total", "Saldo depois"], rows))


# ============================================================
# MISSÕES
# ============================================================

_STATUS_TEXT = {
    config.MISSION_AVAILABLE: "Disponível",
    config.MISSION_IN_PROGRESS: "Em curso",
    config.MISSION_COMPLETED: "Concluída",
    config.MISSION_FAILED: "Falhada",
}


def _missions_table(mission_list):
    """Tabela com as missões e o progresso da personagem."""
    rows = []
    for number, m in enumerate(mission_list, start=1):
        progress = m.progress_text if m.status == config.MISSION_IN_PROGRESS else "-"
        rows.append([
            number, m.name, f"{m.difficulty}/5", m.min_level, m.objective_text,
            f"{m.reward_money} € + {m.reward_xp} XP", _STATUS_TEXT[m.status], progress,
        ])
    return format_table(
        ["Nº", "Missão", "Dific.", "Nível", "Objetivo", "Recompensa", "Estado", "Progresso"],
        rows,
    )


def missions_menu(user):
    """Menu das missões."""
    options = [
        ("Ver missões e progresso", lambda: show_missions(user)),
        ("Aceitar uma missão", lambda: accept_mission_action(user)),
        ("Abandonar uma missão em curso", lambda: abandon_mission_action(user)),
    ]
    run_menu("MISSÕES", options)


def show_missions(user):
    """Lista todas as missões com o estado."""
    character = character_service.get_character(user)
    print(_missions_table(missions.list_missions(character.id)))


def accept_mission_action(user):
    """Aceitar uma missão (custa energia)."""
    character = character_service.get_character(user)
    mission_list = missions.list_missions(character.id)
    print(_missions_table(mission_list))
    messages.print_info(
        f"\nAceitar uma missão custa {config.ENERGY_COST_MISSION} de energia "
        f"(tem {character.energy})."
    )

    mission = ask_list_choice("Número da missão a aceitar (0 para cancelar): ", mission_list)
    if mission is None:
        return
    accepted, completed = missions.accept_mission(character.id, mission.id)
    messages.print_success(f"Missão aceite: {accepted.name} - {accepted.objective_text}")
    messages.print_completed_missions(completed)


def abandon_mission_action(user):
    """Abandonar uma missão em curso (fica 'falhada')."""
    character = character_service.get_character(user)
    in_progress = [m for m in missions.list_missions(character.id)
                   if m.status == config.MISSION_IN_PROGRESS]
    if not in_progress:
        messages.print_info("Não tem missões em curso.")
        return

    print(_missions_table(in_progress))
    mission = ask_list_choice("Número da missão a abandonar (0 para cancelar): ", in_progress)
    if mission is None:
        return
    if ask_yes_no(f"Abandonar '{mission.name}'? O progresso perde-se"):
        missions.abandon_mission(character.id, mission.id)
        messages.print_success("Missão abandonada (ficou marcada como falhada).")


# ============================================================
# COMBATE
# ============================================================

_RESULT_TEXT = {
    combat.RESULT_WIN: "VITÓRIA!",
    combat.RESULT_LOSS: "DERROTA...",
    combat.RESULT_DRAW: "EMPATE (o combate demorou demasiado).",
}


def combat_menu(user):
    """Escolher um adversário e lutar."""
    character = character_service.get_character(user)
    odds = combat.list_enemies_with_odds(character.id)

    messages.print_title("ARENA")
    messages.print_info(
        f"Vida: {character.health}/{character.max_health}    "
        f"Energia: {character.energy} (cada combate custa {config.ENERGY_COST_COMBAT})"
    )
    rows = [
        [number, e.name, e.level, e.health, e.attack, e.defense,
         f"{e.reward_money} € + {e.reward_xp} XP", f"{chance * 100:.0f}%"]
        for number, (e, chance) in enumerate(odds, start=1)
    ]
    print()
    print(format_table(
        ["Nº", "Adversário", "Nível", "Vida", "Ataque", "Defesa", "Recompensa", "Prob. vitória"],
        rows,
    ))

    choice = ask_list_choice("Número do adversário (0 para cancelar): ", odds)
    if choice is None:
        return
    enemy, chance = choice

    if chance < 0.25 and not ask_yes_no(
        f"A probabilidade de vitória é só {chance * 100:.0f}%. Tem a certeza"
    ):
        return

    report = combat.fight(character.id, enemy.id)
    _show_combat_report(report)


def _show_combat_report(report):
    """Mostra o resultado de um combate."""
    if ask_yes_no("Ver o relato turno a turno"):
        print()
        for line in report.rounds:
            print(f"  {line}")

    messages.print_section(f"{_RESULT_TEXT[report.result]} (contra {report.enemy_name})")
    messages.print_info(f"Turnos: {report.turns}    Dano causado: {report.damage_dealt}    "
                        f"Dano sofrido: {report.damage_taken}")
    if report.xp_gained or report.money_gained:
        messages.print_success(f"Recebeu {report.xp_gained} XP e {format_money(report.money_gained)}.")
    if report.money_lost:
        messages.print_error(f"Perdeu {format_money(report.money_lost)}.")
    if report.levels_gained:
        messages.print_success(f"SUBIU DE NÍVEL! Agora é nível {report.new_level}.")
    messages.print_info(f"Vida restante: {report.health_left}")
    messages.print_completed_missions(report.completed_missions)


# ============================================================
# RANKING E HISTÓRICO
# ============================================================

def ranking_menu(user):
    """Mostra o ranking segundo um critério escolhido."""
    character = character_service.get_character(user)

    messages.print_title("RANKING")
    keys = list(ranking.CRITERIA)
    print("Ordenar por:")
    chosen_label = ask_choice("Critério: ", [ranking.CRITERIA[key] for key in keys])
    criterion = keys[[ranking.CRITERIA[key] for key in keys].index(chosen_label)]

    top = ranking.get_ranking(criterion)
    rows = [
        [p["position"], p["name"] + (" (você)" if p["character_id"] == character.id else ""),
         p["class"], p["level"], p["money"], p["wins"], p["missions_completed"]]
        for p in top
    ]
    print()
    print(format_table(["#", "Personagem", "Classe", "Nível", "Dinheiro", "Vitórias", "Missões"], rows))

    mine = ranking.get_my_position(character.id, criterion)
    if mine:
        messages.print_info(f"\nA sua posição: #{mine['position']}")


def history_menu(user):
    """Mostra as últimas ações do jogador."""
    limit = ask_int(
        f"Quantas entradas quer ver? (1-100, sugestão {config.HISTORY_DEFAULT_LIMIT}): ",
        minimum=1, maximum=100,
    )
    entries = history.get_user_history(user.id, limit)

    messages.print_title("HISTÓRICO")
    if not entries:
        messages.print_info("Ainda não há atividade registada.")
        return
    # As mais recentes vêm primeiro; mostramos por ordem cronológica
    for entry in reversed(entries):
        print(f"  {format_datetime(entry['created_at'])} — {entry['description']}")


# ============================================================
# CONTA
# ============================================================

def account_menu(user):
    """Alterar dados da conta."""
    options = [
        ("Alterar username", lambda: change_username_action(user)),
        ("Alterar password", lambda: change_password_action(user)),
    ]
    messages.print_info(f"Conta atual: {user.username}")
    run_menu("A MINHA CONTA", options)


def change_username_action(user):
    """Pede a password atual e o novo username."""
    new_username = ask_text("Novo username: ", validate_username)
    current_password = ask_password("Password atual (para confirmar): ")
    authentication.change_username(user, current_password, new_username)
    messages.print_success(f"Username alterado para {user.username}.")


def change_password_action(user):
    """Pede a password atual e a nova (duas vezes)."""
    current_password = ask_password("Password atual: ")
    new_password = ask_password("Nova password: ", validate_password)
    repeated = ask_password("Repita a nova password: ")
    if new_password != repeated:
        messages.print_error("As passwords não coincidem.")
        return
    authentication.change_password(user, current_password, new_password)
    messages.print_success("Password alterada com sucesso.")
