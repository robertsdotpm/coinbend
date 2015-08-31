echo ">>> Use root for everything."
sudo su

echo ">>> Update DNS resolution."
echo "dns-nameservers 8.8.8.8 8.8.4.4" >> /etc/network/interfaces
ifdown eth0 && ifup eth0

echo ">>> Make crap directory to store downloads in."
cd ~
mkdir downloads
cd downloads

echo ">>> Update package list."
apt-get update

echo ">>> Install basic dependencies."
apt-get install -y make
apt-get install -y git
apt-get install -y libsdl-dev libsdl-image1.2-dev libsdl-mixer1.2-dev libsdl-ttf2.0-dev libsmpeg-dev libportmidi-dev libavformat-dev libswscale-dev libjpeg-dev libfreetype6-dev libssl-dev libbz2-dev openssl mysql-client libmysqlclient-dev unzip safe-rm g++ build-essential libsqlite3-dev sqlite3 bzip2 libbz2-dev zlib1g-dev libncursesw5-dev libgdbm-dev libc6-dev tk-dev libffi-dev lzma lzma-dev screen sed pcregrep

echo ">>> Install XZ."
wget http://tukaani.org/xz/xz-5.2.1.tar.gz
tar -xvzf xz-5.2.1.tar.gz
cd xz-5.2.1
./configure
make
make install
cd ~/downloads

echo ">>> Install and compile Python 3.3."
apt-get build-dep -y python
echo ">>> (note: this repo is huge so this might take a while but the terminal isn't hanging.)"
git clone https://github.com/python/cpython.git
cd cpython
git checkout 3.3
./configure --enable-shared --prefix=/usr
echo "/usr/local/lib" >> /etc/ld.so.conf
ldconfig
make
make install
cd ~/downloads

echo ">>> Install setup tools."
wget https://pypi.python.org/packages/source/s/setuptools/setuptools-18.1.tar.gz
tar -xvzf "setuptools-18.1.tar.gz"
cd setuptools-18.1
python3.3 setup.py install
cd ~/downloads

echo ">>> Install netifaces for Python."
wget https://pypi.python.org/packages/source/n/netifaces/netifaces-0.10.4.tar.gz#md5=36da76e2cfadd24cc7510c2c0012eb1e
tar -xvzf "netifaces-0.10.4.tar.gz"
cd netifaces-0.10.4
python3.3 setup.py install
cd ~/downloads

echo ">>> Install ntplib for Python."
wget https://pypi.python.org/packages/source/n/ntplib/ntplib-0.3.3.tar.gz
tar -xvzf "ntplib-0.3.3.tar.gz"
cd ntplib-0.3.3
python3.3 setup.py install
cd ~/downloads

echo ">>> Install Bitcoinlib for Python."
git clone https://github.com/robertsdotpm/python-bitcoinlib.git
cd python-bitcoinlib
python3.3 setup.py install
cd ~/downloads

echo ">>> Install numpy for Python."
wget https://pypi.python.org/packages/source/n/numpy/numpy-1.9.2.tar.gz#md5=a1ed53432dbcd256398898d35bc8e645
tar -xvzf "numpy-1.9.2.tar.gz"
cd numpy-1.9.2
python3.3 setup.py install
cd ~/downloads

echo ">>> Install ECDSA for Python."
git clone https://github.com/warner/python-ecdsa.git
cd python-ecdsa
python3.3 setup.py install
cd ~/downloads

echo ">>> Install oursql for Python."
wget https://launchpad.net/oursql/py3k/py3k-0.9.4/+download/oursql-0.9.4.tar.gz
tar -xvzf oursql-0.9.4.tar.gz
cd oursql-0.9.4
python3.3 setup.py install
cd ~/downloads

echo ">>> Install flask JSON RPC for Python."
git clone git://github.com/cenobites/flask-jsonrpc.git
cd flask-jsonrpc
python3.3 setup.py install
cd ~/downloads

echo ">>> Install flup for Python."
git clone https://github.com/Pyha/flup-py3.3.git
cd flup-py3.3
python3.3 setup.py install
cd ~/downloads

echo ">>> Install cherrypy for Python."
wget https://pypi.python.org/packages/source/C/CherryPy/CherryPy-3.8.0.tar.gz#md5=542b96b2cd825e8120e8cd822bc18f4b
tar -xvzf "CherryPy-3.8.0.tar.gz"
cd "CherryPy-3.8.0"
python3.3 setup.py install
cd ~/downloads

