# -*- coding: utf-8 -*-
# Copyright 2026 Xindra
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models, fields


class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    # Campos "espejo" del saldo/estado de pago calculado en sale.order,
    # para poder mostrarlos directamente en el popover del Gantt de
    # Planificación sin tener que entrar a la orden de venta.
    x_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='sale_order_id.currency_id',
    )
    x_saldo_pendiente = fields.Monetary(
        string='Saldo pendiente',
        related='sale_order_id.x_saldo_pendiente',
        currency_field='x_currency_id',
    )
    x_estado_pago = fields.Selection(
        related='sale_order_id.x_estado_pago',
        string='Estado de pago',
    )
