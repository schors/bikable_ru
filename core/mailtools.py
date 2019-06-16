# -*- coding: utf-8 -*-

from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.Utils import COMMASPACE, formatdate
from email.Header import Header
from email import Encoders
import os,logging,sys,re

# All we are really doing is comparing the input string to one
# gigantic regular expression.  But building that regexp, and
# ensuring its correctness, is made much easier by assembling it
# from the "tokens" defined by the RFC.  Each of these tokens is
# tested in the accompanying unit test file.
#
# The section of RFC 2822 from which each pattern component is
# derived is given in an accompanying comment.
#
# (To make things simple, every string below is given as 'raw',
# even when it's not strictly necessary.  This way we don't forget
# when it is necessary.)
#
WSP = r'[ \t]'                                       # see 2.2.2. Structured Header Field Bodies
CRLF = r'(?:\r\n)'                                   # see 2.2.3. Long Header Fields
NO_WS_CTL = r'\x01-\x08\x0b\x0c\x0f-\x1f\x7f'        # see 3.2.1. Primitive Tokens
QUOTED_PAIR = r'(?:\\.)'                             # see 3.2.2. Quoted characters
FWS = r'(?:(?:' + WSP + r'*' + CRLF + r')?' +  WSP + r'+)'                                    # see 3.2.3. Folding white space and comments
CTEXT = r'[' + NO_WS_CTL + r'\x21-\x27\x2a-\x5b\x5d-\x7e]'              # see 3.2.3
CCONTENT = r'(?:' + CTEXT + r'|' + QUOTED_PAIR + r')'                        # see 3.2.3 (NB: The RFC includes COMMENT here
                                                                                                         # as well, but that would be circular.)
COMMENT = r'\((?:' + FWS + r'?' + CCONTENT + r')*' + FWS + r'?\)'                       # see 3.2.3
CFWS = r'(?:' + FWS + r'?' + COMMENT + ')*(?:' + FWS + '?' + COMMENT + '|' + FWS + ')'         # see 3.2.3
ATEXT = r'[\w!#$%&\'\*\+\-/=\?\^`\{\|\}~]'           # see 3.2.4. Atom
ATOM = CFWS + r'?' + ATEXT + r'+' + CFWS + r'?'      # see 3.2.4
DOT_ATOM_TEXT = ATEXT + r'+(?:\.' + ATEXT + r'+)*'   # see 3.2.4
DOT_ATOM = CFWS + r'?' + DOT_ATOM_TEXT + CFWS + r'?' # see 3.2.4
QTEXT = r'[' + NO_WS_CTL + r'\x21\x23-\x5b\x5d-\x7e]'                   # see 3.2.5. Quoted strings
QCONTENT = r'(?:' + QTEXT + r'|' +  QUOTED_PAIR + r')'                        # see 3.2.5
QUOTED_STRING = CFWS + r'?' + r'"(?:' + FWS +  r'?' + QCONTENT + r')*' + FWS + r'?' + r'"' + CFWS + r'?'
LOCAL_PART = r'(?:' + DOT_ATOM + r'|' + QUOTED_STRING + r')'                    # see 3.4.1. Addr-spec specification
DTEXT = r'[' + NO_WS_CTL + r'\x21-\x5a\x5e-\x7e]'    # see 3.4.1
DCONTENT = r'(?:' + DTEXT + r'|' + QUOTED_PAIR + r')'                        # see 3.4.1
DOMAIN_LITERAL = CFWS + r'?' + r'\[' + r'(?:' + FWS + r'?' + DCONTENT + r')*' + FWS + r'?\]' + CFWS + r'?'  # see 3.4.1
DOMAIN = r'(?:' + DOT_ATOM + r'|' + DOMAIN_LITERAL + r')'                       # see 3.4.1
ADDR_SPEC = LOCAL_PART + r'@' + DOMAIN               # see 3.4.1
# A valid address will match exactly the 3.4.1 addr-spec.
VALID_ADDRESS_REGEXP = '^' + ADDR_SPEC + '$'

def is_email(email):
	res = re.match(VALID_ADDRESS_REGEXP, email)
	return res

def sendMail(env, fro, to, subject, text, files=[], bcc=None):
	assert type(to) == list
	toz = []
	if fro.find("<") > 0:
		fro = str(Header(fro[:fro.find("<")],'utf-8'))+fro[fro.find("<"):]
	for a in to:
		if a.find("<") > 0:
			a = str(Header(a[:a.find("<")],'utf-8'))+a[a.find("<"):]
		toz.append(a)
	msg = MIMEMultipart()
	msgtext = MIMEText(text,"plain","utf-8")
	msg.attach( msgtext )
	msg['From'] = fro
	if bcc != None:
		msg['Bcc'] = bcc
	msg['To'] = COMMASPACE.join(toz)
	msg['Date'] = formatdate(localtime=True)
	msg['Subject'] = Header(subject, 'utf-8')
	for file in files:
		part = MIMEBase('application', "octet-stream")
		part.set_payload( open(file,"rb").read() )
		Encoders.encode_base64(part)
		part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(file))
		msg.attach(part)
	p = os.popen("""%s -t -f"%s" """ % (env.conf.sendmail_location,env.conf.sendmail_from), "w")
	p.write(msg.as_string())
	status = p.close()

def tplMail(text,replaces):
	for r in replaces.keys():
		text=text.replace(r"%%"+r+r"%%",replaces[r])
	return text

def loadMail(env,tpl,replaces):
	text=""
	subject=""
	try:
		f=open(env.conf.base_path+env.conf.template_path+"/"+tpl,"r")
		subject=f.readline().decode("utf8").strip()
		subject=tplMail(subject,replaces)
		s=f.readline().decode("utf8")
		while s:
			text=text+s
			s=f.readline().decode("utf8")
		f.close()
		text=tplMail(text,replaces)
	except:
		logging.debug("%s",sys.exc_value)
	return subject,text
