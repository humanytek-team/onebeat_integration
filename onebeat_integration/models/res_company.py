from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    onebeat_ftp_server_id = fields.Many2one(
        comodel_name="ftp_server",
        string="OneBeat FTP Server",
    )
