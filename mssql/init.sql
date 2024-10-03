CREATE DATABASE TestDB;
GO

USE TestDB;
GO

CREATE SCHEMA logistics;
GO

CREATE TABLE dbo.Products (
  ProductID int IDENTITY(1,1) NOT NULL,
  ProductName nvarchar(100) COLLATE Latin1_General_CI_AS NOT NULL,
  CONSTRAINT PK_Products PRIMARY KEY (ProductID)
);
GO

CREATE TABLE logistics.ProductBarcodes(
  ProductID int NOT NULL,
  Barcode varchar(50) NOT NULL,
  CONSTRAINT PK_Logistics_ProductBarcodes PRIMARY KEY CLUSTERED (Barcode ASC)
);
GO

EXEC sys.sp_cdc_enable_db;
GO

EXEC sys.sp_cdc_enable_table
  @source_schema = N'dbo',
  @source_name = N'Products',
  @role_name = NULL;
GO

EXEC sys.sp_cdc_enable_table
  @source_schema = N'logistics',
  @source_name = N'ProductBarcodes',
  @role_name = NULL;
GO
