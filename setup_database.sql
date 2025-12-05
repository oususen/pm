-- setup_database.sql
-- pm_db データベースのセットアップスクリプト
--
-- 実行方法:
--   mysql -u root -p --default-character-set=utf8mb4 < setup_database.sql

-- 文字セット設定
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- タイムゾーン設定（日本時間）
SET time_zone = '+09:00';

-- データベース作成
CREATE DATABASE IF NOT EXISTS pm_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- pm_dbを使用
USE pm_db;

-- schema.sqlの内容をインポート
SOURCE schema.sql;

-- 確認用：テーブル一覧表示
SHOW TABLES;
