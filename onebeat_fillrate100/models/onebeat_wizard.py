import csv

from odoo import fields, models

from odoo.addons.onebeat_integration.models.onebeat_wizard import data_to_bytes


def bytes_to_csv(bytes: bytes):
    """Convert byte string to CSV"""

    lines = bytes.decode("utf-8").splitlines()
    return csv.DictReader(lines, delimiter=";")


class OneBeatWizard(models.TransientModel):
    _inherit = "onebeat_wizard"

    fillrate100_format = fields.Boolean()

    def mtsskus_data_to_fillrate(self, data):
        csv_file = bytes_to_csv(data)
        parser = (
            ("External id", ""),
            ("sku", "SKU Name"),
            ("location", "Stock Location Name"),
            ("description", "SKU Description"),
            ("origin", "Origin SL"),
            ("replenishment_time", "Replenishment Time"),
            ("day_to_replenish", ""),
            ("buffer", "Buffer Size"),
            ("unit_cost", "Precio unitario"),
            ("min_qty", ""),
            ("multiple", ""),
        )
        lines = [{new: line.get(old, "") for new, old in parser} for line in csv_file]
        return data_to_bytes([new for new, _old in parser], lines)

    def get_mtsskus_file(self):
        fname, data = super(OneBeatWizard, self).get_mtsskus_file()
        if self.fillrate100_format:
            data = self.mtsskus_data_to_fillrate(data)
        return fname, data

    def get_transactions_file(self):
        fname, data = super(OneBeatWizard, self).get_transactions_file()
        if self.fillrate100_format:
            pass  # TODO
        return fname, data

    def get_status_file(self):
        fname, data = super(OneBeatWizard, self).get_status_file()
        if self.fillrate100_format:
            pass  # TODO
        return fname, data
