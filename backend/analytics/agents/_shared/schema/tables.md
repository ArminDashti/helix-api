# Allowed objects

List one fully qualified object per line (SQL allowlist — AdventureWorks LT sample):

- SalesLT.Customer
- SalesLT.Address
- SalesLT.CustomerAddress
- SalesLT.Product
- SalesLT.ProductCategory
- SalesLT.ProductModel
- SalesLT.ProductDescription
- SalesLT.ProductModelProductDescription
- SalesLT.SalesOrderHeader
- SalesLT.SalesOrderDetail

# Catalog

## SalesLT.Customer

- **Kind:** table
- **Description:** Customer master (AdventureWorks LT). Use for customer counts, salespeople, companies, and contact info.

| Column | Description |
|--------|-------------|
| CustomerID | Customer primary key |
| NameStyle | Name style flag |
| Title | Title (Mr./Ms.) |
| FirstName | First name |
| MiddleName | Middle name |
| LastName | Last name |
| Suffix | Name suffix |
| CompanyName | Company / organization |
| SalesPerson | Assigned salesperson |
| EmailAddress | Email |
| Phone | Phone |
| PasswordHash | Password hash (do not expose) |
| PasswordSalt | Password salt (do not expose) |
| rowguid | Row GUID |
| ModifiedDate | Last modified |

## SalesLT.Address

- **Kind:** table
- **Description:** Postal addresses for customers (city, state/province, country/region).

| Column | Description |
|--------|-------------|
| AddressID | Address primary key |
| AddressLine1 | Street line 1 |
| AddressLine2 | Street line 2 |
| City | City |
| StateProvince | State or province |
| CountryRegion | Country or region |
| PostalCode | Postal code |
| rowguid | Row GUID |
| ModifiedDate | Last modified |

## SalesLT.CustomerAddress

- **Kind:** table
- **Description:** Links customers to addresses with an address type (Main Office, Shipping, etc.).

| Column | Description |
|--------|-------------|
| CustomerID | Customer id |
| AddressID | Address id |
| AddressType | Address type label |
| rowguid | Row GUID |
| ModifiedDate | Last modified |

## SalesLT.Product

- **Kind:** table
- **Description:** Product catalog with costs, list prices, sizes, colors, and category/model links.

| Column | Description |
|--------|-------------|
| ProductID | Product primary key |
| Name | Product name |
| ProductNumber | SKU / product number |
| Color | Color |
| StandardCost | Standard cost |
| ListPrice | List price |
| Size | Size |
| Weight | Weight |
| ProductCategoryID | Category id |
| ProductModelID | Model id |
| SellStartDate | Sell start |
| SellEndDate | Sell end |
| DiscontinuedDate | Discontinued date |
| ThumbNailPhoto | Thumbnail blob |
| ThumbnailPhotoFileName | Thumbnail file name |
| rowguid | Row GUID |
| ModifiedDate | Last modified |

## SalesLT.ProductCategory

- **Kind:** table
- **Description:** Product categories (supports parent/child hierarchy).

| Column | Description |
|--------|-------------|
| ProductCategoryID | Category primary key |
| ParentProductCategoryID | Parent category id |
| Name | Category name |
| rowguid | Row GUID |
| ModifiedDate | Last modified |

## SalesLT.ProductModel

- **Kind:** table
- **Description:** Product models / catalog groupings.

| Column | Description |
|--------|-------------|
| ProductModelID | Model primary key |
| Name | Model name |
| CatalogDescription | Catalog XML/text description |
| rowguid | Row GUID |
| ModifiedDate | Last modified |

## SalesLT.ProductDescription

- **Kind:** table
- **Description:** Localized product description text.

| Column | Description |
|--------|-------------|
| ProductDescriptionID | Description primary key |
| Description | Description text |
| rowguid | Row GUID |
| ModifiedDate | Last modified |

## SalesLT.ProductModelProductDescription

- **Kind:** table
- **Description:** Maps product models to descriptions by culture.

| Column | Description |
|--------|-------------|
| ProductModelID | Model id |
| ProductDescriptionID | Description id |
| Culture | Culture code (e.g. en) |
| rowguid | Row GUID |
| ModifiedDate | Last modified |

## SalesLT.SalesOrderHeader

- **Kind:** table
- **Description:** Sales order headers — dates, customer, totals, tax, freight, status.

| Column | Description |
|--------|-------------|
| SalesOrderID | Order primary key |
| RevisionNumber | Revision |
| OrderDate | Order date |
| DueDate | Due date |
| ShipDate | Ship date |
| Status | Order status |
| OnlineOrderFlag | Online order flag |
| SalesOrderNumber | Order number |
| PurchaseOrderNumber | PO number |
| AccountNumber | Account number |
| CustomerID | Customer id |
| ShipToAddressID | Ship-to address id |
| BillToAddressID | Bill-to address id |
| ShipMethod | Shipping method |
| CreditCardApprovalCode | Approval code |
| SubTotal | Subtotal |
| TaxAmt | Tax amount |
| Freight | Freight |
| TotalDue | Total due |
| Comment | Comment |
| rowguid | Row GUID |
| ModifiedDate | Last modified |

## SalesLT.SalesOrderDetail

- **Kind:** table
- **Description:** Sales order line items — product, qty, unit price, discount, line total.

| Column | Description |
|--------|-------------|
| SalesOrderID | Order id |
| SalesOrderDetailID | Line primary key |
| OrderQty | Quantity ordered |
| ProductID | Product id |
| UnitPrice | Unit price |
| UnitPriceDiscount | Unit discount |
| LineTotal | Line total |
| rowguid | Row GUID |
| ModifiedDate | Last modified |
