"""
Handles authentication of users for the local exchange.
Also includes registration, activation, and deletion.
"""

from .globals import *
from .database import *
from .password_complexity import *
from .username_complexity import *
import datetime

class User():
    def __init__(self, ident=None, db=None):
        self.password_requirements = {
            "length": 10,
            "complexity": [
                "uppercase",
                "lowercase",
                "numeric",
            ]
        }
        
        if db == None:
            self.db = Database()
        else:
            self.db = db
        
        self.loaded = 0
        if ident == None:
            self.ident = None
        else:
            self.ident = str(ident)
            self.load(self.ident)

    #Load user details from DB into class.
    def load(self, ident):
        #Already loaded.
        if ident == self.ident and self.loaded:
            return self.id
        
        """
        Ident can be a number representing ID or the username.
        """
        if ident.isdigit():
            col = "id"
        else:
            col = "username"
        
        ret = 0    
        with Transaction(self.db) as tx:
            sql = "SELECT * FROM `users` WHERE `%s`=?;" % col
            tx.execute(sql, (ident,))
            row = tx.fetchall()[0]
            self.id = row["id"]
            self.email = row["email"]
            self.salt = row["salt"]
            self.password = row["password"]
            self.created_at = row["created_at"]
            self.updated_at = row["updated_at"]
            self.active = row["active"]
            self.email_confirmed = row["email_confirmed"]
            self.main_currency = row["main_currency"]
            self.deduct_trade_fees_from = row["deduct_trade_fees_from"]
            self.public_key = row["public_key"]
            ret = self.id
            self.loaded = 1

        return ret

    #Checks if an email is already associated with an account.
    def email_exists(self, email):
        ret = 0
        with Transaction(self.db) as tx:
            sql = "SELECT * FROM `users` WHERE `email`=?;"
            tx.execute(sql, (email,))
            row = tx.fetchall()[0]
            ret = 1

        return ret
            
    #Creates a new user.
    def create(self, username, password, email, public_key="", email_confirmed=1, active=1):
        global config

        #Check if user already exists.
        id = self.load(username)
        if id:
             return id
             
        #Check if email already exists.
        if self.email_exists(email):
            raise Exception("Email already in use.")
            
        #Check username complexity.
        complexity = UsernameComplexity()
        if not complexity.is_valid(username):
            raise Exception("Username complexity not met.")
        
        #Check password.
        complexity = PasswordComplexity(
            self.password_requirements["complexity"],
            self.password_requirements["length"],
        )
        not_met = complexity.check_complexity(password)
        if not_met != []:
            msg = "Password complexity check failed."
            print(not_met)
            raise Exception(msg)
            
        #Just for a random salt of password_requirements["length"] length.
        #Use garlic salt for more flavour. Requires cooking lvl of 33.
        #http://stackoverflow.com/questions/9619727/how-long-should-a-salt-be-to-make-it-infeasible-to-attempt-dictionary-attacks
        complexity.length = 32
        salt = complexity.generate_password()
        pepper = config["satoshi_identity"]
        password = complexity.hash(password, salt, pepper)
        
        #Todo: Mail activation email
        if not email_confirmed:
            pass
        
        #Insert new user.
        ret = 0
        with Transaction(self.db) as tx:
            created_at = updated_at = datetime.datetime.now()
            sql = "INSERT INTO `users` (`username`, `password`, `salt`, `email`, `public_key`, `created_at`, `updated_at`, `active`, `email_confirmed`) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"
            tx.execute(sql, (username, password, salt, email, public_key, created_at, updated_at, active, email_confirmed))
            ret = self.load(username)

        return ret

    #Deactivates an account without deleting associated data.
    def deactivate(self):
        if not self.loaded:
            raise Exception("This user does not exist.")
            
        ret = 0
        with Transaction(self.db) as tx:
            sql = "UPDATE `users` SET `active`=0 WHERE `id`=?;"
            tx.execute(sql, (self.id,))
            ret = 1

        return ret
        
    def delete(self, deactivate=1):
        """
        This function deletes all the data for a given user
        from the database.
        """
        if not self.loaded:
            raise Exception("This user does not exist.")
        
        #Only these are deleted.
        #The rest are important to keep for accounting purposes.
        hit_list = \
        [
            "trade_orders",
        ]
        
        ret = 0
        with Transaction(self.db) as tx:
            for hit in hit_list:
                sql = "DELETE FROM `%s` WHERE `user_id`=?;" % (hit)
                tx.execute(sql, (self.id,))
            
            #Deactivate.
            if deactivate:    
                deactivated = self.deactivate()
                if not deactivated:
                    raise Exception("Failed to deactive account.")
            ret = 1

        return ret
        
if __name__ == "__main__":
    x = User()
    print(x.create(
    username = "test333",
    password = "Pa4ssw0rrrr",
    email = "assadasdasda@localhost.com",
    public_key = "test"
    ))
    #print(x.email)
    """
    print(x.delete())
    """
