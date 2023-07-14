from odoo import api, fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    onebeat_ignore = fields.Boolean(
        string="Ignore on OneBeat",
    )
    warehouse_ids = fields.One2many(
        comodel_name="stock.warehouse",
        inverse_name="lot_stock_id",
    )
    is_direct_from_warehouse = fields.Boolean(
        compute="_compute_is_direct_from_warehouse",
        store=True,
    )
    onebeat_ignore_complete = fields.Boolean(
        compute="_compute_onebeat_ignore_complete",
        store=True,
    )

    @api.depends("warehouse_ids")
    def _compute_is_direct_from_warehouse(self):
        for location in self:
            location.is_direct_from_warehouse = bool(location.warehouse_ids)

    @api.depends("onebeat_ignore", "is_direct_from_warehouse")
    def _compute_onebeat_ignore_complete(self):
        for location in self:
            location.onebeat_ignore_complete = (
                location.onebeat_ignore or not location.is_direct_from_warehouse
            )
