"""
Funções que ESCREVEM no ecrã: títulos, mensagens de sucesso/erro,
ficha da personagem, recibos, etc.

Ficam todas aqui para o aspeto do jogo ser consistente e para o resto do
código não estar cheio de print() repetidos.
"""

from utils.formatting import format_datetime, format_money

LINE_WIDTH = 60


def print_title(text):
    """Escreve um título grande, entre duas linhas de '='."""
    print()
    print("=" * LINE_WIDTH)
    print(text.center(LINE_WIDTH))
    print("=" * LINE_WIDTH)


def print_section(text):
    """Escreve um subtítulo."""
    print(f"\n--- {text} ---")


def print_success(text):
    """Mensagem de sucesso."""
    print(f"  [OK] {text}")


def print_error(text):
    """Mensagem de erro (legível, sem detalhes técnicos)."""
    print(f"  [ERRO] {text}")


def print_info(text):
    """Mensagem informativa."""
    print(f"  {text}")


def progress_bar(current, total, width=20):
    """
    Barra de progresso em texto. Ex.: progress_bar(30, 100, 10) -> '[###-------]'
    """
    total = max(total, 1)                       # evita dividir por zero
    filled = int(width * min(current, total) / total)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def print_character(character, attack_bonus=0, defense_bonus=0):
    """
    Mostra a ficha completa da personagem.
    Os bónus do equipamento aparecem entre parêntesis, ex.: Ataque: 12 (+4).
    """
    print_title(character.name)
    print_info(f"Classe: {character.character_class}    Nível: {character.level}")

    if character.is_max_level:
        print_info("Experiência: nível máximo atingido!")
    else:
        bar = progress_bar(character.experience, character.xp_to_next_level)
        print_info(f"Experiência: {bar} {character.experience}/{character.xp_to_next_level}")

    print_info(f"Vida: {character.health}/{character.max_health}    "
               f"Energia: {character.energy}")
    print_info(f"Dinheiro: {format_money(character.money)}")

    attack_text = f"{character.attack}" + (f" (+{attack_bonus})" if attack_bonus else "")
    defense_text = f"{character.defense}" + (f" (+{defense_bonus})" if defense_bonus else "")
    print_info(f"Ataque: {attack_text}    Defesa: {defense_text}    "
               f"Agilidade: {character.agility}")
    print_info(f"Vitórias: {character.wins}    Derrotas: {character.losses}")
    print_info(f"Criada em: {format_datetime(character.created_at)}")


def print_receipt(receipt):
    """Mostra o recibo de uma compra ou venda (igual ao exemplo do enunciado)."""
    verb = "comprou" if receipt.kind == "compra" else "vendeu"
    print_success(f"Jogador {verb}: {receipt.item_name} (x{receipt.quantity})")
    print_info(f"Preço unitário: {format_money(receipt.unit_price)}")
    print_info(f"Total: {format_money(receipt.total)}")
    print_info(f"Saldo anterior: {format_money(receipt.balance_before)}")
    print_info(f"Saldo atual: {format_money(receipt.balance_after)}")


def print_completed_missions(completed_missions):
    """Anuncia as missões que acabaram de ser concluídas."""
    for mission in completed_missions:
        print_success(
            f"MISSÃO CONCLUÍDA: {mission.name}! "
            f"Recompensa: {format_money(mission.reward_money)} e {mission.reward_xp} XP."
        )
        if mission.levels_gained:
            print_success("A recompensa fez-o(a) subir de nível!")
