import csv
from datetime import datetime

from odoo import fields, models

from odoo.addons.onebeat_integration.models.onebeat_wizard import data_to_bytes


def bytes_to_csv(bytes: bytes):
    """Convert byte string to CSV"""

    lines = bytes.decode("utf-8").splitlines()
    return csv.DictReader(lines, delimiter=";")


class OneBeatWizard(models.TransientModel):
    _inherit = "onebeat_wizard"

    fillrate100_format = fields.Boolean(
        default=True,
    )

    def mtksskus_fillrate_parser(self):
        return (
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

    def transactions_fillrate_parser(self):
        return (
            ("External id", ""),
            ("replenishment order", ""),
            (
                "order_date",
                lambda line: datetime.strptime(
                    f"{line['Shipping Year']}-{line['Shipping Month']}-{line['Shipping Day']}",
                    "%Y-%m-%d",
                ),
            ),
            ("skuloc", ""),
            ("sku", "SKU Name"),
            ("destination", "Destination"),
            ("description", ""),
            ("Origin", "Origin"),
            ("quantity", "Quantity"),
        )

    def status_fillrate_parser(self):
        return (
            ("External id", ""),
            ("sku", "SKU Name"),
            ("location", "Stock Location Name"),
            ("description", "SKU Description"),
            ("onhand", "Inventory At Hand"),
            ("transit", "Inventory On The Way"),
        )

    def get_old_line_value(self, line, old):
        if callable(old):
            return old(line)
        return line.get(old, "")

    def data_to_fillrate(self, parser, data):
        csv_file = bytes_to_csv(data)
        lines = [
            {new: self.get_old_line_value(line, old) for new, old in parser} for line in csv_file
        ]
        return data_to_bytes([new for new, _old in parser], lines)

    def get_mtsskus_file(self):
        fname, data = super(OneBeatWizard, self).get_mtsskus_file()
        if self.fillrate100_format:
            data = self.data_to_fillrate(self.mtksskus_fillrate_parser(), data)
        return f"input_{fname}", data

    def get_transactions_file(self, start=None, stop=None):
        fname, data = super(OneBeatWizard, self).get_transactions_file(start, stop)
        if self.fillrate100_format:
            data = self.data_to_fillrate(self.transactions_fillrate_parser(), data)
        return f"input_{fname}", data

    def get_status_file(self):
        fname, data = super(OneBeatWizard, self).get_status_file()
        if self.fillrate100_format:
            data = self.data_to_fillrate(self.status_fillrate_parser(), data)
        return f"input_{fname}", data
