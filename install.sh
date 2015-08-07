#Use this script if setup.py fails.
#apt-get install libportaudio-dev
#apt-get install libportaudio0 libportaudio2 libportaudiocpp0 portaudio19-dev
#apt-get install python3-setuptools
#easy_install3 pip
#Pygame stuff
sudo apt-get install gcc
apt-get install make
sudo apt-get install git
apt-get install libsdl-dev libsdl-image1.2-dev libsdl-mixer1.2-dev libsdl-ttf2.0-dev libsmpeg-dev libportmidi-dev libavformat-dev libswscale-dev libjpeg-dev libfreetype6-dev openssl-devel libssl-dev libbz2-dev


sudo apt-get install python-setuptools python-pip python-dev python3-dev libmysqlclient-dev python-pyaudio python-pygame python-nose bzr cython
sudo pip install scrypt colorama
sudo apt-get install libssl-dev

#https://github.com/petertodd/python-bitcoinlib
cd ~
sudo git clone https://github.com/petertodd/python-bitcoinlib.git
cd python-bitcoinlib
sudo python setup.py install

#http://heritagerobotics.wordpress.com/2012/11/20/compiling-pygame-for-python-3-2-in-xubuntu/
#Plus stuff in x folder Todo:
#https://launchpad.net/oursql/py3k

#git clone git://github.com/cenobites/flask-jsonrpc.git
#and also flask, pyqt, etc
#cherrypy
#https://github.com/Pyha/flup-py3.3
#sudo apt-get instlal  libffi-dev
#pyopenssl
#bottle
#jsonrpc2 https://pypi.python.org/pypi/jsonrpc2#downloads


#git clone https://github.com/python/cpython.git
#git checkout 3.3
#./configure --enable-shared
#sudo python3.3 -m easy_install cx_Freeze
#sudo python3.3 -m easy_install ntplib
#wget https://bitbucket.org/pypa/setuptools/raw/0.7.4/ez_setup.py -O - | sudo python3.3
sudo rm -rf /usr/local/lib/python3.3/dist-packages/setuptools*
sudo rm -rf /usr/local/lib/python3.3/dist-packages/distribute*
sudo rm -rf /usr/local/lib/python3.3/dist-packages/pkg_resources.py*
sudo rm -rf /usr/local/lib/python3.3/site-packages/setuptools*
sudo rm -rf /usr/local/lib/python3.3/site-packages/distribute*
sudo rm -rf /usr/local/lib/python3.3/site-packages/pkg_resources.py*
    ^ Script above is buggy ... use this:
    https://pypi.python.org/pypi/setuptools#downloads
    18.1
    cd to zip
    run setup.py install

python 3.3 -m easy_install twisted


https://pypi.python.org/packages/source/n/netifaces/netifaces-0.10.4.tar.gz#md5=36da76e2cfadd24cc7510c2c0012eb1e
tar xvzf netifaces-0.10.4.tar.gz
cd netifaces-0.10.4
sudo python3.3 setup.py install

#TODO: Change references to pip* to pip3.3
wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py
sudo python3.3 get-pip.py

#Not needed:
#sudo apt-get install gfortran libopenblas-dev liblapack-dev
#rm -rf /usr/lib/python3/dist-packages/numpy
#sudo pip3.3 install -U numpy
#sudo pip3.3 install scipy

#Pycrypto
sudo rm -rf /usr/lib/python3/dist-packages/Crypto
sudo rm -rf /usr/lib/python3/dist-packages/pycrypto*
sudo rm -rf /usr/local/lib/python3.3/Crypto
sudo rm -rf /usr/local/lib/python3.3/pycrypto*
wget https://pypi.python.org/packages/source/p/pycrypto/pycrypto-2.4.1.tar.gz#md5=c2a1404a848797fb0806f3e11c29ef15
tar -xvzf pycrypto-2.4.1.tar.gz
cd pycrypto-2.4*
sudo python3.3 setup.py build
sudo python3.3 setup.py install


#https://github.com/warner/python-ecdsa
#python ecsda

pynacl

https://pypi.python.org/pypi/service_identity

https://pypi.python.org/pypi/beautifulsoup4/4.3.2
