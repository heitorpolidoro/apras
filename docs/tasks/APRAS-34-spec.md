# APRAS-34 — Implementar controle de ativos e estoque do condomínio

## Scope

This task implements complete patrimonial asset management and consumable inventory tracking for the condominium. It enables HOA administrators, directors, and building managers to catalog assets (fixed assets like lawn mowers, security cameras, furniture) and track consumable materials (light bulbs, cleaning supplies, maintenance parts) with full movement auditability and low-stock alerting.

### What this task covers:
1. **Data Model**: SQLModel models `Asset` and `InventoryMovement`, plus domain enums `AssetCategory`, `AssetCondition`, and `MovementType`.
2. **Database Migration**: Alembic migration adding the `asset` and `inventory_movement` tables with foreign keys, indexes, and cascades.
3. **Business Logic & RBAC**:
   - `ADMINISTRATOR` & `DIRECTOR`: Full CRUD on assets, inventory movements (`ENTRADA`, `SAIDA`, `AJUSTE_INVENTARIO`, `BAIXA_PATRIMONIAL`), and stock adjustments.
   - `MANAGER`: Read assets/inventory, register `ENTRADA` (arrival) and `SAIDA` (consumption/exit) movements. Cannot create/update/delete asset definitions or perform `AJUSTE_INVENTARIO` / `BAIXA_PATRIMONIAL`.
   - `RESIDENT`, `PORTEIRO`, `GUEST`: Blocked from access (403 Forbidden).
   - Atomic balance updates for `current_quantity`, strict non-negative validation on consumption (`SAIDA`), and automated condition adjustments on patrimonial write-offs (`BAIXA_PATRIMONIAL`).
4. **REST API Endpoints**:
   - `GET /api/v1/assets` — List assets with search and filters (category, location, is_consumable, condition, low_stock_only, pagination).
   - `POST /api/v1/assets` — Create asset/inventory item (Admin/Director).
   - `GET /api/v1/assets/{id}` — Get asset detail with movement history log.
   - `PUT /api/v1/assets/{id}` — Update asset metadata (Admin/Director).
   - `DELETE /api/v1/assets/{id}` — Delete asset and cascade movements (Admin/Director).
   - `POST /api/v1/assets/{id}/movements` — Record a stock/asset movement.
   - `GET /api/v1/inventory-movements` — List movement audit trail across all assets.
5. **Frontend SPA**:
   - Route `/assets` (`AssetsInventoryPage.tsx`) protected by roles `[ADMINISTRATOR, DIRECTOR, MANAGER]`.
   - Components: `AssetSummaryCards`, `AssetTable`, `AssetFormModal`, `StockMovementModal`, `AssetMovementHistoryModal`.
   - Top-level navigation entry in `Navbar.tsx`.
   - Full internationalization keys in `pt.json` and `en.json`.
6. **Testing**:
   - Pytest unit and integration test suite with coverage >= 90%.
   - Vitest component and hook test suite with coverage >= 75%.

---

## Approach

### 1. Data Models (`backend/app/models/`)

#### `backend/app/models/enums.py`
Add the following enums:

```python
class AssetCategory(StrEnum):
    """Enumeration for asset and inventory item categories."""

    ELETRONICOS = "ELETRONICOS"
    FERRAMENTAS = "FERRAMENTAS"
    MOBILIARIO = "MOBILIARIO"
    SEGURANCA = "SEGURANCA"
    LIMPEZA = "LIMPEZA"
    MANUTENCAO = "MANUTENCAO"
    OUTROS = "OUTROS"


class AssetCondition(StrEnum):
    """Enumeration for physical condition of patrimonial assets."""

    NOVO = "NOVO"
    BOM = "BOM"
    REGULAR = "REGULAR"
    RUIM = "RUIM"
    DANIFICADO = "DANIFICADO"
    BAIXADO = "BAIXADO"


class MovementType(StrEnum):
    """Enumeration for inventory and asset movements."""

    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"
    AJUSTE_INVENTARIO = "AJUSTE_INVENTARIO"
    BAIXA_PATRIMONIAL = "BAIXA_PATRIMONIAL"
```

