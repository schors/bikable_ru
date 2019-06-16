# -*- coding: utf-8 -*-
""" Приложение АДМИНКА/ГОРОДА """

import logging,re,sys,md5,time,random,pickle,fcntl, os,tempfile, json
from core import mailtools

BLOCK_SIZE=1024

def dispatch( env ):
	""" Города """
	data = {
		"path" : env.path.current(),
		"session" : env.session.data,
		"error" : {}
	}
	tmpl = env.jinja.get_template("admin/regions.html")
	# если просто регионы, то список
	if not env.path.current():
		# файл с сортировкой
		sortfilename=env.conf.base_path+env.conf.region_conf+"/.region_sort"
		sort=[]
		if os.path.exists(sortfilename):
			with open(sortfilename,'r') as f:
				sort=json.load(f)
				f.close()
		if env.req.has_key("name"):
		# проверить, не хотим ли завести новый регион
			name = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("name",None).decode('utf8').strip().replace(":","").replace('"',"&quot;").replace('>',"&gt;").replace('<',"&lt;"))
			if not name:
				data['error']['name']='empty'
			elif name.__len__()>200:
				data['error']['name']='invalid'
			fulluri = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("fulluri",None).decode('utf8').strip().replace(":","").replace('"',"&quot;"))
			if not fulluri:
				data['error']['fulluri']='empty'
			elif fulluri.__len__()>200:
				data['error']['fulluri']='invalid'
			elif not re.match(r"[A-Z|a-z|0-9|\-]+",fulluri):
				data['error']['fulluri']='invalid'
			elif env.regions['regions'].has_key(fulluri):
				data['error']['fulluri']='exist'
			shorturi = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("shorturi",None).decode('utf8').strip().replace(":","").replace('"',"&quot;"))
			if not shorturi:
				shorturi=""
			elif shorturi.__len__()>200:
				data['error']['shorturi']='invalid'
			elif not re.match(r"[A-Z|a-z|0-9|\-]+",shorturi):
				data['error']['shorturi']='invalid'
			short_r={}
			for region in env.regions['regions'].keys():
				short_r[env.regions['regions'][region]['shorturi']]=env.regions['regions'][region]['fulluri']
			if shorturi and short_r.has_key(shorturi):
				data['error']['shorturi']='exist'
			if data['error']:
				data['name']=name
				data['fulluri']=fulluri
				data['shorturi']=shorturi
			else:
				cnt=env.conf.base_path+env.conf.region_conf+"/region_counter"
				if not os.path.exists(cnt):
					with open(cnt,"w") as f:
						f.seek(0)
						f.truncate()
						f.write("0\n")
						f.close()
				with open(cnt,"r+") as f:
					fcntl.flock(f.fileno(), fcntl.LOCK_EX)
					region_id=int(f.readline())+1
					f.seek(0)
					f.truncate()
					f.write(str(region_id)+"\n")
					env.regions['regions'][fulluri]={ 'fulluri':fulluri, 'shorturi':shorturi, 'name':name, 'id':region_id, 'lock':1}
					env.regions['id'][region_id]=env.regions['regions'][fulluri]
					fcntl.flock(f.fileno(), fcntl.LOCK_UN)
					f.close()
				try:
					sort.append(region_id)
					write_sort_file(env,sort)
				except:
					pass
		if env.req.has_key("delete"):
		# удалить регион
		# добавить проверку что ваще можно удалить
			region_id=int(env.req.getvalue("regid",0))
			sql="""SELECT COUNT(*) as c FROM `users` WHERE region_id=%s"""
			c=env.db.equery(sql,(region_id))
			userc=c.fetchone()
			# удалить
			if env.regions['id'].has_key(region_id):
				if userc["c"]==0:
					conffile=env.conf.base_path+env.conf.region_conf+"/"+env.regions['id'][region_id]['fulluri']+".conf"
					logofile=env.conf.base_path+"/static/"+env.regions['id'][region_id]['fulluri']+"-logo.png"
					# убрать из сортировки
					try:
						sort.remove(region_id)
						write_sort_file(env,sort)
					except:
						pass
					del env.regions['regions'][env.regions['id'][region_id]['fulluri']]
					del env.regions['id'][region_id]
					# не забыть удалить файл конфигурации
					if os.path.exists(conffile):
						os.unlink(conffile)
					# не забыть удалить логотип
					if os.path.exists(logofile):
						os.unlink(logofile)
				else:
					data['error']['user']=env.regions['id'][region_id]['name']
		if env.req.has_key("lock"):
		# заблокировать
			region_id=int(env.req.getvalue("regid",0))
			if env.regions['id'].has_key(region_id):
				env.regions['id'][region_id]['lock']=1
		if env.req.has_key("unlock"):
		# разблокировать
			region_id=int(env.req.getvalue("regid",0))
			if env.regions['id'].has_key(region_id):
				env.regions['id'][region_id]['lock']=0
		# поднять выше
		elif env.req.has_key("up"):
			region_id=int(env.req.getvalue("regid",0))
			if region_id:
				i=sort.index(region_id)
				if i>0:
					tmp=sort[i]
					sort[i]=sort[i-1]
					sort[i-1]=tmp
					write_sort_file(env,sort)
		# опустить ниже
		elif env.req.has_key("down"):
			region_id=int(env.req.getvalue("regid",0))
			if region_id:
				i=sort.index(region_id)
				if i<len(sort)-1:
					tmp=sort[i]
					sort[i]=sort[i+1]
					sort[i+1]=tmp
					write_sort_file(env,sort)
		# записать изменённую информацию
		if not data['error'] and (env.req.has_key("lock") or env.req.has_key("unlock") or env.req.has_key("delete") or env.req.has_key("name")):
			filename0=env.conf.base_path+env.conf.region_conf+"/.regions_db.tmp"
			filename1=env.conf.base_path+env.conf.region_conf+"/.regions_db"
			with open( filename0, 'w') as f:
				fcntl.flock(f.fileno(),fcntl.LOCK_EX)
				pickle.dump(env.regions,f)
				os.rename(filename0,filename1)
				fcntl.flock(f.fileno(),fcntl.LOCK_UN)
				f.close()
		data['regions']=env.regions['regions']
		if not sort:
			for i in env.regions['id'].keys():
				sort.append(i)
			write_sort_file(env,sort)
		data['aregions']=[]
		for i in sort:
			data['aregions'].append(env.regions['id'][i])
		content = tmpl.render( data )
	# если регион с номером, то конфиг
	else:
		# редактирование настроек региона
		env.region_current=env.path.current()
		env.path.next()
		if env.session.data['user']["priv"]!=1:
			# если координатор - сделать редирект
			env.redirect('/_adm/')
			return ''
		# если нет региона - сделать редирект
		if not env.regions["regions"].has_key(env.region_current):
			env.redirect('/_adm/r/')
			return ''
		conffile=env.conf.base_path+env.conf.region_conf+"/"+env.region_current+".conf"
		if os.path.exists(conffile):
			with open(conffile) as f:
				rconf=pickle.load(f)
				f.close()
			data.update(rconf)
		else:
			defconffile=env.conf.base_path+env.conf.region_conf+"/-default.conf"
			if os.path.exists(defconffile):
				with open(defconffile) as f:
					rconf=pickle.load(f)
					f.close()
				data.update(rconf)
		data["cregion"] = env.region_current
		data["regid"] = env.regions["regions"][env.region_current]["id"]
		data['regions']=env.regions['regions']
		# проверить форму настроек
		if env.req.has_key("regid"):
			name = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("name","").decode('utf8').strip().replace('"',"&quot;").replace('>',"&gt;").replace('<',"&lt;"))
			if not name:
				data['error']['name']='empty'
			elif name.__len__()>200:
				data['error']['name']='invalid'
			name1 = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("name1","").decode('utf8').strip().replace('"',"&quot;").replace('>',"&gt;").replace('<',"&lt;"))
			if not name1:
				data['error']['name1']='empty'
			elif name1.__len__()>200:
				data['error']['name1']='invalid'
			text1=env.req.getvalue("text1","")
			text1=re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",text1.decode('utf8').strip())
			text21=env.req.getvalue("text21","")
			text21=re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",text21.decode('utf8').strip())
			text22=env.req.getvalue("text22","")
			text22=re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",text22.decode('utf8').strip())
			text3=env.req.getvalue("text3","")
			text3=re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",text3.decode('utf8').strip())
			footer=env.req.getvalue("footer","")
			footer=re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",footer.decode('utf8').strip())
			contact = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("contact","").decode('utf8').strip().replace('"',"&quot;").replace('>',"&gt;").replace('<',"&lt;"))
			if not contact:
				data['error']['contact']='empty'
			elif contact.__len__()>200:
				data['error']['contact']='invalid'
			email = re.compile(r"[\n|\r|\t|\s]+",re.S|re.U).sub(" ",env.req.getvalue("email",None).decode('utf8').strip().replace('"',"&quot;").replace('>',"&gt;").replace('<',"&lt;"))
			if not email:
				data['error']['email']='empty'
			elif not mailtools.is_email(email):
				data['error']['email']='invalid'
			if env.req.has_key("logo"):
				logo=env.req["logo"]
			# если есть иконка, загрузить
			if logo.file:
				if logo.filename.decode("utf8"):
					tf=tempfile.TemporaryFile(dir=env.conf.base_path+env.conf.tmp_path)
					buf=logo.file.read(BLOCK_SIZE)
					while buf:
						tf.write(buf)
						buf=logo.file.read(BLOCK_SIZE)
					ext=logo.filename.decode("utf8").lower().split('.').pop();
					if ext not in ['png']:
						data["error"]["logo"]='invalid'
						tf.close()
						logging.debug("Bad image %s",ext)
					# если нет ошибок, поменять иконку
					if not data['error']:
							tf.seek(0)
							logging.debug(env.conf.base_path+"/static/i/"+env.region_current+"-logo.png")
							f=open(env.conf.base_path+"/static/i/"+env.region_current+"-logo.png","w")
							buf=tf.read(BLOCK_SIZE)
							while buf:
								f.write(buf)
								buf=tf.read(BLOCK_SIZE)
							tf.close()
							f.close()
					else:
						tf.close()
			# если нет ошибок, поменять конфигурацию
			data["name"]=name
			data["name1"]=name1
			data["text1"]=text1
			data["text21"]=text21
			data["text22"]=text22
			data["text3"]=text3
			data["contact"]=contact
			data["email"]=email
			data["footer"]=footer
			if not data['error']:
				with open(conffile,"w") as f:
					rconf={ "name":name, "name1":name1, "text1":text1, "text21":text21, "text22":text22, "text3":text3, "contact":contact, "email":email, "footer":footer}
					pickle.dump(rconf,f)
					f.close()
		tmpl = env.jinja.get_template("admin/rconf.html")
		content = tmpl.render( data )
	return content

# записать файл с сортировкой
def write_sort_file(env,sort):
	filename=env.conf.base_path+env.conf.region_conf+"/.region_sort"
	with open(filename,'w') as f:
		fcntl.flock(f.fileno(), fcntl.LOCK_EX)
		json.dump(sort,f)
		fcntl.flock(f.fileno(), fcntl.LOCK_UN)
		f.close()
