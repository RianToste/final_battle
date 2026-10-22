"""
Funções para apresentar dados de forma legível ao jogador:
dinheiro, datas e tabelas de texto.
"""

from datetime import datetime


def format_money(amount):
    return f"{amount} €"


def format_datetime(date_text):
    """
    Converte a data da base de dados ('2026-09-21 10:32:05')
    para o formato português ('21/09/2026 10:32').
    Se o formato for inesperado, devolve o texto original.
    """
    if not date_text:
        return "-"
    try:
        parsed = datetime.strptime(date_text, "%Y-%m-%d %H:%M:%S")
        return parsed.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(date_text)


def format_table(headers, rows):
    """
    Constrói uma tabela de texto alinhada.

    - headers: lista com os títulos das colunas
    - rows: lista de linhas (cada linha é uma lista de valores)

    Devolve uma string pronta a imprimir.
    """
    if not rows:
        return "(sem dados)"

    # Converte tudo para texto
    text_rows = [[str(cell) for cell in row] for row in rows]

    # A largura de cada coluna é a do maior texto (título ou valor)
    widths = [len(header) for header in headers]
    for row in text_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def build_line(cells):
        # ljust preenche com espaços à direita até atingir a largura
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    separator = "-+-".join("-" * width for width in widths)

    lines = [build_line(headers), separator]
    lines.extend(build_line(row) for row in text_rows)
    return "\n".join(lines)