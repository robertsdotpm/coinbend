from unittest import TestCase
from coinbend.user import *

class test_user(TestCase):
    def test_0000001_user_create(self):
        x = User()
        ret = x.create(
        username = "test333",
        password = "Pa4ssw0rrrr",
        email = "assadasdasda@localhost.com",
        public_key = "test"
        )
        if not ret:
            raise Exception("Failed to create new user.")

    def test_0000002_user_load(self):
        x = User("test333")
        assert(x != 0)

    def test_0000003_user_email_exists(self):
        x = User("test333").email_exists("assadasdasda@localhost.com")
        assert(x == 1)


    def test_0000004_user_deactivate(self):
        x = User("test333").deactivate()
        assert(x == 1)

    def test_0000004_user_delete(self):
        x = User("test333").delete()
        assert(x == 1)

        

