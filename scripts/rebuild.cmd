@echo off
REM Pyrite rebuild - repo root entry point for Windows
REM Works from anywhere in the repo
python "%~dp0..\tools\rebuild.py" %*

