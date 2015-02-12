from openerp.osv import osv,fields
from datetime import date

class account_invoice(osv.osv):
	_name = "account.invoice"
	_inherit = "account.invoice"

	def _convert_ref(self, ref):
        return (ref or '').replace('/','')

account_invoice()
