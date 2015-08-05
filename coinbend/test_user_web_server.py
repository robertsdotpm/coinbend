from .globals import *
from .user_web_server import *

#Start UI web server.
run(app, host='127.0.0.1', port=7777, server=CherryPyServer, debug=False)
#print("test")
#run(app, host='127.0.0.1', port=7777, debug=True)
