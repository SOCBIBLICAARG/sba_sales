# -*- coding: utf-8 -*-
import logging
import time

from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp
import openerp.addons.product.product

from openerp.addons.l10n_ar_fpoc.invoice import document_type_map, responsability_map

_logger = logging.getLogger(__name__)

class pos_order(osv.osv):
    _inherit = "pos.order"

    def action_ticket(self, cr, uid, ids, context=None):

        for o in self.browse(cr, uid, ids):
            journal = o.session_id.config_id.journal_id
            if journal.use_fiscal_printer:
                debit_note = (o.amount_total < 0)
                factor = -1 if debit_note else 1
                ticket={
                    "turist_ticket": False,
                    "debit_note": debit_note,
                    "partner": {
                        "name": o.partner_id.name,
                        "name_2": "",
                        "address": o.partner_id.street,
                        "address_2": o.partner_id.city,
                        "address_3": o.partner_id.country_id.name,
                        "document_type": document_type_map.get(o.partner_id.document_type_id.code, "D"),
                        "document_number": o.partner_id.document_number,
                        "responsability": responsability_map.get(o.partner_id.responsability_id.code, "F"),
                    },
                    "related_document": o.picking_id and o.picking_id.name or _("No picking"),
                    "related_document_2": o.picking_id and o.picking_type_id and o.picking_type_id.name or "",
                    "turist_check": "",
                    "lines": [ ],
                    "payments": [ ],
                    "cut_paper": True,
                    "electronic_answer": False,
                    "print_return_attribute": False,
                    "current_account_automatic_pay": False,
                    "print_quantities": True,
                    "tail_no": 1 if o.user_id.name else 0,
                    "tail_text": _("Saleman: %s") % o.user_id.name if o.user_id.name else "",
                    "tail_no_2": 0,
                    "tail_text_2": "",
                    "tail_no_3": 0,
                    "tail_text_3": "",
                }
                for line in o.lines:
                    vat_rate = (line.price_subtotal_incl - line.price_subtotal) * factor
                    ticket["lines"].append({
                        "item_action": "sale_item",
                        "as_gross": False,
                        "send_subtotal": True,
                        "check_item": False,
                        "collect_type": "q",
                        "large_label": "",
                        "first_line_label": "",
                        "description": "",
                        "description_2": "",
                        "description_3": "",
                        "description_4": "",
                        "item_description": line.product_id.name,
                        "quantity": line.qty * factor,
                        "unit_price": line.price_unit,
                        "vat_rate": vat_rate,
                        "fixed_taxes": 0,
                        "taxes_rate": 0
                    })
                    if line.discount > 0: ticket["lines"].append({
                        "item_action": "discount_item",
                        "as_gross": False,
                        "send_subtotal": True,
                        "check_item": False,
                        "collect_type": "q",
                        "large_label": "",
                        "first_line_label": "",
                        "description": "",
                        "description_2": "",
                        "description_3": "",
                        "description_4": "",
                        "item_description": "%5.2f%%" % line.discount,
                        "quantity": line.quantity * factor,
                        "unit_price": line.price_unit * (line.discount/100.),
                        "vat_rate": vat_rate * (line.discount/100.),
                        "fixed_taxes": 0,
                        "taxes_rate": 0
                    })
                for st in o.statement_ids:
                    ticket["payments"].append({
                        "type": "pay" if  (o.amount_total > 0) else "null_pay",
                        "description": st.name,
                        "extra_description": False,
                        "amount": st.amount,
                    })
 
                r = journal.make_fiscal_ticket(ticket)[journal.id]
                if r.get('command','') == 'cancel_fiscal_printer':
                    import pdb; pdb.set_trace()
                    raise osv.except_osv(_('Error!'), _("Ticket %s %s is cancelled.") %
                                        (r.get('document_type', '?'),
                                         r.get('document_number', '?')))

                _logger.info('Printer return %s' % r)
        self.create_account_move(cr, uid, ids, context=context)
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