#### `backend/app/models/asset.py` (New File)
```python
from datetime import date, datetime, timezone
from uuid import UUID, uuid4
from sqlmodel import Field, Relationship, SQLModel
from app.models.enums import AssetCategory, AssetCondition, MovementType


class Asset(SQLModel, table=True):
    """Asset or consumable inventory item."""

    __tablename__ = "asset"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(nullable=False, index=True)
    category: AssetCategory = Field(nullable=False, index=True)
    serial_number: str | None = Field(default=None, nullable=True, index=True)
    asset_tag: str | None = Field(default=None, nullable=True, unique=True, index=True)
    location: str = Field(nullable=False, index=True)
    acquisition_date: date | None = Field(default=None, nullable=True)
    acquisition_value: float | None = Field(default=None, nullable=True)
    condition: AssetCondition = Field(default=AssetCondition.BOM, nullable=False, index=True)
    is_consumable: bool = Field(default=False, nullable=False, index=True)
    current_quantity: int = Field(default=1, nullable=False)
    min_quantity: int | None = Field(default=None, nullable=True)
    unit_of_measure: str | None = Field(default="un", nullable=True)
    notes: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    movements: list["InventoryMovement"] = Relationship(
        back_populates="asset",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "InventoryMovement.created_at.desc()"},
    )


class InventoryMovement(SQLModel, table=True):
    """Audit log of stock entries, exits, adjustments, and asset write-offs."""

    __tablename__ = "inventory_movement"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    asset_id: UUID = Field(
        foreign_key="asset.id", nullable=False, index=True, ondelete="CASCADE"
    )
    movement_type: MovementType = Field(nullable=False, index=True)
    quantity: int = Field(nullable=False)
    previous_quantity: int = Field(nullable=False)
    new_quantity: int = Field(nullable=False)
    performed_by_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
    reason: str = Field(nullable=False)
    document_number: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    # Relationships
    asset: Asset = Relationship(back_populates="movements")
```

Expose both models and enums in `backend/app/models/__init__.py`.

---

### 2. Pydantic Schemas (`backend/app/schemas/asset.py`)

Create schemas for API requests, responses, and filtering:

- `AssetCreate`: `name`, `category`, `serial_number`, `asset_tag`, `location`, `acquisition_date`, `acquisition_value`, `condition`, `is_consumable`, `current_quantity` (ge 0), `min_quantity` (ge 0), `unit_of_measure`, `notes`.
- `AssetUpdate`: all fields optional.
- `AssetRead`: all asset columns + calculated `is_low_stock: bool` (`is_consumable and min_quantity is not None and current_quantity <= min_quantity`).
- `PaginatedAssetRead`: `items: list[AssetRead]`, `total: int`, `skip: int`, `limit: int`.
- `InventoryMovementCreate`: `movement_type: MovementType`, `quantity: int` (gt 0 for ENTRADA/SAIDA/BAIXA, ge 0 for AJUSTE_INVENTARIO), `reason: str`, `document_number: str | None = None`.
- `InventoryMovementRead`: all movement columns + `performed_by_name: str | None` + `asset_name: str | None`.
- `PaginatedInventoryMovementRead`: `items: list[InventoryMovementRead]`, `total: int`, `skip: int`, `limit: int`.
- `AssetDetailRead`: `AssetRead` + `movements: list[InventoryMovementRead]`.
- `AssetSummaryRead`: `total_assets: int`, `total_consumables: int`, `low_stock_count: int`, `total_patrimonial_value: float`.

---

### 3. Business Logic & Service (`backend/app/services/asset_service.py`)

Encapsulate all asset operations in `AssetService`:

