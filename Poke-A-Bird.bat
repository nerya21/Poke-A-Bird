@echo off

setlocal
set PATH=%LOCALAPPDATA%\Programs\Python\Python37-32\;%LOCALAPPDATA%\Programs\Python\Python37-32\Scripts
set PYTHONHOME=
set PYTHONPATH=
python.exe .\Poke-A-Bird.py
endlocal