-- tsqldump/test/init.sql

-- Create Test Database if it doesn't exist
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'TestDumpDB')
BEGIN
    CREATE DATABASE TestDumpDB;
END
GO

USE TestDumpDB;
GO

-- STANZA 1: Unicode & Foreign Language Text

IF OBJECT_ID(N'dbo.UnicodeTest', N'U') IS NULL
BEGIN
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
END
GO

-- STANZA 2: Foreign Keys & Relations
IF OBJECT_ID(N'dbo.Categories', N'U') IS NULL
BEGIN
    CREATE TABLE Categories (
        CategoryID INT PRIMARY KEY,
        CategoryName NVARCHAR(50) NOT NULL
    );
    INSERT INTO Categories (CategoryID, CategoryName) VALUES (1, N'Electronics'), (2, N'Books');
END
GO

IF OBJECT_ID(N'dbo.Products', N'U') IS NULL
BEGIN
    CREATE TABLE Products (
        ProductID INT PRIMARY KEY,
        ProductName NVARCHAR(100) NOT NULL,
        Price DECIMAL(10, 2) NOT NULL,
        CategoryID INT FOREIGN KEY REFERENCES Categories(CategoryID),
        CreatedAt DATETIME2 DEFAULT GETDATE()
    );
    INSERT INTO Products (ProductID, ProductName, Price, CategoryID) VALUES
    (101, N'Laptop - 💻', 999.99, 1),
    (102, N'Unicode Manual - 📚', 29.95, 2);
END
GO

-- STANZA 3: Comprehensive SQL Data Types
IF OBJECT_ID(N'dbo.AllTypesTest', N'U') IS NULL
BEGIN
    CREATE TABLE AllTypesTest (
        ID INT IDENTITY(1,1) PRIMARY KEY,
        -- Numerics
        BitCol BIT NOT NULL,
        TinyIntCol TINYINT NOT NULL,
        BigIntCol BIGINT NOT NULL,
        DecimalCol DECIMAL(18,4) NOT NULL,
        FloatCol FLOAT NOT NULL,
        MoneyCol MONEY NOT NULL,
        -- Dates & Times
        DateCol DATE NOT NULL,
        DateTime2Col DATETIME2(7) NOT NULL,
        DateTimeOffsetCol DATETIMEOFFSET(7) NOT NULL,
        -- Binary & Identifiers
        GuidCol UNIQUEIDENTIFIER NOT NULL,
        VarBinaryCol VARBINARY(max) NOT NULL,
        -- XML
        XmlCol XML NOT NULL,
        -- Nullable field
        NullCol NVARCHAR(50) NULL
    );
    INSERT INTO AllTypesTest (
        BitCol, TinyIntCol, BigIntCol, DecimalCol, FloatCol, MoneyCol,
        DateCol, DateTime2Col, DateTimeOffsetCol,
        GuidCol, VarBinaryCol, XmlCol, NullCol
    ) VALUES (
        1, 255, 9223372036854775807, 123456.7891, 3.1415926535, 99.99,
        '2026-09-27', '2026-09-27 20:09:39.1234567', '2026-09-27 20:09:39.1234567 +00:00',
        'A0EEBC99-9C0B-4EF8-BB6D-6BB9BD380A11', 0xDEADBEEF1234, N'<root><element>Test</element></root>', NULL
    );
END
GO

-- 1. View (Must be in its own batch)
IF OBJECT_ID(N'dbo.vw_ProductCategories', N'V') IS NOT NULL
    DROP VIEW dbo.vw_ProductCategories;
GO
CREATE VIEW dbo.vw_ProductCategories AS
SELECT p.ProductID, p.ProductName, p.Price, c.CategoryName
FROM dbo.Products p
LEFT JOIN dbo.Categories c ON p.CategoryID = c.CategoryID;
GO

-- 2. Scalar Function
IF OBJECT_ID(N'dbo.fn_CalculateTax', N'FN') IS NOT NULL
    DROP FUNCTION dbo.fn_CalculateTax;
GO
CREATE FUNCTION dbo.fn_CalculateTax(@Amount DECIMAL(10,2))
RETURNS DECIMAL(10,2)
AS
BEGIN
    RETURN @Amount * 0.08;
END;
GO

-- 3. Stored Procedure
IF OBJECT_ID(N'dbo.sp_GetProductsByCategory', N'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_GetProductsByCategory;
GO
CREATE PROCEDURE dbo.sp_GetProductsByCategory
    @CatID INT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT ProductID, ProductName, Price
    FROM dbo.Products
    WHERE CategoryID = @CatID;
END;
GO

-- 4. Trigger
IF OBJECT_ID(N'dbo.trg_UpdateCategoryTimestamp', N'TR') IS NOT NULL
    DROP TRIGGER dbo.trg_UpdateCategoryTimestamp;
GO
CREATE TRIGGER dbo.trg_UpdateCategoryTimestamp
ON dbo.Categories
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    -- Simple trigger stub for testing definition extract
END;
GO
