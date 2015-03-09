# -*- coding: utf-8 -*-
import logging

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.addons.l10n_ar_fpoc.invoice \
    import document_type_map, responsability_map

_logger = logging.getLogger(__name__)


class pos_order_line(osv.osv):
    _inherit = "pos.order.line"

    def onchange_product_id(self, cr, uid, ids, pricelist, product_id, qty=0,
                            partner_id=False, context=None):
        context = context or {}
        if not product_id:
            return {}
        if not pricelist:
            raise osv.except_osv(
                _('No Pricelist!'),
                _('You have to select a pricelist in the sale form !\n'
                  'Please set one before choosing a product.'))

        base_pricelist = self.pool.get('product.pricelist').search(
            cr,
            uid,
            [('name', 'ilike', 'CONSUMIDOR FINAL')]
        )
        if not base_pricelist:
            raise osv.except_osv(
                _('No Pricelist base!'),
                _('You have to create a "CONSUMIDOR FINAL" ',
                  'price list to continue!'))

        price_base = self.pool.get('product.pricelist').price_get(
            cr, uid, base_pricelist, product_id, qty or 1.0, partner_id
        )[base_pricelist[0]]

        price = self.pool.get('product.pricelist').price_get(
            cr, uid, [pricelist], product_id, qty or 1.0, partner_id
        )[pricelist]

        discount = (1. - (price / price_base)) * 100

        result = self.onchange_qty(
            cr, uid, ids, product_id, discount, qty, price, context=context
        )
        result['value']['price_unit'] = price_base
        result['value']['discount'] = discount
        return result


