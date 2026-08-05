# Sales.DarkhastFaktor

## Table overview

Header of a sales order / invoice request (Darkhast Faktor). Core company-sale document tying customer, salesperson, branch, amounts, discounts, taxes, delivery, GPS visit data, and workflow status (`CodeVazeiat`). Composite key is typically `ccDarkhastFaktor` + `Sal`.

## Columns

| # | Column | Type | Null | Key | Description |
|---|--------|------|------|-----|-------------|
| 1 | ccDarkhastFaktor | bigint | NO | PK, Identity | Order/invoice request id |
| 2 | Sal | int | NO | PK | Fiscal/calendar year part of key |
| 3 | CodeNoeVorod | tinyint | NO | | Entry channel/type (tablet, portal, …) |
| 4 | ccMantaghehPakhsh | int | NO | | Distribution region id |
| 5 | ccMarkazPakhsh | int | NO | | Distribution center id |
| 6 | ccForoshandeh | int | NO | | Salesperson id |
| 7 | NoeForoshandeh | tinyint | NO | | Salesperson type |
| 8 | ccAfradForoshandeh | int | YES | | Salesperson person (Afrad) id |
| 9 | ccMoshtary | int | NO | | Customer id |
| 10 | ccShahrMoshtary | int | YES | | Customer city id |
| 11 | ccAddressMoshtary | int | YES | | Customer address id |
| 12 | EtebarJary | float | NO | | Current credit snapshot at order time |
| 13 | ShomarehDarkhast | int | NO | | Request number |
| 14 | TarikhDarkhast | datetime | NO | | Request date |
| 15 | ShomarehFaktor | int | NO | | Invoice number (0 if not invoiced yet) |
| 16 | TarikhFaktor | datetime | YES | | Invoice date |
| 17 | TarikhPishbinyTahvil | datetime | YES | | Planned delivery date |
| 18 | TarikhErsal | datetime | YES | | Send/dispatch date |
| 19 | CodeNoeVosolAzMoshtary | tinyint | NO | | Collection type |
| 20 | ModateVosol | smallint | NO | | Collection period (days) |
| 21 | CodeNoeHaml | tinyint | NO | | Shipping method code |
| 22 | ccNoeMashin | int | YES | | Vehicle type id |
| 23 | ccTaminKonandeh | int | YES | | Supplier id (when relevant) |
| 24 | CodeVazeiat | tinyint | NO | | Document status/workflow code |
| 25 | Elat | nvarchar(50) | YES | | Status reason short text |
| 26 | MablaghKolDarkhast | float | YES | | Gross request amount |
| 27 | MablaghTakhfifDarkhastTitr | float | YES | | Header discount on request |
| 28 | MablaghTakhfifDarkhastSatr | float | YES | | Line discounts total on request |
| 29 | MablaghKolFaktor | float | YES | | Gross invoice amount |
| 30 | MablaghTakhfifFaktorTitr | float | YES | | Header discount on invoice |
| 31 | MablaghTakhfifFaktorSatr | float | YES | | Line discounts total on invoice |
| 32 | MablaghEzafat | float | YES | | Surcharges / extras |
| 33 | DateVorod | datetime | NO | | Insert / entry datetime |
| 34 | SaatVorodBeMaghazeh | datetime | YES | | Arrival time at store |
| 35 | SaatKhorojAzMaghazeh | datetime | YES | | Leave time from store |
| 36 | ccUser | int | YES | | User who entered the document |
| 37 | ccGorohForosh | int | YES | | Sales group id |
| 38 | ModatRoozRaasGiri | smallint | NO | | Settlement / due-day count |
| 39 | MablaghTakhfifFaktorTaavoni | float | YES | | Cooperative discount amount |
| 40 | SumTedad3 | int | YES | | Sum of unit-3 quantities |
| 41 | ccAfradGorohForosh | int | YES | | Sales-group person id |
| 42 | InvCode | smallint | YES | | Invoice type/code (legacy) |
| 43 | Serial | int | YES | | Serial number |
| 44 | DiscntType | int | YES | | Discount type |
| 45 | DiscntSubType | int | YES | | Discount subtype |
| 46 | ccNoeMoshtary | int | YES | | Customer type id at order time |
| 47 | ccNoeSenf | int | YES | | Trade guild / senf type |
| 48 | ShomarehFaktorIndex | bigint | YES | | Indexed invoice number |
| 49 | ccDorehMaly | int | YES | | Fiscal period id |
| 50 | BeMasoliat | tinyint | NO | | Responsibility / custody flag |
| 51 | SumMaliat | float | NO | | Total VAT/tax |
| 52 | SumAvarez | float | NO | | Total duties/surcharges |
| 53 | TarikhEntry | datetime | NO | | Business entry date |
| 54 | ModifiedDate | datetime | NO | | Last modification date |
| 55 | ccDarkhastFaktorPPC | nvarchar(40) | YES | | PPC / tablet external id |
| 56 | HoghoghiShodeh | tinyint | YES | | Escalated to legal flag |
| 57 | TarikhTahvil | datetime | YES | | Actual delivery date |
| 58 | SaatTahvil | datetime | YES | | Actual delivery time |
| 59 | TarikhSarResid | datetime | YES | | Due date |
| 60 | ccForoshandehAsli | int | YES | | Original/main salesperson |
| 61 | ID_Sms | bigint | NO | | Related SMS id |
| 62 | ToziSari | tinyint | NO | | Express distribution flag |
| 63 | ClientOrderId | int | YES | | Client-side order id |
| 64 | unVisit | int | YES | | Unvisited / visit result code |
| 65 | unVisitReason | nvarchar(255) | YES | | Reason for no visit/order |
| 66 | unOrder | int | YES | | No-order flag/code |
| 67 | averageDistance | float | YES | | Average visit distance |
| 68 | distanceFromPreviousVisit | float | YES | | Distance from previous visit |
| 69 | gpsStartTime | datetime | YES | | GPS visit start |
| 70 | gpsEndTime | datetime | YES | | GPS visit end |
| 71 | gpsStartLongitude | float | YES | | Start longitude |
| 72 | gpsStartLatitude | float | YES | | Start latitude |
| 73 | gpsEndLongitude | float | YES | | End longitude |
| 74 | gpsEndLatitude | float | YES | | End latitude |
| 75 | Tozihat | nvarchar(512) | YES | | Notes |
| 76 | MobileNum | varchar(15) | YES | | Contact mobile on order |
| 77 | SmsId | bigint | YES | | SMS tracking id |
| 78 | EntryDate | datetime | YES | | Alternate entry timestamp |
| 79 | ccKardexMokhader | bigint | YES | | Narcotic kardex link |
| 80 | Mokhader | tinyint | YES | | Contains narcotic items |
| 81 | MablaghTakhfifRialiTitr | float | YES | | Header rial discount |
| 82 | ModateVosolTakhfifRiali | smallint | YES | | Collection days for rial discount |
| 83 | ModatRoozRaasGiriTakhfifRiali | smallint | YES | | Settlement days for rial discount |
| 84 | idSMSSabadKalaErsali | bigint | YES | | Basket SMS campaign id |
| 85 | Calculate | bit | NO | | Needs recalculation flag |
| 86 | ElatHazf | nvarchar(500) | NO | | Deletion reason |
| 87 | IsDeleted | bit | NO | | Soft-delete flag |
| 88 | IsMokhader | bit | YES | | Narcotic document flag |
| 89 | PishFaktor | tinyint | NO | | Proforma / pre-invoice flag |
| 90 | VosoulInTablet | bit | NO | | Collection done on tablet |
| 91 | VosoulTavafoghi | bit | NO | | Agreed collection flag |
| 92 | TozihatTaeed | nvarchar(max) | NO | | Approval notes |
| 93 | ccAfradHesabdar | int | NO | | Accountant person id |
| 94 | ShenasehPardakhat | nvarchar(max) | YES | | Payment tracking id |
| 95 | RaveshPardakhat | int | YES | | Payment method |
| 96 | ShippingMethod | nvarchar(max) | YES | | Shipping method text |
| 97 | ShippingAddress | nvarchar(max) | YES | | Shipping address text |
| 98 | ccAfradMamoorVosoul | int | NO | | Collection officer id |
| 99 | IsMasirRooz | int | YES | | Is on today's route |
| 100 | VisitDateTime | datetime | YES | | Visit start datetime |
| 101 | EndOfVisitDateTime | datetime | YES | | Visit end datetime |
| 102 | IsNewApp | float | YES | | New app version/marker |
| 103 | NoeVisit | int | YES | | Visit type |
| 104 | ConfirmPortalDolaty | bit | YES | | Government portal confirmed |
| 105 | ElatOdatPortalDolati | nvarchar(300) | YES | | Gov portal rejection reason |
| 106 | IgnorAdamForosh | bit | YES | | Ignore no-sale restriction |
| 107 | SumTakhfifJayezeh | float | NO | | Total prize/discount amount |
| 108 | ConfirmEshantionMazad | bit | YES | | Extra free-goods confirmed |
| 109 | ElatOdatEshantionMazad | nvarchar(300) | YES | | Extra free-goods reject reason |
| 110 | MablaghTakhfifTahsilatTitr | float | YES | | Header education/facility discount |
| 111 | MablaghKhalesDarkhast | float | YES | | Net request amount |
| 112 | MablaghKhalesFaktor | float | YES | | Net invoice amount |
| 113 | MablaghMandehMoshtary | float | YES | | Customer remaining balance snapshot |
| 114 | MablaghVajhDaryaftyFaktor | float | YES | | Cash/received amount on invoice |
