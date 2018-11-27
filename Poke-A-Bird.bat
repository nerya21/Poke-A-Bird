REM supports poke-a-bird_prerequisites_0.2 and above
@echo off

setlocal
PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python37-32\;%LOCALAPPDATA%\Programs\Python\Python37-32\Scripts
python.exe .\Poke-A-Bird.py
endlocal