"""Backfill the new sectores_detalle and paladas_detalle columns for
pre-existing rows in test_metrics.

Reads from:
  - tiempos_por_distancia (already populated) -> sectores_detalle
  - segment_gps_json (already populated) -> paladas_detalle (embedded list)

Idempotent: rows that already have sectores_detalle / paladas_detalle
non-null are skipped.

Usage:
    python -m dragonboat.tools.backfill_sectores_paladas
"""
from __future__ import annotations

import json

from dragonboat.analysis import calcular_sectores
from dragonboat.database import get_session, init_db
from dragonboat.db_models import TestMetric, Distancia


def _extract_paladas(segment_gps_json: str | None) -> list[float] | None:
    if not segment_gps_json:
        return None
    try:
        data = json.loads(segment_gps_json)
    except (ValueError, TypeError):
        return None
    paladas = data.get("dist_por_palada")
    if isinstance(paladas, list):
        return [float(x) for x in paladas]
    return None


def _build_sectores(tpd_str: str | None, distancia_metros: int) -> list[dict] | None:
    if not tpd_str or not distancia_metros:
        return None
    try:
        tpd = json.loads(tpd_str)
    except (ValueError, TypeError):
        return None
    return calcular_sectores(tpd, distancia_metros)


def run() -> dict:
    """Run the backfill. Returns counts of updated / skipped rows."""
    init_db()
    updated = 0
    skipped = 0
    failed = 0

    with get_session() as s:
        rows = (
            s.query(TestMetric)
            .all()
        )
        for tm in rows:
            try:
                need_sect = not tm.sectores_detalle
                need_pal = not tm.paladas_detalle
                if not need_sect and not need_pal:
                    skipped += 1
                    continue

                if need_sect and tm.tiempos_por_distancia and tm.distancia:
                    sectores = _build_sectores(
                        tm.tiempos_por_distancia, tm.distancia.metros
                    )
                    if sectores is not None:
                        tm.sectores_detalle = json.dumps(sectores, ensure_ascii=False)

                if need_pal and tm.segment_gps_json:
                    paladas = _extract_paladas(tm.segment_gps_json)
                    if paladas is not None:
                        tm.paladas_detalle = json.dumps(paladas, ensure_ascii=False)

                s.flush()
                updated += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"[WARN] id={tm.id} backfill failed: {exc}")
        s.commit()

    return {"updated": updated, "skipped": skipped, "failed": failed}


if __name__ == "__main__":
    result = run()
    print(f"Backfill done: {result}")
