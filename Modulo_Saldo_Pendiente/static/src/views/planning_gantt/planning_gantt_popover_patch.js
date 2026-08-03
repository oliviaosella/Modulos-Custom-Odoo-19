/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PlanningGanttRenderer } from "@planning/views/planning_gantt/planning_gantt_renderer";

// Selection value -> (clase visual, etiqueta)
const ESTADO_PAGO_INFO = {
    pagado: { cls: "badge rounded-pill bg-success me-1", label: "Pagado" },
    parcial: { cls: "badge rounded-pill bg-warning text-dark me-1", label: "Saldo pendiente" },
    no_pagado: { cls: "badge rounded-pill bg-danger me-1", label: "A pagar" },
};

function formatMonto(monto) {
    const value = Number(monto) || 0;
    try {
        return new Intl.NumberFormat("es-AR", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
    } catch {
        return String(value);
    }
}

/**
 * Agrega un badge chico de color (rojo/amarillo/verde) con el saldo
 * pendiente de la reserva en el popover del Gantt de planificación.
 */
patch(PlanningGanttRenderer.prototype, {
    /**
     * @override
     */
    async getPopoverProps(pill) {
        const popoverProps = await super.getPopoverProps(...arguments);
        const { record } = pill;

        const estadoPago = record.x_estado_pago;
        const info = ESTADO_PAGO_INFO[estadoPago];

        if (info) {
            let text = info.label;
            if (estadoPago !== "pagado" && record.x_saldo_pendiente) {
                text += `: $ ${formatMonto(record.x_saldo_pendiente)}`;
            }

            popoverProps.buttons = popoverProps.buttons || [];
            popoverProps.buttons.unshift({
                text,
                class: info.cls,
                onClick: () => {},
            });
        }

        return popoverProps;
    },
});
