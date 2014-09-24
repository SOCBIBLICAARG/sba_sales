from openerp.osv import osv,fields
from openerp.tools.translate import _
from datetime import date
from datetime import datetime
import string

class sale_stockout(osv.osv):
	_name = "sale.stockout"
	_description = "Modelo con los productos que tuvieron stockout durante la confirmacion del pedido"

	_columns = {
		'date': fields.date('Fecha'),
		'product_id': fields.many2one('product.product','Producto'),
		'sale_id': fields.many2one('sale.order','Pedido'),
		'qty': fields.integer('Cantidad'),
		}


        def _update_stock_outs(self,cr,uid,ids=None,context=None):

		sale_obj = self.pool.get('sale.order')
		sale_ids = sale_obj.search(cr,uid,[('state','=','manual')])

		for sale in sale_obj.browse(cr,uid,sale_ids,context=context):
	       		for line in sale.order_line:
                        	if line.product_id.qty_available < line.product_uom_qty :
                                	stock_out_id = self.search(cr,uid,[('sale_id','=',sale.id),('product_id','=',line.product_id.id)])
		                        if not stock_out_id:
                		                vals_stock_out = {
                                	     	        'date': str(date.today()),
                                                	'product_id': line.product_id.id,
		                                        'sale_id': sale.id,
                		                        'qty': line.product_uom_qty,
                                	               }
                                        	return_id = self.create(cr,uid,vals_stock_out)

		return True

sale_stockout()

class survey_input(osv.osv):
	_name = "survey.user_input"
	_inherit = "survey.user_input"

	_columns = {
		'opportunity_id': fields.many2one('sale.order','Opportunity'),
		}

survey_input()


class survey_survey(osv.osv):
	_name = "survey.survey"
	_inherit = "survey.survey"

	_columns = {
		'opportunity_ids': fields.one2many('sale.order','survey_id','Opportunity'),
		}

survey_survey()

