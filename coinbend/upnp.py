from .lib import *
from .sock import *
import urllib.request, re, sys, select, socket, time
import multiprocessing
import threading
import netifaces

"""
This is a modified version of "UPnP-Exploiter." It's been
changed to work with Python 3.3, the code has been
restructured to make it modular, commented, and easier to use.
I've also removed the original exploit code and only the port
forwarding code remains.

Original code available here: https://github.com/dc414/Upnp-Exploiter
Credits to "Anarchy Angel", "Ngharo", and www.dc414.org
for the code.
"""

class UPnP():
    def __init__(self, interface="default"):
        """
        Port used to listen to UPnP replies on.
        This port is actually arbitrary because
        all the sockets used are datagram sockets
        bound to all address which lets
        the socket hear broadcasts.
        """
        self.listen_port = 49170

        #Port that UPnP configured hosts listen on.
        self.upnp_port = 1900

        #Address used for IPv4 multicasts.
        self.multicast = "239.255.255.250"

        #Number of seconds to wait for replies.
        self.reply_wait = 15

        #Socket timeout.
        self.timeout = 1

        #Networking interface.
        self.interface = interface

    def create_multicast(self, addr, port, reuse=0):
        #Create socket for UDP broadcasts.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #REUSE causes problems with windows: i.e. dropped packets
        #When sockets aren't gracefully closed from app crashes
        if reuse:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)
        s.bind((addr, port))
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)

        #Join multicast group.
        iface = socket.inet_aton(addr) # listen for multicast packets on this interface.
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, iface)
        group = socket.inet_aton(self.multicast)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, group + iface)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(0)

        return s

    def close_socket(self, s):
        if s:
            try:
                s.shutdown(socket.SHUT_RDWR)
            except:
                pass

            try:
                s.close()
            except:
                pass

    def send_search(self, msg, addr):
        s = self.create_multicast(addr, 0)
        s.sendto(bytes(msg, 'UTF-8'), (self.multicast, self.upnp_port))
        self.close_socket(s)

    #Uses broadcasting to find default UPnP compatible gateway.
    def find_gateway(self):
        print("Trying to find UPnP compatible gateway.")

        """
        Responses are monitored on every possible interface because on other operating systems *cough* Windows *cough* it doesn't process multicast very well ...
        """
        cons = []
        ips = []
        for interface in netifaces.interfaces():
            try:
                ip = get_lan_ip(interface)
                if ip == None:
                    continue
        
                con = self.create_multicast(ip, self.upnp_port)
            except:
                continue

        
            cons.append(con)
            ips.append(ip)

        #Broadcast search message to multicast address.
        search_msg =  "M-SEARCH * HTTP/1.1\r\n"
        search_msg += "HOST: %s:%s\r\n" % (str(self.multicast), str(self.upnp_port))
        search_msg += "ST: ssdp:all\r\n"
        search_msg += "MX: 3\r\n"
        search_msg += "\r\n"
        for ip in ips:
            self.send_search(search_msg, ip)
            
        #Log replies from all interfaces.
        replies = []
        start_time = time.time()
        while int(time.time() - start_time) < self.reply_wait:
            for con in cons:
                res = select.select([con], [], [], self.timeout)
                if len(res[0]):
                    (string, addr) = res[0][0].recvfrom(1024);
                    replies.append([addr[0], string])

            time.sleep(1)

        #Graceful shutdown.
        for con in cons:
            self.close_socket(con)

        #Error: no UPnP replies - try guess gateway.
        if replies == []:
            default_gateway = get_default_gateway(self.interface)
            print("Replies = none")
            print("Trying to guess gateway address.")
            print(default_gateway)
            if default_gateway == None:
                return None
            else:
                #Optimise scanning.
                likely_candidates = [80, 1780, 1900, 1981, 2468, 5555, 5678, 49000, 55345, 65535]

                #Brute force port by scanning.
                for port in likely_candidates:
                    try:
                        #Fast connect() / SYN open scanning.
                        s = Sock(default_gateway, port, blocking=1, timeout=1, interface=self.interface)
                        s.close()
                        
                        #Build http request.
                        gateway_addr = "http://" + str(default_gateway) + ":" + str(port) + "/"
                        buf = urllib.request.urlopen(gateway_addr, timeout=self.timeout).read().decode("utf-8")

                        #Check response is XML and device is a router.
                        if 'InternetGatewayDevice' in buf:
                            print("Guessed gateway address.")
                            return gateway_addr
                    except:
                        continue

                return None

        #Find gateway address in replies.
        gateway_addr = None
        pdata = list(dict((x[0], x) for x in replies).values())
        #return None
        rh = []
        for L in pdata:
            rh.append(L[0])
        hosts = []
        pd = []
        for host in rh:
            try:
                spot = rh.index(host)
                hdata = pdata[spot][1]
                url = 'http://' + host + ':'
                port = re.findall("http:\/\/[0-9\.]+:(\d.+)", hdata.decode("utf-8"))
                url += port[0]
                p = urllib.request.urlopen(url, timeout=self.timeout)
                rd = re.findall('schemas-upnp-org:device:([^:]+)', p.read().decode("utf-8"))
                if rd[0] == 'InternetGatewayDevice':
                    gateway_addr = url
                    break
            except:
                continue

        return gateway_addr

    def forward_port(self, proto, src_port, dest_ip, dest_port=None, skip=0):
        """
        Creates a new mapping for the default gateway to forward ports.
        Source port is from the perspective of the original client.
        For example, if a client tries to connect to us on port 80,
        the source port is port 80. The destination port isn't
        necessarily 80, however. We might wish to run our web server
        on a different port so we can have the router forward requests
        for port 80 to another port (what I call the destination port.)

        If the destination port isn't specified, it defaults to the
        source port. Proto is either TCP or UDP. Function returns None
        on success, otherwise it raises an exception.
        """

        proto = proto.upper()
        valid_protos = ["TCP", "UDP"]
        if proto not in valid_protos:
            raise Exception("Invalid protocol for forwarding.")

        valid_ports = range(1, 65535)
        if src_port not in valid_ports:
            raise Exception("Invalid port for forwarding.")

        #Source port is forwarded to same destination port number.
        if dest_port == None:
            dest_port = src_port

        #Find gateway address.
        gateway_addr = self.find_gateway()
        print("Gateway addr = ")
        print(gateway_addr)
        if gateway_addr == None:
            raise Exception("Unable to find UPnP compatible gateway.")

        #Get control URL.
        try:
            rhost = re.findall('([^/]+)', gateway_addr)
            res = urllib.request.urlopen(gateway_addr, timeout=self.timeout).read().decode("utf-8")
            res = res.replace('\r', '')
            res = res.replace('\n', '')
            res = res.replace('\t', '')
            pres = res.split('<serviceId>urn:upnp-org:serviceId:WANIPConn1</serviceId>')
            p2res = pres[1].split('</controlURL>')
            p3res = p2res[0].split('<controlURL>')
            ctrl = p3res[1]
            rip = res.split('<presentationURL>')
            rip1 = rip[1].split('</presentationURL>')
            routerIP = rip1[0]
        except:
            raise Exception("Unable to find control URL.")

        port_map_desc = "Coinbend"
        msg = \
            '<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:AddPortMapping xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1"><NewRemoteHost></NewRemoteHost><NewExternalPort>' \
            + str(src_port) \
            + '</NewExternalPort><NewProtocol>' + str(proto) + '</NewProtocol><NewInternalPort>' \
            + str(dest_port) + '</NewInternalPort><NewInternalClient>' + str(dest_ip) \
            + '</NewInternalClient><NewEnabled>1</NewEnabled><NewPortMappingDescription>' + str(port_map_desc) + '</NewPortMappingDescription><NewLeaseDuration>0</NewLeaseDuration></u:AddPortMapping></s:Body></s:Envelope>'

        #Attempt to add new port map.
        x = 'http://' + rhost[1] + '/' + ctrl
        try:
            req = urllib.request.Request('http://' + rhost[1] + '/' + ctrl, bytes(msg, "utf-8"))
            req.add_header('SOAPAction',
                           '"urn:schemas-upnp-org:service:WANIPConnection:1#AddPortMapping"'
                           )
            req.add_header('Content-type', 'application/xml')
            res = urllib.request.urlopen(req, timeout=self.timeout)
        except Exception as e:
            print(e)
            #Sometimes the device is busy - try one more time.
            try:
                if not skip:
                    self.forward_port(proto, src_port, dest_ip, dest_port, 1)
                else:
                    raise Exception("Second attempt to UPnP forward failed.")
            except Exception as e:
                print(e)
                raise Exception("Failed to add port mapping.")

if __name__ == "__main__":
    port = 50500
    addr = "192.168.0.3" 
    UPnP().forward_port("TCP", port, addr)
    forwarding_servers = [{"addr": "www.coinbend.com", "port": 80, "url": "/net.php"}]
    print(is_port_forwarded(addr, str(port), "TCP",  forwarding_servers))