echo ">>> Install pycrypto for Python."
wget https://pypi.python.org/packages/source/p/pycrypto/pycrypto-2.6.1.tar.gz
cd ~/pycrypto-2.6.1
python3.3 setup.py install
cd ~/downloads

echo ">>> Install JSONRPC2 for Python."
wget https://pypi.python.org/packages/source/j/jsonrpc2/jsonrpc2-0.4.1.tar.gz#md5=1fce3d89554325e0a3a80f69b7e806c8
tar -xvzf "jsonrpc2-0.4.1.tar.gz"
cd jsonrpc2-0.4.1
python3.3 setup.py install
cd ~/downloads

echo ">>> Install Twisted for Python."
wget https://pypi.python.org/packages/source/T/Twisted/Twisted-15.3.0.tar.bz2#md5=b58e83da2f00b3352afad74d0c5c4599
tar -jxf "Twisted-15.3.0.tar.bz2"
cd "Twisted-15.3.0"
python3.3 setup.py install
cd ~/downloads

echo ">>> Install BS4 for Python."
wget https://pypi.python.org/packages/source/b/beautifulsoup4/beautifulsoup4-4.3.2.tar.gz#md5=b8d157a204d56512a4cc196e53e7d8ee
tar -xvzf "beautifulsoup4-4.3.2.tar.gz"
cd beautifulsoup4-4.3.2
python3.3 setup.py install
cd ~/downloads

echo ">>> Install pyopenssl for Python."
wget https://pypi.python.org/packages/source/p/pyOpenSSL/pyOpenSSL-0.15.1.tar.gz#md5=f447644afcbd5f0a1f47350fec63a4c6
tar -xvzf "pyOpenSSL-0.15.1.tar.gz"
cd "pyOpenSSL-0.15.1"
python3.3 setup.py install
cd ~/downloads

echo ">>> Install service identify for Python."
wget https://pypi.python.org/packages/source/s/service_identity/service_identity-14.0.0.tar.gz#md5=cea0b0156d73b025ecef660fb51f0d9a
tar -xvzf "service_identity-14.0.0.tar.gz"
cd "service_identity-14.0.0"
python3.3 setup.py install
cd ~/downloads

echo ">>> Install colorama for Python."
wget https://pypi.python.org/packages/source/c/colorama/colorama-0.3.3.tar.gz
tar -xvzf "colorama-0.3.3.tar.gz"
cd colorama-0.3.3
python3.3 setup.py install
cd ~/downloads

