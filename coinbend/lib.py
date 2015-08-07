"""
Small functions that don't really fit any where.
"""

import os
import platform
import netifaces
import random
import socket
import ipaddress
import ntplib
import time
import urllib.request
import select
import bitcoin
import hashlib
import random
import datetime
import binascii
import re
import base64
import struct
import uuid
import json
import sys
import traceback

from .ipgetter import *
from .cryptocurrencies import *
from .fiatcurrencies import *
from .args import args

from bitcoin import SelectParams
import bitcoin.base58
from bitcoin.core import b2x, lx, x, COIN, COutPoint, CTxOut, CTxIn, CTransaction, Hash160, Serializable
from bitcoin.core.script import CScript, OP_DUP, OP_NUMEQUAL, OP_DROP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, SIGHASH_ANYONECANPAY, SIGHASH_SINGLE, OP_IF, OP_CHECKMULTISIGVERIFY, OP_NOTIF, OP_ELSE, OP_ENDIF, OP_VERIFY, OP_SHA256, OP_CHECKSIGVERIFY, OP_EQUAL, OP_FALSE, OP_3, OP_0, OP_1, OP_2, OP_5, OP_4, OP_TOALTSTACK, OP_TRUE, OP_DEPTH
from bitcoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from bitcoin.wallet import CBitcoinAddress, CBitcoinSecret
from decimal import Decimal
import numpy

def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError as e:
        return False

    return True

def log_exception(file_path, msg):
    msg = "\r\n" + msg
    with open(file_path, "a") as error_log:
        error_log.write(msg)

def parse_exception(e, output=0):
    tb = traceback.format_exc()
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    error = "%s %s %s %s %s" % (str(tb), str(exc_type), str(fname), str(exc_tb.tb_lineno), str(e))

    if output:
        print(error)

    return str(error)

def get_unique_id():
    guid = str(uuid.uuid4()).encode("ascii")
    return hashlib.sha256(guid).hexdigest()

def otp_encrypt(plaintext):
    from Crypto import Random
    satoshi = Random.new()
    plaintext_len = len(plaintext)
    otp = satoshi.read(plaintext_len)

    ciphertext = b""
    if type(plaintext) == str:
        plaintext = plaintext.encode("ascii")
    for i in range(0, plaintext_len):
        ciphertext += bytes([plaintext[i] ^ otp[i]])

    ret = {
        "otp": otp,
        "ciphertext": ciphertext
    }

    return ret

def otp_decrypt(otp, ciphertext):
    plaintext = b""
    ciphertext_len = len(ciphertext)
    for i in range(0, ciphertext_len):
        plaintext += bytes([ciphertext[i] ^ otp[i]])

    return plaintext

def ip2int(addr):                                                               
    return struct.unpack("!I", socket.inet_aton(addr))[0]                       

def int2ip(addr):                                                               
    return socket.inet_ntoa(struct.pack("!I", addr))    

#Patches for urllib2 and requests to bind on specific interface.
#http://rossbates.com/2009/10/26/urllib2-with-multiple-network-interfaces/
true_socket = socket.socket
def build_bound_socket(source_ip):
    def bound_socket(*a, **k):
        sock = true_socket(*a, **k)
        sock.bind((source_ip, 0))
        return sock
    
    return bound_socket

def find_trade_by_instance_id(instance_id, trades):
    if instance_id == None:
        raise Exception("Invalid contract hash in find_match_state.")

    for our_trade in trades:
        contract_factory = our_trade.contract_factory
        if contract_factory == None:
            continue

        if contract_factory.instance_id == instance_id:
            return our_trade

    return None

def parse_msg(msg, version, con, msg_handlers, sys_clock, config):
    #Unicode / str for text patterns.
    try:
        if type(msg) == bytes:
            msg = msg.decode("utf-8")
    except:
        #Received invalid characters.
        print("Parse msg error 1")
        return []

    #Get version and time for message.
    matches = re.findall(r"^([0-9]+) ([0-9]+(?:[.][0-9]+)?) ([a-zA-Z_]+)", msg)
    if not len(matches):
        print("Parse msg error 2")
        return []
    protocol_version, ntp, rpc = matches[0]
    protocol_version = int(protocol_version)
    ntp = int(ntp)

    #Check protocol version.
    if protocol_version != version:
        print("Parse msg error 3")
        return []

    #Message sending time compared to actual time.
    #(This helps stop messages from propagating forever.)
    t = sys_clock.time()
    dif = t - ntp

    #NTP is too far in the future (invalid.)
    if not int(config["debug"]):
        if dif <= -(60 * 15):
            return []

        #NTP is too far in the past (expired.)
        if dif >= 60 * 15:
            return []

    if rpc in msg_handlers:
        return msg_handlers[rpc](msg, protocol_version, ntp, con)

    return []