class pos_order(osv.osv):
    _inherit = "pos.order"

    _columns = {
        'origin_id': fields.many2one('pos.order', 'Origin'),
    }

    def create_picking(self, cr, uid, ids, context=None):
        """Create a picking for each order and validate it."""
        picking_obj = self.pool.get('stock.picking')
        partner_obj = self.pool.get('res.partner')
        move_obj = self.pool.get('stock.move')

        for order in self.browse(cr, uid, ids, context=context):
            if (order.amount_total >= 25000):
                raise osv.except_osv(_('Error!'),
                                     _("Total must less than 25000 $"))

            addr = order.partner_id and partner_obj.address_get(
                cr, uid, [order.partner_id.id], ['delivery']) or {}
            picking_type = order.picking_type_id
            picking_id = False
            if picking_type:
                picking_id = picking_obj.create(cr, uid, {
                    'origin': order.name,
                    'partner_id': addr.get('delivery', False),
                    'picking_type_id': picking_type.id,
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'note': order.note or "",
                    'invoice_state': 'none',
                }, context=context)
                self.write(cr, uid, [order.id],
                           {'picking_id': picking_id}, context=context)
            location_id = order.location_id.id
            if order.partner_id:
                destination_id = order.partner_id.property_stock_customer.id
            elif picking_type:
                if not picking_type.default_location_dest_id:
                    raise osv.except_osv(
                        _('Error!'),
                        _('Missing source or destination location for picking '
                          'type %s. '
                          'Please configure those fields and try again.' %
                          (picking_type.name,)))
                destination_id = picking_type.default_location_dest_id.id
            else:
                destination_id = partner_obj.default_get(
                    cr, uid, ['property_stock_customer'],
                    context=context)['property_stock_customer']

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
                    'location_id': location_id
                    if line.qty >= 0 else destination_id,
                    'location_dest_id': destination_id
                    if line.qty >= 0 else location_id,
                }, context=context))

            if picking_id:
                picking_obj.action_confirm(
                    cr, uid, [picking_id], context=context)
                picking_obj.force_assign(
                    cr, uid, [picking_id], context=context)
                picking_obj.action_done(
                    cr, uid, [picking_id], context=context)
            elif move_list:
                move_obj.action_confirm(
                    cr, uid, move_list, context=context)
                move_obj.force_assign(
                    cr, uid, move_list, context=context)
                move_obj.action_done(
                    cr, uid, move_list, context=context)
        return True

    def create_invoice(self, cr, uid, ids, context=None):
        """Create invoice from sale order if session require it."""
        inv_obj = self.pool.get('account.invoice')
        inv_line_obj = self.pool.get('account.invoice.line')
        product_obj = self.pool.get('product.product')
        for o in self.browse(cr, uid, ids):
            # Check if it is a ticket for fiscal printer
            journal = o.session_id.config_id.journal_id
            if not (journal.use_fiscal_printer and
                    o.session_id.config_id.iface_invoicing):
                continue

            # Prepare data to build invoice
            partner = journal.fiscal_printer_anon_partner_id \
                if not o.partner_id else o.partner_id

            acc = partner.property_account_receivable.id

            credit_note = (o.amount_total < 0)
            o_type = 'out_invoice' if not credit_note else 'out_refund'

            # Build invoice
            vals = {
                'name': o.name,
                'internal_number': o.pos_reference,
                'number': o.pos_reference,
                'origin': o.name,
                'account_id': acc,
                'journal_id': o.sale_journal.id or None,
                'type': o_type,
                'reference': o.name,
                'partner_id': partner.id,
                'comment': o.note or '',
                'currency_id': o.pricelist_id.currency_id.id
            }
            vals.update(inv_obj.onchange_partner_id(
                cr, uid, [], o_type, partner.id)['value'])
            if not vals.get('account_id', None):
                vals['account_id'] = acc
            inv_id = inv_obj.create(cr, uid, vals, context=context)
            for line in o.lines:
                vals = {
                    'invoice_id': inv_id,
                    'product_id': line.product_id.id,
                    'quantity': abs(line.qty),
                }
                inv_name = product_obj.name_get(
                    cr, uid, [line.product_id.id], context=context)[0][1]
                vals.update(inv_line_obj.product_id_change(
                    cr, uid, [], line.product_id.id,
                    line.product_id.uom_id.id,
                    line.qty, partner_id=partner.id,
                    fposition_id=partner.property_account_position.id
                )['value'])
                vals['price_unit'] = abs(line.price_unit)
                vals['discount'] = abs(line.discount)
                vals['name'] = inv_name
                vals['invoice_line_tax_id'] = [
                    (6, 0, [x.id for x in line.product_id.taxes_id])]
                inv_line_obj.create(cr, uid, vals, context=context)
            inv_obj.button_reset_taxes(cr, uid, [inv_id], context=context)
            self.signal_workflow(cr, uid, [o.id], 'invoice')
            inv_obj.signal_workflow(cr, uid, [inv_id], 'invoice_open')

            # Finally update invoice in pos_order
            self.write(cr, uid, [o.id], { 'invoice_id': inv_id })

    def refund(self, cr, uid, ids, context=None):
        r = super(pos_order, self).refund(cr, uid, ids, context=context)
        self.write(cr, uid, r['res_id'], {'origin_id': ids[0]})
        return r

    def build_ticket_factura(self, cr, uid, ids, context=None):
        r = {}
        for o in self.browse(cr, uid, ids):
            ticket = {
                "turist_ticket": False,
                "debit_note": False,
                "partner": {
                    "name": o.partner_id.name or "",
                    "name_2": "",
                    "address": o.partner_id.street or "",
                    "address_2": o.partner_id.city or "",
                    "address_3": o.partner_id.country_id.name or "",
                    "document_type": document_type_map.get(
                        o.partner_id.document_type_id.code, "D"),
                    "document_number": o.partner_id.document_number,
                    "responsability": responsability_map.get(
                        o.partner_id.responsability_id.code, "F"),
                },
                "related_document": o.picking_id and o.picking_id.name
                or _("No picking"),
                "related_document_2": o.picking_id and o.picking_type_id
                and o.picking_type_id.name or "",
                "turist_check": "",
                "lines": [],
                "payments": [],
                "cut_paper": True,
                "electronic_answer": False,
                "print_return_attribute": False,
                "current_account_automatic_pay": False,
                "print_quantities": True,
                "tail_no": 1 if o.user_id.name else 0,
                "tail_text": _("Saleman: %s") % o.user_id.name
                if o.user_id.name else "",
                "tail_no_2": 0,
                "tail_text_2": "",
                "tail_no_3": 0,
                "tail_text_3": "",
            }
            for line in o.lines:
                vat_rate = ([t.amount
                             for t in line.product_id.product_tmpl_id.taxes_id
                             if 'IVA' in t.ref_tax_code_id.name] + [0])[0] * 100
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
                    "quantity": line.qty,
                    "unit_price": line.price_unit,
                    "vat_rate": vat_rate,
                    "fixed_taxes": 0,
                    "taxes_rate": 0
                })
                if line.discount > 0:
                    ticket["lines"].append({
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
                        "quantity": line.qty,
                        "unit_price": line.price_unit * (
                            line.discount/100.),
                        "vat_rate": vat_rate * (
                            line.discount/100.),
                        "fixed_taxes": 0,
                        "taxes_rate": 0
                    })
            for st in o.statement_ids:
                ticket["payments"].append({
                    "null_pay": (o.amount_total < 0),
                    "include_in_arching": False,
                    "card_pay": False,
                    "description": st.journal_id.name,
                    "extra_description": False,
                    "amount": st.amount,
                })
            r[o.id] = ticket
        return r

    def build_ticket_notacredito(self, cr, uid, ids, context=None):
        r = {}
        for o in self.browse(cr, uid, ids):
            ticket = {
                "turist_ticket": False,
                "debit_note": False,
                "partner": {
                    "name": o.partner_id.name or "Consumidor Final",
                    "name_2": "",
                    "address": o.partner_id.street or "Consumidor Final",
                    "address_2": o.partner_id.city or "",
                    "address_3": o.partner_id.country_id.name or "",
                    "document_type": document_type_map.get(
                        o.partner_id.document_type_id.code, "D"),
                    "document_number": o.partner_id.document_number or "0",
                    "responsability": responsability_map.get(
                        o.partner_id.responsability_id.code, "F"),
                },
                "related_document": o.picking_id and o.picking_id.name
                or _("No picking"),
                "related_document_2": o.picking_id and o.picking_type_id
                and o.picking_type_id.name or "",
                "origin_document": o.origin_id.pos_reference
                if o.origin_id else _("Unknown"),
                "lines": [],
                "payments": [],
                "cut_paper": True,
                "electronic_answer": False,
                "print_return_attribute": False,
                "current_account_automatic_pay": False,
                "print_quantities": True,
                "tail_no": 1 if o.user_id.name else 0,
                "tail_text": _("Saleman: %s") % o.user_id.name
                if o.user_id.name else "",
                "tail_no_2": 0,
                "tail_text_2": "",
                "tail_no_3": 0,
                "tail_text_3": "",
                "sign_no": 3,
            }
            for line in o.lines:
                vat_rate = ([t.amount
                             for t in line.product_id.product_tmpl_id.taxes_id
                             if 'IVA' in t.ref_tax_code_id.name] + [0])[0] * 100
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
                    "quantity": -line.qty,
                    "unit_price": line.price_unit,
                    "vat_rate": vat_rate,
                    "fixed_taxes": 0,
                    "taxes_rate": 0
                })
                if line.discount > 0:
                    ticket["lines"].append({
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
                        "quantity": -line.qty,
                        "unit_price": line.price_unit * (
                            line.discount/100.),
                        "vat_rate": vat_rate,
                        "fixed_taxes": 0,
                        "taxes_rate": 0
                    })
            for st in o.statement_ids:
                ticket["payments"].append({
                    "null_pay": False,
                    "include_in_arching": False,
                    "card_pay": False,
                    "description": st.journal_id.name,
                    "extra_description": False,
                    "amount": -st.amount,
                })
            r[o.id] = ticket
        return r

    def action_ticket(self, cr, uid, ids, context=None):
        """
        Print the ticket and generate the invoice.
        """
        picking_obj = self.pool.get('stock.picking')
        if len(ids) != 1:
            raise osv.except_osv(_('Error!'), _("Print one ticket at time"))
        for o in self.browse(cr, uid, ids):
            # Verify if a ticket for printer
            # and if pos_reference is not defined
            journal = o.session_id.config_id.journal_id
            if journal.use_fiscal_printer and not o.pos_reference:
                # Check if amount is valid
                if (o.amount_total >= 25000):
                    raise osv.except_osv(_('Error!'),
                                         _("Total must less than 25000 $"))

                # If amount is negative is a credit note else an invoice.
                credit_note = (o.amount_total < 0)
                # Print ticket
                if credit_note:
                    ticket = o.build_ticket_notacredito()[o.id]
                    r = journal.make_ticket_notacredito(ticket)[journal.id]
                else:
                    ticket = o.build_ticket_factura()[o.id]
                    r = journal.make_ticket_factura(ticket)[journal.id]
                _logger.info('Printer return %s' % r)

                # Verifing if the ticket was cancelled
                ticket_canceled = r and r.get('error', 'x') == 'ticket canceled'
                if r and 'error' in r and not ticket_canceled:
                    # Raise if an error and not cancelation happen
                    raise osv.except_osv(
                        _('Printer Error!'),
                        _('Printer return: %s') % r['error'])
                if 'document_type' not in r or 'document_number' not in r:
                    raise osv.except_osv(
                        _('Printer Error!'),
                        _('No number was assigned!'))

                # Generate ticket number
                document_type = r['document_type']
                point_of_sale = (journal.point_of_sale or
                                 journal.fiscal_printer_id.pointOfSale or
                                 0)
                document_number = int(r['document_number'])
                pos_reference = ("%s%s-%04i-%08i" % (
                    "NC" if credit_note else "F",
                    document_type, point_of_sale,
                    int(document_number)))

                # Store ticket number
                self.write(cr, uid, ids, {'pos_reference': pos_reference})

                # If ticket was canceled, cancel pos_order
                if r.get('command', '') == 'cancel_ticket_factura':
                    if (o.picking_type_id):
                        self.cancel_order(cr, uid, ids, context=context)
                    else:
                        self.write(cr, uid, ids, {'state': 'cancel'},
                                   context=context)
                else:
                    # Move stock products and create moves account
                    picking_obj.action_done(cr, uid, [o.picking_id.id],
                                            context=context)
                    self.create_account_move(cr, uid, ids, context=context)

            if journal.use_fiscal_printer and o.pos_reference:
                # Create the invoice
                inv_id = self.create_invoice(cr, uid, ids, context=context)

        return True

pos_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
