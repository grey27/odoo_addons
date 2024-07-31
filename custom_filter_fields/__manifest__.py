{
    'name': 'Custom Filter Fields',
    'version': '16.0.1.0',
    'summary': '',
    'images': ['static/description/banner.png'],
    'description': '''
    Adds an input box filter field to the custom filter field. 
    To resolve the need for quick query of fields when there are too many fields.
    ''',
    'author': 'grey27',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [
    ],
    "assets": {
        "web.assets_backend": [
            "/custom_filter_fields/static/src/js/custom_filter_fields.js",
            "/custom_filter_fields/static/src/xml/custom_filter_fields.xml",
        ]
    },
}
