from openerp.osv import osv,fields
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

