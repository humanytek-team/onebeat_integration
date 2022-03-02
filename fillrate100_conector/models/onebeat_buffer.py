import csv
import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class OnebeatBuffer(models.Model):
    _inherit = "onebeat.buffer"

    def update_buffers(self, content, company=None):
        company = company or self.env.company
        reader = csv.DictReader(content.splitlines(), delimiter=";")
        actual_buffers = self.search([("company_id", "=", company.id)])
        buffers_by_tuple = {
            (buffer.product_id.default_code, buffer.location_id.name): buffer
            for buffer in actual_buffers
        }
        updated_by_tuple = {
            (updated["sku"], updated["location"]): updated["buffer"] for updated in reader
        }
        for tuple, buffer_size in updated_by_tuple.items():
            if tuple not in buffers_by_tuple:
                _logger.warning(_("Missing info %s"), tuple)
                continue
            buffers_by_tuple[tuple].buffer_size = buffer_size
