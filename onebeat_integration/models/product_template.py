from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    buffer_size = fields.Float()