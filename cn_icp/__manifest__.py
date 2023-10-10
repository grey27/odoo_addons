{
    'name': '中国ICP备案号',
    'version': '16.0.1.0',
    'summary': '在登陆界面展示ICP号',
    'images': ['static/description/banner.png'],
    'description': '''
    使用方法：
        在 技术 -> 设置 -> 系统参数 中找到变量名cn_icp.display_name并设置自己的ICP备案号

    温馨提示：
        1.监管只要求网站首页设置ICP（无账号他们也无法进入其他页面），所以只修改了登录页面一个地方\n  
        2.这个模块只适用于未安装website模块，否则首页不再是登录页面了  

    如有其他需求欢迎联系开发：624854240@qq.com
    ''',
    'author': 'grey27',
    "license": "LGPL-3",
    'depends': ['base', 'web'],
    'data': [
        'data/icp_data.xml',
        'views/icp_template.xml',
    ],
}
