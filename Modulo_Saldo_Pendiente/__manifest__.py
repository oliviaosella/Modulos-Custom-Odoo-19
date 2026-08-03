# -*- coding: utf-8 -*-
# Copyright 2026 Xindra
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
{
    'name': 'Reservaciones - Saldo Pendiente',
    'summary': 'Semáforo de saldo pendiente de cobro (rojo/amarillo/verde) '
               'en el popover del Gantt de reservas y en la Orden de venta.',
    'description': """
Reservaciones - Saldo Pendiente
================================

Agrega, sin modificar otros módulos:

1. sale.order: campos calculados x_monto_pagado, x_saldo_pendiente y
   x_estado_pago (no_pagado / parcial / pagado), en base a las facturas
   validadas de la orden (incluye anticipos/down payments).

2. planning.slot: los mismos campos, relacionados a la orden de venta
   vinculada (sale_order_id), para poder mostrarlos en el popover del
   Gantt de Planificación.

3. Vista kanban (planning.planning_view_kanban_inherit): el popover del
   Gantt arma su cuerpo con esta vista kanban (es su kanban_view_id, ver
   planning/views/planning_views.xml). Ahí agregamos x_estado_pago como
   badge chico justo al lado del badge de estado "Publicado", y
   x_saldo_pendiente como texto chico cuando corresponda. No hace falta
   JS: el popover del Gantt no es más que un render kanban.

4. Orden de venta: mismo semáforo como campo chico (badge + monto),
   ubicado junto a Duración en el header, sin alterar el resto del
   layout del formulario.

Estados:
- Rojo (a pagar): no se registró ningún cobro, ni el anticipo.
- Amarillo (saldo pendiente): se cobró un anticipo pero falta el resto.
- Verde (pagado): no queda saldo pendiente.
    """,
    'version': '19.0.1.2.0',
    'category': 'Hidden',
    'author': 'Olivia - Xindra',
    'license': 'LGPL-3',

    'depends': ['sale_planning'],

    'data': [
        'views/planning_slot_kanban_views.xml',
        'views/sale_order_views.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': False,
}
