# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'SBA Sales Customizations',
    'version': '0.1.7.19',
    'category': 'Tools',
    'complexity': "easy",
    'description': "",
    'author': 'Gustavo Orrillo',
    'website': 'http://business.moldeo.coop',
    'depends': ['base','sale','crm','product','stock','l10n_ar_invoice','fl_additional_discount','sales_team','survey'],
    'init_xml': [],
    'update': [
	],
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
    ],
    'demo_xml': [],
    'test':[
    ],
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
