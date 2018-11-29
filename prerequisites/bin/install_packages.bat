@echo off

setlocal
PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python37-32\;%LOCALAPPDATA%\Programs\Python\Python37-32\Scripts
pip3 -q --disable-pip-version-check install %1\Pillow-5.3.0-cp37-cp37m-win32.whl
pip3 -q --disable-pip-version-check install %1\python-vlc-3.0.4106.tar.gz
pip3 -q --disable-pip-version-check install %1\pyttk-0.3.2.tar.gz
pip3 -q --disable-pip-version-check install %1\Pmw-2.0.1.tar.gz
endlocal
