"""
The contract client is what communicates with the contract server and is designed to manipulate the status of setup transactions.
"""

from .globals import *
from .lib import *
from .sock import *
from .coinlib import *
from .currency_type import *
from .microtransfer_contract import *
import base64
import binascii
from bitcoin.core import b2x

class ContractClient():
    def __init__(self, hybrid_protocol, config, blocking=0):
        self.version = 1
        self.hybrid_protocol = hybrid_protocol
        self.config = config
        self.host = self.config["contract_server"]["addr"]
        self.port = self.config["contract_server"]["port"]
        self.blocking = blocking
        self.con = Sock(self.host, self.port, blocking=self.blocking, use_ssl=1)
        self.msg_handlers = {
            "READY": self.parse_ready_msg
        }

    def new_register(self, tx_hex, ecdsa_1, ecdsa_2, sig_1, sig_2, instance_id=None):
        msg  = "%s " % (str(self.version))
        msg += "%s " % (str(int(self.hybrid_protocol.sys_clock.time())))
        msg += "REGISTER %s " % (tx_hex)
        msg += "%s " % (ecdsa_1.get_public_key())
        msg += "%s " % (ecdsa_2.get_public_key())
        msg += "%s " % (base64.b64encode(sig_1).decode("utf-8"))
        msg += "%s " % (base64.b64encode(sig_2).decode("utf-8"))
        if instance_id == None:
            msg += "Syro"
        else:
            msg += instance_id

        return msg

    def new_match(self, contract_msg, our_handshake, their_handshake, collateral_info, instance_id):
        if type(contract_msg) == str:
            contract_msg = contract_msg.encode("ascii")
        if type(our_handshake) == str:
            our_handshake = our_handshake.encode("ascii")
        if type(their_handshake) == str:
            their_handshake = their_handshake.encode("ascii")
        if type(collateral_info) == str:
            collateral_info = collateral_info.encode("ascii")

        msg  = "%s " % (str(self.version))
        msg += "%s " % (str(int(self.hybrid_protocol.sys_clock.time())))
        msg += "MATCH %s " % (base64.b64encode(contract_msg).decode("utf-8"))
        msg += "%s " % (base64.b64encode(our_handshake).decode("utf-8"))
        msg += "%s " % (base64.b64encode(their_handshake).decode("utf-8"))
        msg += "%s " % (base64.b64encode(collateral_info).decode("utf-8"))
        msg += "%s" % (instance_id)
        
        return msg

    def new_update(self, instance_id, new_tx_hex):
        msg  = "%s " % (str(self.version))
        msg += "%s " % (str(int(self.hybrid_protocol.sys_clock.time())))
        msg += "UPDATE %s " % (instance_id)
        msg += "%s" % ((base64.b64encode(binascii.unhexlify(new_tx_hex)).decode("utf-8")))

        return msg

    def new_query(self, instance_id):
        msg  = "%s " % (str(self.version))
        msg += "%s " % (str(int(self.hybrid_protocol.sys_clock.time())))
        msg += "QUERY %s" % (instance_id)

        return msg

    def parse_setup_details_msg(self, msg):
        pass

    def parse_ready_msg(self, msg, version, ntp, con=None):
        global coins
        global tx_monitor

        print("In parse ready message.")
        matches = re.findall("(READY) ([^\s]{1,120}) ([^\s]{1,256})((?:\s[^\s@]+@[^\s@]+)+)((?:\s[^\s]+)+)$", msg)
        if not len(matches):
            print("Invalid ready message.")
            time.sleep(20)
            return [80]
        else:
            #Parse matches.
            rpc, instance_id, sig_3, setup_details, collateral_info = matches[0]
            sig_3 = base64.b64decode(sig_3.encode("ascii"))
            setup_details = filter(None, setup_details.split(" "))

            #Parse collateral_infos.
            temp = {}
            collateral_info = filter(None, collateral_info.split(" "))
            for info in collateral_info:
                info = self.hybrid_protocol.parse_collateral_info(info)
                temp[info["pub_1"]] = info
            collateral_info = temp

            #Find trade.
            trade = find_trade_by_instance_id(instance_id, self.hybrid_protocol.trade_engine.trades)
            if trade != None:
                print("Found trade in ready message.")

                #Find contract factory.
                contract_factory = trade.contract_factory
                if contract_factory == None:
                    return []

                #Check signed setup TX is valid.
                ecdsa_1 = contract_factory.green_address.ecdsa_1
                ecdsa_2 = contract_factory.green_address.ecdsa_2
                sig_1 = contract_factory.setup["sig_1"]
                sig_2 = contract_factory.setup["sig_2"]
                trade_fee = C(self.config["trade_fee"])
                ret = validate_setup_tx(config, contract_factory.setup["tx_hex"], ecdsa_1, ecdsa_2, sig_1, sig_2, sig_3, collateral_info, trade_fee)
                if type(ret) != dict:
                    print("Validate setup tx failed. \a \a \a")
                    time.sleep(20)
                    return []

                #Save setup tx details.
                setup_tx = ret["setup"]["signed"]["tx"].serialize()
                setup_tx_hex = b2x(setup_tx)
                contract_factory.setup["signed"]["tx_hex"] = setup_tx_hex
                contract_factory.setup["signed"]["txid"] = ret["setup"]["signed"]["txid"]
                contract_factory.green_address.setup_tx_hex = setup_tx_hex
                contract_factory.green_address.setup_txid = calculate_txid(setup_tx_hex)
                contract_factory.green_address.update()

                #Broadcast our setup transactions.
                rpc = coins[trade.to_send.currency]["rpc"]["sock"]
                print(rpc)
                print(trade.to_send.currency)
                print("Setup txid = ")
                print(calculate_txid(setup_tx_hex))
                print(rpc.sendrawtransaction(setup_tx_hex))

                #Update setup_txid table.
                for setup_detail in setup_details:
                    """
                    I always get confused what these additional setup TXIDs are for. Basically, every contract has two sides: our side and theirs. This ready message gives us back our signed TX hex for our setup TX but every contract this applies to also has a corresponding setup TX belonging to the person the contract is for. These TXIDs are for those setup transactions and allow the client to verify received setup transactions so they can't be double spent. The other sides setup transaction basically prove that their money that is being moved to us is funded and exists in the contract outputs.
                    """
                    setup_detail = setup_detail.split("@")
                    setup_txid, contract_hash = setup_detail
                    contract_factory.setup_txids[contract_hash] = setup_txid
                    contract = contract_factory.contracts[contract_hash]
                    matched = contract.matched

                def callback(event, tx_hex, needle):
                    print("------------------")
                    print("\a")
                    print("\a")
                    print("Setup TX confirmed.")

                    #Update state.
                    if trade.actor == "seller":
                        matched.update_state("pending_seller_get_refund_sig")
                    else:
                        matched.update_state("pending_buyer_return_refund_sig")

                    #Todo: you could update the setup TX here so if it gets mutated the client still returns the correct hex. You would have to update the logic for the setup_txid checks though.
                    contract_factory.green_address.setup_tx_hex = tx_hex
                    contract_factory.green_address.setup_txid = calculate_txid(tx_hex)
                    contract_factory.green_address.update()

                callbacks = {
                    "confirm": callback,
                    "mutate": callback
                }

                needle = {
                    "type": "tx_hex",
                    "value": setup_tx_hex
                }

                tx_monitor.add_watch(trade.to_send.currency, needle, callbacks, "Contract setup TX", contract_hash)

                #Update collateral info.
                contract_factory.collateral_info = collateral_info
                
                print("Pending refund.")
                return []

        print("Didn't find trade \a\a\a\a\a !!!")
        time.sleep(20)

        return []

    def process_replies(self):
        try:
            for reply in self.con:
                print(reply)
                parse_msg(reply, self.version, self.con, self.msg_handlers, self.hybrid_protocol.sys_clock, self.config)
        except Exception as e:
            error = parse_exception(e)
            log_exception(error_log_path, error)
            print(error)


