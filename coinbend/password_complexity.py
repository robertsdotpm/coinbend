"""
This module is used to ensure that a password meet
a certain level of complexity such as length and character
set. It can be used to generate conforming passwords to
an arbitrary complexity, check that a password conforms,
create hashes, and see if a password is vulnerable to a
dictionary attack among other things.
"""

import random
import re
import binascii

#print(x.hash("password", "a", str(config["satoshi_identity"])))
#print(x.hash("password", "b", str(config["satoshi_identity"])))

#Password complexity check.
class PasswordComplexity():
    def __init__(self, requirements=["lowercase"], length=1):
        self.valid_requirements = [
            "anything",
            "uppercase",
            "lowercase",
            "whitespace",
            "numeric",
            "minus",
            "underscore",
            "special",
            "custom",
        ]
        self.requirements = requirements 
        self.length = length

        #Check requirements.
        requirement_found = 0
        requirements = list(set(requirements)) #Remove duplicates.
        for requirement in requirements:
            #Valid requirement.
            if requirement not in self.requirements:
                raise Exception("Invalid requirement.")
            requirement_found = 1

        if not requirement_found:
            raise Exception("This class expects complexity requirements.")

        #Valid string length.
        if len(self.requirements) > length:
            msg = "Requirements cannot be met with the specified string length."
            msg += " Length needs to be at least " + str(len(self.requirements)) + " long."
            raise Exception(msg)

        #Valid charsets.
        self.charsets = {
            "uppercase": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "lowercase": "abcdefghijklmnopqrstuvwxyz",
            "whitespace": "\t\r\n ",
            "numeric": "0123456789",
            "minus": "-",
            "underscore": "_",
            "special": "~!@#$%^&*()+[{]}\\|;:'\",<.>/?",
            "custom": ""
        }
        anything = ""
        for charset in self.charsets:
            anything += charset
        self.charsets["anything"] = anything

        #Dictionary attack wordlists.
        self.wordlists = [
            "/usr/share/dict/words",
            "/usr/share/dict/british-english",
            "/usr/share/dict/american-english"
        ]

    def check_complexity(self, password):
        not_met = []
        if self.requirements[0] == "anything":
            return not_met
        for requirement in self.requirements:
            found = 0
            for ch in password:
                for x in self.charsets[requirement]:
                    if ch == x:
                        found = 1
            if not found:
                msg = "At least one " + requirement + " character"
                msg += " was not found in password."
                not_met.append(msg)

        #Check length requirements.
        if len(password) < self.length:
            msg = "Password was not at least " + str(self.length)
            msg += " characters long."
            not_met.append(msg)

        #Do dictionary attack.
        if len(self.requirements) == 2:
            if "uppercase" in self.requirements and "lowercase" in self.requirements:
                if self.dictionary_attack(password):
                    not_met.append("Password is a dictionary word!")

        return not_met

    def is_valid(self, password):
        if not len(self.check_complexity(password)):
            return 1
        else:
            return 0

    def generate_password(self):
        password = ""
        requirements_buffer = self.requirements[:]
        for i in range(0, self.length):
            #Reset buffer when empty.
            requirements_buffer_len = len(requirements_buffer)
            if not requirements_buffer_len:
                requirements_buffer = self.requirements[:]
                requirements_buffer_len = len(requirements_buffer)

            #Select random charset.
            requirement = requirements_buffer[random.randrange(0, requirements_buffer_len)]
            charset = self.charsets[requirement]
            charset_len = len(charset)

            #Select random character from charset.
            password += charset[random.randrange(0, charset_len)]
            requirements_buffer.remove(requirement)

        return password

    def dictionary_attack(self, password, flashy=0):
        password = password.lower()
        for wordlist in self.wordlists:
            try:
                with open(wordlist) as f:
                    for word in f:
                        word = word.strip()
                        if flashy:
                            print(word)
                        if password == word:
                            if flashy:
                                print("> Password found.")
                            return 1
            except:
                continue
        if flashy:
            print("> Password not found.")
        return 0

    def human_error(self, not_met):
        if not_met == []:
            print("Success. Password meets complexity requirements.")
        else:
            print("Failure. The following errors were found with your password:")
            for requirement in not_met:
                print("- " + requirement)

    def hash(self, password, salt, pepper):
        """
        Uses Scrypt to compute the hash. Every user has an individual
        salt. Salt ensures that users with the same password have
        a different hash otherwise cracking one hash could potentially
        reveal passwords for other users. To further strengthen the
        hash a special "pepper" value is concantenated with the salt.
        The pepper ensures that a database compromise won't allow
        hashes to be cracked.
        
        (Scrypt parameters taken from recommendations made in
        http://www.tarsnap.com/scrypt/scrypt-slides.pdf)
        """

        #Todo: code this function.
        return ""
        

if __name__ == "__main__":
    #from .parse_config import *
    #x = PasswordComplexity(["lowercase", "uppercase"], 4)
    #p = x.generate_password()
    #print(x.check_complexity(p))
    #x.dictionary_attack("dog", 1)
    pass