class sale_order(osv.osv):
	_name = "sale.order"
	_inherit = "sale.order"

	_columns = {
	        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', required=True, readonly=True,\
				 help="Pricelist for current sales order."),
		'discount_ok': fields.boolean('Discount OK',readonly=True),
		'survey_input_id': fields.one2many('survey.user_input','opportunity_id','Survey Input'),
		'survey_id': fields.many2one('survey.survey','Survey'),
		}


	_defaults = {
		'discount_ok': False,
		# 'warehouse_id': lambda self,cr,uid, context: self.pool.get('res.users').browse(cr, uid, uid, context).partner_id.warehouse_id,
		}

	def action_quotation_send(self, cr, uid, ids, context=None):
        	'''
	        This function opens a window to compose an email, with the edi sale template message loaded by default
        	'''
		obj = self.browse(cr,uid,ids)
		if obj:
			if not self.approve_discount_so(cr,uid,ids) and not obj.discount_ok:
				raise osv.except_osv(('Alerta!'), ("El descuento necesita ser aprobado"))
				return None
			
		return super(sale_order, self).action_quotation_send(cr,uid,ids,context=context)


	def print_quotation(self, cr, uid, ids, context=None):
        	'''
	        This function prints the sales order and mark it as sent, so that we can see more easily the next step of the workflow
        	'''
		obj = self.browse(cr,uid,ids)
		if obj:
			if not self.approve_discount_so(cr,uid,ids) and not obj.discount_ok:
				raise osv.except_osv(('Alerta!'), ("El descuento necesita ser aprobado"))
				return None
	        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        	# self.signal_workflow(cr, uid, ids, 'quotation_sent')
	        return self.pool['report'].get_action(cr, uid, ids, 'sba_sales.report_saleorder_sba', context=context)
			

	def action_button_confirm(self, cr, uid, ids, context=None):
		survey_id = self.pool.get('survey.survey').search(cr,uid,[('res_model','=','sales')])
		if survey_id:
			if isinstance(survey_id,list):
				survey_id = survey_id[0]
			vals_sale_order = {
				'survey_id': survey_id
				}
			return_id = self.write(cr,uid,ids,vals_sale_order)
		return super(sale_order,self).action_button_confirm(cr,uid,ids,context)
		
        def create(self, cr, uid, vals, context=None):
		if vals['add_disc'] < 0.01:
			vals['discount_ok'] = True
		else:
			vals['discount_ok'] = False
        	return super(sale_order, self).create(cr, uid, vals, context=context)
		# if not vals['discount_ok']:
		#	raise osv.except_osv(('Warning!'), ("El descuento necesita ser aprobado"))


        def write(self, cr, uid, ids, vals, context=None):
		if ids:
			if 'discount_ok' not in vals.keys() and 'date_confirm' not in vals.keys():
		                obj = self.browse(cr, uid, ids[0], context=context)
				# if obj.state in ['draft','sent']:
				if obj.state in ['draft']:
					if obj.add_disc < 0.01:
						vals['discount_ok'] = True
					else:
						vals['discount_ok'] = False
				if 'add_disc' in vals.keys():
					if vals['add_disc'] < 0.01:
						vals['discount_ok'] = True
					else:
						vals['discount_ok'] = False

        	return super(sale_order, self).write(cr, uid, ids, vals, context=context)
	#	#if not vals['discount_ok']:
	#	#	raise osv.except_osv(('Warning!'), ("El descuento necesita ser aprobado"))

	def _check_validation_sba(self, cr, uid, ids, context = None):
                obj = self.browse(cr, uid, ids[0], context=context)
                if obj.state == 'manual' or obj.state == 'sent':
			if obj.discount_ok:
				return True
                	if obj.add_disc < 0.01:
                        	return True
			if not obj.discount_ok:
				return False
		return True


	_constraints = [(_check_validation_sba, '\n\nUd acaba de otorgar un descuento superior al descuento que se le permite otorgar.\nPor favor, pida a su superior que autorice el pedido', ['add_disc','state']),
			]

	def approve_discount(self, cr, uid, ids, context=None):
		vals = {
			'discount_ok': self.approve_discount_so(cr,uid,ids),
			'state': 'sent',
			}
		self.write(cr,uid,ids,vals)

	def approve_discount_so(self, cr, uid, ids, context=None):

        	obj = self.browse(cr, uid, ids[0], context=context)
		if obj.add_disc < 0.01:
			return True
		user_obj = self.pool.get('res.users').browse(cr,uid,uid)
		warehouse_id = self.pool.get('res.partner').browse(cr,uid,user_obj.partner_id.id).warehouse_id
		if obj.warehouse_id != warehouse_id:
			return False
	        config_adddisc = 0
        	config_credit_tolerance = 0
	        config_disc_level1 = 0
        	config_disc_level2 = 0
	        config_disc_level3 = 0
        	config_grupo_aprob1 = ''
	        config_grupo_aprob2 = ''
        	config_grupo_aprob3 = ''
	        config_ids = self.pool.get('ir.config_parameter').search(cr, uid, [('key', 'like', 'SBA')])
        	if config_ids:
	            for config in self.pool.get('ir.config_parameter').browse(cr, uid, config_ids):
        	        if config.key == 'SBA_DESCUENTO_NIVEL1':
                	    config_disc_level1 = float(config.value)
	                if config.key == 'SBA_DESCUENTO_NIVEL2':
        	            config_disc_level2 = float(config.value)
                	if config.key == 'SBA_DESCUENTO_NIVEL3':
	                    config_disc_level3 = float(config.value)
        	        if config.key == 'SBA_GRUPO_APROB_1':
                	    config_grupo_aprob1 = config.value
	                if config.key == 'SBA_GRUPO_APROB_2':
        	            config_grupo_aprob2 = config.value
                	if config.key == 'SBA_GRUPO_APROB_3':
	                    config_grupo_aprob3 = config.value
        	        if config.key == 'SBA_GRUPO_VENTAS':
                	    config_grupo_ventas = config.value
	                if config.key == 'SBA_TOLERANCIA_CREDITO1':
        	            config_credit_tolerance1 = float(config.value)
                	if config.key == 'SBA_TOLERANCIA_CREDITO2':
	                    config_credit_tolerance2 = float(config.value)
        	        if config.key == 'SBA_TOLERANCIA_CREDITO3':
                	    config_credit_tolerance3 = float(config.value)

	        user_groups = {}
	
        	group_ventas_id = self.pool.get('res.groups').search(cr, uid, [('name', '=', config_grupo_ventas)])
	        group_aprob1_id = self.pool.get('res.groups').search(cr, uid, [('name', '=', config_grupo_aprob1)])
        	group_aprob2_id = self.pool.get('res.groups').search(cr, uid, [('name', '=', config_grupo_aprob2)])
	        group_aprob3_id = self.pool.get('res.groups').search(cr, uid, [('name', '=', config_grupo_aprob3)])
        	user_groups['grupo_ventas'] = group_ventas_id
	        user_groups['group_aprob1'] = group_aprob1_id
        	user_groups['group_aprob2'] = group_aprob2_id
	        user_groups['group_aprob3'] = group_aprob3_id
        	user_list_aprob1 = self.pool.get('res.groups').read(cr, uid, group_aprob1_id, ['users'])
	        user_list_aprob2 = self.pool.get('res.groups').read(cr, uid, group_aprob2_id, ['users'])
        	user_list_aprob3 = self.pool.get('res.groups').read(cr, uid, group_aprob3_id, ['users'])
		# If UID is director, return True
               	for user_group in user_list_aprob3:
	        	if uid in user_group['users']:
				return True
		# otherwise...
	        return_value = True
        	if obj.add_disc <= config_disc_level1:
                	return_value = True
			return return_value
	        elif obj.add_disc >= config_disc_level1 and obj.add_disc < config_disc_level2:
        	        return_flag_level1 = False
                	return_flag_level2 = False
	                for user_group in user_list_aprob1:
        	            if uid in user_group['users']:
                	        return_flag_level1 = True

	                for user_group in user_list_aprob2:
        	            if uid in user_group['users']:
        	                return_flag_level2 = True
	
                	return_value = return_flag_level1 or return_flag_level2
			return return_value
	        elif obj.add_disc >= config_disc_level2 and obj.add_disc < config_disc_level3:
        	        return_flag_level2 = False
                	for user_group in user_list_aprob2:
	                    if uid in user_group['users']:
        	                return_flag_level2 = True

	                return_value = return_flag_level2
		elif obj.add_disc > config_disc_level3:
        	        return_flag_level3 = False
                	for user_group in user_list_aprob3:
	                    if uid in user_group['users']:
        	                return_flag_level3 = True

	                return_value = return_flag_level3
			return return_value
        	if not return_value:
                	return False
	        if obj.partner_id.credit == 0:
        	        return True
	        total_check_1 = obj.partner_id.credit_limit * (1 + config_credit_tolerance1 / 100) - (obj.amount_total + obj.partner_id.credit)
        	total_check_2 = obj.partner_id.credit_limit * (1 + config_credit_tolerance2 / 100) - (obj.amount_total + obj.partner_id.credit)
	        total_check_3 = obj.partner_id.credit_limit * (1 + config_credit_tolerance3 / 100) - (obj.amount_total + obj.partner_id.credit)
        	if total_check_1 < 0 and total_check_2 > 0:
                	return_flag_level1 = False
	                return_flag_level2 = False
        		for user_group in user_list_aprob1:
                	    if uid in user_group['users']:
                        	return_flag_level1 = True

	                for user_group in user_list_aprob2:
        	            if uid in user_group['users']:
                	        return_flag_level2 = True

	                return_value = return_flag_level1 or return_flag_level2
        	        if not return_value:
                	    raise osv.except_osv('Error', 'El cliente supera su limite de credito por ' + str(total_check_1 * -1) + '$')
	                    return False
        	        else:
                	    return True
	        if total_check_2 < 0 and total_check_3 > 0:
        	        return_flag_level1 = False
	                return_flag_level2 = False
        	        for user_group in user_list_aprob2:
                	    if uid in user_group['users']:
                        	return_flag_level1 = True

	                for user_group in user_list_aprob3:
        	            if uid in user_group['users']:
                	        return_flag_level2 = True

	                return_value = return_flag_level1 or return_flag_level2
        	        if not return_value:
                	    raise osv.except_osv('Error', 'El cliente supera su limite de credito por ' + str(total_check_1 * -1) + '$')
	                    return False
        	        else:
                	    return True
	        if total_check_3 < 0:
        	        return_flag_level = False
                	for user_group in user_list_aprob3:
	                    if uid in user_group['users']:
        	                return_flag_level = True

                	if not return_flag_level:
	                    raise osv.except_osv('Error', 'El cliente supera su limite de credito por ' + str(total_check_3 * -1) + '$')
        	            return False
	                else:
			    return True

