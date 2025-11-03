@echo off
title FGD Fusion Stack Pro (v4)
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Launching GUI...
python gui_main_pro.py
