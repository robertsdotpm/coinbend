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
    sock.send_line("1 1438950100 REGISTER 01000000017795156d2942ee5e01e01fe1df29dafda64fa99a60425b974bca7c7b17004c0f0000000000ffffffff027c380f00000000001976a91485c4047b337bb045a06684a096ab6615119c58e288ac84a8e6050000000017a914aebd60767b97a9c9557db7fdf619f9af94132d638700000000 A4/yn8gEuzGwH8V8ADw3soQgWUceV80c4PXFj9r5EDcn A1k1qhGNK97o+OH8V6QqJujtccMd4JlryB53F6hJmP9H MEQCICt3AJwBS2IrZiQQYPH2mzMHufU82IANUQ/CFitPb8uPAiB1UciiZ0Ok/n8+zVHqLxjGmNE8mfXeLj96htKZq1eNIwE= MEYCIQC6gfJE7u270LdhAX4Svw9zqP+9ezdt1am3PTqKjf6OEwIhAPzTxbEpWNEv/H4hmZGaclj77/PmN3jn0/YX2dqbJe+oAQ== iZ7Z4s0Ts6pLA1odK9Z2b4Va6kRi0R")

    sock.send_line("1 1438950100 REGISTER 0100000001970ee9d179a2c81db915155816adc870ea0c2f6ce2569bc215f1ee1bed8b2e130000000000ffffffff02e020e40b000000001976a91485c4047b337bb045a06684a096ab6615119c58e288ac20a7339c0400000017a9146f30a2f027a1899e7250e96e6ecbe9569d6052058700000000 A2x6nmIvvUAi4504FtjL0Bg2bLA9EoAXCOgIJYurOnXA A+9gMxkRBoPG83x+tM9WeD4BokwFiQ5nITRIy2r9ldxK MEQCIGBvG5lMe4N1i4Ln4M/MdnVAlDKAzG9ZY1N8MqnO3vn0AiBrrDLtSddAyGYeZ4KdQCZFcKmPK5IjJuJ2+7znKeNGgQE= MEUCIDB+qK6dRYEgnRrIJSw7v2I1A1RoEeOBB+fLmBg3B4aMAiEA3oLwsF4+nH+klyzDjgKCo78aIigDemj6v7ZL5Rarn4sB aW24BzQu9Nq4cR98yZiY09mS8NsOu9")


    #Alice.

    sock.send_line("1 1438950100 MATCH MSAxNDM4OTUwMDAwIDkxZDU2YmExYTgwYThlZDcwMzZmNjRlZDc2MGMxYTZjOTVjZjdkOWZiN2E5NTgwYzY2OWQxZjZlNjMzYWM5MmMgZG9nZWNvaW4vbGl0ZWNvaW4gMTk5LjAwIDAuMDA1IG5rdFZxWmF5cmJnd2IyOFFwYXAxZ2VnbjNqeW16aVlOYnEgbjRlZ1VWb0FCdHdoOUdUOXRMZmZ2Wk5EN2lrQ0RxN3RZTiBBNC95bjhnRXV6R3dIOFY4QUR3M3NvUWdXVWNlVjgwYzRQWEZqOXI1RURjbiBBMWsxcWhHTks5N28rT0g4VjZRcUp1anRjY01kNEpscnlCNTNGNmhKbVA5SCBBeGRwQ0I5UWZyVXUzVFZ2WitzOEw3blZ3ZzRSbWQvbnExbzRnV1JNcXN3MyBBMng2bm1JdnZVQWk0NTA0RnRqTDBCZzJiTEE5RW9BWENPZ0lKWXVyT25YQSBBKzlnTXhrUkJvUEc4M3grdE05V2VENEJva3dGaVE1bklUUkl5MnI5bGR4SyBBeGRwQ0I5UWZyVXUzVFZ2WitzOEw3blZ3ZzRSbWQvbnExbzRnV1JNcXN3MyAwZjRjMDAxNzdiN2NjYTRiOTc1YjQyNjA5YWE5NGZhNmZkZGEyOWRmZTExZmUwMDE1ZWVlNDIyOTZkMTU5NTc3IDBfIDEzMmU4YmVkMWJlZWYxMTVjMjliNTZlMjZjMmYwY2VhNzBjOGFkMTY1ODE1MTViOTFkYzhhMjc5ZDFlOTBlOTcgMF8gMC4wMCAwLjAwIDAuOTk1IDAuMDA0OTc1IHdNVzNua0VmeXJaVXdYQ08zTkNpMHRxb3cxM1NZYit1WGJMRU4zRmdURXRkZGR1eVhwZnhjcjlZbG1oS1k5UmR3Tmd1L3VINTVVNFowMWh0czdQaExRPT0gUFFTbitaZ0FkbGJJbnV1YnA3KzFwdmVIVnlLa0J1V2owSEFYRW1LMkovc2pKeGlBaVBGUm1xUlppdCtBWTh3M0twN2R1NzVWVnM0R2J4OVVTWUxsRUE9PSBxMnlhNXh3UnBWTzFyZDR3V21yWEY2ckhhTk5xMjRXblZPTE96b2tXV2kzb256cVExL294QklPd2xQQ1B1eVRiM2cvTEwvdW9XQjFUVTJjZHJnSUovUT09IENvTGlUOWN1UVlSKytNeUZScysvODVjaG9kaXFST3hLemx3a2J6NGpMdFgzbUN2NVI0V2tlSG0yVGNYajMxSTlmblhUbWtmQm1HVjArVmlrSVYyanJBPT0= MSAxNDM4OTUwMTAwIHNoYWtlX29uX2l0IDgyNTg1ZDE3MWFlYWNiOTE0YzJlZDU5MzNmNjM1NDMwNTMxYjY0MzhlNjFiNGRkNDhjODliOTBhY2ZmNGFmY2IgTE5YTVRCbUQ2OW1XT1NNZFpGaDA5M1ZSTHpLYmpjRmRtVHdiaGVqa2U0QUdnRWFKajFXNE1NbExTN0Fvdm1CR0tjN1plV0ZiWU9VTjZVUnB0SHBwQkE9PQ== MSAxNDM4OTUwMTAwIHNoYWtlX29uX2l0IDgyNTg1ZDE3MWFlYWNiOTE0YzJlZDU5MzNmNjM1NDMwNTMxYjY0MzhlNjFiNGRkNDhjODliOTBhY2ZmNGFmY2IgOTg0TDlTOW5BVzhrTlpvK0ZpV2VVQlp3RnI1Ym11c1pWTXV3dWNpaUEwZ0Voa3NXdk44b3c5T3hFVytUSjZaQjN0L05acVRIS2NzWThZSUVQaWhFbGc9PQ== MC45OTUgQTd6RlJIci9QNXdQY0p0bU8wSkJva3BWc3BFb1VoNDc2MlEwdFNWeEJhR1IgUkNYTGxaYURwcHB3SEw2bkVCeUdybldhbHRCTWZVMVgwbVRoajkyNUVNN3Y1TEpTTEFxR1NqL2VGcDV3SHBYa0FUZ3BPTFdIZVdHU2g4STl0K0tHQ2c9PSBBNC95bjhnRXV6R3dIOFY4QUR3M3NvUWdXVWNlVjgwYzRQWEZqOXI1RURjbiBGenlTaitJT2lrVXhWU3Q3S1BsZVVwV3BmTFJKUWpWUEpGZmxXRThhQW0vTUc2T21jcWN5NUo1d3FXa2tRaWoyZ3o1M3E3MU9VeSt3cmtyNGNiLzVGdz09IEExazFxaEdOSzk3bytPSDhWNlFxSnVqdGNjTWQ0SmxyeUI1M0Y2aEptUDlI iZ7Z4s0Ts6pLA1odK9Z2b4Va6kRi0R")

    sock.send_line("1 1438950100 MATCH MSAxNDM4OTUwMDAwIDkxZDU2YmExYTgwYThlZDcwMzZmNjRlZDc2MGMxYTZjOTVjZjdkOWZiN2E5NTgwYzY2OWQxZjZlNjMzYWM5MmMgZG9nZWNvaW4vbGl0ZWNvaW4gMTk5LjAwIDAuMDA1IG5rdFZxWmF5cmJnd2IyOFFwYXAxZ2VnbjNqeW16aVlOYnEgbjRlZ1VWb0FCdHdoOUdUOXRMZmZ2Wk5EN2lrQ0RxN3RZTiBBNC95bjhnRXV6R3dIOFY4QUR3M3NvUWdXVWNlVjgwYzRQWEZqOXI1RURjbiBBMWsxcWhHTks5N28rT0g4VjZRcUp1anRjY01kNEpscnlCNTNGNmhKbVA5SCBBeGRwQ0I5UWZyVXUzVFZ2WitzOEw3blZ3ZzRSbWQvbnExbzRnV1JNcXN3MyBBMng2bm1JdnZVQWk0NTA0RnRqTDBCZzJiTEE5RW9BWENPZ0lKWXVyT25YQSBBKzlnTXhrUkJvUEc4M3grdE05V2VENEJva3dGaVE1bklUUkl5MnI5bGR4SyBBeGRwQ0I5UWZyVXUzVFZ2WitzOEw3blZ3ZzRSbWQvbnExbzRnV1JNcXN3MyAwZjRjMDAxNzdiN2NjYTRiOTc1YjQyNjA5YWE5NGZhNmZkZGEyOWRmZTExZmUwMDE1ZWVlNDIyOTZkMTU5NTc3IDBfIDEzMmU4YmVkMWJlZWYxMTVjMjliNTZlMjZjMmYwY2VhNzBjOGFkMTY1ODE1MTViOTFkYzhhMjc5ZDFlOTBlOTcgMF8gMC4wMCAwLjAwIDAuOTk1IDAuMDA0OTc1IHdNVzNua0VmeXJaVXdYQ08zTkNpMHRxb3cxM1NZYit1WGJMRU4zRmdURXRkZGR1eVhwZnhjcjlZbG1oS1k5UmR3Tmd1L3VINTVVNFowMWh0czdQaExRPT0gUFFTbitaZ0FkbGJJbnV1YnA3KzFwdmVIVnlLa0J1V2owSEFYRW1LMkovc2pKeGlBaVBGUm1xUlppdCtBWTh3M0twN2R1NzVWVnM0R2J4OVVTWUxsRUE9PSBxMnlhNXh3UnBWTzFyZDR3V21yWEY2ckhhTk5xMjRXblZPTE96b2tXV2kzb256cVExL294QklPd2xQQ1B1eVRiM2cvTEwvdW9XQjFUVTJjZHJnSUovUT09IENvTGlUOWN1UVlSKytNeUZScysvODVjaG9kaXFST3hLemx3a2J6NGpMdFgzbUN2NVI0V2tlSG0yVGNYajMxSTlmblhUbWtmQm1HVjArVmlrSVYyanJBPT0= MSAxNDM4OTUwMTAwIHNoYWtlX29uX2l0IDgyNTg1ZDE3MWFlYWNiOTE0YzJlZDU5MzNmNjM1NDMwNTMxYjY0MzhlNjFiNGRkNDhjODliOTBhY2ZmNGFmY2IgOTg0TDlTOW5BVzhrTlpvK0ZpV2VVQlp3RnI1Ym11c1pWTXV3dWNpaUEwZ0Voa3NXdk44b3c5T3hFVytUSjZaQjN0L05acVRIS2NzWThZSUVQaWhFbGc9PQ== MSAxNDM4OTUwMTAwIHNoYWtlX29uX2l0IDgyNTg1ZDE3MWFlYWNiOTE0YzJlZDU5MzNmNjM1NDMwNTMxYjY0MzhlNjFiNGRkNDhjODliOTBhY2ZmNGFmY2IgTE5YTVRCbUQ2OW1XT1NNZFpGaDA5M1ZSTHpLYmpjRmRtVHdiaGVqa2U0QUdnRWFKajFXNE1NbExTN0Fvdm1CR0tjN1plV0ZiWU9VTjZVUnB0SHBwQkE9PQ== MC4wMDQ5NzUgQTd6RlJIci9QNXdQY0p0bU8wSkJva3BWc3BFb1VoNDc2MlEwdFNWeEJhR1Igb0xpcVkzeE5WUXkwUm1qa0VhbnUreFRQeXV0anc1ZHQ0NFduQkV0cnJyNjBiS1VtT0VHNGVVOGcxS1FERkV6L2g5WmFHUW1pMmtCMkQzcFkyOWVVV1E9PSBBMng2bm1JdnZVQWk0NTA0RnRqTDBCZzJiTEE5RW9BWENPZ0lKWXVyT25YQSA3b3lrbGcrYXdpcERKQmIvTS8rV3hnMkRBa1pVS2puSFU2bXVENFoxWUdGUjU2ZGtNL3p4VmxzdlFNSUtPNkpYbGw1RlBzNkZZbHRabkNOMHVESlhPUT09IEErOWdNeGtSQm9QRzgzeCt0TTlXZUQ0Qm9rd0ZpUTVuSVRSSXkycjlsZHhL aW24BzQu9Nq4cR98yZiY09mS8NsOu9")


    print(sock.recv_line())
    
    print(sock.recv_line())

    sock.close()
    
from .hybrid_protocol import parse_msg