"""
Determines whether the difference between two numbers is within a n% increase or decrease of each other.
"""
def is_percent_change(a, b, p=0.2):
    if a == b:
        return 1

    if a < b:
        dif = b - a
        bound = b * p
    else:
        dif = a - b
        bound = a * p

    if dif <= bound:
        return 1
    else:
        return 0

"""
Takes an unknown string and returns bytes.
* If the string is a hex string it will be decoded.
* If the string is base64 encoded it will be decoded.
"""
def auto_bytes(s):
    #None.
    if s == None:
        return s

    #Already bytes.
    if type(s) == bytes:
        return s

    #Hex string.
    if re.match("^[#][0-9a-fA-F]+$", s) != None and not ((len(s) - 1) % 2):
        return binascii.unhexlify(s[1:])

    #Base64 string.
    if re.match("^[a-zA-Z0-9+=/]+$", s) != None:
        try:
            return base64.b64decode(s)
        except:
            pass

    return s.encode("ascii")

def pow_mod(x, y, z):
    "Calculate (x ** y) % z efficiently."
    number = 1
    while y:
        if y & 1:
            number = number * x % z
        y >>= 1
        x = x * x % z
    return number

b58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def base58encode(n):
    result = ''
    while n > 0:
        result = b58[n % 58] + result
        n /= 58
    return result

def base58decode(s):
    result = 0
    for i in range(0, len(s)):
        result = result * 58 + b58.index(s[i])
    return result

def base256encode(n):
    result = b''
    while n > 0:
        result = bytes([int(n % 256)]) + result
        n /= 256
    return result

def base256decode(s):
    result = 0
    for c in s:
        result = result * 256 + ord(c)
    return result

def countLeadingChars(s, ch):
    count = 0
    for c in s:
        if c == ch:
            count += 1
        else:
            break
    return count

def random_index_in_list(l):
    return random.randrange(0, len(l)) 

#Resolves, sym links, rel paths, variables, and tilds to abs paths.
def map_path(path):
    return os.path.realpath \
    (
        os.path.expandvars \
        (
            os.path.expanduser(path)
        )
    )

def init_data_dirs(data_dir, bk_data_dir):
    #Create data dirs if needed.
    data_dir = data_dir
    bk_data_dir = bk_data_dir
    for path in [data_dir, bk_data_dir]:
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except:
                print("Unable to make data dir: " + path)
                exit()

def get_ntp():
    """
    Retrieves network time from a European network time server.
    """

    global args
    if args.uselocaltime != None:
        return int(time.time())

    servers = [
    "0.pool.ntp.org",
    "1.pool.ntp.org",
    "2.pool.ntp.org",
    "3.pool.ntp.org"]
    for server in servers:
        try:
            client = ntplib.NTPClient()
            response = client.request(server)
            ntp = response.tx_time
            return ntp
        except Exception as e:
            continue
    return None

def get_default_gateway(interface="default"):
    try:
        gws = netifaces.gateways()
        return gws[interface][netifaces.AF_INET][0]
    except:
        return None

def get_lan_ip(interface="default"):
    try:
        gws = netifaces.gateways()
        if interface == "default":
            interface = gws["default"][netifaces.AF_INET][1]
        addr = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]["addr"]
        return addr
    except:
        return None

def sequential_bind(n, interface="default"):
    bound = 0
    mappings = []
    while not bound:
        bound = 1
        start = random.randrange(1024, 65535 - n)
        for i in range(0, n):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            local = start + i
            try:
                addr = ''
                if interface != "default":
                    addr = get_lan_ip(interface)
                sock.bind((addr, local))
            except Exception as e:
                bound = 0
                for mapping in mappings:
                    mapping["sock"].close()
                mappings = []
                break
            mapping = {
                "source": local,
                "sock": sock
            }
            mappings.append(mapping)
                    
    return mappings

