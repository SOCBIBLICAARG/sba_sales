# -*- coding: utf-8 -*-
{
    'name': 'SBA Sales Customizations',
    'version': '0.1.7.23',
    'category': 'Tools',
    'complexity': "easy",
    'description': "",
    'author': 'Gustavo Orrillo',
    'website': 'http://business.moldeo.coop',
    'depends': [
        'base',
        'sale',
        'crm',
        'product',
        'stock',
        'l10n_ar_invoice',
        'fl_additional_discount',
        'sales_team',
        'survey',
        'point_of_sale',
        'l10n_ar_fpoc_pos'
    ],
    'init_xml': [],
    'update': [],
    'data': [
        'partner_view.xml',
        'product_view.xml',
        'crm_view.xml',
        'sale_view.xml',
        'sale_report.xml',
        'user_assign.xml',
        'sale_report_discount_view.xml',
        'ir_cron.xml',
        'views/report_saleorder_sba.xml',
        'views/pos_order_view.xml',
    ],
    'demo_xml': [],
    'test':[
        'tests/region.yml',
        'tests/users.yml',
        'tests/sale_teams.yml',
        'tests/products.yml',
        'tests/partners.yml',
        'tests/lead2oportunity2win.yml',
        'tests/win2sale.yml',
        'tests/sale.yml',
    ],
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
