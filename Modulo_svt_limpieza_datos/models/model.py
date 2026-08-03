import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Tablas satélite que quedan con huérfanos cuando se borra un modelo por SQL
    # crudo (sin unlink). Se listan como (tabla, columna_de_modelo). Todas ellas
    # tienen además la columna res_id.
    _SVT_ORPHAN_TABLES = [
        ('mail_message', 'model'),
        ('mail_followers', 'res_model'),
        ('mail_activity', 'res_model'),
        ('ir_attachment', 'res_model'),
    ]

    def _svt_remove_orphans(self, model_name, table_name):
        """Elimina los registros huérfanos de las tablas satélite
        (mail_message, mail_followers, mail_activity, ir_attachment) que
        apuntan a ``model_name`` pero cuyo ``res_id`` ya no existe en la tabla
        principal ``table_name``.

        Como el borrado principal vacía la tabla, en la práctica se eliminan
        todas las filas satélite de ese modelo; el filtro ``NOT IN`` deja
        intacto cualquier registro que todavía exista (borrados parciales) y
        los registros sin ``res_id`` (mensajes no asociados a un registro).

        ``table_name`` proviene de ``_table`` del modelo, no de input del
        usuario, por lo que es seguro interpolarlo en el SQL. ``model_name`` se
        pasa siempre como parámetro.
        """
        for sat_table, model_col in self._SVT_ORPHAN_TABLES:
            sql = """
                DELETE FROM {sat}
                 WHERE {col} = %s
                   AND res_id IS NOT NULL
                   AND res_id NOT IN (SELECT id FROM {main})
            """.format(sat=sat_table, col=model_col, main=table_name)
            try:
                # Savepoint para que un fallo en una tabla satélite (p. ej. que
                # no exista) no aborte la transacción del borrado principal.
                with self._cr.savepoint():
                    self._cr.execute(sql, (model_name,))
            except Exception as e:
                _logger.warning(
                    'limpieza en cascada de huérfanos falló en %s para %s: %s',
                    sat_table, model_name, e)

    def _remove_data(self, o, s=[]):
        if not self.env.user.has_group('base.group_system'):
            return False
        for line in o:
            try:
                if not self.env['ir.model']._get(line):
                    continue
            except Exception as e:
                _logger.warning('remove data error get ir.model: %s,%s', line, e)
                continue
            obj_name = line
            obj = self.pool.get(obj_name)
            if not obj:
                t_name = obj_name.replace('.', '_')
            else:
                t_name = obj._table
            sql = "delete from %s" % t_name
            try:
                # Savepoint alrededor del DELETE principal + cascada: si un modelo
                # puntual falla (p. ej. un abstracto sin tabla, o un FK), se hace
                # rollback SOLO de ese modelo y la transacción sigue viva, de modo
                # que los modelos siguientes de la cadena se borran igual.
                with self._cr.savepoint():
                    self._cr.execute(sql)
                    # Limpieza en cascada de huérfanos del modelo recién borrado.
                    self._svt_remove_orphans(obj_name, t_name)
                self._cr.commit()
            except Exception as e:
                _logger.warning('remove data error: %s,%s', line, e)
        for line in s:
            domain = ['|', ('code', '=ilike', line + '%'), ('prefix', '=ilike', line + '%')]
            try:
                seqs = self.env['ir.sequence'].sudo().search(domain)
                if seqs.exists():
                    seqs.write({
                        'number_next': 1,
                    })
            except Exception as e:
                _logger.warning('reset sequence data error: %s,%s', line, e)
        return True

    def _svt_model_installed(self, model_name):
        """True si ``model_name`` existe en esta base (el módulo que lo
        define está instalado). Permite que la lógica específica de
        Reservaciones (booking_engine) sea un no-op seguro en cualquier
        otro proyecto donde ese módulo no exista."""
        try:
            return bool(self.env['ir.model']._get(model_name))
        except Exception:
            return False

    def _svt_recompute_availabilities(self):
        """Al borrar órdenes de venta por SQL crudo (sin ORM), las
        automatizaciones del motor de Reservaciones (booking_engine) que
        recalculan la Disponibilidad (x_availability) NO se disparan, porque
        esas automatizaciones se activan con el unlink/create normal de
        Odoo. Eso deja "ocupación fantasma" en la vista de Disponibilidad
        aunque ya no existan reservas.

        Este método:
          1) Borra los turnos de planificación (planning.slot) huérfanos,
             es decir, los que estaban ligados a una línea de venta que
             acabamos de eliminar (no toca turnos de personal sin relación
             a una venta).
          2) Marca todas las disponibilidades para recalcular y ejecuta (o
             dispara) el motor de recálculo propio de Reservaciones.

        Es un no-op seguro si el proyecto no tiene instalado el módulo de
        Reservaciones ni el modelo x_availability, para no atar este módulo
        de limpieza (pensado para reutilizarse en otros proyectos) a un
        desarrollo a medida de este cliente.
        """
        if not self.env.user.has_group('base.group_system'):
            return False

        if self._svt_model_installed('planning.slot'):
            try:
                with self._cr.savepoint():
                    self._cr.execute("""
                        DELETE FROM planning_slot
                         WHERE sale_line_id IS NOT NULL
                           AND sale_line_id NOT IN (SELECT id FROM sale_order_line)
                    """)
                    self._svt_remove_orphans('planning.slot', 'planning_slot')
                self._cr.commit()
            except Exception as e:
                _logger.warning('limpieza de turnos de planificación huérfanos falló: %s', e)

        if self._svt_model_installed('x_availability'):
            try:
                availability = self.env['x_availability'].sudo()
                pending = availability.search([])
                if pending:
                    pending.write({'x_to_recompute': True})
                    action = self.env.ref(
                        'booking_engine.server_action_update_availabilities',
                        raise_if_not_found=False)
                    if action:
                        action.sudo().run()
                    else:
                        cron = self.env.ref(
                            'booking_engine.ir_cron_create_500_days_availability',
                            raise_if_not_found=False)
                        if cron:
                            cron.sudo()._trigger()
            except Exception as e:
                _logger.warning('recálculo de disponibilidades falló: %s', e)
        return True

    def _svt_remove_material_resource_leaves(self):
        """Elimina las "Pausas" (resource.calendar.leaves) que bloquean
        recursos de tipo Material (cabañas/habitaciones), típicamente
        creadas como pruebas o eventos puntuales (ej. "Pintura de cabaña").

        A propósito NO se tocan:
          - Pausas de recursos de tipo Usuario (resource_type='user'):
            vacaciones/licencias de personal, que son datos de RRHH, no de
            reservas.
          - Pausas sin recurso (resource_id NULL): feriados/cierres
            generales del calendario de la empresa, que son configuración.

        Es un no-op seguro si el modelo no existe en esta base.
        """
        if not self.env.user.has_group('base.group_system'):
            return False
        if not self._svt_model_installed('resource.calendar.leaves'):
            return True
        try:
            with self._cr.savepoint():
                self._cr.execute("""
                    DELETE FROM resource_calendar_leaves
                     WHERE resource_id IS NOT NULL
                       AND resource_id IN (
                            SELECT id FROM resource_resource WHERE resource_type = 'material'
                       )
                """)
                self._svt_remove_orphans('resource.calendar.leaves', 'resource_calendar_leaves')
            self._cr.commit()
        except Exception as e:
            _logger.warning('remove data error: resource.calendar.leaves,%s', e)
        return True

    def _remove_sales(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        to_removes = [
            'sale.order.line',
            'sale.order',
        ]
        seqs = [
            'sale',
        ]
        res = self._remove_data(to_removes, seqs)
        self._svt_remove_material_resource_leaves()
        self._svt_recompute_availabilities()
        return res

    def _remove_product(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        to_removes = [
            'product.product',
            'product.template',
        ]
        seqs = [
            'product.product',
        ]
        return self._remove_data(to_removes, seqs)

    def _remove_product_attribute(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        to_removes = [
            'product.attribute.value',
            'product.attribute',
        ]
        seqs = []
        return self._remove_data(to_removes, seqs)

    def _remove_pos(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        to_removes = [
            'pos.payment',
            'pos.order.line',
            'pos.order',
            'pos.session',
        ]
        seqs = [
            'pos.',
        ]
        res = self._remove_data(to_removes, seqs)
        try:
            statement = self.env['account.bank.statement'].sudo().search([])
            for s in statement:
                s._end_balance()
        except Exception as e:
            _logger.error('reset sequence data error: %s', e)
        return res

    def _remove_purchase(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        to_removes = [
            'purchase.order.line',
            'purchase.order',
            'purchase.requisition.line',
            'purchase.requisition',
        ]
        seqs = [
            'purchase.',
        ]
        return self._remove_data(to_removes, seqs)

    def _remove_expense(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        to_removes = [
            'hr.expense.sheet',
            'hr.expense',
            'hr.payslip',
            'hr.payslip.run',
        ]
        seqs = [
            'hr.expense.',
        ]
        return self._remove_data(to_removes, seqs)

    def _remove_mrp(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        to_removes = [
            'mrp.workcenter.productivity',
            'mrp.workorder',
            'mrp.production.workcenter.line',
            'change.production.qty',
            'mrp.production',
            'mrp.production.product.line',
            'mrp.unbuild',
            'change.production.qty',
            'sale.forecast.indirect',
            'sale.forecast',
        ]
        seqs = [
            'mrp.',
        ]
        return self._remove_data(to_removes, seqs)

    def _remove_mrp_bom(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        to_removes = [
            'mrp.bom.line',
            'mrp.bom',
        ]
        seqs = []
        return self._remove_data(to_removes, seqs)

    def _remove_inventory(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        to_removes = [
            'stock.quant',
            'stock.move.line',
            'stock.package_level',
            'stock.quantity.history',
            'stock.quant.package',
            'stock.move',
            'stock.picking',
            'stock.scrap',
            'stock.picking.batch',
            'stock.inventory.line',
            'stock.inventory',
            'stock.valuation.layer',
            'stock.production.lot',
            'procurement.group',
        ]
        seqs = [
            'stock.',
            'picking.',
            'procurement.group',
            'product.tracking.default',
            'WH/',
        ]
        return self._remove_data(to_removes, seqs)

    def _remove_account(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        to_removes = [
            'payment.transaction',
            'account.bank.statement.line',
            'account.payment',
            'account.analytic.line',
            # NOTA: 'account.analytic.account' NO se incluye a propósito.
            # Las cuentas analíticas son configuración (siempre asociadas a
            # planes analíticos) y nunca deben borrarse en la limpieza; su
            # eliminación dejaba con root_id inválido a los planes
            # analíticos y rompía la creación de órdenes de venta.
            'account.partial.reconcile',
            'account.move.line',
            'hr.expense.sheet',
            'account.move',
        ]
        res = self._remove_data(to_removes, [])
        domain = [
            ('company_id', '=', self.env.company.id),
            '|', ('code', '=ilike', 'account.%'),
            '|', ('prefix', '=ilike', 'BNK1/%'),
            '|', ('prefix', '=ilike', 'CSH1/%'),
            '|', ('prefix', '=ilike', 'INV/%'),
            '|', ('prefix', '=ilike', 'EXCH/%'),
            '|', ('prefix', '=ilike', 'MISC/%'),
            '|', ('prefix', '=ilike', '账单/%'),
            ('prefix', '=ilike', '杂项/%')
        ]
        try:
            seqs = self.env['ir.sequence'].search(domain)
            if seqs.exists():
                seqs.write({
                    'number_next': 1,
                })
        except Exception as e:
            _logger.error('reset sequence data error: %s,%s', domain, e)
        return res

    def _remove_project(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        to_removes = [
            'account.analytic.line',
            'project.task',
            'project.forecast',
            'project.project',
        ]
        seqs = []
        return self._remove_data(to_removes, seqs)

    # XML ID del proyecto de Housekeeping que crea automáticamente el módulo
    # de Reservaciones (booking_engine). Se preserva en el borrado masivo
    # ("Eliminar todas las transacciones") para no romper el menú Limpieza
    # (tablero y tareas) de Reservaciones.
    _SVT_KEEP_PROJECT_XMLID = 'booking_engine.project_project_1'

    def _remove_project_safe(self):
        """Como ``_remove_project``, pero preserva el proyecto de Housekeeping
        (y sus tareas) que crea el módulo de Reservaciones, para no eliminar
        el menú Limpieza (tablero/tareas). El resto de los proyectos -por
        ejemplo, registros basura de pruebas- se eliminan igual que antes.
        """
        if not self.env.user.has_group('base.group_system'):
            return False
        keep_project = self.env.ref(self._SVT_KEEP_PROJECT_XMLID, raise_if_not_found=False)
        if not keep_project:
            # No existe en esta base (no es una BD de Reservaciones, o el
            # XML ID cambió): comportamiento normal, sin excepciones.
            return self._remove_project()
        keep_id = keep_project.id

        self._remove_data(['account.analytic.line'])

        for model_name in ('project.task', 'project.forecast'):
            try:
                if not self.env['ir.model']._get(model_name):
                    continue
            except Exception as e:
                _logger.warning('remove data error get ir.model: %s,%s', model_name, e)
                continue
            obj = self.pool.get(model_name)
            if not obj or 'project_id' not in obj._fields:
                continue
            t_name = obj._table
            sql = "DELETE FROM {table} WHERE project_id IS NULL OR project_id != %s".format(table=t_name)
            try:
                with self._cr.savepoint():
                    self._cr.execute(sql, (keep_id,))
                    self._svt_remove_orphans(model_name, t_name)
                self._cr.commit()
            except Exception as e:
                _logger.warning('remove data error: %s,%s', model_name, e)

        sql = "DELETE FROM project_project WHERE id != %s"
        try:
            with self._cr.savepoint():
                self._cr.execute(sql, (keep_id,))
                self._svt_remove_orphans('project.project', 'project_project')
            self._cr.commit()
        except Exception as e:
            _logger.warning('remove data error: %s,%s', 'project.project', e)
        return True

    def _remove_quality(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        to_removes = [
            'quality.check',
            'quality.alert',
        ]
        seqs = [
            'quality.check',
            'quality.alert',
        ]
        return self._remove_data(to_removes, seqs)

    def _remove_quality_setting(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        to_removes = [
            'quality.point',
            'quality.alert.stage',
            'quality.alert.team',
            'quality.point.test_type',
            'quality.reason',
            'quality.tag',
        ]
        return self._remove_data(to_removes)

    def _remove_website(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        # Solo modelos reales con tabla propia. Se excluyen los mixins
        # abstractos (website.published.multi.mixin, website.published.mixin,
        # website.multi.mixin, website.seo.metadata): están registrados en
        # ir.model pero NO tienen tabla en la base, y el DELETE sobre ellos
        # aborta la transacción de Postgres.
        to_removes = [
            'blog.tag.category',
            'blog.tag',
            'blog.post',
            'blog.blog',
            'product.wishlist',
            'website.visitor',
            'website.redirect',
        ]
        seqs = []
        return self._remove_data(to_removes, seqs)

    def _remove_message(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        to_removes = [
            'mail.message',
            'mail.followers',
            'mail.activity',
        ]
        seqs = []
        return self._remove_data(to_removes, seqs)

    def action_remove_all(self):
        self._remove_all()

    def action_remove_sales(self):
        self._remove_sales()

    def action_remove_pos(self):
        self._remove_pos()

    def action_remove_purchase(self):
        self._remove_purchase()

    def action_remove_expense(self):
        self._remove_expense()

    def action_remove_mrp(self):
        self._remove_mrp()

    def action_remove_mrp_bom(self):
        self._remove_mrp_bom()

    def action_remove_inventory(self):
        self._remove_inventory()

    def action_remove_account(self):
        self._remove_account()

    def action_remove_project(self):
        self._remove_project()

    def action_remove_project_safe(self):
        self._remove_project_safe()

    def action_remove_quality(self):
        self._remove_quality()

    def action_remove_quality_setting(self):
        self._remove_quality_setting()

    def action_remove_website(self):
        self._remove_website()

    def action_remove_product(self):
        self._remove_product()

    def action_remove_product_attribute(self):
        self._remove_product_attribute()

    def action_remove_message(self):
        self._remove_message()

    def _remove_all(self):
        if not self.env.user.has_group('base.group_system'):
            return False
        # NOTA: a diferencia de om_data_remove, NO se llama a un reset del plan
        # de cuentas: se preservan diarios, cuentas e impuestos (localización
        # argentina, retenciones, etc.).
        self.action_remove_account()
        self.action_remove_quality()
        self.action_remove_website()
        self.action_remove_quality_setting()
        self.action_remove_inventory()
        self.action_remove_purchase()
        self.action_remove_mrp()
        self.action_remove_sales()
        self.action_remove_project_safe()
        self.action_remove_pos()
        self.action_remove_expense()
        self.action_remove_message()
        return True

    def reset_cat_loc_name(self):
        ids = self.env['product.category'].search([
            ('parent_id', '!=', False)
        ], order='complete_name')
        for rec in ids:
            try:
                rec._compute_complete_name()
            except:
                pass
        try:
            ids = self.env['stock.location'].search([
                ('location_id', '!=', False),
                ('usage', '!=', 'views'),
            ], order='complete_name')
            for rec in ids:
                rec._compute_complete_name()
        except:
            pass
        return True
