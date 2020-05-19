# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_quantities(self, today, location_id):
        quantities = self._compute_quantities_dict2([location_id.id])
        return {
            'Stock Location Name': location_id.display_name,
            'SKU Name': self.default_code,
            'Inventory At Hand': quantities['qty_available'],
            'Inventory On The Way': quantities['outgoing_qty'],
            'Reported Year': today.split('-')[0],
            'Reported Month': today.split('-')[1],
            'Reported Day': today.split('-')[2],
        }

    def _compute_quantities_dict2(self, location_ids):
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations_new(location_ids)
        domain_quant = [('product_id', 'in', self.ids)] + domain_quant_loc
        # only to_date as to_date will correspond to qty_available

        domain_move_in = [('product_id', 'in', self.ids)] + domain_move_in_loc
        domain_move_out = [('product_id', 'in', self.ids)] + domain_move_out_loc

        Move = self.env['stock.move']
        Quant = self.env['stock.quant']
        domain_move_in_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_in
        domain_move_out_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_out
        moves_in_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        moves_out_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        quants_res = dict((item['product_id'][0], item['quantity']) for item in Quant.read_group(domain_quant, ['product_id', 'quantity'], ['product_id'], orderby='id'))

        rounding = self.uom_id.rounding
        qty_available = quants_res.get(self.id, 0.0)
        res = {
            'qty_available': float_round(qty_available, precision_rounding=rounding),
            'incoming_qty': float_round(moves_in_res.get(self.id, 0.0), precision_rounding=rounding),
            'outgoing_qty': float_round(moves_out_res.get(self.id, 0.0), precision_rounding=rounding),
        }

        return res