1. **`list_assets`**:
   - Filter by `category`, `location`, `is_consumable`, `condition`.
   - Full-text or substring `search` across `name`, `serial_number`, `asset_tag`, `location`.
   - `low_stock_only` boolean flag: filters `is_consumable == True` and `min_quantity is not None` and `current_quantity <= min_quantity`.
   - Sorting and pagination (`skip`, `limit`).
2. **`get_asset_summary`**:
   - Aggregate statistics for dashboard summary cards.
3. **`create_asset`**:
   - Enforce RBAC (`ADMINISTRATOR`, `DIRECTOR`).
   - Validate uniqueness of `asset_tag` if provided.
   - If initial `current_quantity > 0`, create an initial `ENTRADA` or `AJUSTE_INVENTARIO` movement record noting initial inventory setup.
4. **`get_asset_by_id`**:
   - Retrieve asset with movement history.
5. **`update_asset`**:
   - Enforce RBAC (`ADMINISTRATOR`, `DIRECTOR`).
   - Note: Quantity changes should go through movements, but administrative corrections update metadata fields.
6. **`delete_asset`**:
   - Enforce RBAC (`ADMINISTRATOR`, `DIRECTOR`).
   - Cascades and removes associated movement records.
7. **`record_movement`**:
   - RBAC check:
     - `ADMINISTRATOR`, `DIRECTOR`: allowed all `MovementType`s.
     - `MANAGER`: allowed only `MovementType.ENTRADA` and `MovementType.SAIDA`. Reject `AJUSTE_INVENTARIO` and `BAIXA_PATRIMONIAL` with `ForbiddenError`.
     - Other roles: `ForbiddenError`.
   - Stock math calculation:
     - `ENTRADA`: `new_quantity = asset.current_quantity + movement_in.quantity`
     - `SAIDA`:
       - If `movement_in.quantity > asset.current_quantity`, raise `DomainError("Saldo insuficiente em estoque")` (HTTP 400).
       - `new_quantity = asset.current_quantity - movement_in.quantity`
     - `AJUSTE_INVENTARIO`:
       - `new_quantity = movement_in.quantity` (sets inventory directly to counted balance)
     - `BAIXA_PATRIMONIAL`:
       - If not consumable, writes off asset: `new_quantity = max(0, asset.current_quantity - movement_in.quantity)`, and sets `asset.condition = AssetCondition.BAIXADO`.
   - Update `asset.current_quantity = new_quantity` and `asset.updated_at = utcnow`.
   - Persist `InventoryMovement` with `previous_quantity`, `new_quantity`, `performed_by_id = current_user.id`.
8. **`list_inventory_movements`**:
   - Filter by `asset_id`, `movement_type`, `performed_by_id`, date range.
   - Paginated response.

---

### 4. API Endpoints (`backend/app/api/v1/endpoints/assets.py` & `inventory_movements.py`)

- Include routers in `backend/app/api/v1/api.py`:
  - `api_router.include_router(assets.router, prefix="/assets", tags=["assets"])`
  - `api_router.include_router(inventory_movements.router, prefix="/inventory-movements", tags=["inventory-movements"])`

#### Endpoint Specs:
- `GET /api/v1/assets`:
  - Query: `category: AssetCategory | None`, `location: str | None`, `is_consumable: bool | None`, `condition: AssetCondition | None`, `search: str | None`, `low_stock_only: bool = False`, `skip: int = 0`, `limit: int = 100`.
  - Auth: `deps.get_current_user` (`ADMINISTRATOR`, `DIRECTOR`, `MANAGER`).
- `GET /api/v1/assets/summary`:
  - Auth: `deps.get_current_user` (`ADMINISTRATOR`, `DIRECTOR`, `MANAGER`).
  - Response: `AssetSummaryRead`.
- `POST /api/v1/assets`:
  - Auth: `deps.get_current_user` (`ADMINISTRATOR`, `DIRECTOR`).
  - Response: `AssetRead`, status 201.
