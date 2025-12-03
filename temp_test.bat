@echo off
cd /d %~dp0
mysql -u root -p < setup_database.sql