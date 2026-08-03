# -*- coding: utf-8 -*-
# Copyright 2025 Xindra
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id', 'planning_slot_ids')
    def _compute_is_rental(self):
        """
        Override de _compute_is_rental para preservar is_rental=True en líneas
        que tienen planning slots vinculados (reservas de hotel creadas por este módulo).

        Problema original:
          _compute_is_rental (sale_renting) calcula:
            is_rental = is_product_rentable AND context.get('in_rental_app')
          Cuando el usuario edita la variante del producto desde una orden de venta,
          el contexto no tiene 'in_rental_app', por lo que is_rental queda False.
          Esto hace que:
            1. La descripción de la línea pierda las fechas (depende de is_rental).
            2. La línea desaparezca del wizard de recolección/devolución.

        Solución:
          Para líneas con planning_slot_ids, forzamos is_rental=True siempre,
          independientemente del contexto. Esto arregla tanto el display durante
          la edición (onchange) como el valor persistido al guardar.
        """
        # Separar líneas con slots (siempre deben ser rental) del resto
        lines_with_slots = self.filtered(lambda l: l._origin.planning_slot_ids)
        lines_without_slots = self - lines_with_slots

        # Ejecutar compute estándar solo en las líneas sin slots
        if lines_without_slots:
            super(SaleOrderLine, lines_without_slots)._compute_is_rental()

        # Para las líneas con slots, is_rental siempre es True
        for line in lines_with_slots:
            line.is_rental = True

    def write(self, vals):
        """
        Respaldo adicional: restaura is_rental=True al guardar, por si acaso
        el compute no alcanza a correr con planning_slot_ids disponibles.
        """
        lines_to_fix = self.env['sale.order.line']
        if 'product_id' in vals:
            lines_to_fix = self.filtered(lambda l: l.is_rental and l.planning_slot_ids)

        result = super().write(vals)

        if lines_to_fix:
            super(SaleOrderLine, lines_to_fix).write({'is_rental': True})

        return result
