import csv
import os
import re
from collections import defaultdict
from typing import Dict, Iterable

from odoo import fields, models
from odoo.exceptions import UserError

FILE_PATH = r"ftp"
FILE_NAME_REGEX = r"sku_ro_.+\.csv"
# Asume que el archivo contiene la fecha de creación en el nombre en formato ISO

FILLRATE_CSV_DELIMITER = ";"


class OnebeatReplenisher(models.TransientModel):
    _name = "onebeat.replenisher"
    _description = "Onebeat Replenisher"

    def _get_last_update_content(self):
        ftp_server = self.env.company.onebeat_ftp_server_id
        file_names = [f.split("/")[-1] for f in ftp_server.list(FILE_PATH)]
        file_names = [f for f in file_names if re.match(FILE_NAME_REGEX, f)]
        if not file_names:
            return None
        file_name = max(file_names)
        full_path = os.path.join(FILE_PATH, file_name)
        return ftp_server.download(full_path).decode("UTF-8")

    def replenish(self):
        last_update_content = self._get_last_update_content()
        if not last_update_content:
            raise UserError("No se encontró el archivo para reponer")
        self._replenish(last_update_content)

    def _get_supplier_info_by_sku(self, products):
        return {
            product.default_code: product.seller_ids[0]
            for product in products
            if product.seller_ids
        }

    def _get_purchase_lines_by_supplier(self, rows):
        skus = tuple(row["sku"] for row in rows)
        products = self.env["product.product"].search([("default_code", "in", skus)])
        supplier_info_by_sku = self._get_supplier_info_by_sku(products)
        return self._gen_purchase_lines_from_supplier_info_by_sku(supplier_info_by_sku, rows)

    def _gen_purchase_line_from_supplier_info_and_row(self, supplier_info, row):
        return {
            "product_id": supplier_info.product_id.id
            or supplier_info.product_tmpl_id.product_variant_id.id,
            "product_qty": row["qty_replenishment"],
        }

    def _gen_purchase_lines_from_supplier_info_by_sku(self, supplier_info_by_sku, rows):
        purchase_lines_by_supplier = defaultdict(list)
        for row in rows:
            sku = row["sku"]
            supplier_info = supplier_info_by_sku.get(sku)
            if not supplier_info:
                continue
            partner = supplier_info.name
            purchase_lines_by_supplier[partner].append(
                self._gen_purchase_line_from_supplier_info_and_row(supplier_info, row)
            )
        return purchase_lines_by_supplier

    def _replenish_rows(self, rows: Iterable[Dict[str, str]]) -> None:
        purchase_lines_by_supplier = self._get_purchase_lines_by_supplier(rows)
        self._create_purchase_orders(purchase_lines_by_supplier)

    def _create_purchase_orders(self, purchase_lines_by_supplier):
        for supplier, lines in purchase_lines_by_supplier.items():
            self.env["purchase.order"].create(
                {
                    "partner_id": supplier.id,
                    "order_line": [(0, 0, line) for line in lines],
                    "origin": "Fillrate",
                    "date_planned": None,
                }
            )

    def _replenish(self, data: str) -> None:
        reader = csv.DictReader(data.splitlines(), delimiter=FILLRATE_CSV_DELIMITER)
        rows = tuple(reader)
        self._replenish_rows(rows)
