import csv
from datetime import datetime

from odoo import fields, models
from odoo.addons.onebeat_integration.models.onebeat_wizard import data_to_bytes

BUFFER_FILE = "ftp/buffers_update.csv"

FILLRATE_CSV_DELIMITER = ";"


def bytes_to_csv(bytes: bytes):
    """Convert byte string to CSV"""

    lines = bytes.decode("utf-8").splitlines()
    return csv.DictReader(lines, delimiter=FILLRATE_CSV_DELIMITER)


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
            # ("origin", "Origin SL"),
            # ("replenishment_time", "Replenishment Time"),
            # ("day_to_replenish", ""),
            # ("buffer", "Buffer Size"),
            ("unit_cost", "TVC"),
            # ("min_qty", "Minimo Reabastecimiento"),
            # ("multiple", ""),
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
            ("onhand", "Inventory At Hand"),
            ("transit", "Inventory On The Way"),
        )

    def get_old_line_value(self, line, old):
        return old(line) if callable(old) else line.get(old, "")

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
        if self.fillrate100_format or not self.ids:
            return None, b""
        fname, data = super(OneBeatWizard, self).get_transactions_file(start, stop)
        return fname, data

    def get_stocklocations_file(self):
        if self.fillrate100_format or not self.ids:
            return None, b""
        fname, data = super(OneBeatWizard, self).get_stocklocations_file()
        return fname, data

    def get_status_file(self):
        fname, data = super(OneBeatWizard, self).get_status_file()
        if self.fillrate100_format or not self.ids:
            data = self.data_to_fillrate(self.status_fillrate_parser(), data)
            fname = f"input_{fname}"
        return fname, data

    def _get_new_buffers(self):
        ftp_server = self.get_ftp_server()
        return ftp_server.download(BUFFER_FILE).decode("UTF-8")

    def update_buffers_from_ftp(self):
        content = self._get_new_buffers()
        self.env["onebeat.buffer"].update_buffers(content)
