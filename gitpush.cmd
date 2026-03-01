@echo off
echo [GIT PUSH] Universal UDC Zettelkasten v7.2.2-STABLE
echo Current Path: %CD%
echo.

:: Initialize git if not already done
if not exist ".git" (
    echo Initializing Git repository...
    git init
    git remote add origin https://github.com/rausejop/CDU_Zettelkasten
)

:: Ensure we are on the main branch
git branch -M main

:: Add all files
echo Adding files to staging...
git add .

:: Commit changes with version info
set commit_msg="Universal UDC Zettelkasten v7.2.2-STABLE: Perfect Linking, URL Encoding & Deep Sync"
echo Committing changes: %commit_msg%
git commit -m %commit_msg%

:: Push to origin
echo.
echo Pushing to GitHub (https://github.com/rausejop/CDU_Zettelkasten)...
git push -u origin main

echo.
echo [DONE] Universal UDC Zettelkasten uploaded successfully.
pause
