# -*- coding: utf-8 -*-
# Copyright 2026 Xindra
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_monto_pagado = fields.Monetary(
        string='Monto pagado',
        compute='_compute_x_saldo_pendiente',
        currency_field='currency_id',
        help='Total efectivamente cobrado (incluye anticipos/down payments) '
             'según las facturas validadas de esta orden.',
    )
    x_saldo_pendiente = fields.Monetary(
        string='Saldo pendiente',
        compute='_compute_x_saldo_pendiente',
        currency_field='currency_id',
        help='Total de la reserva menos lo ya cobrado. 0 si está totalmente pagada.',
    )
    x_estado_pago = fields.Selection(
        [
            ('no_pagado', 'A pagar'),
            ('parcial', 'Saldo pendiente'),
            ('pagado', 'Pagado'),
        ],
        string='Estado de pago',
        compute='_compute_x_saldo_pendiente',
    )

    @api.depends(
        'amount_total',
        'currency_id',
        'invoice_ids',
        'invoice_ids.state',
        'invoice_ids.move_type',
        'invoice_ids.amount_total_signed',
        'invoice_ids.amount_residual_signed',
    )
    def _compute_x_saldo_pendiente(self):
        for order in self:
            posted_invoices = order.invoice_ids.filtered(
                lambda m: m.state == 'posted' and m.move_type in ('out_invoice', 'out_refund')
            )
            monto_pagado = sum(
                (inv.amount_total_signed - inv.amount_residual_signed) for inv in posted_invoices
            )
            # Defensivo: diferencias de redondeo no deberían dar montos negativos.
            monto_pagado = max(monto_pagado, 0.0)
            saldo_pendiente = max(order.amount_total - monto_pagado, 0.0)

            order.x_monto_pagado = monto_pagado
            order.x_saldo_pendiente = saldo_pendiente

            precision = order.currency_id.rounding if order.currency_id else 0.01
            if order.amount_total <= 0 or saldo_pendiente <= precision:
                order.x_estado_pago = 'pagado'
            elif monto_pagado <= precision:
                order.x_estado_pago = 'no_pagado'
            else:
                order.x_estado_pago = 'parcial'
