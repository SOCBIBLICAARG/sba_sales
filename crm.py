from openerp.osv import osv,fields
from datetime import date,timedelta,time,datetime
from time import strftime,gmtime

class crm_lead(osv.osv):
	_name = "crm.lead"
	_inherit = "crm.lead"

	_columns = {
	       'date_deadline': fields.date('Expected Closing', help="Estimate of the date on which the opportunity will be won.",required=True),
	       'categ_ids': fields.many2many('crm.case.categ', 'crm_lead_category_rel', 'lead_id', 'category_id', 'Tags', \
	        	    domain="['|', ('section_id', '=', section_id), ('section_id', '=', False), ('object_id.model', '=', 'crm.lead')]",\
			 help="Classify and analyze your lead/opportunity categories like: Training, Service",required=True),
		}

	def _check_date(self, cr, uid, ids, context=None):
        	obj = self.browse(cr, uid, ids[0], context=context)
		if not obj.date_deadline:
			return False
	        if obj.date_deadline < obj.date_action:
        	    return False
	        return True

	_constraints = [
        	(_check_date, 'Deadline should be higher than next action date.', ['date_deadline']),
	    ]

	_defaults = {
		'date_deadline': str(date.today()+timedelta(days=15)),
		# 'date_deadline': lambda *a: strftime("%Y-%m-%d", gmtime()),
		}
	
crm_lead()
