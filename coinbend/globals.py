"""
Try to only put stateless globals in here / globals which don't change
after they're loaded. Use dependency injection to make code easier
to test.
"""

from .cryptocurrencies import *
from .fiatcurrencies import *
from .lib import *
from .parse_config import *
from .args import *
from .coin_config import *
from .exchange_rate import *
from .net import *
from .rendezvous_client import *
from .sys_clock import *
from .trade_engine import *
from .tx_monitor import TXMonitor
import os
import netifaces
import re
import platform
import urllib.request
import hashlib
import uuid
import time
import threading

#TOdo: there's an error with getting this occasionally.
print("Wan ip = ")
print(get_wan_ip())

#Parse config file.
ParseConfig = config = ParseConfig(os.path.join(data_dir, "config.json"))

#Error log path.
error_log_path = os.path.join(data_dir, config["error_file"])

#Threading mutex.
thread_lock = None
    
#Log all.
if args.logall != None:
    thread_lock = threading.Lock()
    print("starting tee")
    print(error_log_path)
    Tee(error_log_path, "a",  thread_lock)

#Running on testnet?
if str(config["testnet"]) == "0":
    print("Woah! I've detected you're running this software on the main network [testnet=0]. The software in this mode will trade -real- money and this is only a pre-alpha version. Are you absolutely, 100%, sure you want to do that knowing full well this program isn't yet ready for real money?")
    print()
    print("[y]es: I understand this is unstable. I'm only risking a small amount of coins.")
    print("[n]o: Yikes, get me out of here.")
    print()
    choice = input("Enter yes or no: ")
    choice = choice.lower()
    if choice[0] == "n":
        print()
        input("Good call. Press [enter] to exit.")
        exit()

#Used to identify UNLs in the DHT.
guid = hashlib.sha256(str(uuid.uuid4()).encode("ascii")).hexdigest()

nat_type = config["nat_type"]
if args.nat_type != None:
    valid_nat_types = ["random", "preserving", "delta", "reuse", "unknown"]
    if args.nat_type not in valid_nat_types:
        print("Invalid argument supplied for NAT type.")
        exit()
    nat_type = args.nat_type

node_type = config["node_type"]
if args.node_type != None:
    valid_node_types = ["passive", "simultaneous", "active", "unknown"]
    if args.node_type not in valid_node_types:
        print("Invalid argument supplied for node type.")
        exit()
    node_type = args.node_type

#Max outbound p2p connections.
max_outbound = config["max_outbound"]
if args.max_outbound != None:
    max_outbound = args.max_outbound

#Max inbound p2p connections.
max_inbound = config["max_inbound"]
if args.max_inbound != None:
    max_inbound = args.max_inbound

#Max direct connections.
max_direct = config["max_direct"]
if args.max_direct != None:
    max_direct = args.max_direct

#Passive server details (passive p2p_net inbound)
passive_bind = config["passive_server"]["bind"]
if args.passive_bind != None:
    passive_bind = args.passive_bind

passive_port = config["passive_server"]["port"]
if args.passive_port != None:
    passive_port = int(args.passive_port)

#Direct server details (passive direct_net inbound)
direct_bind = config["direct_server"]["bind"]
if args.direct_bind != None:
    direct_bind = args.direct_bind

direct_port = config["direct_server"]["port"]
if args.direct_port != None:
    direct_port = int(args.direct_port)

#User web server / UI server bind details
ui_bind = config["user_web_server"]["bind"]
if args.ui_bind != None:
    ui_bind = args.ui_bind

ui_port = config["user_web_server"]["port"]
if args.ui_port != None:
    ui_port = args.ui_port

#Network interface.
interface = config["interface"]
if args.interface != None:
    if args.interface not in netifaces.interfaces():
        print("Invalid argument supplied for interface.")
        exit()
    interface = args.interface

#List public IP as LAN IP.
local_only = config["local_only"]
if args.local_only != None:
    local_only = args.local_only

#Load coin config files + RPC connections.
if args.fastload == "1" or args.coins == "0":
    coins = {}
else:
    coins = load_coins(this_os, config["testnet"])

#Overwrite coin variables with manually set config values.
for coin in list(coins):
    #Overwrite TX fee.
    if coin in config["tx_fee"]:
        coins[coin]["tx_fee"] = C(config["tx_fee"][coin])
    else:
        #Use default fee.
        if coins[coin]["tx_fee"] == C(0):
            if "default" in config["tx_fee"]:
                coins[coin]["tx_fee"] = C(config["tx_fee"]["default"])

    #Overwrite dust_threshold.
    if coin in config["dust_threshold"]:
        coins[coin]["dust_threshold"] = C(config["dust_threshold"][coin])

    #Check coin is configured for right network.
    if str(int(coins[coin]["testnet"])) != str(config["testnet"]):
        raise Exception("Coin is on a network other than one configured for the currency.")

