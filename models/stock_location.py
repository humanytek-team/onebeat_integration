# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    to_report = fields.Boolean(
    )

    @api.constrains('to_report')
    def _check_to_report(self):
        for record in self:
            if record.to_report and record.usage not in ['supplier', 'internal', 'customer']:
                raise ValidationError(_('Only `supplier`, `internal` or `customer` are location types valid to report.'))