if __name__ == '__main__':
    sock = Sock("localhost", 64111, blocking=1, use_ssl=1)

    #Bob
    sock.send_line("1 1426058400 REGISTER 0100000001a460e209db9ba6bc9789485e332f8db282b5b2220c256339b9459449db8b49290100000000ffffffff02bd090000000000001976a91485c4047b337bb045a06684a096ab6615119c58e288acd3c603000000000017a9142ba418946938122da64bface7de4148c8d519ac68700000000 A4v2/cjrCO6fQhvyptLigei7flOqOSPvXtAoOFNEIEpT AhRTGoLQb3oaoRWnZ0V7qdkMVSZqRU0mTnp6NT3Gtc0K MEUCIBHTjdmB6+3HTnBS7cbaoDJ+iCaHB8ZcqLC7o5luCre7AiEA9T33escRMcCyB+asrNka28VmY2CRRfo52MZwQh46/RwB MEUCIQCFJlbdlqf51TnhPeg+SiO9HhLAD86A6I1OHae2Toeu3QIgCNBXwou1wzPWadI/Y3SFDz4TZk6lZ5B601H0Atsud9EB i2XM0rb3BhO98GdI4bdT2uB85Up0Mg")

    sock.send_line("1 1426058400 MATCH MSAxNDI2MDU4NDAwIGUzZDkxOGVhM2ZiNjg2NDJkYjBjZWYxN2M3MWFmMmUwYTg4ZDlkZDk5NDk0YzUxMzJiYTM5Y2NkMDM3ZGY2YzMgYml0Y29pbi9saXRlY29pbiAwLjQ5NzUgMC4wMDUgQTR2Mi9janJDTzZmUWh2eXB0TGlnZWk3ZmxPcU9TUHZYdEFvT0ZORUlFcFQgQWhSVEdvTFFiM29hb1JXblowVjdxZGtNVlNacVJVMG1UbnA2TlQzR3RjMEsgQXhkcENCOVFmclV1M1RWdlorczhMN25Wd2c0Um1kL25xMW80Z1dSTXFzdzMgQS9jRmtlN2ErQlpQNmpZN2FFZkhpYmRTOXZQbFp2NHlOZVNLdlZXV3VzNmkgQW40enl2aTBOdG8wenVXNEU3aGpFdUVPckZMYmYrR0wzbU1tNTl6NlNMd0YgQXhkcENCOVFmclV1M1RWdlorczhMN25Wd2c0Um1kL25xMW80Z1dSTXFzdzMgMjk0OThiZGI0OTk0NDViOTM5NjMyNTBjMjJiMmI1ODJiMjhkMmYzMzVlNDg4OTk3YmNhNjliZGIwOWUyNjBhNCAxXyA5YWYxYzk4ZTQ2YzhiZGE0NmNkZTU3Mzc0YjRkOGJhYTMwNGZhZjEzMmJhYmZjMzg2Y2FmN2QzMzMwM2U4ZDc1IDBfIDAuMDAgMC4wMCAwLjAwMjQ4NzUgMC4wMDAwMTI0MyA4Q3MzLzltb1ozVGtqQ3J2ZXkvOUsxVFc1cXk0VERHV3dXQmd0R280c081a3dVd0JSTjU3MG5OL29ZTkNzenRka0hFcFVNSFRveGhMeTBlKzlGKy9mdz09IHZpRzQxOHkyc0lUVHFVMENvK3NSREpJcGNBV1gvWjJwVVRXZnk1V2kzUlc2bkh1OWlzdEp4Y2x3anhqeUVNRGpsTkFGYXR6ODdlLzZrdVpzY3daTGtnPT0gL21wbmNaNzJZNmVDenlrdzdlM3ZpUW9SZW05L1JSZWhDbDBDVE9lVXJ0U1hVNktiYUpjT0hwdVhPRGlnMkU2dkFSN1RhaFFhNVR5cGZSNzlCc1NmNmc9PSB4VGprSDFvVVlWN3ZuUXUrZVFydDBGUXBvN3o3WFJMQ1RLbkV0TnJ3UTBmRlVTMG95UFJwOGs1VmtMUyt6OENtV0VSaGRCYU1kajB5YzJFRitIZEU5UT09 MSAxNDI2MDU4NDAwIHNoYWtlX29uX2l0IDNhYWQyNWQ1N2Y1M2U2ODM3YzNjNmQ1NmI0M2Q5MTQ5NDVlNjM1ZjUzZTFmNTFlZGI5ZTIwODA2NWY3OTgwMTQgWlQ3ZnVVZytuMkRFRmsrMU85Sjl6NzViRitOVUtUSVFFYnAvWWJqalJ3OTMrelpwNll4SFFTTTBBMm42ZFBLMWUzdVBwM0R2Y3hWRDBFSy9GQnlMVkE9PQ== MSAxNDI2MDU4NDAwIHNoYWtlX29uX2l0IDNhYWQyNWQ1N2Y1M2U2ODM3YzNjNmQ1NmI0M2Q5MTQ5NDVlNjM1ZjUzZTFmNTFlZGI5ZTIwODA2NWY3OTgwMTQgcGwvS1hRMk8vbnpYVjA1aDVLM0YvSW9xb0xVT2xUemxKMzFORU5iYW1LanhvaFgxczBmWnN1djdQU1ZPVk1HOVdCc3F2ckdoL1EzWUlENUVtZnFnOXc9PQ== MC4wMDAwMTI0MyBBN3pGUkhyL1A1d1BjSnRtTzBKQm9rcFZzcEVvVWg0NzYyUTB0U1Z4QmFHUiBNWmEvNTR5RWkyLzUxdmNqM2QralNqNFhDM29nU2dsU2JrMUVrbGFlckR4ZGJnS0FYa1B2eDJMWk5ONk1QU0R1UVp4WWdBeTZid1JVQUtLWlFIdlhLZz09IEE0djIvY2pyQ082ZlFodnlwdExpZ2VpN2ZsT3FPU1B2WHRBb09GTkVJRXBUIGlWMloyckZrK2VUenk0cStCbVRXbVUwMUIySVFpZmZxZC9GWklXWlVnaWZNb2xUNVh4cnRhaENGTEdEY1ZrNC9pYm5GNkFsZU4zZFdGcWQ2Qk1MS0t3PT0gQWhSVEdvTFFiM29hb1JXblowVjdxZGtNVlNacVJVMG1UbnA2TlQzR3RjMEs= i2XM0rb3BhO98GdI4bdT2uB85Up0Mg")


    #Alice.

    sock.send_line("1 1426058400 REGISTER 0100000001758d3e30337daf6c38fcab2b13af4f30aa8b4d4b3757de6ca4bdc8468ec9f19a0000000000ffffffff023e9c0700000000001976a91485c4047b337bb045a06684a096ab6615119c58e288ac4254f3020000000017a914ba9cd4af6f553e4a2ac3a593cf0ca8d3127a58bd8700000000 A/cFke7a+BZP6jY7aEfHibdS9vPlZv4yNeSKvVWWus6i An4zyvi0Nto0zuW4E7hjEuEOrFLbf+GL3mMm59z6SLwF MEUCIQCL022H928+hIBT2sB2+CWTfQpoXJMq5KwncQYRxxSujQIgc0ZF1qb11VStefWD8kVxiyYTe6fFvt6EkbIas8/csncB MEUCIEs2KDy0whO8ViXwHIkup9mMOOrW2yqiNq0GW4MhW4kWAiEAyXHN5lBJDRYkVsS1VDpQekTTTvw+C+eCRriVEKTcb3wB Xk8O4j1qVjQ49HwG2t7lDOq3h9B3aY")

    sock.send_line("1 1426058400 MATCH MSAxNDI2MDU4NDAwIGUzZDkxOGVhM2ZiNjg2NDJkYjBjZWYxN2M3MWFmMmUwYTg4ZDlkZDk5NDk0YzUxMzJiYTM5Y2NkMDM3ZGY2YzMgYml0Y29pbi9saXRlY29pbiAwLjQ5NzUgMC4wMDUgQTR2Mi9janJDTzZmUWh2eXB0TGlnZWk3ZmxPcU9TUHZYdEFvT0ZORUlFcFQgQWhSVEdvTFFiM29hb1JXblowVjdxZGtNVlNacVJVMG1UbnA2TlQzR3RjMEsgQXhkcENCOVFmclV1M1RWdlorczhMN25Wd2c0Um1kL25xMW80Z1dSTXFzdzMgQS9jRmtlN2ErQlpQNmpZN2FFZkhpYmRTOXZQbFp2NHlOZVNLdlZXV3VzNmkgQW40enl2aTBOdG8wenVXNEU3aGpFdUVPckZMYmYrR0wzbU1tNTl6NlNMd0YgQXhkcENCOVFmclV1M1RWdlorczhMN25Wd2c0Um1kL25xMW80Z1dSTXFzdzMgMjk0OThiZGI0OTk0NDViOTM5NjMyNTBjMjJiMmI1ODJiMjhkMmYzMzVlNDg4OTk3YmNhNjliZGIwOWUyNjBhNCAxXyA5YWYxYzk4ZTQ2YzhiZGE0NmNkZTU3Mzc0YjRkOGJhYTMwNGZhZjEzMmJhYmZjMzg2Y2FmN2QzMzMwM2U4ZDc1IDBfIDAuMDAgMC4wMCAwLjAwMjQ4NzUgMC4wMDAwMTI0MyA4Q3MzLzltb1ozVGtqQ3J2ZXkvOUsxVFc1cXk0VERHV3dXQmd0R280c081a3dVd0JSTjU3MG5OL29ZTkNzenRka0hFcFVNSFRveGhMeTBlKzlGKy9mdz09IHZpRzQxOHkyc0lUVHFVMENvK3NSREpJcGNBV1gvWjJwVVRXZnk1V2kzUlc2bkh1OWlzdEp4Y2x3anhqeUVNRGpsTkFGYXR6ODdlLzZrdVpzY3daTGtnPT0gL21wbmNaNzJZNmVDenlrdzdlM3ZpUW9SZW05L1JSZWhDbDBDVE9lVXJ0U1hVNktiYUpjT0hwdVhPRGlnMkU2dkFSN1RhaFFhNVR5cGZSNzlCc1NmNmc9PSB4VGprSDFvVVlWN3ZuUXUrZVFydDBGUXBvN3o3WFJMQ1RLbkV0TnJ3UTBmRlVTMG95UFJwOGs1VmtMUyt6OENtV0VSaGRCYU1kajB5YzJFRitIZEU5UT09 MSAxNDI2MDU4NDAwIHNoYWtlX29uX2l0IDNhYWQyNWQ1N2Y1M2U2ODM3YzNjNmQ1NmI0M2Q5MTQ5NDVlNjM1ZjUzZTFmNTFlZGI5ZTIwODA2NWY3OTgwMTQgcGwvS1hRMk8vbnpYVjA1aDVLM0YvSW9xb0xVT2xUemxKMzFORU5iYW1LanhvaFgxczBmWnN1djdQU1ZPVk1HOVdCc3F2ckdoL1EzWUlENUVtZnFnOXc9PQ== MSAxNDI2MDU4NDAwIHNoYWtlX29uX2l0IDNhYWQyNWQ1N2Y1M2U2ODM3YzNjNmQ1NmI0M2Q5MTQ5NDVlNjM1ZjUzZTFmNTFlZGI5ZTIwODA2NWY3OTgwMTQgWlQ3ZnVVZytuMkRFRmsrMU85Sjl6NzViRitOVUtUSVFFYnAvWWJqalJ3OTMrelpwNll4SFFTTTBBMm42ZFBLMWUzdVBwM0R2Y3hWRDBFSy9GQnlMVkE9PQ== MC4wMDI0ODc1IEE3ekZSSHIvUDV3UGNKdG1PMEpCb2twVnNwRW9VaDQ3NjJRMHRTVnhCYUdSIFlmVmx1dTd1TkNGRGxGWWMxcFpaNnZaRmtWUjBuSzZrVjJMSXFIUk1DOFFNcWZPYVVYMG45NkZVcXZzM2VSdVM2KzNOZjlLSlNlWEZyRy91c0c1WS9nPT0gQS9jRmtlN2ErQlpQNmpZN2FFZkhpYmRTOXZQbFp2NHlOZVNLdlZXV3VzNmkgdkFNTHZRQ3UvdmlnN2lDcTB1S1VQOGdyZFRoSENMeXh2TUZkcXBGcjVOd054K2p1eDNZSVpBeHVDcWNaK1I4a0xRdjNjeFRibDZLVVd6N3poc25BdFE9PSBBbjR6eXZpME50bzB6dVc0RTdoakV1RU9yRkxiZitHTDNtTW01OXo2U0x3Rg== Xk8O4j1qVjQ49HwG2t7lDOq3h9B3aY")


    print(sock.recv_line())
    
    print(sock.recv_line())

    sock.close()
    
from .hybrid_protocol import parse_msg