- `GET /api/v1/assets/{id}`:
  - Auth: `deps.get_current_user` (`ADMINISTRATOR`, `DIRECTOR`, `MANAGER`).
  - Response: `AssetDetailRead`.
- `PUT /api/v1/assets/{id}`:
  - Auth: `deps.get_current_user` (`ADMINISTRATOR`, `DIRECTOR`).
  - Response: `AssetRead`.
- `DELETE /api/v1/assets/{id}`:
  - Auth: `deps.get_current_user` (`ADMINISTRATOR`, `DIRECTOR`).
  - Response: status 204 No Content.
- `POST /api/v1/assets/{id}/movements`:
  - Auth: `deps.get_current_user` (`ADMINISTRATOR`, `DIRECTOR`, `MANAGER`).
  - Response: `InventoryMovementRead`, status 201.
- `GET /api/v1/inventory-movements`:
  - Query: `asset_id: UUID | None`, `movement_type: MovementType | None`, `skip: int = 0`, `limit: int = 100`.
  - Auth: `deps.get_current_user` (`ADMINISTRATOR`, `DIRECTOR`, `MANAGER`).
  - Response: `PaginatedInventoryMovementRead`.

---

### 5. Frontend Architecture (`frontend/src/`)

#### TypeScript Definitions (`frontend/src/types/asset.ts`):
```ts
export const AssetCategory = {
  ELETRONICOS: "ELETRONICOS",
  FERRAMENTAS: "FERRAMENTAS",
  MOBILIARIO: "MOBILIARIO",
  SEGURANCA: "SEGURANCA",
  LIMPEZA: "LIMPEZA",
  MANUTENCAO: "MANUTENCAO",
  OUTROS: "OUTROS",
} as const;
export type AssetCategory = (typeof AssetCategory)[keyof typeof AssetCategory];

export const AssetCondition = {
  NOVO: "NOVO",
  BOM: "BOM",
  REGULAR: "REGULAR",
  RUIM: "RUIM",
  DANIFICADO: "DANIFICADO",
  BAIXADO: "BAIXADO",
} as const;
export type AssetCondition = (typeof AssetCondition)[keyof typeof AssetCondition];

export const MovementType = {
  ENTRADA: "ENTRADA",
  SAIDA: "SAIDA",
  AJUSTE_INVENTARIO: "AJUSTE_INVENTARIO",
  BAIXA_PATRIMONIAL: "BAIXA_PATRIMONIAL",
} as const;
export type MovementType = (typeof MovementType)[keyof typeof MovementType];

export interface Asset {
  id: string;
  name: string;
  category: AssetCategory;
  serial_number: string | null;
  asset_tag: string | null;
  location: string;
  acquisition_date: string | null;
  acquisition_value: number | null;
  condition: AssetCondition;
  is_consumable: boolean;
  current_quantity: number;
  min_quantity: number | null;
  unit_of_measure: string | null;
  notes: string | null;
  is_low_stock: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryMovement {
  id: string;
  asset_id: string;
  movement_type: MovementType;
  quantity: number;
  previous_quantity: number;
  new_quantity: number;
  performed_by_id: string;
  performed_by_name?: string | null;
  reason: string;
  document_number: string | null;
  created_at: string;
}

export interface AssetSummary {
  total_assets: number;
  total_consumables: number;
  low_stock_count: number;
  total_patrimonial_value: number;
}
```

#### API Client (`frontend/src/api/assets.ts`):
- `getAssets(params)`
- `getAssetSummary()`
- `getAsset(id)`
- `createAsset(data)`
- `updateAsset(id, data)`
- `deleteAsset(id)`
- `createMovement(assetId, data)`
- `getInventoryMovements(params)`

