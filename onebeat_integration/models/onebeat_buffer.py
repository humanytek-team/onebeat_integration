from odoo import fields, models


class OnebeatBuffer(models.Model):
    _name = "onebeat.buffer"
    _description = "Product Location Buffer"

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company.id,
        index=True,
        required=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        required=True,
        index=True,
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        required=True,
        index=True,
    )
    buffer_size = fields.Float(
        required=True,
    )
    replenishment_time = fields.Integer(
        required=True,
    )

    def generate_all_combinations(
        self,
        products,
        locations,
        company=None,
        default_buffer=0,
    ):
        """Generate (if needed) all combinations of products and locations with a buffer and a replenishment time.

        Args:
            products (List[product.product]): Products to generate combinations for.
            locations (List[stock.location]): Locations to generate combinations for.
            company (res.company, optional): Company to generate combinations for. Defaults to None.
            default_buffer (float, optional): Default buffer size to new buffers. Defaults to 0.

        Returns:
            [type]: [description]
        """
        if not company:
            company = self.env.company
        buffers = self.search(
            [
                ("company_id", "=", company.id),
                ("product_id", "in", products.ids),
                ("location_id", "in", locations.ids),
            ]
        )
        current_set = {(buffer.product_id.id, buffer.location_id.id) for buffer in buffers}
        all_set = {(product.id, location.id) for product in products for location in locations}
        to_create = all_set - current_set
        replenishment_times = {
            product.id: product.seller_ids[0].delay if product.seller_ids else product.produce_delay
            for product in products
        }
        news = self.create(
            [
                {
                    "company_id": company.id,
                    "product_id": tuple[0],
                    "location_id": tuple[1],
                    "buffer_size": default_buffer,
                    "replenishment_time": replenishment_times[tuple[0]],
                }
                for tuple in to_create
            ]
        )
        return buffers + news

    def update_buffer(self, buffers):
        pass  # TODO
