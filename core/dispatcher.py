# -*- coding: utf-8 -*-
# Главный диспетчер URL-ов

from apps import admin, customers
from core import session
import logging,pickle

def dispatch(env):
	""" Главный диспетчер """
	content = ''
	# админка
	if env.path.current() == "_adm":
		# перейти в админку
		env.path.next()
		content = admin.dispatch(env)
	elif env.path.current() == "app":
		# перейти в шаблоны
		env.path.next()
		if not env.path.current():
			env.redirect('/saint-petersburg/')
		else:
			content = customers.dispatch(env)
	else:
		full_r=[]
		short_r={}
		for region in env.regions['regions'].keys():
			if env.regions['regions'][region]['lock']==0:
				full_r.append(env.regions['regions'][region]['fulluri'])
				short_r[env.regions['regions'][region]['shorturi']]=env.regions['regions'][region]['fulluri']
		# сделать редирект при наличии короткого имени
		if env.path.current() in short_r.keys():
			env.redirect('/'+str(short_r[env.path.current()])+'/')
		# продолжить при наличии полного имени
		elif env.path.current() in full_r or env.path.current()=='saint-petersburg':
			env.region_current=env.path.current()
			env.path.next()
			content = customers.dispatch(env)
		else:
			# затычка
			logging.debug("=unknown region=%s==",env.path.current())
			env.redirect('/saint-petersburg/')
	return content
