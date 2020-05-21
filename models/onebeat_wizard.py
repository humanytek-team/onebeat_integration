# -*- coding: utf-8 -*-
import csv
import base64
from io import StringIO
from datetime import timedelta, datetime

from odoo import _, api, fields, models


def data_to_bytes(fieldnames, data):
    writer_file = StringIO()
    writer = csv.DictWriter(writer_file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
    return writer_file.getvalue().encode('utf-8')


class OneBeatWizard(models.TransientModel):
    _name = 'onebeat_wizard'

    stocklocations_file = fields.Binary(
        compute='get_stocklocations_file',
    )
    stocklocations_file_fname = fields.Char(
        compute="get_stocklocations_file",
    )
    mtsskus_file = fields.Binary(
        compute='get_mtsskus_file',
    )
    mtsskus_file_fname = fields.Char(
        compute="get_mtsskus_file",
    )
    transactions_file = fields.Binary(
        compute='get_transactions_file',
    )
    transactions_file_fname = fields.Char(
        compute="get_transactions_file",
    )
    status_file = fields.Binary(
        compute='get_status_file',
    )
    status_file_fname = fields.Char(
        compute="get_status_file",
    )
    start = fields.Date(
        default=fields.Date.from_string(fields.Date.today()) - timedelta(days=1),
        required=True,
    )
    stop = fields.Date(
        default=fields.Date.context_today,
        required=True,
    )

    def generate(self):
        self.get_stocklocations_file()
        self.get_mtsskus_file()
        self.get_transactions_file()
        self.get_status_file()
        return {
            "type": "ir.actions.do_nothing",
        }

    def get_stocklocations_file(self):
        now = fields.Datetime.from_string(fields.Datetime.now(self)).isoformat()
        year, month, day = now.split('-')
        day = day[:2]
        self.stocklocations_file_fname = 'STOCKLOCATIONS_%s.csv' % now.replace('-', '').replace('T', '_').replace(':', '')[:-2]

        Locations = self.env['stock.location'].search([('to_report', '=', True)])
        data = [{
            'Nombre Agencia': location_id.display_name,
            'Descripción': location_id.barcode,
            'Año reporte': year,
            'Mes Reporte': month,
            'Dia Reporte': day,
            'Ubicación': None,
        } for location_id in Locations]

        fieldnames = ['Nombre Agencia', 'Descripción', 'Año reporte', 'Mes Reporte', 'Dia Reporte', 'Ubicación']
        self.stocklocations_file = base64.b64encode(data_to_bytes(fieldnames, data))

    def get_mtsskus_file(self):
        now = fields.Datetime.from_string(fields.Datetime.now(self)).isoformat()
        year, month, day = now.split('-')
        day = day[:2]
        self.mtsskus_file_fname = 'MTSSKUS_%s.csv' % now.replace('-', '').replace('T', '_').replace(':', '')[:-2]

        Locations = self.env['stock.location'].search([
            ('to_report', '=', True),
            ('usage', 'in', ['internal']),
        ])
        Products = self.env['product.product'].search([('sale_ok', '=', True)])
        data = [{
            'Stock Location Name': location_id.display_name,
            'Origin SL': product_id.seller_ids[0].name.property_stock_supplier.display_name if product_id.seller_ids else 'Planta de producción',
            'SKU Name': product_id.default_code,
            'SKU Description': product_id.name,
            'Buffer Size': product_id.buffer_size,
            'Replenishment Time': product_id.seller_ids[0].delay if product_id.seller_ids else product_id.produce_delay,
            'Inventory at Site': 0,
            'Inventory at Transit': 0,
            'Inventory at Production': 0,
            'Precio unitario': product_id.list_price,
            'TVC': product_id.standard_price,
            'Throughput': max(product_id.list_price - product_id.standard_price, 0),
            # 'Minimo Reabastecimiento': None,
            'Unidad de Medida': product_id.uom_id.name,
            'Reported Year': year,
            'Reported Month': month,
            'Reported Day': day,
        } for location_id in Locations for product_id in Products]

        fieldnames = [
            'Stock Location Name',
            'Origin SL',
            'SKU Name',
            'SKU Description',
            'Buffer Size',
            'Replenishment Time',
            'Inventory at Site',
            'Inventory at Transit',
            'Inventory at Production',
            'Precio unitario',
            'TVC',
            'Throughput',
            # 'Minimo Reabastecimiento',
            'Unidad de Medida',
            'Reported Year',
            'Reported Month',
            'Reported Day',
        ]
        self.mtsskus_file = base64.b64encode(data_to_bytes(fieldnames, data))

    def get_transactions_file(self, start=None, stop=None, last_day=False):
        start = (last_day and fields.Date.from_string(fields.Date.today()) - timedelta(days=1)) or start or self.start
        stop = (last_day and fields.Date.from_string(fields.Date.today())) or stop or self.stop
        now = fields.Datetime.from_string(fields.Datetime.now(self)).isoformat()
        year, month, day = now.split('-')
        day = day[:2]
        self.transactions_file_fname = 'TRANSACTIONS_%s.csv' % now.replace('-', '').replace('T', '_').replace(':', '')[:-2]

        Moves = self.env['stock.move'].search([
            '|',
            ('location_id.to_report', '=', True),
            ('location_dest_id.to_report', '=', True),
            ('location_id.usage', 'in', ['supplier', 'internal', 'customer']),
            ('location_dest_id.usage', 'in', ['supplier', 'internal', 'customer']),
            ('date', '>=', start),
            ('date', '<', stop),
        ])
        data = [{
            'Origin': move_id.location_id.display_name,
            'SKU Name': move_id.product_id.default_code,
            'Destination': move_id.location_dest_id.display_name,
            'Transaction Type (in/out)': 'OUT' if move_id.location_id.usage == 'internal' else 'IN',
            'Quantity': move_id.quantity_done,
            'Shipping Year': move_id.date.isoformat().split('-')[0],
            'Shipping Month': move_id.date.isoformat().split('-')[1],
            'Shipping Day': move_id.date.isoformat().split('-')[2][:2],
        } for move_id in Moves]

        fieldnames = ['Origin', 'SKU Name', 'Destination', 'Transaction Type (in/out)', 'Quantity', 'Shipping Year', 'Shipping Month', 'Shipping Day', ]
        self.transactions_file = base64.b64encode(data_to_bytes(fieldnames, data))

    def get_status_file(self, start=None, stop=None, last_day=False):
        start = (last_day and fields.Date.from_string(fields.Date.today()) - timedelta(days=1)) or start or self.start
        stop = (last_day and fields.Date.from_string(fields.Date.today())) or stop or self.stop
        now = fields.Datetime.from_string(fields.Datetime.now(self)).isoformat()
        self.status_file_fname = 'STATUS_%s.csv' % now.replace('-', '').replace('T', '_').replace(':', '')[:-2]

        Locations = self.env['stock.location'].search([
            ('to_report', '=', True),
            ('usage', 'in', ['internal']),
        ])
        Products = self.env['product.product'].search([('sale_ok', '=', True)])
        data = [product_id.get_quantities(now, location_id) for location_id in Locations for product_id in Products]

        fieldnames = ['Stock Location Name', 'SKU Name', 'Inventory At Hand', 'Inventory On The Way', 'Reported Year', 'Reported Month', 'Reported Day', ]
        self.status_file = base64.b64encode(data_to_bytes(fieldnames, data))
