@echo off
cd /d "C:\Users\richa\Desktop\Weeding project"

echo Initializing Git...
git init

echo Adding files...
git add .

echo Committing...
git commit -m "Initial commit"

echo Adding remote...
git remote add origin https://github.com/SwastikKaushal1/PartypixAi.git

echo Setting branch to main...
git branch -M main

echo Pushing to GitHub...
git push -u origin main

pause
