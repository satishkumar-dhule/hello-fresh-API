virtualenv vnev.hello-fresh
source vnev.hello-fresh/bin/activate
pip install -r requirements.txt
./manage.py compose up -d
