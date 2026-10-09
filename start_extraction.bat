@echo off
title Brightspace Transcriber - MOT Week 2 ^& KOM
cd /d "%~dp0"
echo ======================================================================
echo Starting Brightspace Downloader and GPU Transcriber...
echo A browser window will open. If prompted, please log in with your RUG
echo credentials and approve MFA.
echo ======================================================================
call .venv\Scripts\python.exe run_full_extraction.py
pause
