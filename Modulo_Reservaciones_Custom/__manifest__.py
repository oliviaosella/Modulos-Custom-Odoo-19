# -*- coding: utf-8 -*-
# Copyright 2025 Xindra
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
{
    'name': 'Modulo reservaciones personalizado',
    'summary': 'Líneas independientes por reserva y acceso directo a orden de venta',
    'description': """
Hotel Planning Custom
=====================

1. Reemplaza action_add_last_order para crear siempre una línea
   independiente por reserva en lugar de acumular cantidad.

2. Agrega botón "Ver Orden de Venta" en el popover del Gantt
   (el tooltip que aparece al hacer clic sobre una reserva),
   para acceder directamente a la orden sin usar el link interno.
   Requiere exponer sale_order_id en el arch de la vista Gantt,
   ya que la vista base no lo declara.
    """,
    'version': '19.0.1.2.0',
    'category': 'Hidden',
    'author': 'Olivia - Xindra',
    'license': 'LGPL-3',

    'depends': [
        'sale_renting_planning',
        'sale_planning',
    ],

    'data': [
        'security/ir_model_access.xml',
        'views/planning_slot_gantt_views.xml',
    ],

    'assets': {
        'web.assets_backend_lazy': [
            'hotel_planning_custom/static/src/views/planning_gantt/planning_gantt_popover_patch.js',
        ],
    },

    'installable': True,
    'auto_install': False,
    'application': False,
}