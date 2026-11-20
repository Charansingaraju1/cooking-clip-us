@echo off
title Deploy Cooking Clip US to Hugging Face Spaces
cd /d "%~dp0"

echo ========================================================
echo   Deploy Cooking Clip US to Hugging Face Spaces
echo ========================================================
echo.
echo 1. Make sure you created a Docker Space on Hugging Face:
echo    https://huggingface.co/new-space  (Select 'Docker')
echo.
set /p SPACE_URL="Enter your Space Git URL (e.g. https://huggingface.co/spaces/username/myspace): "

if "%SPACE_URL%"=="" (
    echo [!] No URL provided. Exiting.
    pause
    exit /b
)

echo [*] Initializing git repository...
git init
git remote remove origin 2>nul
git remote add origin %SPACE_URL%
git branch -M main
git add .
git commit -m "Deploy autonomous clipping engine to Hugging Face Spaces"
echo.
echo [*] Pushing to Hugging Face...
git push -u origin main --force
echo.
echo ========================================================
echo   DONE! Check your Space build logs on Hugging Face!
echo ========================================================
pause
