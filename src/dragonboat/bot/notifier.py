"""Telegram notifier — placeholder for now."""

from __future__ import annotations

from pathlib import Path


async def enviar_informe_telegram(texto: str, imagen_path: str | Path | None = None) -> bool:
    """Send a report to the configured Telegram chat.

    Currently a placeholder — prints to console.
    Returns True if sent successfully.
    """
    print("[TELEGRAM] Informe generado (envio deshabilitado):")
    print(texto[:200] + "..." if len(texto) > 200 else texto)
    if imagen_path:
        print(f"[TELEGRAM] Imagen: {imagen_path}")
    return True
