import csv
from datetime import datetime
from io import BytesIO

import pysftp

from odoo import fields, models

from odoo.addons.onebeat_integration.models.onebeat_wizard import data_to_bytes

BUFFER_FILE = "ftp/buffers_update.csv"


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
            ("name", self._get_fillrate_name),
            ("sku", "SKU Name"),
            ("location", "Stock Location Name"),
            ("description", "SKU Description"),
            ("origin", "Origin SL"),
            ("replenishment_time", "Replenishment Time"),
            ("day_to_replenish", ""),
            ("buffer", "Buffer Size"),
            ("unit_cost", "Precio unitario"),
            ("min_qty", "Minimo Reabastecimiento"),
            ("multiple", ""),
        )

    def _get_fillrate_name(self, line):
        if isinstance(line, dict):
            return f"{line['SKU Name']}{line['Stock Location Name']}"
        return f"{line.product_id.default_code}{self._get_location_name(line.location_id)}"

    def transactions_fillrate_parser(self):
        return (
            ("name", self._get_fillrate_name),
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
            ("name", self._get_fillrate_name),
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
        if self.fillrate100_format or not self.ids:
            data = self.data_to_fillrate(self.mtksskus_fillrate_parser(), data)
            fname = f"input_{fname}"
        return fname, data

    def get_transactions_file(self, start=None, stop=None):
        fname, data = super(OneBeatWizard, self).get_transactions_file(start, stop)
        if self.fillrate100_format or not self.ids:
            return None, b""
        return fname, data

    def get_stocklocations_file(self):
        fname, data = super(OneBeatWizard, self).get_stocklocations_file()
        if self.fillrate100_format or not self.ids:
            return None, b""
        return fname, data

    def get_status_file(self):
        fname, data = super(OneBeatWizard, self).get_status_file()
        if self.fillrate100_format or not self.ids:
            data = self.data_to_fillrate(self.status_fillrate_parser(), data)
            fname = f"input_{fname}"
        return fname, data

    def _get_new_buffers(self):
        ftp: pysftp.Connection = self.get_ftp_connector()
        buffer_file = BytesIO()
        ftp.getfo(BUFFER_FILE, buffer_file)
        ftp.close()
        buffer_file.seek(0)
        return buffer_file.read().decode("utf-8")

    def update_buffers_from_ftp(self):
        content = self._get_new_buffers()
        self.env["onebeat.buffer"].update_buffers(content)
