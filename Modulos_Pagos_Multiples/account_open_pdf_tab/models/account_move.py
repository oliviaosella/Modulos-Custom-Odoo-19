from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_print_pdf(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/report/pdf/account.report_invoice/{self.id}",
            "target": "new",
        }
