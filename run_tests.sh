./sys_path_add.sh
cd tests
sudo python3.3 -m "nose" -v test_currency_type.py
sudo python3.3 -m "nose" -v test_duplicate_currency_codes.py
sudo python3.3 -m "nose" -v test_database.py
sudo python3.3 -m "nose" -v test_user.py
sudo python3.3 -m "nose" -v test_upnp.py
sudo python3.3 -m "nose" -v test_sock.py


#sudo python3.3 test_trade_engine.py
cd ..
./sys_path_remove.sh
