virtualenv vnev.hello-fresh
source vnev.hello-fresh/bin/activate
pip install -r requirements.txt >install.log 2>install.error
./manage.py compose up -d
