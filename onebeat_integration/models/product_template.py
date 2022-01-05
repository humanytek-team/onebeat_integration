from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    buffer_size = fields.Float()
    default_code = fields.Char(  # Inherit base field
        required=True,
    )

    _sql_constraints = [
        (
            "uniq_default_code",
            "UNIQUE(default_code, company_id)",
            _("The default code must be unique per company."),
        )
    ]

    @api.constrains("name")
    def _check_valid_name(self):
        invalid_chars = ",'\""
        for record in self:
            if any(char in record.name for char in invalid_chars):
                raise ValueError(
                    _("The name of the product can not contain the following characters: %s")
                    % invalid_chars
                )
