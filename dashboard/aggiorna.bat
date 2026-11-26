@echo off
rem Aggiorna la dashboard del Conto Unificato dai conti MetaTrader 5
cd /d "%~dp0"
py aggiorna_da_mt5.py >> aggiorna.log 2>&1
