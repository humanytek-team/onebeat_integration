from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.constrains("default_code")
    def _check_unique_default_code(self):
        for record in self:
            if not record.default_code:
                continue
            duplicated = self.search(
                [
                    ("default_code", "=", record.default_code),
                    ("id", "!=", record.id),
                    ("company_id", "=", record.company_id.id),
                ],
                limit=1,
            )
            if duplicated:
                raise UserError(
                    _("The product code %s already exists in the company %s " "for the product %s")
                    % (record.default_code, record.company_id.name, duplicated.name)
                )