echo ">>> Install config files for Coinbend."
cd ~/downloads
wget www.coinbend.com/linux.zip
unzip linux.zip
cd linux
mkdir /home/vagrant/.Coinbend
mv install/* /home/vagrant/.Coinbend
sed -Ei 's/confirmations["]: [0-9]+/confirmations": 1/g' /home/vagrant/.Coinbend/config.json
rm -rf /home/vagrant/.Coinbend/www
ln -s /vagrant/coinbend/install/www /home/vagrant/.Coinbend/www
chown -R vagrant /home/vagrant/.Coinbend 
cd ~/downloads

echo ">>> Patch coin config files."
mkdir /home/vagrant/.dogecoin
#mkdir /home/vagrant/.bitcoin
mkdir /home/vagrant/.litecoin
cd /home/vagrant/.dogecoin #Testnet dogecoin is a bit hard to bootstrap.
echo "testnet=1" >> dogecoin.conf
echo "maxconnections=100" >> dogecoin.conf
echo "addnode=178.32.61.149" >> dogecoin.conf
echo "addnode=144.76.203.73" >> dogecoin.conf
echo "addnode=66.228.37.215" >> dogecoin.conf
echo "addnode=198.58.102.18" >> dogecoin.conf
echo "addnode=188.166.53.132" >> dogecoin.conf
echo "addnode=176.9.113.75" >> dogecoin.conf
echo "addnode=104.237.131.138" >> dogecoin.conf
echo "addnode=71.58.72.67" >> dogecoin.conf
cd /home/vagrant/.litecoin
echo "testnet=1" >> litecoin.conf
echo "addnode=176.9.147.116" >> litecoin.conf
echo "addnode=144.76.29.213" >> litecoin.conf
#cd /home/vagrant/.bitcoin
#echo "testnet=1" >> bitcoin.conf
#echo "addnode=176.9.147.116" >> bitcoin.conf
#echo "addnode=144.76.29.213" >> bitcoin.conf

echo ">>> Install Dogecoin."
cd /home/vagrant
mkdir coins
cd coins
wget https://github.com/dogecoin/dogecoin/releases/download/v1.10-beta-1/dogecoin-1.10.0-linux32.tar.gz
tar -xvzf dogecoin-1.10.0-linux32.tar.gz
mv dogecoin-1.10.0 dogecoin
chmod +x dogecoin/bin/dogecoind
cd /home/vagrant/coins

echo ">>> Install Litecoin."
wget https://download.litecoin.org/litecoin-0.10.2.2/linux/litecoin-0.10.2.2-linux32.tar.gz
tar -xvzf "litecoin-0.10.2.2-linux32.tar.gz"
mv litecoin-0.10.2.2 litecoin
chmod +x litecoin/bin/litecoind
cd /home/vagrant/coins

#echo ">>> Install Bitcoin."
#wget https://bitcoin.org/bin/bitcoin-core-0.11.0/bitcoin-0.11.0-linux32.tar.gz
#tar -xvzf "bitcoin-0.11.0-linux32.tar.gz"
#mv bitcoin-0.11.0 bitcoin
#chmod +x bitcoin/bin/bitcoind

echo ">>> Creating start coin script."
cd /home/vagrant
echo "/home/vagrant/coins/dogecoin/bin/dogecoind &" >> start_coins.sh
echo "/home/vagrant/coins/litecoin/bin/litecoind &" >> start_coins.sh
#echo "/home/vagrant/coins/bitcoin/bin/bitcoind &" >> start_coins.sh
chmod +x start_coins.sh
echo "./start_coins.sh" >> .bash_login
chown -R vagrant /home/vagrant
cd ~/downloads

echo ">>> Install cxfreeze for Python."
wget https://pypi.python.org/packages/source/c/cx_Freeze/cx_Freeze-4.3.3.tar.gz
tar -xvzf "cx_Freeze-4.3.3.tar.gz"
python3.3 setup.py install

echo ">>> Unzipping Python egg modules."
cd /usr/lib/python3.3/site-packages

#Characteristic.
mkdir characteristic-14.3.0-py3.3
cp -R characteristic-14.3.0-py3.3.egg characteristic-14.3.0-py3.3
cd characteristic-14.3.0-py3.3
unzip characteristic-14.3.0-py3.3.egg
rm -rf characteristic-14.3.0-py3.3.egg
cd ..
rm -rf characteristic-14.3.0-py3.3.egg
mv characteristic-14.3.0-py3.3 characteristic-14.3.0-py3.3.egg

#Colorama.
mkdir colorama-0.3.3-py3.3
cp -R colorama-0.3.3-py3.3.egg colorama-0.3.3-py3.3
cd colorama-0.3.3-py3.3
unzip colorama-0.3.3-py3.3.egg
rm -rf colorama-0.3.3-py3.3.egg
cd ..
rm -rf colorama-0.3.3-py3.3.egg
mv colorama-0.3.3-py3.3 colorama-0.3.3-py3.3.egg

#Enum34.
mkdir enum34-1.0.4-py3.3
cp -R enum34-1.0.4-py3.3.egg enum34-1.0.4-py3.3
cd enum34-1.0.4-py3.3
unzip enum34-1.0.4-py3.3.egg
rm -rf enum34-1.0.4-py3.3.egg
cd ..
rm -rf enum34-1.0.4-py3.3.egg
mv enum34-1.0.4-py3.3 enum34-1.0.4-py3.3.egg

#Flup.
mkdir flup-1.0-py3.3
cp -R flup-1.0-py3.3.egg flup-1.0-py3.3
cd flup-1.0-py3.3
unzip flup-1.0-py3.3.egg
rm -rf flup-1.0-py3.3.egg
cd ..
rm -rf flup-1.0-py3.3.egg
mv flup-1.0-py3.3 flup-1.0-py3.3.egg

#IDNA.
mkdir idna-2.0-py3.3
cp -R idna-2.0-py3.3.egg idna-2.0-py3.3
cd idna-2.0-py3.3
unzip idna-2.0-py3.3.egg
rm -rf idna-2.0-py3.3.egg
cd ..
rm -rf idna-2.0-py3.3.egg
mv idna-2.0-py3.3 idna-2.0-py3.3.egg

#JSON RPC2.
mkdir jsonrpc2-0.4.1-py3.3
cp -R jsonrpc2-0.4.1-py3.3.egg jsonrpc2-0.4.1-py3.3
cd jsonrpc2-0.4.1-py3.3
unzip jsonrpc2-0.4.1-py3.3.egg
rm -rf jsonrpc2-0.4.1-py3.3.egg
cd ..
rm -rf jsonrpc2-0.4.1-py3.3.egg
mv jsonrpc2-0.4.1-py3.3 jsonrpc2-0.4.1-py3.3.egg

#Netifaces.
mkdir netifaces-0.10.4-py3.3-linux-i686
cp -R netifaces-0.10.4-py3.3-linux-i686.egg netifaces-0.10.4-py3.3-linux-i686
cd netifaces-0.10.4-py3.3-linux-i686
unzip netifaces-0.10.4-py3.3-linux-i686.egg
rm -rf netifaces-0.10.4-py3.3-linux-i686.egg
cd ..
rm -rf netifaces-0.10.4-py3.3-linux-i686.egg
mv netifaces-0.10.4-py3.3-linux-i686 netifaces-0.10.4-py3.3-linux-i686.egg

#Pyasn 1...0.1.8
mkdir pyasn1-0.1.8-py3.3
cp -R pyasn1-0.1.8-py3.3.egg pyasn1-0.1.8-py3.3
cd pyasn1-0.1.8-py3.3
unzip pyasn1-0.1.8-py3.3.egg
rm -rf pyasn1-0.1.8-py3.3.egg
cd ..
rm -rf pyasn1-0.1.8-py3.3.egg
mv pyasn1-0.1.8-py3.3 pyasn1-0.1.8-py3.3.egg

#Pyasn1_modules ...
mkdir pyasn1_modules-0.0.7-py3.3
cp -R pyasn1_modules-0.0.7-py3.3.egg pyasn1_modules-0.0.7-py3.3
cd pyasn1_modules-0.0.7-py3.3
unzip pyasn1_modules-0.0.7-py3.3.egg
rm -rf pyasn1_modules-0.0.7-py3.3.egg
cd ..
rm -rf pyasn1_modules-0.0.7-py3.3.egg
mv pyasn1_modules-0.0.7-py3.3 pyasn1_modules-0.0.7-py3.3.egg

#Pycparser.
mkdir pycparser-2.14-py3.3
cp -R pycparser-2.14-py3.3.egg pycparser-2.14-py3.3
cd pycparser-2.14-py3.3
unzip pycparser-2.14-py3.3.egg
rm -rf pycparser-2.14-py3.3.egg
cd ..
rm -rf pycparser-2.14-py3.3.egg
mv pycparser-2.14-py3.3 pycparser-2.14-py3.3.egg

#Pyopenssl.
mkdir pyOpenSSL-0.15.1-py3.3
cp -R pyOpenSSL-0.15.1-py3.3.egg pyOpenSSL-0.15.1-py3.3
cd pyOpenSSL-0.15.1-py3.3
unzip pyOpenSSL-0.15.1-py3.3.egg
rm -rf pyOpenSSL-0.15.1-py3.3.egg
cd ..
rm -rf pyOpenSSL-0.15.1-py3.3.egg
mv pyOpenSSL-0.15.1-py3.3 pyOpenSSL-0.15.1-py3.3.egg

#Service identity.
mkdir service_identity-14.0.0-py3.3
cp -R service_identity-14.0.0-py3.3.egg service_identity-14.0.0-py3.3
cd service_identity-14.0.0-py3.3
unzip service_identity-14.0.0-py3.3.egg
rm -rf service_identity-14.0.0-py3.3.egg
cd ..
rm -rf service_identity-14.0.0-py3.3.egg
mv service_identity-14.0.0-py3.3 service_identity-14.0.0-py3.3.egg

#Setuptools.
mkdir setuptools-18.1-py3.3
cp -R setuptools-18.1-py3.3.egg setuptools-18.1-py3.3
cd setuptools-18.1-py3.3
unzip setuptools-18.1-py3.3.egg
rm -rf setuptools-18.1-py3.3.egg
cd ..
rm -rf setuptools-18.1-py3.3.egg
mv setuptools-18.1-py3.3 setuptools-18.1-py3.3.egg

#Setup virtual interfaces on login.
cd /home/vagrant
wget www.coinbend.com/setup_virtual_interfaces.py
chmod +x setup_virtual_interfaces.py
echo "sudo python3.3 /home/vagrant/setup_virtual_interfaces.py" >> .bash_login
echo "sudo ifconfig lo up" >> .bash_login
echo "sudo ip addr flush dev eth1" >> .bash_login
echo "sudo ifdown eth1 && sudo ifup -v eth1" >> .bash_login
chown -R vagrant /home/vagrant