def is_port_forwarded(source_ip, port, proto, forwarding_servers):
    import urllib.request
    global true_socket
    if source_ip != None:
        socket.socket = build_bound_socket(source_ip)

    ret = 0
    for forwarding_server in forwarding_servers:
        url = "http://" + forwarding_server["addr"] + ":"
        url += str(forwarding_server["port"])
        url += forwarding_server["url"]
        url += "?action=is_port_forwarded&port=" + str(port)
        url += "&proto=" + str(proto.upper())
        req = urllib.request.Request(url)
        r = urllib.request.urlopen(req, timeout=2)
        response = r.read().decode("utf-8")
        if "yes" in response:
            ret = 1
            break

    socket.socket = true_socket
    return ret

def is_ip_private(ip_addr):
    try:
        if ipaddress.ip_address(ip_addr).is_private or ip_addr != "127.0.0.1":
            return 1
        else:
            return 0
    except:
        return 0

def is_ip_public(ip_addr):
    if is_ip_private(ip_addr):
        return 0
    else:
        return 1

def is_ip_valid(ip_addr):
    try:
        ipaddress.ip_address(ip_addr)
        return 1
    except:
        return 0

def is_valid_port(port):
    try:
        port = int(port)
    except:
        return 0
    if port < 1 or port > 65536:
        return 0
    else:
        return 1

def memoize(function):
    memo = {}
    def wrapper(*args):
        if args in memo:
            return memo[args]
        else:
            rv = function(*args)
            memo[args] = rv
            return rv
    return wrapper

@memoize
def get_wan_ip():
    global args
    if args.wanip != None:
        return args.wanip
    else:
        return myip()

def trimmed_mean(array, percent=0.20):
    """
    Calculates the largest possible set of similar numbers by comparing numbers to every other number and noting the number of similarities shown by considering the % of difference. All numbers outside the most common set are excluded as outliers and the remaining numbers are averaged.
    """

    #Record a list of numbers close in value to each other.
    related_numbers = []
    array_len = len(array)
    for i in range(0, array_len):
        #Init.
        related_numbers.append([])

        #Store the current number in the set.
        related_numbers[i].append(array[i])

        #Now compare the other numbers to find similarities.
        for j in range(0, array_len):
            if i == j:
                continue

            if array[i] < array[j]:
                dif = array[j] - array[i]
                if dif and array[i]:
                    if dif / array[i] <= percent:
                        related_numbers[i].append(array[j])
            else:
                dif = array[i] - array[j]
                if dif and array[j]:
                    if dif / array[j] <= percent:
                        related_numbers[i].append(array[j])

    #Sort related number sets by highest membership.
    sorting = True
    while sorting:
        sorting = False
        for i in range(0, len(related_numbers)):
            if i == len(related_numbers) - 1:
                break

            if len(related_numbers[i]) < len(related_numbers[i + 1]):
                sorting = True
                related_numbers[i], related_numbers[i + 1] = \
                related_numbers[i + 1], related_numbers[i]

    #Create sets of just the highest memberships.
    highest_memberships = []
    for i in range(0, len(related_numbers)):
        if len(related_numbers[i]) == len(related_numbers[0]):
            highest_memberships.append(related_numbers[i])

    #Calculate the averages for prospective sets.
    related_avgs = []
    for i in range(0, len(highest_memberships)):
        total = 0
        related_numbers = len(highest_memberships[i])
        for j in range(0, related_numbers):
            total += highest_memberships[i][j]
        
        avg = total / related_numbers
        related_avgs.append(avg)

    #Sort related averages from lowest to highest.
    sorting = True
    while sorting:
        sorting = False
        for i in range(0, len(related_avgs)):
            if i == len(related_avgs) - 1:
                break

            if related_avgs[i] > related_avgs[i + 1]:
                sorting = True
                related_avgs[i], related_avgs[i + 1] = \
                related_avgs[i + 1], related_avgs[i]

    #Return the first average.
    if len(related_avgs):
        return related_avgs[0]
    else:
        return Decimal(0)

def get_currency_code(unknown, crypto={}, fiat={}):
    unknown = unknown.upper()
    if unknown in crypto:
        if "code" not in crypto[unknown]:
            return unknown
        else:
            return crypto[unknown]["code"]

    if unknown in fiat:
        if "code" not in fiat[unknown]:
            return unknown
        else:
            return fiat[unknown]["code"]

    return None

if __name__ == "__main__":
    print(trimmed_mean([Decimal('0.393748'), Decimal('179015'), Decimal('0.6034667256')]))




