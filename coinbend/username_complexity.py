"""
Ensures that usernames chosen are sufficiently complex and
not made of default usernames that can easily be guessed.
"""

import re
from .cryptocurrencies import *
from .fiatcurrencies import *

class UsernameComplexity():
    def __init__(self):
        self.invalid_users = [
            "user",
            "smtp",
            "email",
            "proxy",
            "default",
            "ftp",
            "apache",
            "www-data",
            "coinbend",
            "staff",
            "support",
            "contact",
            "ssh",
            "root",
            "admin",
            "administrator",
            "yoshimitsu",
            "god",
            "naruto",
            "mysql",
            "system",
            "guest",
            "operator",
            "super",
            "ssh",
            "test",
            "qa",
            "testing"
            "satoshi",
            "phpmyadmin",
            "pma",
            "btc",
            "ltc",
            "bitcoin",
            "litecoin",
            "",
            " ",
            "\r\n",
            "\n"
        ]
        self.invalid_users += get_cryptocurrencies()
        self.invalid_users += get_fiatcurrencies()

    #Checks if a username is valid.
    def is_valid(self, username):
        if type(username) != str:
            return 0
        
        #All numeric has special status of indicating ID.    
        if username.isdigit():
            return 0
        
        #Alpha numeric only.    
        username = username.lower()
        if re.match("^[a-zA-Z0-9_]+$", username) == None:
            return 0
        
        for invalid_user in self.invalid_users:
            if username == invalid_user:
                return 0
        return 1
