{
    "name": "OneBeat integration",
    "version": "14.0.1.0.0",
    "author": "Humanytek",
    "license": "LGPL-3",
    "depends": [
        "mrp",
        "purchase",
        "stock",
    ],
    "data": [
        # security
        "security/ir.model.access.csv",
        # data
        "data/ir_cron.xml",
        # reports
        # views
        "views/onebeat_buffer.xml",
        "views/onebeat_wizard.xml",
        "views/product_template.xml",
        "views/res_company.xml",
        "views/stock_location.xml",
    ],
}
