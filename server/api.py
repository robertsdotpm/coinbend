from .bottle import *
from .parse_config import *
from .password_complexity import PasswordComplexity
from .database import Database

# this section is _not_ needed until we get cherrypy to accept externally created SSL contexts
from OpenSSL.crypto import FILETYPE_PEM, load_privatekey, load_certificate
from OpenSSL.SSL import TLSv1_METHOD, SSLv23_METHOD, VERIFY_PEER, VERIFY_FAIL_IF_NO_PEER_CERT
from OpenSSL.SSL import Context, Connection

import ssl
from cherrypy.wsgiserver import CherryPyWSGIServer
from cherrypy.wsgiserver.ssl_builtin import BuiltinSSLAdapter

class PatchBuiltinSSLAdapter(BuiltinSSLAdapter):
    def wrap(self, sock):
        '''
        Overload the wrap method and suppress unknown
        ca alerts from clients on connection
        '''
        try:
            s, env = super(PatchBuiltinSSLAdapter, self).wrap(sock)
        except ssl.SSLError as e:
            return None, {}
        return s, env

# Create our own sub-class of Bottle's ServerAdapter so that we can specify SSL.
# Using just server='cherrypy' uses the default cherrypy server, which doesn't use SSL
class SSLCherryPyServer(ServerAdapter):
    def run(self, handler):
        server = CherryPyWSGIServer((self.host, self.port), handler, server_name='localhost')
        """
        openssl genrsa -out privkey.pem 1024
        openssl req -new -x509 -key privkey.pem -out cacert.pem -days 1095
        """
        crt = '/etc/coinbend/cacert.pem'
        key = '/etc/coinbend/privkey.pem'
        #ca  = '/etc/ssl/intermediate.crt'
        server.ssl_module  = "pyopenssl"
        server.ssl_adapter = PatchBuiltinSSLAdapter(crt, key)

        # fucking p.o.s. cherry does NOT support prebuilt ssl contexts
        #server.ssl_adapter.context = sc

        try:
            server.start()
        finally:
            server.stop()
            
def redirect_http_to_https(callback):
    '''Bottle plugin that redirects all http requests to https'''

    def wrapper(*args, **kwargs):
        scheme = request.urlparts[0]
        if scheme == 'http':
            # request is http; redirect to https
            redirect(request.url.replace('http', 'https', 1))
        else:
            # request is already https; okay to proceed
            return callback(*args, **kwargs)
    return wrapper
    
def check_basic_auth(user, passwd):
    passed = False
    db = None
    try:
        #Get user.
        db = Database()
        sql = "SELECT * FROM `users` WHERE `username`=?"
        db.execute(sql, (user,))
        user = db.cur.fetchall()[0]
        
        #Convert provided password to hash.
        salt = user["salt"]
        pc = PasswordComplexity()
        passwd = pc.hash(passwd, salt, str(config["satoshi_identity"]))
        
        #Check password.
        if passwd == user["password"]:
            passed = True
        
        #We're done here.
        db.finish_transaction()
        db = None
    except:
        pass
    finally:
        if db != None:
            db.kill_connection()
        
    return passed
    
app = default_app()    
install(redirect_http_to_https)


def main():
    """
    sdfsdfsdf
    sdfsdfsdf

# deny non-ssl
@app.hook('before_request')
def require_ssl():
    if not request['wsgi.url_scheme'] == 'https':
        abort(400,'Encrypted connection required')

@app.route('/recipes/')
@auth_basic(check_basic_auth)
def recipes_list():
    #bottle.request.auth
    return "LIST"
    
"""
Todo: Client should also verify server.
Server should sign a message and client should
verify message. If it can verify then MITM is harder
"""

@app.route('/recipes/<name>', method='GET')
def recipe_show( name="Mystery Recipe" ):
    return "SHOW RECIPE " + name

@app.route('/recipes/<name>', method='DELETE' )
def recipe_delete( name="Mystery Recipe" ):
    return "DELETE RECIPE " + name

@app.route('/recipes/<name>', method='PUT')
def recipe_save( name="Mystery Recipe" ):
    return "SAVE RECIPE " + name

#python3 -m "coinbend.api"
if __name__ == "__main__":
    run(app, host='0.0.0.0', port=443, server=SSLCherryPyServer)
