@echo off
title Mail Service - Dev
pushd %~dp0

echo [0/1] Kill process cu tren port 8701 (neu co)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8701 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo [1/1] Khoi dong Mail Service (port 8701)...
start "Mail Service (8701)" python main.py