#Initialise exchange rates.
if args.erateinit != None:
    btc_value_init = 0
else:
    btc_value_init = 1
if args.fastload == "1" or args.externalexchange == "0":
    e_exchange_rate = ExchangeRate(config, preload=0, btc_value_init=btc_value_init)
else:
    e_exchange_rate = ExchangeRate(config, btc_value_init=btc_value_init)
if args.erateinit != None:
    exchange_rates = []
    for exchange_rate in args.erateinit.split(","):
        exchange_rate = exchange_rate.split("_")
        if len(exchange_rate) != 3:
            continue
        exchange_rates.append(exchange_rate)
    e_exchange_rate.manual_override(exchange_rates)

#Todo: save this value and remove this.
args.clockskew = 1

#Clock skew against NTP.
if args.clockskew != None:
    sys_clock = SysClock(clock_skew=Decimal(args.clockskew))
else:
    sys_clock = SysClock()

#Demo mode.
demo = int(config["demo"])
if args.demo != None:
    demo = int(args.demo)

print("Demo mode = ")
print(demo)

#Get external IP.
if args.wanip != None:
    def args_get_wan_ip():
        return args.wanip
    get_wan_ip = args_get_wan_ip
else:
    get_wan_ip()

if args.skipnet == None:
    #Parse add node.
    direct_nodes = []
    p2p_nodes = []
    if args.addnode != None:
        #E.g. simultaneous://127.0.0.1:70/p2p,passive://4.4.4.4:80/direct
        node_pattern = "(passive|simultaneous)://([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+)[:]([0-9]+)/(p2p|direct)"
        node_list_pattern = """^((?:\s*,*\s*%s)+)$""" % (node_pattern)
        node_urls = re.findall(node_list_pattern, args.addnode)
        if len(node_urls):
            for node_url in list(filter(None, node_urls[0][0].split(","))):
                node = re.findall(node_pattern, node_url)[0]
                node = {
                    "type": node[0],
                    "addr": node[1],
                    "port": node[2],
                    "network":  node[3]
                }

                if node["network"] == "direct":
                    direct_nodes.append(node)

                if node["network"] == "p2p":
                    p2p_nodes.append(node)

    #Networking for direct connections from other nodes.
    direct_rendezvous = RendezvousClient(nat_type, config["rendezvous_servers"], interface)
    direct_net = Net(nat_type, node_type, 0, max_direct, direct_bind, direct_port, config["forwarding_servers"], direct_rendezvous, interface, local_only, error_log_path=error_log_path)
    direct_net.disable_bootstrap()
    direct_net.disable_advertise() #For passive, not simultaneous.
    #There's no connection here for simultaneous because
    #advertise is disabled. What is the correct behaviour?
    if args.skipforwarding != None:
        direct_net.disable_forwarding()
    direct_net.start()
    direct_net.advertise()
    for node in direct_nodes:
        direct_net.add_node(node["addr"], node["port"], node["type"])

    #Save detected network details.
    direct_node_type = node_type = direct_net.node_type
    direct_nat_type = nat_type = direct_net.nat_type
    print("direct net params")
    print(direct_node_type)
    print(direct_nat_type)

    #Simultaneous should only be enabled for direct network.
    #Todo: have seperate variables for p2p network.
    if direct_net.node_type == "simultaneous":
        node_type = "active"

    #Connect to peer-to-peer network.
    p2p_rendezvous = RendezvousClient(nat_type, config["rendezvous_servers"], interface)
    p2p_net = Net(nat_type, node_type, max_outbound, max_inbound, passive_bind, passive_port, config["forwarding_servers"], p2p_rendezvous, interface, local_only, error_log_path=error_log_path)
    if args.skipforwarding != None:
        p2p_net.disable_forwarding()
    p2p_net.start()
    for node in p2p_nodes:
        con = p2p_net.add_node(node["addr"], node["port"], node["type"])
        print("ADding node")
        print(node["addr"])
        print(node["port"])
        print(con)

    if args.skipbootstrap == None:
        p2p_net.bootstrap()
    else:
        p2p_net.disable_bootstrap()
    print("p2p net params")
    print("advertising 2.")
    print(p2p_net.node_type)
    print(p2p_net.nat_type)
    #Don't list this node for bootstrapping when in demo mode.
    if not demo:
        print("p2p net advertising.")
        p2p_net.advertise()
    p2p_node_type = p2p_net.node_type
    p2p_nat_type = p2p_net.nat_type
    p2p_forwarding_type = forwarding_type = p2p_net.forwarding_type

if demo:
    print("Demo mode is enabled.")

tx_monitor = TXMonitor(coins, config["confirmations"], error_log_path=error_log_path)
trade_engine = TradeEngine(config, coins, tx_monitor, demo)
    

