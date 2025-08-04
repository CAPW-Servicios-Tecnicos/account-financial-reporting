from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """Carga datos de noupdate_changes.xml sin usar openupgradelib"""
    env = api.Environment(cr, SUPERUSER_ID, {})

    try:
        # Usamos el método estándar para cargar datos XML
        env['ir.module.module'].load_xml(
            'mis_builder_cash_flow',
            ['migrations/16.0.1.0.0/noupdate_changes.xml']
        )
        _logger.info("Datos de noupdate_changes.xml cargados correctamente durante la migración.")
    except Exception as e:
        _logger.error("Error al cargar noupdate_changes.xml durante la migración: %s", str(e))
