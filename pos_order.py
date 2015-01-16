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

    def create_picking(self, cr, uid, ids, context=None):
        """Create a picking for each order and validate it."""
        picking_obj = self.pool.get('stock.picking')
        partner_obj = self.pool.get('res.partner')
        move_obj = self.pool.get('stock.move')

        for order in self.browse(cr, uid, ids, context=context):
            addr = order.partner_id and partner_obj.address_get(cr, uid, [order.partner_id.id], ['delivery']) or {}
            picking_type = order.picking_type_id
            picking_id = False
            if picking_type:
                picking_id = picking_obj.create(cr, uid, {
                    'origin': order.name,
                    'partner_id': addr.get('delivery',False),
                    'picking_type_id': picking_type.id,
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'note': order.note or "",
                    'invoice_state': 'none',
                }, context=context)
                self.write(cr, uid, [order.id], {'picking_id': picking_id}, context=context)
            location_id = order.location_id.id
            if order.partner_id:
                destination_id = order.partner_id.property_stock_customer.id
            elif picking_type:
                if not picking_type.default_location_dest_id:
                    raise osv.except_osv(_('Error!'), _('Missing source or destination location for picking type %s. Please configure those fields and try again.' % (picking_type.name,)))
                destination_id = picking_type.default_location_dest_id.id
            else:
                destination_id = partner_obj.default_get(cr, uid, ['property_stock_customer'], context=context)['property_stock_customer']

            move_list = []
            for line in order.lines:
                if line.product_id and line.product_id.type == 'service':
                    continue

                move_list.append(move_obj.create(cr, uid, {
                    'name': line.name,
                    'product_uom': line.product_id.uom_id.id,
                    'product_uos': line.product_id.uom_id.id,
                    'picking_id': picking_id,
                    'picking_type_id': picking_type.id, 
                    'product_id': line.product_id.id,
                    'product_uos_qty': abs(line.qty),
                    'product_uom_qty': abs(line.qty),
                    'state': 'draft',
                    'location_id': location_id if line.qty >= 0 else destination_id,
                    'location_dest_id': destination_id if line.qty >= 0 else location_id,
                }, context=context))
                
            if picking_id:
                picking_obj.action_confirm(cr, uid, [picking_id], context=context)
                picking_obj.force_assign(cr, uid, [picking_id], context=context)
                #picking_obj.action_done(cr, uid, [picking_id], context=context)
            elif move_list:
                move_obj.action_confirm(cr, uid, move_list, context=context)
                move_obj.force_assign(cr, uid, move_list, context=context)
                #move_obj.action_done(cr, uid, move_list, context=context)
        return True

    def action_ticket(self, cr, uid, ids, context=None):
        picking_obj = self.pool.get('stock.picking')
        if len(ids)!= 1:
            raise osv.except_osv(_('Error!'), _("Print one ticket at time"))
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
                        "description": "[%s]" % (line.product_id.ean13 or
                                                 line.product_id.sba_code or 0),
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
                _logger.info('Printer return %s' % r)
                document_type = r.get('document_type', '?')
                point_of_sale = journal.point_of_sale or 0
                document_number = r.get('document_number', '?')
                pos_reference = ("%s:%04i-%08i" % (document_type, point_of_sale,
                                                   int(document_number)) if
                                 unicode(document_number).isnumeric() else
                                 'unknown')
                self.write(cr, uid, ids, {'pos_reference': pos_reference})
                if r.get('command','') == 'cancel_fiscal_ticket':
                    if (o.picking_type_id):
                        self.cancel_order(cr, uid, ids, context=context)
                    else:
                        self.write(cr, uid, ids, {'state': 'cancel'},
                                   context=context)
                else:
                    picking_obj.action_done(cr, uid, [o.picking_id.id], context=context)
                    self.create_account_move(cr, uid, ids, context=context)
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
