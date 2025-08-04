# Copyright 2024 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref('mis_builder_cash_flow.noupdate_changes', False)
    env['ir.model.data']._load_xml_files(
        'mis_builder_cash_flow', ['migrations/16.0.1.0.0/noupdate_changes.xml']
    )