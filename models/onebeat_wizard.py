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
        readonly=True,
    )
    stocklocations_file_fname = fields.Char(
    )
    mtsskus_file = fields.Binary(
        readonly=True,
    )
    mtsskus_file_fname = fields.Char(
    )
    transactions_file = fields.Binary(
        readonly=True,
    )
    transactions_file_fname = fields.Char(
    )
    status_file = fields.Binary(
        readonly=True,
    )
    status_file_fname = fields.Char(
    )
    start = fields.Date(
        default=fields.Date.from_string(fields.Date.today()) - timedelta(days=1),
        required=True,
    )
    stop = fields.Date(
        default=fields.Date.context_today,
        required=True,
    )

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

        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

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

        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def get_transactions_file(self):
        now = fields.Datetime.from_string(fields.Datetime.now(self)).isoformat()
        self.transactions_file_fname = 'TRANSACTIONS_%s.csv' % now.replace('-', '').replace('T', '_').replace(':', '')[:-2]

        Moves = self.env['stock.move'].search([
            '|',
            ('location_id.to_report', '=', True),
            ('location_dest_id.to_report', '=', True),
            ('location_id.usage', 'in', ['supplier', 'internal', 'customer']),
            ('location_dest_id.usage', 'in', ['supplier', 'internal', 'customer']),
            ('date', '>=', self.start),
            ('date', '<', self.stop),
        ])
        data = [{
            'Origin': move_id.location_id.display_name,
            'SKU Name': move_id.product_id.default_code,
            'Destination': move_id.location_dest_id.display_name,
            'Transaction Type (in/out)': 'OUT' if move_id.location_id.usage == 'internal' else 'IN',
            'Quantity': move_id.quantity_done,
            'Shipping Year': fields.Datetime.from_string(move_id.date).isoformat().split('-')[0],
            'Shipping Month': fields.Datetime.from_string(move_id.date).isoformat().split('-')[1],
            'Shipping Day': fields.Datetime.from_string(move_id.date).isoformat().split('-')[2][:2],
        } for move_id in Moves]

        fieldnames = ['Origin', 'SKU Name', 'Destination', 'Transaction Type (in/out)', 'Quantity', 'Shipping Year', 'Shipping Month', 'Shipping Day', ]
        self.transactions_file = base64.b64encode(data_to_bytes(fieldnames, data))

        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def get_at_hand(self, product_id, location_id):
        return sum(quant_id.quantity for quant_id in self.env['stock.quant'].search([
            ('product_id', '=', product_id.id),
            ('location_id', '=', location_id.id),
        ]))

    def get_on_the_way(self, product_id, location_id):
        return sum(line.product_uom_qty for line in self.env['stock.move.line'].search([
            ('product_id', '=', product_id.id),
            ('location_id', '=', location_id.id),
            ('state', 'not in', ['done', 'draft', 'cancel']),
        ]))

    def get_status_file(self):
        now = fields.Datetime.from_string(fields.Datetime.now(self)).isoformat()
        year, month, day = now.split('-')
        day = day[:2]
        self.status_file_fname = 'STATUS_%s.csv' % now.replace('-', '').replace('T', '_').replace(':', '')[:-2]

        Locations = self.env['stock.location'].search([
            ('to_report', '=', True),
            ('usage', 'in', ['internal']),
        ])
        Products = self.env['product.product'].search([('sale_ok', '=', True)])
        data = [{
            'Stock Location Name': location_id.display_name,
            'SKU Name': product_id.default_code,
            'Inventory At Hand': max(self.get_at_hand(product_id, location_id), 0),
            'Inventory On The Way': 158,
            'Reported Year': year,
            'Reported Month': month,
            'Reported Day': day,
        } for location_id in Locations for product_id in Products]

        fieldnames = ['Stock Location Name', 'SKU Name', 'Inventory At Hand', 'Inventory On The Way', 'Reported Year', 'Reported Month', 'Reported Day', ]
        self.status_file = base64.b64encode(data_to_bytes(fieldnames, data))

        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
