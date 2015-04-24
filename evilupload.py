from io import open

import requests, mechanize, cookielib
import sys, os
import re
from getpass import getpass

def get_file_size(filename):
	if os.path.exists(filename):
		size = os.stat(filename).st_size
		if size <= 0:
			raise ValueError('File size too small.')
		if size > 1*1024*1024*1024:
			raise ValueError('File is larger than 1GB.')
	else:
		raise OSError('No such file or directory: %s' %filename)	

def get_image_size(filename):
	if os.path.exists(filename):
		size = os.stat(filename).st_size
		if size <= 0:
			raise ValueError('File size too small.')
		if size > 30*1024*1024:
			raise ValueError('File is larger than 1GB.')
	else:
		raise OSError('No such file or directory: %s' %filename)	 

def is_supported_image(image):
	supported_ext = ['gif', 'jpeg', 'png', 'bmp']
	image_ext = os.path.splitext(image)[1]
	if image_ext[1:] in supported_ext:
		return True
	else:
		return False

def get_link(html):
	r_ul = re.compile(r'\s*(?i)href\s*=\s*(\"([^"]*\")|"[^"]*"|([^"">\s]+))')
	link = re.findall(r_ul, html)
	return link[0][0]

def check_cookie(cj, name):
	for cookie in cj:
		if cookie.name == name:
			return True
	return False

class evilupload():
	
	def __init__(self, filename=None):
		self.filename = filename
		self.forum = 'https://evilzone.org/index.php'#
		self.host = 'upload.evilzone.org'
		self.url = 'http://{0}'.format(self.host)
		self.cj = None
		self.loggedin=False
		
		self.agent = 'Mozilla/5.0 (X11; Linux i686; rv:25.0) Gecko/20100101 Firefox/25.0'
		self.type = 'multipart/form-data'
		self.referer = 'http://upload.evilzone.org/index.php?page=fileupload'
		self.headers = {'content-type': self.type, 'User-Agent': self.agent, 'Referer': self.referer}
	
	def get_input(self, prompt):
		"""
		Function Get input from the user maintaining the python compatibility with earlier and newer versions.
		:param prompt:
		:rtype : str
		:return: Returns the Hash string received from user.
		"""
		if sys.hexversion > 0x03000000:
			return input(prompt)
		else:
			return raw_input(prompt)

	def login(self):
		
		if self.cj is None or not check_cookie(self.cj, 'DarkEvilCookie'):#wonder if this logic is right!
			login_url = 'https://evilzone.org/login'
			username = self.get_input('Username for Evilzone.org: ')
			password = getpass('Password for Evilzone.org: ')

			agent = mechanize.Browser()
			agent.set_handle_robots(False)
			self.cj = cookielib.LWPCookieJar()
		
			agent.set_cookiejar(self.cj)
			agent.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
			agent.open(login_url)
	
			#login
			agent.select_form(name='frmLogin')
			agent.form['user'] = username
			agent.form['passwrd'] = password
			response = agent.submit()
	
			if response.code == requests.codes.ok:
				if check_cookie(self.cj, 'DarkEvilCookie'): 
					self.loggedin=True
#					self.cj.save(ignore_discard=True)
					return self.cj
				else:
					self.loggedin=False
					return None
		else:
			return None
		
	def fileupload(self, filename=None):
		path = '/index.php?page=fileupload&filename={0}'
		filepath = filename or self.filename
		_filename = os.path.basename(filepath)
		file_url = self.url + path.format(_filename)
		size = get_file_size(filepath)
		self.headers['Content-Length'] = size
		
		if self.cj is not None and self.loggedin and check_cookie(self.cj, 'DarkEvilCookie'):
			session = requests.session()
			r = session.get(url='https://evilzone.org/rauploadmod.php',
					 headers=self.headers, cookies=self.cj)#lets pass that cookie around
			try:
				#ok, lets stream them big files.
				with open(filepath, 'rb') as f:
					r = session.post(url=file_url, headers=self.headers, data=f.read(), cookies=self.cj)
			except IOError as e:
				print 'Something went wrong while reading the file: %s' %e
				return
			
			if 'Error' not in r.text:
				return 'http://upload.evilzone.org?page=download&file='+r.text
			else:
				return None
		else:
			print 'Login prolly failed.'
			return None

	def imageupload(self, filename=None):
		path = '/index.php?page=imageupload&upload=true'
		imagepath = filename or self.filename
		image_url = self.url + path
		size = get_image_size(imagepath)
		self.headers['Content-Length'] = size
		if is_supported_image(imagepath):
			if self.cj is not None and self.loggedin and check_cookie(self.cj, 'DarkEvilCookie'):
				session = requests.session()
				r = session.get(url='https://evilzone.org/rauploadmod.php',
					 headers=self.headers, cookies=self.cj)#fsck subdomains
				try:
					#ok, lets stream them big files.
					with open(imagepath, 'rb') as f:
						r = session.post(url=image_url, headers=self.headers, data=f.read(), cookies=self.cj)
				except IOError as e:
					print 'Something went wrong while reading the file: %s' %e
					return
				if 'Error' not in r.text:
					return self.url + '/' + get_link(r.text).strip('"')
				else:
					return None#TODO: parse error and return it
			else:
				print 'Login prolly failed.'
				return None

		else:
			raise TypeError("Image format not supported.")

#	def delete(self, url):
#		def get_token(url):
#			indx = url.rfind('=')
#			token = url[indx+1:]
#			print (token)
#			if 50 == len(token):
#				return token
#			else:
#				return None
#	
#		token = get_token(url)
#		path = ''
#		if token is not None:
#			if 'yourimages' in url:
#				path = '/index.php?page=yourimages&delete='
#			elif 'yourfiles' in url:
#				path = '/index.php?page=yourfiles&delete='
#
#		image_url = self.url + path + token
#		print image_url
#
#		r = requests.post(url=image_url, headers=self.headers, cookies=self.cj)
#		print(r.text)
#		delete= 'http://upload.evilzone.org/index.php?page=yourimages&delete=S7YDymME33ZidFLEagaQ6YfC7KMCDEUREFMg7piNjlGHXpOFrz'
#		delete='http://upload.evilzone.org/index.php?page=yourfiles&delete=8wPtrctGEoETO7lIbX38Y3QqyAYXQMqchWxUpBSYLND5FT9RO1'
