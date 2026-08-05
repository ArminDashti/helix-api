# Sales.Moshtary

## Table overview

Master customer (Moshtary) registry for company sales. Holds identity, contact, license, credit hints, GPS/GLN identifiers, and operational status used across orders, visits, and credit checks.

## Columns

| # | Column | Type | Null | Key | Description |
|---|--------|------|------|-----|-------------|
| 1 | ccMoshtary | int | NO | PK, Identity | Customer primary key |
| 2 | ccMoshtaryJadid | int | YES | | Link to new-customer request record |
| 3 | MoshtaryAsli | bit | NO | | Marks main/parent customer |
| 4 | ccMoshtary_Link | int | YES | | Related/parent customer id |
| 5 | TarikhMoarefiMoshtary | datetime | YES | | Customer introduction date |
| 6 | NameMoshtary | nvarchar(255) | YES | | Customer legal/display name |
| 7 | NameTablo | nvarchar(255) | YES | | Storefront / signboard name |
| 8 | CodePosty | nvarchar(20) | NO | | Postal code |
| 9 | CodeEghtesady | nvarchar(15) | NO | | Economic / tax code |
| 10 | CodeNoeVosolAzMoshtary | tinyint | NO | | Default collection type from customer |
| 11 | ModateVosol | smallint | NO | | Default collection period (days) |
| 12 | CodeNoeShakhsiat | tinyint | NO | | Person type (real/legal, etc.) |
| 13 | ccMahaleh | int | YES | | Neighborhood / locality id |
| 14 | ccNoeMalekiatMoshtary | int | YES | | Ownership type of premises |
| 15 | ModateParvanehKasb | tinyint | NO | | Business license duration class |
| 16 | ModateHozor | smallint | NO | | Presence / tenure duration |
| 17 | Telephone | varchar(50) | NO | | Phone number |
| 18 | Fax | varchar(50) | NO | | Fax number |
| 19 | Kart | bit | NO | | Has business card flag |
| 20 | Javaz | bit | NO | | Has license flag |
| 21 | NoeJavaz | nvarchar(15) | NO | | License type |
| 22 | ShomarehJavaz | nvarchar(15) | NO | | License number |
| 23 | TarikhEnghezaJavaz | datetime | YES | | License expiry date |
| 24 | Darajeh | nvarchar(1) | NO | | Customer grade/rank |
| 25 | Namaiandeh | bit | NO | | Is representative flag |
| 26 | NoeMashin | nvarchar(50) | NO | | Vehicle type used by customer |
| 27 | Sanad | bit | NO | | Has ownership deed flag |
| 28 | GhafasehBandy | bit | NO | | Has shelving flag |
| 29 | TedadYakhchal | tinyint | NO | | Refrigerator count |
| 30 | TedadFraizer | tinyint | NO | | Freezer count |
| 31 | TedadSandogh | tinyint | NO | | Cash register / safe count |
| 32 | HosneShohrat | bit | NO | | Good reputation flag |
| 33 | ForoshTaghribiRoozaneh | float | NO | | Approx. daily sales amount |
| 34 | MojoudiTaghriby | float | NO | | Approx. inventory value |
| 35 | EtebarPishnahady | float | NO | | Suggested credit limit |
| 36 | EtebarKol | float | NO | | Total credit limit |
| 37 | Tozihat | nvarchar(200) | NO | | Notes / comments |
| 38 | CodeVazeiat | tinyint | NO | | Status code (active/inactive, etc.) |
| 39 | ccElatAdamFaalMoshtary | int | YES | | Reason id for inactivity |
| 40 | ccUser | int | NO | | Creating/editing user id |
| 41 | CodeMoshtaryOld | nvarchar(15) | NO | | Legacy customer code |
| 42 | TarikhEjareh | datetime | YES | | Lease date |
| 43 | KharidPishnahady | float | NO | | Suggested purchase amount |
| 44 | CodeNahvehTahiehKala | tinyint | NO | | Goods supply method code |
| 45 | EtebarPishnahadySystem | float | NO | | System-calculated suggested credit |
| 46 | CodeMoshtaryOldDos | nvarchar(15) | NO | | Old DOS-era customer code |
| 47 | FlagCodeVazeiat | tinyint | NO | | Extra status flag |
| 48 | TarikhEntry | datetime | NO | | Record create date |
| 49 | ModifiedDate | datetime | NO | | Last modify date |
| 50 | ElatOdat | nvarchar(500) | YES | | Rejection / return reason text |
| 51 | CodeShenase | nvarchar(15) | YES | | National ID / identifier code |
| 52 | IsDolaty | bit | YES | | Government customer flag |
| 53 | x | float | YES | | Legacy coordinate X |
| 54 | y | float | YES | | Legacy coordinate Y |
| 55 | z | float | YES | | Legacy coordinate Z |
| 56 | CodeMoshtaryNew | bigint | YES | | New external customer code |
| 57 | HIXCode | nvarchar(255) | YES | | HIX pharmacy system code |
| 58 | GLN | nvarchar(255) | YES | | Global Location Number |
| 59 | gln_convert_with_codemeli | bit | YES | | GLN matched via national id |
| 60 | gln_convert_with_name | bit | YES | | GLN matched via name |
| 61 | gln_date | datetime | YES | | GLN assignment/match date |
| 62 | gln_convert_with_codeposti | bit | YES | | GLN matched via postal code |
| 63 | gln_convert_with_mobile | bit | YES | | GLN matched via mobile |
| 64 | ccMasirTozieMoshtarian | int | NO | | Customer distribution path id |
| 65 | ActiveForToday | bit | NO | | Active for today's operations |
| 66 | NameMoshtaryOld | nvarchar(50) | NO | | Previous customer name |
| 67 | ccAfradHesabdar | int | NO | | Assigned accountant person id |
| 68 | TarikhPayanGharardad | datetime | YES | | Contract end date |
| 69 | ShomarehGharardad | nvarchar(15) | NO | | Contract number |
| 70 | ccMoshtaryPeymankarLast | int | NO | | Last contractor customer id |
| 71 | PeymankarAsli | bit | NO | | Main contractor flag |
| 72 | ccMoshtaryPeymankar_Link | int | NO | | Linked contractor customer |
| 73 | CodeVazeiatBeforActiveForToday | tinyint | NO | | Status before ActiveForToday |
| 74 | CustomerId | bigint | YES | | External/portal customer id |
| 75 | NezamPezeshkiCode | nvarchar(50) | YES | | Medical council code |
| 76 | ParvaneCode | nvarchar(50) | YES | | Practice license code |
| 77 | ParvaneClinic | nvarchar(50) | YES | | Clinic license code |
| 78 | CodeShenaseSaderat | nvarchar(20) | YES | | Export identifier code |
| 79 | ccAfradMamoorVosoul | int | NO | | Collection officer person id |
| 80 | bankCardNumber | nvarchar(100) | YES | | Bank card number |
| 81 | bankAccountNumber | nvarchar(100) | YES | | Bank account number |
| 82 | RoleIdMojazForWarehouse | int | YES | | Allowed warehouse role id |
| 83 | SharhMoshtary | nvarchar(max) | YES | | Extended customer description |
| 84 | validGln | tinyint | YES | | GLN validity flag |
| 85 | DatevalidGln | datetime | YES | | GLN validation date |
| 86 | Latitude | float | YES | | GPS latitude |
| 87 | Longitude | float | YES | | GPS longitude |
| 88 | CodeShobeKharidar | nvarchar(20) | YES | | Buyer branch code |
| 89 | CodeMosharekaty | nvarchar(50) | YES | | Cooperative/partnership code |
| 90 | ccAfradUnBlockMali | int | YES | | Person who financially unblocked |
