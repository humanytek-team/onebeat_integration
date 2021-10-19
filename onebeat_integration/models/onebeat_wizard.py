import base64
import csv
import logging
from datetime import datetime, timedelta
from ftplib import FTP, FTP_TLS
from io import BytesIO, StringIO

import pytz

from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


def data_to_bytes(fieldnames, data):
    writer_file = StringIO()
    writer = csv.DictWriter(writer_file, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()
    writer.writerows(data)
    return writer_file.getvalue().encode("utf-8")


def clean(val):
    return val.replace("\n", "") if isinstance(val, str) else ""


def keep_wizard_open(f):
    def wrapper(*args, **kwargs):
        f(*args, *kwargs)
        self = args[0]
        return {
            "context": self.env.context,
            "view_type": "form",
            "view_mode": "form",
            "res_model": self._name,
            "res_id": self.id,
            "view_id": False,
            "type": "ir.actions.act_window",
            "target": "new",
        }

    return wrapper


class OneBeatWizard(models.TransientModel):
    _name = "onebeat_wizard"
    _description = "OneBeat Wizard"

    stocklocations_file = fields.Binary(
        readonly=True,
    )
    stocklocations_file_fname = fields.Char()
    mtsskus_file = fields.Binary(
        readonly=True,
    )
    mtsskus_file_fname = fields.Char()
    transactions_file = fields.Binary(
        readonly=True,
    )
    transactions_file_fname = fields.Char()
    status_file = fields.Binary(
        readonly=True,
    )
    status_file_fname = fields.Char()
    start = fields.Datetime(
        default=fields.Datetime.from_string(fields.Datetime.now()) - timedelta(days=1),
        required=True,
    )
    stop = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
    )
    all_combinations = fields.Boolean()
    production_default_location_id = fields.Many2one(
        comodel_name="stock.location",
        domain=[("usage", "=", "production")],
        required=True,
    )

    def get_dates_betwen(self, start, stop):
        return [
            (start + timedelta(days=x)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            for x in range((stop - start).days)
        ]

    def _get_all_combinations(self, products, oringin_locations, dest_locations, dates):
        return {
            (
                product.default_code,
                location.name,
                location_dest.name,
                "OUT" if location.usage == "internal" else "IN",
                self.datetime_localized(date).strftime("%Y-%m-%d"),
            ): 0
            for product in products
            for location in oringin_locations
            for location_dest in dest_locations
            for date in dates
            if location != location_dest
        }

    def datetime_localized(self, date_time):
        now_utc = fields.Datetime.from_string(date_time)
        tz = pytz.timezone(self.env.user.tz or "UTC")
        return pytz.utc.localize(now_utc).astimezone(tz)

    def get_company_id(self):
        if not self.env.company.vat:
            raise ValidationError(
                f"The company `{self.env.company.name}` does not have a valid VAT"
            )
        return self.env.company.vat[:3]

    def get_stocklocations_file(self):
        now = self.datetime_localized(fields.Datetime.now(self))
        year, month, day = now.strftime("%Y-%m-%d").split("-")

        Locations = self.env["stock.location"].browse(
            [
                self.env.ref("stock.stock_location_stock").id,
                self.env.ref("stock.stock_location_customers").id,
                self.env.ref("stock.stock_location_suppliers").id,
                self.production_default_location_id.id,
            ]
        )
        data = [
            {
                "Nombre Agencia": clean(location.name),
                "Descripción": clean(location.barcode),
                "Año reporte": year,
                "Mes Reporte": month,
                "Dia Reporte": day,
                "Ubicación": None,
            }
            for location in Locations
        ]

        fieldnames = [
            "Nombre Agencia",
            "Descripción",
            "Año reporte",
            "Mes Reporte",
            "Dia Reporte",
            "Ubicación",
        ]
        return (
            "STOCKLOCATIONS_{}_{}.csv".format(self.get_company_id(), now.strftime("%Y%m%d")),
            data_to_bytes(fieldnames, data),
        )

    @keep_wizard_open
    def set_stocklocations_file(self):
        fname, data = self.get_stocklocations_file()
        self.stocklocations_file_fname = fname
        self.stocklocations_file = base64.b64encode(data)

    def get_product_origin_location(self, product):
        if product.seller_ids:
            return product.seller_ids[0].name.property_stock_supplier
        if product.property_stock_production:
            return product.property_stock_production
        else:
            return self.production_default_location_id

    def get_mtsskus_file(self):
        now = self.datetime_localized(fields.Datetime.now(self))
        year, month, day = now.strftime("%Y-%m-%d").split("-")

        Locations = self.env["stock.location"].browse(
            [
                self.env.ref("stock.stock_location_stock").id,
            ]
        )
        Products = self.env["product.product"].search(
            [
                ("type", "!=", "service"),
                ("default_code", "!=", False),
            ]
        )
        data = [
            {
                "Stock Location Name": clean(location.name),
                "Origin SL": clean(self.get_product_origin_location(product).name),
                "SKU Name": clean(product.default_code),
                "SKU Description": clean(product.name),
                "Buffer Size": product.buffer_size,
                "Replenishment Time": product.seller_ids[0].delay
                if product.seller_ids
                else product.produce_delay,
                "Inventory at Site": 0,
                "Inventory at Transit": 0,
                "Inventory at Production": 0,
                "Precio unitario": product.list_price,
                "TVC": product.standard_price,
                "Throughput": max(product.list_price - product.standard_price, 0),
                # 'Minimo Reabastecimiento': None,
                "Unidad de Medida": clean(product.uom_id.name),
                "Reported Year": year,
                "Reported Month": month,
                "Reported Day": day,
            }
            for location in Locations
            for product in Products
        ]

        fieldnames = [
            "Stock Location Name",
            "Origin SL",
            "SKU Name",
            "SKU Description",
            "Buffer Size",
            "Replenishment Time",
            "Inventory at Site",
            "Inventory at Transit",
            "Inventory at Production",
            "Precio unitario",
            "TVC",
            "Throughput",
            # 'Minimo Reabastecimiento',
            "Unidad de Medida",
            "Reported Year",
            "Reported Month",
            "Reported Day",
        ]
        return (
            "MTSSKUS_{}_{}.csv".format(self.get_company_id(), now.strftime("%Y%m%d")),
            data_to_bytes(fieldnames, data),
        )

    @keep_wizard_open
    def set_mtsskus_file(self):
        fname, data = self.get_mtsskus_file()
        self.mtsskus_file_fname = fname
        self.mtsskus_file = base64.b64encode(data)

    def group_moves(self, Moves):
        grouped = {}
        for move in Moves:
            if move.location_id.usage == move.location_dest_id.usage:
                continue
            date = self.datetime_localized(move.date).strftime("%Y-%m-%d")
            key = (
                move.product_id.default_code,
                move.location_id.name,
                move.location_dest_id.name,
                "OUT" if move.location_id.usage == "internal" else "IN",
                date,
            )
            grouped[key] = grouped.get(key, 0) + move.quantity_done
        return grouped

    def get_transactions_file(self, start=None, stop=None):
        start = self.start or start
        stop = self.stop or stop
        now = self.datetime_localized(fields.Datetime.now(self))
        Moves = self.env["stock.move"].search(
            [
                ("state", "in", ["done"]),
                ("date", ">=", start),
                ("date", "<", stop),
                ("location_id.onebeat_ignore", "=", False),
                ("location_dest_id.onebeat_ignore", "=", False),
                "|",
                "&",
                ("location_id.usage", "=", "production"),
                ("location_dest_id.usage", "=", "internal"),
                "&",
                (
                    "location_id.usage",
                    "in",
                    [
                        "supplier",
                        "internal",
                        "customer",
                        # 'production',
                    ],
                ),
                (
                    "location_dest_id.usage",
                    "in",
                    [
                        # 'supplier',
                        "internal",
                        "customer",
                        "production",
                    ],
                ),
                ("same_usage", "=", False),
            ]
        )
        if self.all_combinations:
            valid_products = self.env["product.product"].search(
                [
                    ("type", "!=", "service"),
                    ("default_code", "!=", False),
                ]
            )
            origin_locations = [
                self.env.ref("stock.stock_location_stock"),
            ]
            dest_locations = [
                self.env.ref("stock.stock_location_customers"),
            ]
            if type(start) == str:
                start = datetime.strptime(start, DEFAULT_SERVER_DATETIME_FORMAT)
            if type(stop) == str:
                stop = datetime.strptime(stop, DEFAULT_SERVER_DATETIME_FORMAT)
            dates = self.get_dates_betwen(start, stop)
            grouped = self._get_all_combinations(
                valid_products, origin_locations, dest_locations, dates
            )
        else:
            grouped = {}
        grouped.update(self.group_moves(Moves))
        data = [
            {
                "Origin": group[1],
                "SKU Name": group[0],
                "Destination": group[2],
                "Transaction Type (in/out)": group[3],
                "Quantity": grouped[group],
                "Shipping Year": group[4].split("-")[0],
                "Shipping Month": group[4].split("-")[1],
                "Shipping Day": group[4].split("-")[2],
            }
            for group in grouped
        ]

        fieldnames = [
            "Origin",
            "SKU Name",
            "Destination",
            "Transaction Type (in/out)",
            "Quantity",
            "Shipping Year",
            "Shipping Month",
            "Shipping Day",
        ]
        return (
            "TRANSACTIONS_{}_{}.csv".format(self.get_company_id(), now.strftime("%Y%m%d")),
            data_to_bytes(fieldnames, data),
        )

    @keep_wizard_open
    def set_transactions_file(self):
        fname, data = self.get_transactions_file()
        self.transactions_file_fname = fname
        self.transactions_file = base64.b64encode(data)

    def get_status_file(self):
        now = self.datetime_localized(fields.Datetime.now(self))
        year, month, day = now.strftime("%Y-%m-%d").split("-")

        Locations = self.env["stock.location"].browse(
            [
                self.env.ref("stock.stock_location_stock").id,
            ]
        )
        Products = self.env["product.product"].search(
            [
                ("type", "!=", "service"),
                ("default_code", "!=", False),
            ]
        )

        Lines = self.env["stock.move.line"].read_group(
            domain=[
                ("state", "not in", ["done", "draft", "cancel"]),
                ("location_id.onebeat_ignore", "=", False),
                ("location_dest_id.onebeat_ignore", "=", False),
                (
                    "location_id.usage",
                    "in",
                    [
                        "supplier",
                    ],
                ),
                (
                    "location_dest_id.usage",
                    "in",
                    [
                        "internal",
                    ],
                ),
            ],
            fields=["product_id", "product_uom_qty"],
            groupby=["product_id"],
        )
        lines_dict = {line["product_id"][0]: line["product_uom_qty"] for line in Lines}

        data = [
            {
                "Stock Location Name": clean(location.name),
                "SKU Name": clean(product.default_code),
                "Inventory At Hand": product.virtual_available,
                "Inventory On The Way": lines_dict.get(product.id, 0),
                "Reported Year": year,
                "Reported Month": month,
                "Reported Day": day,
            }
            for location in Locations
            for product in Products
        ]

        fieldnames = [
            "Stock Location Name",
            "SKU Name",
            "Inventory At Hand",
            "Inventory On The Way",
            "Reported Year",
            "Reported Month",
            "Reported Day",
        ]
        return (
            "STATUS_{}_{}.csv".format(self.get_company_id(), now.strftime("%Y%m%d")),
            data_to_bytes(fieldnames, data),
        )

    @keep_wizard_open
    def set_status_file(self):
        fname, data = self.get_status_file()
        self.status_file_fname = fname
        self.status_file = base64.b64encode(data)

    def send_to_ftp(self, start=None, stop=None):
        now = self.datetime_localized(fields.Datetime.now(self))
        start = start or now.replace(hour=0, minute=0, second=0)
        stop = stop or start + timedelta(days=1)
        host = self.env.company.ftp_host
        port = self.env.company.ftp_port
        user = self.env.company.ftp_user
        passwd = self.env.company.ftp_passwd
        ftp_tls = False
        ftp = FTP_TLS() if ftp_tls else FTP()
        try:
            ftp.connect(host, port)
            ftp.login(user, passwd)
        except:
            _logger.error("Unable to reach FTP server")
        else:
            stocklocations = self.get_stocklocations_file()
            mtsskus = self.get_mtsskus_file()
            transactions = self.get_transactions_file(str(start), str(stop))
            status = self.get_status_file()
            ftp.storbinary("STOR " + stocklocations[0], BytesIO(stocklocations[1]))
            ftp.storbinary("STOR " + mtsskus[0], BytesIO(mtsskus[1]))
            ftp.storbinary("STOR " + transactions[0], BytesIO(transactions[1]))
            ftp.storbinary("STOR " + status[0], BytesIO(status[1]))
        finally:
            ftp.close()