#### Feature Components (`frontend/src/features/asset-management/`):
- `AssetsInventoryPage.tsx`: Main page containing tabs/toggle between "All Items", "Fixed Assets", "Consumables / Stock", and "Low Stock Alerts", top action buttons ("Novo Ativo / Item"), and rendered subcomponents.
- `components/AssetSummaryCards.tsx`: 4 metric cards (Total Ativos, Itens Consumíveis, Alertas Estoque Baixo, Valor Total Patrimônio).
- `components/AssetTable.tsx`: Responsive data table with sorting, search query input, filters (category select, location, condition, consumable switch), badge indicators (category color badges, condition badges, low stock danger badges), and action buttons (Record Movement, Edit, View History, Delete).
- `components/AssetFormModal.tsx`: Modal form for asset creation and edition with field validations.
- `components/StockMovementModal.tsx`: Modal for registering `ENTRADA`, `SAIDA`, `AJUSTE_INVENTARIO`, `BAIXA_PATRIMONIAL` with reason and document number. Restricts movement types based on user role (Manager only sees Entrada/Saída).
- `components/AssetMovementHistoryModal.tsx`: Modal dialog showing movement history log for the selected asset with date, type, quantity delta, user name, and justification.

#### Navigation & Routing:
- Update `frontend/src/App.tsx`:
  ```tsx
  <Route
    path="/assets"
    element={
      <ProtectedRoute
        requiredRoles={[
          UserRole.ADMINISTRATOR,
          UserRole.DIRECTOR,
          UserRole.MANAGER,
        ]}
      >
        <AssetsInventoryPage />
      </ProtectedRoute>
    }
  />
  ```
- Update `frontend/src/features/user-administration/components/Navbar.tsx`:
  - Show link `{t("nav.assets")}` pointing to `/assets` when role is `ADMINISTRATOR`, `DIRECTOR`, or `MANAGER`.

#### i18n Localization (`pt.json` & `en.json`):
- Add comprehensive translation dictionaries under `assets` namespace and `nav.assets`.

---

## Expected Results

- [ ] Database migration successfully creates `asset` and `inventory_movement` tables with proper foreign keys and indexes.
- [ ] Model validation rejects negative stock quantities upon `SAIDA` when requested quantity exceeds available balance.
- [ ] `POST /api/v1/assets` creates a new asset; only accessible by `ADMINISTRATOR` and `DIRECTOR`.
- [ ] `GET /api/v1/assets` returns paginated assets with search, category, condition, consumable, and `low_stock_only` filters.
- [ ] `POST /api/v1/assets/{id}/movements` calculates and updates `asset.current_quantity` atomically, creating an audit `InventoryMovement` entry.
- [ ] Manager role can execute `ENTRADA` and `SAIDA` movements, but receives 403 Forbidden when attempting `AJUSTE_INVENTARIO` or `BAIXA_PATRIMONIAL`.
- [ ] `RESIDENT`, `PORTEIRO`, and `GUEST` roles receive 403 Forbidden on all asset and inventory endpoints.
- [ ] `DELETE /api/v1/assets/{id}` removes asset and cascades deletion to all associated movements; restricted to `ADMINISTRATOR` and `DIRECTOR`.
- [ ] `GET /api/v1/assets/summary` returns accurate count of total assets, consumables, low stock warnings, and total acquisition value.
- [ ] Frontend displays summary metrics, filterable asset table, modal forms for asset CRUD, stock movements, and audit history.
- [ ] Low-stock items display visible warning indicators when `is_consumable=True` and `current_quantity <= min_quantity`.
- [ ] Role-aware UI hides or disables restricted actions (e.g. Asset creation/editing and Inventory Adjustment hidden from Managers).
- [ ] Backend test suite achieves >= 90% test coverage on new asset models, endpoints, and services.
- [ ] Frontend test suite achieves >= 75% test coverage on asset components and hooks.

---

## Out of Scope

- Barcode / QR-code camera scanner hardware integration (manual tag string entry is supported).
- Supplier / Vendor catalog management and purchase order approval workflows.
- Depreciation accounting calculation engine (straight-line / declining balance formulas).
- Multi-warehouse transfer routing (single condominium / multi-location strings supported).
