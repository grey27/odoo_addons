{
    'name': 'Downlad All Attachment',
    'version': '1.0',
    'summary': 'Download all attachments from a record',
    'description': 'This module adds a download button to the attachment box to pack all attachments for download',
    'category': 'web',
    'author': 'grey27',
    "license": "LGPL-3",
    "images": ["static/description/banner.png"],
    'depends': ['mail'],
    'data': ['views/assets.xml'],
    'qweb': ["static/src/xml/download_all_attachment.xml"],
    'installable': True,
    'auto_install': False
}
