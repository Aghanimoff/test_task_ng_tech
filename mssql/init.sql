IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'TestDB')
BEGIN
    CREATE DATABASE TestDB;
END
GO

USE TestDB;
GO

IF NOT EXISTS (SELECT schema_name FROM information_schema.schemata WHERE schema_name = N'logistics')
BEGIN
    EXEC('CREATE SCHEMA logistics AUTHORIZATION dbo;');
END
GO

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Products') AND type in (N'U'))
BEGIN
    CREATE TABLE dbo.Products (
        ProductID int IDENTITY(1,1) NOT NULL,
        ProductName nvarchar(100) COLLATE Latin1_General_CI_AS NOT NULL,
        CONSTRAINT PK_Products PRIMARY KEY (ProductID)
    );
END
GO

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'logistics.ProductBarcodes') AND type in (N'U'))
BEGIN
    CREATE TABLE logistics.ProductBarcodes(
        ProductID int NOT NULL,
        Barcode varchar(50) NOT NULL,
        CONSTRAINT PK_Logistics_ProductBarcodes PRIMARY KEY CLUSTERED (Barcode ASC)
    );
END
GO

IF EXISTS (SELECT 1 FROM sys.databases WHERE name = 'TestDB' AND is_cdc_enabled = 0)
BEGIN
    EXEC sys.sp_cdc_enable_db;
END
GO

IF NOT EXISTS (SELECT * FROM cdc.change_tables WHERE source_object_id = OBJECT_ID('dbo.Products'))
BEGIN
    EXEC sys.sp_cdc_enable_table
        @source_schema = N'dbo',
        @source_name = N'Products',
        @role_name = NULL;
END
GO

IF NOT EXISTS (SELECT * FROM cdc.change_tables WHERE source_object_id = OBJECT_ID('logistics.ProductBarcodes'))
BEGIN
    EXEC sys.sp_cdc_enable_table
        @source_schema = N'logistics',
        @source_name = N'ProductBarcodes',
        @role_name = NULL;
END
GO
