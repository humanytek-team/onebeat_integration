{
    "name": "Fillrate100 Connector",
    "version": "14.0.0.1.0",
    "author": "Humanytek",
    "license": "LGPL-3",
    "depends": [
        "purchase",
        # Custom
        "onebeat_integration",
        # Custom external
        "ftp_save",
    ],
    "data": [
        # security
        # data
        "data/ir_cron.xml",
        # reports
        # views
        "views/onebeat_wizard.xml",
    ],
}