sale_order()


class sale_order_line(osv.osv):
	_name = "sale.order.line"
	_inherit = "sale.order.line"

	def onchange_discount(self, cr, uid, ids, discount, context=None):
		import pdb;pdb.set_trace()
		obj = self.browse(cr,uid,ids)
		if obj.discount > discount:
			res['discount'] = discount
		else:
	        	warning = {
		            'title': _('Alerta Lista de Precios!'),
        		    'message' : _('Si cambia la lista de precios, no se modificaran los precios a los productos ya cargados.')
		        	}
        		return {'warning': warning, 'value': value}
        	return {'value': res}

        def _fnct_listprice_unit(self, cr, uid, ids, field_name, args, context=None):

                if context is None:
                    context = {}
                res = {}
		for id in ids:
        		obj = self.browse(cr, uid, id, context=context)
			if obj.product_uom_qty > 0:
		                res[obj.id] = obj.price_subtotal / obj.product_uom_qty
			else:
				res[obj.id] = 0
                return res

        #def write(self, cr, uid, ids, vals, context=None):
	#	obj = self.browse(cr,uid,ids)
	#	diff_discount = obj.discount - obj.original_discount
	#	if diff_discount > 0:
	#		order_id = obj.order_id
	#		vals = {}
	#		vals['discount_ok'] = False
	#		return_id = self.pool.get('sale.order').write(cr,uid,order_id.id,vals,context=context)
			
        #	return super(sale_order_line, self).write(cr, uid, ids, vals, context=context)

        #def create(self, cr, uid, vals, context=None):
	#	if 'discount' in vals.keys():
	#		vals['original_discount'] = vals['discount']
        #	return super(sale_order_line, self).create(cr, uid, vals, context=context)

	_columns = {
		'original_price': fields.related('product_id','list_price',string='Original Price',readonly=True),
		'original_discount': fields.float('Original Discount',readonly=True),
                'list_price_perunit': fields.function(_fnct_listprice_unit, string='Precio Publico'),
		}


sale_order_line()
