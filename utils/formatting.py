#!/usr/bin/env python3
# utils/formatting.py - Formatting utilities for hicloud

import shutil
from typing import List, Dict, Any

from utils.colors import TABLE_HEADER_COLOR, TABLE_ROW_COLOR, PROMPT_TEXT_COLOR, ANSI_RESET

def format_size(size_gb: float) -> str:
    """Format size in GB or MB with 2 decimal places"""
    if size_gb >= 1:
        return f"{size_gb:.2f} GB"
    else:
        return f"{size_gb * 1024:.2f} MB"

def get_terminal_width() -> int:
    """Get the width of the terminal"""
    try:
        # Versuchen, die Terminalbreite zu ermitteln
        columns, _ = shutil.get_terminal_size()
        # Einen sinnvollen Standardwert zurückgeben, falls die Breite sehr klein ist
        return max(columns, 80)
    except Exception:
        # Fallback, wenn die Terminalbreite nicht ermittelt werden kann
        return 80

def horizontal_line(char="=") -> str:
    """Returns a horizontal line across the entire terminal width"""
    return char * get_terminal_width()

def create_table_layout(headers: List[str], rows: List[List[Any]], padding: int = 2) -> Dict:
    """
    Creates a table layout with dynamically sized columns based on content
    
    Args:
        headers: List of column headers
        rows: List of rows, each row being a list of column values
        padding: Padding between columns
        
    Returns:
        Dict with column widths and format string
    """
    # Bestimme die maximale Breite jeder Spalte
    column_widths = []
    for i, header in enumerate(headers):
        # Berücksichtige die Header-Breite
        max_width = len(str(header))
        
        # Finde die maximale Breite für jede Spalte in den Daten
        for row in rows:
            if i < len(row):  # Stelle sicher, dass der Index in Reichweite ist
                cell_width = len(str(row[i]))
                max_width = max(max_width, cell_width)
        
        # Füge Spaltenbreite hinzu (plus Padding)
        column_widths.append(max_width + padding)
    
    # Bestimme die gesamte Tabellenbreite
    total_width = sum(column_widths)
    
    # Wenn die Tabelle breiter als das Terminal ist, passe die Spaltenbreiten proportional an
    terminal_width = get_terminal_width()
    if total_width > terminal_width:
        # Berechne den Skalierungsfaktor
        scale_factor = (terminal_width - len(headers) * padding) / (total_width - len(headers) * padding)
        
        # Skaliere jede Spaltenbreite, aber stelle sicher, dass sie mindestens die Header-Breite hat
        new_column_widths = []
        for i, width in enumerate(column_widths):
            # Minimum ist Header-Breite + 1 Padding
            min_width = len(str(headers[i])) + padding
            # Skalierte Breite, aber mindestens min_width
            scaled_width = max(int(width * scale_factor), min_width)
            new_column_widths.append(scaled_width)
            
        column_widths = new_column_widths
        total_width = sum(column_widths)
    
    # Erstelle das Format für die Tabellenzeile
    format_str = ""
    for i, width in enumerate(column_widths):
        format_str += f"{{:{width}}}"
    
    return {
        "column_widths": column_widths,
        "format_str": format_str,
        "total_width": total_width
    }

def print_table(headers: List[str], rows: List[List[Any]], title: str = None) -> None:
    """
    Prints a nicely formatted table with headers and rows
    
    Args:
        headers: List of column headers
        rows: List of rows, each row being a list of column values
        title: Optional title for the table
    """
    if not rows:
        if title:
            print(f"\n{title}:")
        print("No data found")
        return
    
    # Erstelle das Tabellen-Layout
    layout = create_table_layout(headers, rows)
    format_str = layout["format_str"]
    total_width = layout["total_width"]
    
    # Zeige Titel an, falls vorhanden
    if title:
        print(f"\n{title}:")
        print()  # Blank line between the title and the table body
    
    # Zeige Header in gelber Schrift an
    header_line = format_str.format(*headers)
    print(f"{TABLE_HEADER_COLOR}{header_line}{ANSI_RESET}")
    
    # Zeige Trennlinie in Prompt-Farbe an
    separator = horizontal_line("-")[:total_width]
    print(f"{PROMPT_TEXT_COLOR}{separator}{ANSI_RESET}")
    
    # Zeige Daten an
    for row in rows:
        # Stelle sicher, dass die Zeile die richtige Länge hat
        padded_row = row + [""] * (len(headers) - len(row))
        # Wandle alle Werte in Strings um
        str_row = [str(cell) for cell in padded_row]
        row_line = format_str.format(*str_row[:len(headers)])
        print(f"{TABLE_ROW_COLOR}{row_line}{ANSI_RESET}")
