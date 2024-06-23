{
    'name': 'Image Field Paste Upload',
    'version': '14.0.1.0',
    'summary': 'Image field adds an input box for pasting and uploading images',
    'images': ['static/description/banner.png'],
    'description': '''
    Image field adds an input box for pasting and uploading images
    ''',
    'author': 'grey27',
    'depends': ['web'],
    'data': [
        'views/assets.xml',
    ],
    'qweb': [
        'static/src/xml/web_widget_image_paste_upload.xml',
    ],
}
