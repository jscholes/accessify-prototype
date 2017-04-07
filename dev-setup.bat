@echo off

pip install -r requirements.txt --upgrade
pip install --no-index --find-links=wheelhouse tolk --upgrade
pip install --no-index --find-links=http://wxpython.org/Phoenix/snapshot-builds/ --trusted-host wxpython.org wxPython_Phoenix --upgrade
python setup.py develop
