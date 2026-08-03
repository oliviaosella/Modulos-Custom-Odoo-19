/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PlanningGanttRenderer } from "@planning/views/planning_gantt/planning_gantt_renderer";

/**
 * Agrega el botón "Ver Orden de Venta" en el popover del Gantt de planificación.
 */
patch(PlanningGanttRenderer.prototype, {

    /**
     * @override
     */
    async getPopoverProps(pill) {
        const popoverProps = await super.getPopoverProps(...arguments);
        const { record } = pill;

        // DIAGNÓSTICO TEMPORAL
        console.log("=== hotel_planning_custom DEBUG ===");
        console.log("record.sale_order_id:", record.sale_order_id, "| typeof:", typeof record.sale_order_id);
        console.log("record.sale_line_id:", record.sale_line_id, "| typeof:", typeof record.sale_line_id);
        console.log("record completo:", record);

        if (record.sale_order_id) {
            // Manejar ambos formatos posibles: [id, name] o {id, display_name} o entero plano
            let saleOrderId;
            let saleOrderName = _t("Orden de Venta");

            if (Array.isArray(record.sale_order_id)) {
                saleOrderId = record.sale_order_id[0];
                saleOrderName = record.sale_order_id[1] || saleOrderName;
            } else if (typeof record.sale_order_id === "object" && record.sale_order_id !== null) {
                saleOrderId = record.sale_order_id.id;
                saleOrderName = record.sale_order_id.display_name || saleOrderName;
            } else {
                saleOrderId = record.sale_order_id;
            }

            console.log("saleOrderId resuelto:", saleOrderId, "| typeof:", typeof saleOrderId);

            if (saleOrderId) {
                const openOrderBtn = {
                    text: _t("Ver Orden de Venta"),
                    class: "btn btn-secondary btn-sm",
                    icon: "fa-file-text-o",
                    onClick: async () => {
                        await this.env.services.action.doAction({
                            type: "ir.actions.act_window",
                            res_model: "sale.order",
                            res_id: saleOrderId,
                            name: saleOrderName,
                            view_mode: "form",
                            views: [[false, "form"]],
                            target: "current",
                        });
                    },
                };

                // Insertar después de "Editar" (posición 1): Editar | Ver Orden | Anular | Eliminar
                popoverProps.buttons.splice(1, 0, openOrderBtn);
            }
        }

        return popoverProps;
    },
});