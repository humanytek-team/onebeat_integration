# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class StockLocation(models.Model):
    _inherit = 'stock.location'

    to_report = fields.Boolean(
    )
