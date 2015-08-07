"""
Provides a web-based trading interface for currency exchange
and other services. Server is spawned on port 7777 by
default.
"""

from .bottle import *
from .globals import *
from .coin_config import *
from .password_complexity import *
from .database import *
from .cryptocurrencies import *
from .fiatcurrencies import *
from .currency_type import *
from .json_rpc import *
from .trade_engine import *
from .unl import *
from .lib import *
from .trade_type import *
from cherrypy.wsgiserver import CherryPyWSGIServer
import os
import json
import html
import decimal
import re
import uuid
import binascii
import hashlib
import time

"""
Token: Generate random token at UI start. Check token
is part of all POST, DELETE requests for the API.
Send token to page with Javascript with template function.
Now page can make calls and it's more secure against CSRF
and JSON hijacking (so long as there's no XSS.)

Note: Also add this for GET requests that return senstive
info.
"""
csrf_token = PasswordComplexity(["uppercase", "lowercase", "numeric"], 60).generate_password()
if config["debug"]:
    print(csrf_token)

class CherryPyServer(ServerAdapter):
    global error_log_path
    def run(self, handler):
        server = CherryPyWSGIServer((self.host, self.port), handler, server_name='localhost')
        try:
            server.start()
        except Exception as e:
            error = parse_exception(e)
            log_exception(error_log_path, error)
            print(error)
        finally:
            server.stop()

  
app = default_app()

@error(404)
def error404(error):
    return """Something unexpected has happened. Please email an error report to matthew@roberts.pm and I'll write a fix."""

@error(403)
def error403(error):
    return """Forbidden. You probably need to refresh the page to get a current access token or double-check your token is correct."""

