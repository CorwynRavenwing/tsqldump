-- Create Test Database
CREATE DATABASE TestDumpDB;
GO

USE TestDumpDB;
GO

-- 1. Table with international multi-byte strings
CREATE TABLE UnicodeTest (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    LanguageName NVARCHAR(50) NOT NULL,
    SampleText NVARCHAR(250) NOT NULL,
    EmojiSample NVARCHAR(50) NULL
);

INSERT INTO UnicodeTest (LanguageName, SampleText, EmojiSample) VALUES
(N'Japanese', N'こんにちは世界 - Welcome to SQL Server', N'🚀🎉'),
(N'Russian', N'Привет, мир! Тестирование кодировки.', N'🇷🇺'),
(N'Arabic', N'مرحبا بالعالم - اختبار البرامج', N'✨'),
(N'Chinese (Traditional)', N'繁體中文測試 - 𪚥𪚥', N'🐉'),
(N'Hebrew', N'שלום עולם - בדיקת טקסט', N'✡️'),
(N'Mixed Accents', N'Café, Niños, Åse, François', N'☕');

-- 2. Table with foreign keys and datatypes to verify schema dumping
CREATE TABLE Categories (
    CategoryID INT PRIMARY KEY,
    CategoryName NVARCHAR(50) NOT NULL
);

CREATE TABLE Products (
    ProductID INT PRIMARY KEY,
    ProductName NVARCHAR(100) NOT NULL,
    Price DECIMAL(10, 2) NOT NULL,
    CategoryID INT FOREIGN KEY REFERENCES Categories(CategoryID),
    CreatedAt DATETIME2 DEFAULT GETDATE()
);

INSERT INTO Categories (CategoryID, CategoryName) VALUES (1, N'Electronics'), (2, N'Books');
INSERT INTO Products (ProductID, ProductName, Price, CategoryID) VALUES
(101, N'Laptop - 💻', 999.99, 1),
(102, N'Unicode Manual - 📚', 29.95, 2);
GO

