@echo off
title 100 Popular Cars - Video Generation Batch
cd /d "%~dp0"
echo =================================================================
echo  100 POPULAR CARS IN INDIA - BATCH GENERATOR
echo =================================================================
echo  Default: Generates next 10 pending cars on Google Flow
echo  Press Ctrl+C anytime to pause gracefully.
echo =================================================================
python run_100_cars_batch.py --limit 10
pause
