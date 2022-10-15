{
    'name': '企业微信模块-基础',
    'version': '14.0.01',
    'summary': '对接企业微信接口',
    'description': '',
    'category': 'WorkWX',
    'author': 'grey27',
    "license": "LGPL-3",
    "images": ["static/description/banner.png"],
    'depends': ['base', 'web', 'auth_oauth', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/assets.xml',
        'views/workwx_views.xml',
        'views/workwx_hr_views.xml',
        'views/workwx_application_views.xml',
        'views/workwx_message_views.xml',
        'views/workwx_setting_views.xml',
        'wizard/workwx_wizard_views.xml',
    ],
    'external_dependencies': {
        'python': [
            'cacheout',
            'pycrypto',
            'xmltodict',
        ]
    },
}
