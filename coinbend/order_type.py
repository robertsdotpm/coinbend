
import copy

class OrderType():
    def __init__(self, order_hash, version, ntp, trade, routes, green_address, address, ecdsa_1, ecdsa_2, sig_1, sig_2, nonce):
        self.order_hash = order_hash
        self.version = version
        self.ntp = ntp
        self.trade = trade
        self.routes = routes
        self.green_address = green_address
        self.address = address
        self.ecdsa_1 = ecdsa_1
        self.ecdsa_2 = ecdsa_2
        self.sig_1 = sig_1
        self.sig_2 = sig_2
        self.nonce = nonce

    def copy(self):
        return OrderType(self.order_hash, self.version, self.ntp, self.trade.copy(), self.routes, self.green_address, self.address, self.ecdsa_1, self.ecdsa_2, self.sig_1, self.sig_2, self.nonce)

if __name__ == "__main__":
    pass

