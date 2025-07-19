# Author: Julien Coux
# Copyright 2016 Camptocamp SA
# Copyright 2021 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, models

class TrialBalanceXslx(models.AbstractModel):
    _name = "report.a_f_r.report_trial_balance_xlsx"
    _description = "Trial Balance XLSX Report"
    _inherit = "report.account_financial_report.abstract_report_xlsx"

    def _get_report_name(self, report, data=False):
        company_id = data.get("company_id", False)
        report_name = _("Trial Balance")
        if company_id:
            company = self.env["res.company"].browse(company_id)
            suffix = f" - {company.name} - {company.currency_id.name}"
            report_name = report_name + suffix
        return report_name

    def _get_report_columns(self, report):
        columns = []
        if not report.show_partner_details:
            columns.extend([
                {"header": _("Code"), "field": "code", "width": 10},
                {"header": _("Account"), "field": "name", "width": 60},
                {"header": _("Initial balance"), "field": "initial_balance", "type": "amount", "width": 14},
                {"header": _("Debit"), "field": "debit", "type": "amount", "width": 14},
                {"header": _("Credit"), "field": "credit", "type": "amount", "width": 14},
                {"header": _("Ending balance"), "field": "ending_balance", "type": "amount", "width": 14},
            ])
            if report.foreign_currency:
                columns.extend([
                    {"header": _("Moneda"), "field": "currency_id.symbol", "type": "string", "width": 7},
                    {"header": _("Ending balance"), "field": "ending_currency_balance", "type": "amount_currency", "width": 14},
                ])
        else:
            columns.extend([
                {"header": _("Partner"), "field": "name", "width": 70},
                {"header": _("Initial balance"), "field": "initial_balance", "type": "amount", "width": 14},
                {"header": _("Debit"), "field": "debit", "type": "amount", "width": 14},
                {"header": _("Credit"), "field": "credit", "type": "amount", "width": 14},
                {"header": _("Ending balance"), "field": "ending_balance", "type": "amount", "width": 14},
            ])
            if report.foreign_currency:
                columns.extend([
                    {"header": _("Moneda"), "field": "currency_id.symbol", "type": "string", "width": 7},
                    {"header": _("Ending balance"), "field": "ending_currency_balance", "type": "amount_currency", "width": 14},
                ])
        return {index: col for index, col in enumerate(columns)}

    def _get_report_filters(self, report):
        return [
            [_("Date range filter"), _("From: %(date_from)s To: %(date_to)s") % {"date_from": report.date_from, "date_to": report.date_to}],
            [_("Target moves filter"), _("All posted entries") if report.target_move == "posted" else _("All entries")],
            [_("Account at 0 filter"), _("Hide") if report.hide_account_at_0 else _("Show")],
            [_("Show foreign currency"), _("Yes") if report.foreign_currency else _("No")],
            [_("Limit hierarchy levels"), _("Level %s") % report.show_hierarchy_level if report.limit_hierarchy_level else _("No limit")],
        ]

    def _get_col_count_filter_name(self):
        return 2

    def _get_col_count_filter_value(self):
        return 3

    def _generate_report_content(self, workbook, report, data, report_data):
        res_data = self.env["report.account_financial_report.trial_balance"]._get_report_values(report, data)
        trial_balance = res_data["trial_balance"]
        trial_balance_grouped = res_data["trial_balance_grouped"]
        total_amount = res_data["total_amount"]
        total_amount_grouped = res_data["total_amount_grouped"]
        partners_data = res_data["partners_data"]
        accounts_data = res_data["accounts_data"]
        show_hierarchy = res_data["show_hierarchy"]
        show_partner_details = res_data["show_partner_details"]
        show_hierarchy_level = res_data["show_hierarchy_level"]
        foreign_currency = res_data["foreign_currency"]
        limit_hierarchy_level = res_data["limit_hierarchy_level"]
        hide_parent_hierarchy_level = res_data["hide_parent_hierarchy_level"]
        grouped_by = res_data["grouped_by"]

        # Inyectar manual balances para 330101 y 3401
        manual_values = data.get("manual_balances", {})

        if not show_partner_details:
            if grouped_by:
                for grouped_item in trial_balance_grouped:
                    self.write_array_title(grouped_item["name"], report_data)
                    self.write_array_header(report_data)
                    for balance in grouped_item["account_data"]:
                        self.write_line_from_dict(balance, report_data)
                    grouped_item["code"] = ""
                    grouped_item["currency_id"] = False
                    self.write_account_footer(grouped_item, _("Total"), report_data)
                    report_data["row_pos"] += 1
                total_amount_grouped["currency_id"] = False
                total_amount_grouped["code"] = ""
                self.write_account_footer(total_amount_grouped, _("TOTAL"), report_data)
            else:
                self.write_array_header(report_data)

                # Acumuladores solo para cuentas de capital (grupo 3)
                capital_accumulators = {}

                for balance in trial_balance:
                    account_id = balance.get('id')
                    account_code = balance.get('code')

                    if not account_code:
                        continue

                    # Mostrar símbolo de moneda si no está
                    if account_id and accounts_data.get(account_id):
                        if not balance.get('currency_id.symbol') and accounts_data[account_id].get(
                            'currency_id.symbol'):
                            balance['currency_id.symbol'] = accounts_data[account_id]['currency_id.symbol']

                    # Inyección manual si aplica
                    if account_code in manual_values:
                        manual = manual_values[account_code]
                        for key in ["initial_balance", "debit", "credit", "ending_balance"]:
                            if key in manual:
                                balance[key] = manual[key]

                    # Solo acumular para cuentas específicas
                    accumulate_to = {
                        "3": ["330101", "3401", "310101"],  # si quieres incluir 310101 también
                        "3301": ["330101"],
                        "34": ["3401"],
                    }

                    for parent_code, child_codes in accumulate_to.items():
                        if account_code in child_codes:
                            if parent_code not in capital_accumulators:
                                capital_accumulators[parent_code] = {
                                    "initial_balance": 0.0,
                                    "debit": 0.0,
                                    "credit": 0.0,
                                    "ending_balance": 0.0,
                                }
                            for key in ["initial_balance", "debit", "credit", "ending_balance"]:
                                capital_accumulators[parent_code][key] += balance.get(key, 0.0)

                # Aplicar acumulados a cuentas de capital (solo grupo 3)
                for balance in trial_balance:
                    account_code = balance.get("code")
                    if account_code in capital_accumulators:
                        for key in ["initial_balance", "debit", "credit", "ending_balance"]:
                            balance[key] = capital_accumulators[account_code][key]

                # Escribir líneas del reporte
                for balance in trial_balance:
                    if show_hierarchy and limit_hierarchy_level:
                        if show_hierarchy_level > balance["level"] and (
                            not hide_parent_hierarchy_level or (show_hierarchy_level - 1) == balance["level"]
                        ):
                            self.write_line_from_dict(balance, report_data)
                    else:
                        self.write_line_from_dict(balance, report_data)
        else:
            for account_id in total_amount:
                self.write_array_title(
                    accounts_data[account_id]["code"] + "- " + accounts_data[account_id]["name"],
                    report_data,
                )
                self.write_array_header(report_data)
                for partner_id in total_amount[account_id]:
                    if isinstance(partner_id, int):
                        self.write_line_from_dict_order(
                            total_amount[account_id][partner_id],
                            partners_data[partner_id],
                            report_data,
                        )
                accounts_data[account_id].update({
                    "initial_balance": total_amount[account_id]["initial_balance"],
                    "credit": total_amount[account_id]["credit"],
                    "debit": total_amount[account_id]["debit"],
                    "balance": total_amount[account_id]["balance"],
                    "ending_balance": total_amount[account_id]["ending_balance"],
                })
                if foreign_currency:
                    accounts_data[account_id].update({
                        "initial_currency_balance": total_amount[account_id]["initial_currency_balance"],
                        "ending_currency_balance": total_amount[account_id]["ending_currency_balance"],
                    })
                self.write_account_footer(
                    accounts_data[account_id],
                    accounts_data[account_id]["code"] + "- " + accounts_data[account_id]["name"],
                    report_data,
                )
                report_data["row_pos"] += 2

    def _prepare_currency_symbol(self, balance):
        currency_id = balance.get("currency_id")
        if isinstance(currency_id, (list, tuple)) and currency_id:
            currency = self.env["res.currency"].browse(currency_id[0])
            balance["currency_id.symbol"] = currency.symbol or ""
        elif isinstance(currency_id, int) and currency_id:
            currency = self.env["res.currency"].browse(currency_id)
            balance["currency_id.symbol"] = currency.symbol or ""
        else:
            balance["currency_id.symbol"] = ""

    def write_line_from_dict_order(self, total_amount, partner_data, report_data):
        total_amount.update({
            "name": str(partner_data["name"]),
        })
        self._prepare_currency_symbol(total_amount)
        self.write_line_from_dict(total_amount, report_data)

    def write_line(self, line_object, type_object, report_data):
        if type_object == "partner":
            line_object.currency_id = line_object.report_account_id.currency_id
        elif type_object == "account":
            line_object.currency_id = line_object.currency_id
        return super().write_line(line_object, report_data)

    def write_account_footer(self, account, name_value, report_data):
        format_amt = self._get_currency_amt_header_format_dict(account, report_data)
        for col_pos, column in report_data["columns"].items():
            if column["field"] == "name":
                value = name_value
            else:
                value = account[column["field"]]
            cell_type = column.get("type", "string")
            if cell_type == "string":
                report_data["sheet"].write_string(
                    report_data["row_pos"],
                    col_pos,
                    value or "",
                    report_data["formats"]["format_header_left"],
                )
            elif cell_type == "amount":
                report_data["sheet"].write_number(
                    report_data["row_pos"],
                    col_pos,
                    float(value),
                    report_data["formats"]["format_header_amount"],
                )
            elif cell_type == "many2one" and account["currency_id"]:
                report_data["sheet"].write_string(
                    report_data["row_pos"],
                    col_pos,
                    value.name or "",
                    report_data["formats"]["format_header_right"],
                )
            elif cell_type == "amount_currency" and account["currency_id"]:
                report_data["sheet"].write_number(
                    report_data["row_pos"], col_pos, float(value), format_amt
                )
            else:
                report_data["sheet"].write_string(
                    report_data["row_pos"],
                    col_pos,
                    "",
                    report_data["formats"]["format_header_right"],
                )
        report_data["row_pos"] += 1
