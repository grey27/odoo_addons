{
    'name': '下载文件动作',
    'version': '16.0.1.0',
    'summary': '新增一个下载文件的动作类型',
    'images': ['static/description/banner.png'],
    'description': '''
    在odoo中经常遇到文件下载的需求，但是普通的按钮方法不能做到直接返回文件流实现下载功能
    本插件新增了一个新的前端动作类型，可以通过返回文件流达到前端直接下载文件的需求
    使用方法：
    def download_file(self):
        # 文件流生成代码
        return {
        
        }

    如有其他需求欢迎联系开发：624854240@qq.com
    ''',
    'author': 'grey27',
    "license": "LGPL-3",
    'depends': ['base', 'web'],
    'data': [
        'views/icp_template.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "/web_download_action/static/src/js/web_download_action.js",
        ]
    },
}
