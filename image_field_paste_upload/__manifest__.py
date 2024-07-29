{
    'name': 'Image Field Paste Upload',
    'version': '16.0.1.0',
    'summary': 'Image field adds an input box for pasting and uploading images',
    'images': ['static/description/banner.png'],
    'description': '''
    Image field adds an input box for pasting and uploading images
    ''',
    'author': 'grey27',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [
    ],
    "assets": {
        "web.assets_backend": [
            "/image_field_paste_upload/static/src/js/web_widget_image_paste_upload.js",
            "/image_field_paste_upload/static/src/xml/web_widget_image_paste_upload.xml",
        ]
    },
}
