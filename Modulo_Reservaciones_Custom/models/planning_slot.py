# -*- coding: utf-8 -*-
# Copyright 2025 Xindra
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class PlanningSlot(models.Model):
    _inherit = 'planning.slot'

    def action_add_last_order(self):
        """
        Override de action_add_last_order (sale_renting_planning).

        PROBLEMA DEL MÉTODO ENTERPRISE ORIGINAL:
          1. Busca si ya existe una sale.order.line con el mismo producto
             y planning_hours_to_plan == 0 → reutiliza esa línea.
          2. Al final llama a update_product_uom_qty() que SUMA las horas
             de todos los slots vinculados a esa línea → multiplica cantidad.

        SOLUCIÓN:
          Siempre creamos una línea nueva e independiente (nunca reutilizamos).
          Vinculamos el slot a esa línea nueva via sale_line_id y planning_slot_ids
          para que la vista de planificación refleje el vínculo correctamente.
          Usamos la misma lógica de búsqueda de producto que el enterprise
          (role_id.product_ids.filtered('rent_ok')) para consistencia.
        """
        self.ensure_one()

        # ── Validación de conflictos (igual que el enterprise) ──────────────
        if self.overlap_slot_count:
            raise ValidationError(self.env._(
                'The shift should not be in conflict to be able to correctly '
                'add it to an existing rental order.'
            ))

        # ── Buscar la última orden de alquiler en borrador ──────────────────
        # Usamos 'draft' en lugar de 'sale' (el enterprise filtra 'sale')
        # porque queremos poder modificar líneas antes de confirmar.
        last_order = self.env['sale.order'].search(
            [
                ('is_rental_order', '=', True),
                ('state', '=', 'draft'),
            ],
            order='id desc',
            limit=1,
        )

        if not last_order:
            raise UserError(self.env._(
                'No se encontró ninguna orden de alquiler en borrador. '
                'Cree o reactiva una orden antes de continuar.'
            ))

        # ── Obtener el producto del rol (igual que el enterprise) ───────────
        products = self.role_id.product_ids.filtered('rent_ok')
        product = products[:1]

        if not product:
            raise UserError(self.env._(
                'El rol "%s" no tiene ningún producto de alquiler configurado. '
                'Verifique la configuración del rol en Planificación.',
                self.role_id.display_name,
            ))

        # ── Calcular cantidad ───────────────────────────────────────────────
        # Usamos x_nights si existe, sino fallback a allocated_hours (enterprise)
        uom_hour = self.env.ref('uom.product_uom_hour')
        if hasattr(last_order, 'x_nights') and last_order.x_nights:
            qty = last_order.x_nights
        elif product.uom_id == uom_hour:
            qty = self.allocated_hours
        else:
            qty = 1

        # ── Crear SIEMPRE una línea nueva (NUNCA reutilizar existente) ──────
        # Inyectamos las fechas en contexto para evitar el AssertionError
        # de sale_planning que require default_start/end_datetime.
        new_line = self.env['sale.order.line'].with_context(
            planning_slot_generation=False,
            default_start_datetime=self.start_datetime,
            default_end_datetime=self.end_datetime,
        ).create({
            'order_id': last_order.id,
            'product_id': product.product_variant_id.id,
            'is_rental': True,
            'product_uom_qty': qty,
            'planning_slot_ids': [self.id],   # vincula este slot a la línea nueva
        })

        # ── Vincular el slot a la nueva línea y publicarlo ──────────────────
        self.write({
            'sale_line_id': new_line.id,
            'state': 'published',
        })

        # ── Asignar recurso si el slot no tiene uno ─────────────────────────
        if not self.resource_id:
            try:
                self._set_slot_resource()
            except ValidationError:
                # Si no hay recurso disponible, continuamos sin bloquear.
                # El usuario puede asignarlo manualmente desde la vista.
                pass

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': self.env._('Reserva agregada como línea independiente en la orden'),
            },
        }