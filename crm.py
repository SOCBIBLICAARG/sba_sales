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

	def create(self, cr, uid, vals, context=None):
                opportunity_id = super(crm_lead, self).create(cr, uid, vals, context=context)
                if 'date_deadline' in vals.keys():
			alarm_id = self.pool.get('calendar.alarm').search(cr,uid,[('name','=','1 day mail')])
			if not alarm_id:
				alarm_id = [1]	
			vals_event = {
				'allday': True,
				'start_date': vals['date_deadline'],
				'stop_date': vals['date_deadline'],
				'state': 'open',
				'description': 'Vencimiento oportunidad ' + vals['name'] + '\nMonto estimado: ' + str(vals['planned_revenue'] or 0),
				'name': vals['name'],
				'opportunity_id': opportunity_id,
				'alarm_id': [(6,0,alarm_id)],
				}	
			event_id = self.pool.get('calendar.event').create(cr,uid,vals_event)
		return opportunity_id

	def write(self, cr, uid, ids, vals, context=None):
                return_id = super(crm_lead, self).write(cr, uid, ids, vals, context=context)
                if 'date_deadline' in vals.keys():
			for opportunity_id in ids:
				event_id = self.pool.get('calendar.event').search(cr,uid,[('opportunity_id','=',opportunity_id)])
				vals_event = {
					'start_date': vals['date_deadline'],
					'stop_date': vals['date_deadline'],
					}
				if event_id:
					event_id = self.pool.get('calendar.event').write(cr,uid,event_id,vals_event)
		return return_id


	_constraints = [
        	(_check_date, 'Deadline should be higher than next action date.', ['date_deadline']),
	    ]

	_defaults = {
		'date_deadline': str(date.today()+timedelta(days=15)),
		# 'date_deadline': lambda *a: strftime("%Y-%m-%d", gmtime()),
		}
	
crm_lead()
