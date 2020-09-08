# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    onebeat_ignore = fields.Boolean(
        string='Ignore on OneBeat',
    )
