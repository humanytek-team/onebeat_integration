from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    onebeat_ignore = fields.Boolean(
        string="Ignore on OneBeat",
    )
