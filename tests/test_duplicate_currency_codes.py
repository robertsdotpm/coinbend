from unittest import TestCase

from coinbend.cryptocurrencies import *
from coinbend.fiatcurrencies import *

class test_duplicate_currency_codes(TestCase):
    def test(self):
        cryptocurrencies_len = len(cryptocurrencies)
        fiatcurrencies_len = len(fiatcurrencies)
        duplicates = [] #{"set": duplicate, "set": duplicate}    
    
        #Duplicate codes in cryptocurrencies:
        i = 0
        j = 0
        for cryptocurrency in cryptocurrencies:
            for fiatcurrency in fiatcurrencies:
                if fiatcurrency == cryptocurrency:
                    duplicate = {
                    "cryptocurrencies": cryptocurrency,
                    "fiatcurrency": fiatcurrency
                    }
                    duplicates.append(duplicate)
                j += 1
            i += 1
        if len(duplicates):
            print("Test failed.")
            print("Duplicate currency codes found.")
            print("All currency codes need to be unique.")
            assert False

