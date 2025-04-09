@echo off
cd /d "C:\Users\richa\Desktop\Weeding project"

echo Initializing Git...
git init

echo Adding files...
git add .

set /p msg="Enter commit message: "
git commit -m "%msg%"

echo Adding remote (if not already added)...
git remote add origin https://github.com/SwastikKaushal1/PartypixAi.git 2>nul

echo Setting branch to main...
git branch -M main

echo Pulling from remote to avoid conflicts...
git pull origin main --allow-unrelated-histories

echo Pushing to GitHub...
git push -u origin main

pause
