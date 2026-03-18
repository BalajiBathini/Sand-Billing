{
    'name': 'Sand Billing System',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Billing system for sand selling with QR code and thermal printing',
    'author': 'BalajiBathini',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'stock',
    ],
    'data': [
        'data/sequences.xml',
        'security/ir.model.access.csv',
        'views/SAND_BILLING_views.xml',
        'views/sand_mobile_views.xml',
        'views/sand_mobile_views_form.xml',
        'reports/sand_receipt_report.xml',
        'reports/sand_receipt_template.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

