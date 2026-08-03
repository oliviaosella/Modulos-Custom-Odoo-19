{
    'name': 'Limpieza de Datos (SaviaTech)',
    'version': '19.0.4.0.0',
    'author': 'Xindra Group / SaviaTech',
    'category': 'Tools',
    'summary': 'Limpieza de datos transaccionales preservando la configuración '
               '(sin tocar el plan de cuentas) y con borrado en cascada de '
               'registros huérfanos de mensajería/adjuntos.',
    'description': """
Limpieza de Datos (SaviaTech)
=============================

Deja una base lista para producción borrando los datos transaccionales
(ventas, compras, POS, inventario, facturas, etc.) y preservando la
configuración.

Diferencias respecto de om_data_remove (Odoo Mates), del cual deriva:

* NO incluye "Limpiar y resetear plan de cuentas": se preserva el plan de
  cuentas, diarios e impuestos (localización argentina, retenciones, etc.).
* Para cada modelo borrado limpia en cascada los registros huérfanos en
  mail_message, mail_followers, mail_activity e ir_attachment, de modo que
  no queden filas apuntando a registros inexistentes.
* Interfaz en español.
""",
    'maintainer': 'Xindra Group / SaviaTech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'views/view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'svt_limpieza_datos/static/src/css/style.css',
        ],
    },
    'images': ['static/description/banner.png'],
    'application': False,
    'installable': True,
}
