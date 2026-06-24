# -*- coding: utf-8 -*-
{
    'name': 'Device Approval Security',
    'version': '18.0.1.0.0',
    'category': 'Security',
    'summary': 'Restrict login to admin-approved devices only',
    'description': """
        Device Approval Security Module for Odoo 19
        =============================================
        Features:
        - Device fingerprinting on login
        - Admin approval workflow for new devices
        - Device limit per user
        - Email notifications for new device attempts
        - OTP-based self-service device approval
        - Login history tracking
        - Device revocation
        - Suspicious login alerts
    """,
    'author': 'BalajiBathini',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'security/device_approval_security.xml',
        'data/mail_template_data.xml',
        'data/ir_config_param_data.xml',
        'views/res_user_device_views.xml',
        'views/device_login_history_views.xml',
        'views/res_users_views.xml',
        'views/device_approval_menus.xml',
        'wizard/device_otp_wizard_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'device_approval/static/src/css/device_approval.css',
            'device_approval/static/src/js/device_fingerprint.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
