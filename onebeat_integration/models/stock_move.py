from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    same_usage = fields.Boolean(
        compute="_compute_same_usage",
        stored=True,
    )

    @api.depends("location_id", "location_dest_id")
    def _compute_same_usage(self):
        for record in self:
            record.same_usage = record.location_id.usage == record.location_dest_id.usage