@route('/assets/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root=os.path.join(data_dir, "www", "assets"))

@route('/views/<filepath:path>')
def server_views(filepath):
    return static_file(filepath, root=os.path.join(data_dir, "www", "views"))

@route('/satoshi/<page>')
def satoshi_controller(page="portfolio"):
    valid_pages = {
        "portfolio": {
            "no": 1,
            "page": "portfolio",
            "icon": "key",
            "title": "Portfolio",
            "desc": "overview & accounting"
        },
        "trade": {
            "no": 2,
            "icon": "exchange",
            "title": "Coin Trading",
            "desc": "buy & sell currencies"
        },
        "withdraw": {
            "no": 3,
            "icon": "mail-reply",
            "title": "Withdrawals",
            "desc": "withdraw your funds"
        },
        "accept": {
            "no": 4,
            "icon": "globe",
            "title": "Accept Bitcoin",
            "desc": "merchant & business services"
        },
        "download": {
            "no": 5,
            "icon": "download",
            "title": "Downloads",
            "desc": "trading programs"
        },
        "shopping": {
            "no": 6,
            "icon": "shopping-cart",
            "title": "Shopping",
            "desc": "our web store"
        },
        "profile": {
            "no": 7,
            "icon": "user",
            "title": "Profile",
            "desc": "update your information"
        },
        "settings": {
            "no": 8,
            "icon": "cog",
            "title": "Settings",
            "desc": "change your settings"
        },
        "logout": {
            "no": 9,
            "icon": "power-off",
            "title": "Logout",
            "desc": "logout"
        }
    }
    
    if page == "trade_chart":
        return static_file("trade_chart.html", root="www/views")
    if page not in valid_pages:
        page = "portfolio"
    meta = valid_pages[page]

    #Main page logic here.
    navlist = []
    for key, value in valid_pages.items():
        li = ""
        if page == key:
            li += '<li class="active">'
        else:
            li += '<li>'
        extra = ''

        li += """
    <a href="/satoshi/%s">
        <i class="icon-%s"></i>
        <span class="menu-text">%s</span>
    </a>
</li>
        """ % ( \
        html.escape(key),
        html.escape(valid_pages[key]["icon"]),
        html.escape(valid_pages[key]["title"])
        )

        navlist.append([valid_pages[key]["no"], li])

    #Put the nav links in their proper order.
    #There's a standard lib function but it was faster
    #to code it instead of look it up.
    temp = ""
    sort = 1
    l = len(navlist)
    while sort:
        sort = 0
        for i in range(0, l):
            if i == l - 1:
                break

            if navlist[i][0] > navlist[i + 1][0]:
                navlist[i], navlist[i + 1] = navlist[i + 1], navlist[i]
                sort = 1
    for nav in navlist:
        temp += nav[1]
    navlist = temp

    content = ""
    with open(os.path.join(data_dir, "www", "views", page + ".html"), "r") as fp:
        content = fp.read()
    if re.match("\s+", content) != None:
        content = "This is a pre-alpha version. Maybe there will be something here in the future."

    js = ""
    with open(os.path.join(data_dir, "www", "views", page + ".js"), "r") as fp:
        js = fp.read()

    main = ""
    with open(os.path.join(data_dir, "www", "views", "main.html"), "r") as fp:
        main = fp.read()

    """
    Script code for the CSRF token.
    Escaped even though the token is alpha-numeric.
    (It's a global variable so it could get changed and
    it would be very ironic if the token to prevent
    CSRF ended up introducing XSS.)
    """
    global csrf_token
    csrf_token = """%s""" % (html.escape(csrf_token))

    global config
    global direct_net
    global p2p_net
    global coins
    global demo
    print("In user web server.")

    #Json TX fee structure.
    tx_fees = "{"
    index = 1
    for coin in coins:
        if index != 1:
            tx_fees += ","

        tx_fees += '"' + html.escape(coin) + '":'
        tx_fees += ' "' + html.escape(str(coins[coin]["tx_fee"])) + '"'

        index += 1
    tx_fees += "}"
    if not is_json(tx_fees):
        raise Exception("Potential exploit detected in tx_fee field.")

    #Make standard information available in the template.
    return template(main, content=content, js=js, navlist=navlist, title=meta["title"], desc=meta["desc"], csrf_token=csrf_token, trade_fee=config["trade_fee"], prefered_currency=config["prefered_currency"].upper(), connection_no=p2p_net.get_connection_no(), node_type=node_type, nat_type=nat_type, testnet=config["testnet"], passive_port=passive_port, forwarding_type=forwarding_type, direct_unl=UNL(direct_net).construct(), p2p_unl=UNL(p2p_net).construct(), tx_fees=tx_fees, demo=demo)

@route('/')
def default_page():
    return satoshi_controller()

@hook('before_request')
def api_hook():
    if re.match("/api([^?&=]+)?", request.path) != None:
        #Attempt to reconnect RPC sockets for coins.
        global coins
        global config
        for coin in list(coins):
            if not coins[coin]["connected"]:
                try:
                    if str(int(coins[coin]["testnet"])) == str(config["testnet"]):
                        coins[coin]["rpc"]["sock"] = JsonRpc(coins[coin]["rpc"]["endpoint"])
                        coins[coin]["rpc"]["sock"].getbalance()
                        coins[coin]["connected"] = 1
                    else:
                        raise Exception("Config for coin is on a network different to config network.")
                except Exception as e:
                    print(e)
                    coins[coin]["rpc"]["sock"] = None
                    coins[coin]["connected"] = 0

        """
        Attempt to verify access token. The access token
        can either be the random CSRF token generated at
        the start of this program, or alternatively, it can
        be an API key as specified in config["user_web_server"].
        """
        global config
        global csrf_token
        data = request.path
        data += request.query_string
        try:
            data += "access=" + request.POST["access"]
        except:
            pass
        access_token = re.findall("access[=]([a-zA-Z0-9-_]+)", data)
        if len(access_token):
            access_token = access_token[0]
            is_valid = 0
            if access_token == csrf_token:
                is_valid = 1
            for api_key in config["user_web_server"]["api_keys"]:
                #Check restrictions.
                if access_token == api_key["value"]:
                    if api_key["type"] == "server_key":
                        for ip_addr in api_key["ips"]:
                            if request.environ.get('REMOTE_ADDR') == ip_addr:
                                is_valid = 1
                                break

                    if api_key["type"] == "browser_key":
                        for referer in api_key["referers"]:
                            if re.match(referer, request.environ.get('HTTP_REFERER', '/')) != None:
                                is_valid = 1
                                break

            if not is_valid:
                abort(403, "Invalid access token.")
        else:
            abort(403, "Access token required.")

@get('/api/currencies')
@get('/api/currencies/<currency>')
def api_currencies(currency=None):
    global coins
    response.content_type = 'application/json'
    json_out = {}
    for coin in coins:
        json_out[coin] = {}
        json_out[coin]["connected"] = coins[coin]["connected"]
        json_out[coin]["balance"] = str(C("0"))
        json_out[coin]["pending"] = str(C("0"))
        json_out[coin]["rpc"] = {}
        json_out[coin]["rpc"]["port"] = coins[coin]["rpc"]["port"]
        json_out[coin]["rpc"]["addr"] = coins[coin]["rpc"]["addr"]
        json_out[coin]["conf_path"] = coins[coin]["conf_path"]
        json_out[coin]["address"] = coins[coin]["address"]
        json_out[coin]["tx_fee"] = str(coins[coin]["tx_fee"])
        json_out[coin]["dust_threshold"] = str(coins[coin]["dust_threshold"])
        if json_out[coin]["connected"]:
            try:
                coins[coin]["balance"] = C(coins[coin]["rpc"]["sock"].getbalance())
                json_out[coin]["balance"] = str(coins[coin]["balance"])

                #Set pending transactions.
                transactions = coins[coin]["rpc"]["sock"].listtransactions()
                pending = C()
                for transaction in transactions:
                    if transaction["confirmations"] == 0:
                        amount = transaction["amount"]
                        if amount < decimal.Decimal(0):
                            amount = -amount
                        pending += C(amount)
                json_out[coin]["pending"] = str(pending)
            except Exception as e:
                print(e)
                json_out[coin]["connected"] = coins[coin]["connected"] = 0
                coins[coin]["rpc"]["sock"] = None
        try:
            json_out[coin]["code"] = cryptocurrencies[coin]["code"]
        except:
            json_out[coin]["code"] = ""

    if currency != None:
        if currency in json_out:
            json_out = {currency: json_out[currency]}
        else:
            json_out = {}

    return json.dumps(json_out, sort_keys=True, indent=4, separators=(',', ': '))

@get('/api/trades')
def get_trades():
    with Transaction() as tx:
        sql = "SELECT * FROM `trade_orders` ORDER BY `created_at` DESC;"
        tx.execute(sql)
        rows = tx.fetchall()
        rows = combine_number_parts(rows)
        rows = add_currency_codes(rows)

        return json.dumps(rows, sort_keys=True, indent=4, separators=(',', ': '))

    return json.dumps({"error": "Unable to get trades."}, sort_keys=True, indent=4, separators=(',', ': '))

@get('/api/contracts')
def get_contracts():
    #Load microtransfer contracts.
    rows = []
    with Transaction() as tx:
        sql = "SELECT * FROM `microtransfers` ORDER BY `created_at` DESC;"
        tx.execute(sql)
        rows = tx.fetchall()
        rows = combine_number_parts(rows)
    
    #Load green address information.
    for row in rows:
        with Transaction() as tx:
            sql = "SELECT * FROM `green_addresses` WHERE `deposit_address`=? AND `currency`=?"
            trade = trade_from_row(row)
            tx.execute(sql, (row["green_address"], trade.to_send.currency))
            green_address = tx.fetchall()[0]
            row["deposit_txid"] = green_address["deposit_txid"]
            row["deposit_tx_hex"] = green_address["deposit_tx_hex"]
            row["setup_txid"] = green_address["setup_txid"]
            row["setup_tx_hex"] = green_address["setup_tx_hex"]

    #Return results.
    if len(rows):
        return json.dumps(rows, sort_keys=True, indent=4, separators=(',', ': '))
    else:
        return json.dumps({"error": "Unable to get contracts."}, sort_keys=True, indent=4, separators=(',', ': '))

@get('/api/transactions')
def get_transactions():
    with Transaction() as tx:
        sql = "SELECT * FROM `transactions` ORDER BY `created_at` DESC;"
        tx.execute(sql)
        rows = tx.fetchall()
        rows = combine_number_parts(rows)

        return json.dumps(rows, sort_keys=True, indent=4, separators=(',', ': '))

    return json.dumps({"error": "Unable to get transactions."}, sort_keys=True, indent=4, separators=(',', ': '))

@app.route('/api/trades/<id>', method='DELETE' )
def delete_trades(id):
    global demo
    if demo:
        return '{"error": "Unable to delete trade in demo mode."}'

    ret = 0
    db = Database()
    with Transaction(db) as tx:
        sql = "DELETE FROM `trade_orders` WHERE `id`=?;"
        tx.execute(sql, (id,))
        ret = id

    if ret:
        return '{}'
    else:
        return '{"error": "Unable to delete trade."}'

@app.route('/api/trades/<base_currency>_<quote_currency>', method='POST')
def create_trades(base_currency, quote_currency):
    global trade_engine
    global error_log_path
    global config
    global demo

    #Convert currency codes to names.
    if base_currency in cryptocurrencies:
        if "code" not in cryptocurrencies[base_currency]:
            base_currency = cryptocurrencies[base_currency]["name"]
    if quote_currency in cryptocurrencies:
        if "code" not in cryptocurrencies[quote_currency]:
            quote_currency = cryptocurrencies[quote_currency]["name"]
   
    #Process fields.
    try:
        action = request.forms.get('action')
        pair = [base_currency, quote_currency]
        amount = request.forms.get('amount')
        ppc = request.forms.get('ppc')
        dest_ip = request.forms.get('dest_ip')
        test_trade = Trade(action, amount, pair, ppc, dest_ip=dest_ip)
        if dest_ip == "any":
            dest_ip = ""

        #Demo mode: restrict to demo nodes.
        if demo:
            if dest_ip not in config["demo_nodes"]:
                return '{"error": "Demo mode is enabled so you can only connect to other demo nodes."}'
            
    except Exception as e:
        error = parse_exception(e)
        print(error)
        log_exception(error_log_path, error)
        return '{"error": "Invalid form data."}';

    #Save trade.
    try:
        ret = trade_engine.open_trade(action, amount, pair, ppc, dest_ip=dest_ip, src_ip=request.environ.get('REMOTE_ADDR'))
        return '{"id": %s}' % (str(ret.id))
    except Exception as e:
        error = parse_exception(e)
        print(error)
        log_exception(error_log_path, error)
        return '{"error": "%s"}' % (str(e))

@get('/api/rates/<location>/<base_currency>_<quote_currency>')
def get_exchange_rate(location, base_currency, quote_currency):
    global exchange
    global error_log_path
    
    pair = str(base_currency).upper() + "/" + str(quote_currency).upper()
    rate = {
        pair: "0"
    }

    if location == "external":
        try:
            ret = C(e_exchange_rate.calculate_rate(base_currency, quote_currency))
            if ret != C(0):
                rate[pair] = str(ret)
        except Exception as e:
            error = parse_exception(e)
            print(error)
            log_exception(error_log_path, error)
            rate[pair] = "0"
    else:
        pass

    return json.dumps(rate, sort_keys=True, indent=4, separators=(',', ': '))

@get('/api/node_id/<network>')
def generate_unl_pointer(network):
    global dht
    global direct_net
    global p2p_net
    global error_log_path

    try:
        #Check network.
        networks = ["direct", "p2p"]
        if network not in networks:
            return '{"error": "Invalid network."}'

        #Choose network.
        if network == "direct":
            unl = UNL(direct_net)
        if network == "p2p":
            unl = UNL(p2p_net)

        #Generate DHT data.
        plaintext = unl.construct()
        crypt = otp_encrypt(plaintext)
        content = crypt["ciphertext"]
        content = binascii.hexlify(content).decode("utf-8")
        id = "UNL" + str(uuid.uuid4())
        key = hashlib.sha256(id.encode("ascii") + content.encode("ascii")).hexdigest()

        #Store encrypted UNL in DHT.
        dht[id] = content

        #Generate pointer to UNL in DHT.
        pointer = key
        pointer += binascii.hexlify(crypt["otp"]).decode("utf-8")
        ret = {
            "unl_pointer": pointer
        }

        #Return results as JSON.
        return json.dumps(ret, sort_keys=True, indent=4, separators=(',', ': '))
    except Exception as e:
        error = parse_exception(e)
        log_exception(error_log_path, error)
        print(error)
        return '{"error": "Unknown exception occured generating UNL %s."}' % (error)
 
@app.route('/api/network/<network>', method='POST')
def add_connection(network):
    global direct_net
    global p2p_net
    global dht
    global demo
    global config
    global error_log_path

    #Wait enough time for DHT to store encrypted details.
    time.sleep(5)

    #Check network.
    networks = ["direct", "p2p"]
    if network not in networks:
        return '{"error": "Invalid network."}'
    
    #Choose network.
    if network == "direct":
        unl = UNL(direct_net)
    if network == "p2p":
        unl = UNL(p2p_net)

    try:
        #Our UNL.
        src_unl = unl.construct()

        #Decode their UNL from the DHT.
        dest_unl_pointer = request.forms.get('unl_pointer')
        dest_unl_key = dest_unl_pointer[0:64]
        dest_unl_ciphertext = dht[dest_unl_key]
        dest_unl_ciphertext = dest_unl_ciphertext.encode("ascii")
        dest_unl_ciphertext = binascii.unhexlify(dest_unl_ciphertext)
        dest_unl_otp = dest_unl_pointer[64:]
        dest_unl_otp = dest_unl_otp.encode("ascii")
        dest_unl_otp = binascii.unhexlify(dest_unl_otp)
        dest_unl = otp_decrypt(dest_unl_otp, dest_unl_ciphertext)
        dest_unl = dest_unl.decode("utf-8")

        #Demo mode: restrict to demo nodes.
        if demo:
            their_wan_ip = unl.deconstruct(dest_unl)["wan_ip"]
            if their_wan_ip not in config["demo_nodes"]:
                return '{"error": "Demo mode is enabled so you can only connect to other demo nodes."}'

        #Vist UNL.
        dest_ip = unl.connect(src_unl, dest_unl)
        if dest_ip == None:
            return '{"error": "Unable to connect to UNL."}'
        else:
            #Used for identifying sockets for direct connect.
            ret = {
                "dest_ip": dest_ip
            }

            return json.dumps(ret, sort_keys=True, indent=4, separators=(',', ': '))
    except Exception as e:
        e = parse_exception(e)
        log_exception(error_log_path, e)
        print(e)
        ret = {
            "error": e
        }

        return json.dumps(ret, sort_keys=True, indent=4, separators=(',', ': '))

#python3.3 -m "coinbend.ui"
if __name__ == "__main__":
    print("yes")
