</Meridian Spec Generator — Task Spec Author>
<T002 — Cadastro de Moradores por Lote e vinculação de contas de usuário>

## Scope

This task implements the Resident Management module ("Cadastro de Moradores por Lote e Vinculação de Contas de Usuário") for APRAS, enabling HOAs to maintain census records of physical residents per property unit (lot) and seamlessly bind them to authenticated system user accounts.

### In Scope
1. **Database Schema & Models**:
   - SQLModel entity `Resident` with foreign key `lot_id` (`FK -> lot.id`, `ON DELETE CASCADE`) and nullable `user_id` (`FK -> user.id`, `ON DELETE SET NULL`).
   - Domain enumeration `ResidentRelationship` (`TITULAR`, `CONJUGE`, `FILHO_DEPENDENTE`, `INQUILINO`, `PARENTE`, `OUTRO`).
   - Indexed fields on `cpf` and `email` for high-performance auto-matching during user signup.
   - Alembic DDL migration script generating the `resident` table, foreign keys, indices, and defaults.

2. **Auto-linking Rule on User Signup**:
   - Automatic matching logic invoked when a new `User` registers (`POST /api/v1/auth/signup`) or is created by an administrator.
   - If `new_user.cpf` or `new_user.email` matches an existing unlinked `Resident` profile (`user_id IS NULL`), automatically update `Resident.user_id = new_user.id`.
   - Emit structured audit log notifications for administrator visibility whenever an auto-link occurs.

3. **Visibility & Role-Based Access Control (RBAC)**:
   - **Administration (ADMINISTRATOR / DIRECTOR)**: Full CRUD access to resident profiles across all lots.
   - **Manager (MANAGER)**: Read access to residents across assigned lots.
   - **Lot Residents / Standard Users**: Strictly restricted to viewing co-residents within their own associated lot(s). Attempts to view residents of other lots return `403 Forbidden`.

4. **Backend API & Service Endpoints**:
   - `GET /api/v1/lots/{lot_id}/residents`: List residents for a lot (enforcing lot-level visibility guards).
   - `POST /api/v1/lots/{lot_id}/residents`: Register a new resident profile under a lot.
   - `GET /api/v1/residents/{id}`: Retrieve single resident profile details.
   - `PUT /api/v1/residents/{id}`: Update resident profile metadata.
   - `DELETE /api/v1/residents/{id}`: Soft deactivate resident profile (`is_active = False`).
   - `POST /api/v1/residents/{id}/link-user`: Manually bind a resident profile to a system `User` account.
   - `POST /api/v1/residents/{id}/unlink-user`: Manually remove user account binding (`user_id = None`).
   - Domain exceptions (`ResidentNotFoundError`, `ResidentAlreadyLinkedError`, `ResidentCPFConflictError`) handled in global exception handlers.

5. **Frontend UI & State Management**:
   - Tab subview `ResidentsTab` embedded inside `LotDetailsView.tsx`.
   - Components: `ResidentTable`, `ResidentFormModal`, and `LinkUserAccountModal`.
   - TypeScript interfaces (`src/types/resident.ts`), API client module (`src/api/residents.ts`), and custom hooks (`src/hooks/useResidents.ts`).
   - i18n translation keys in `pt.json` and `en.json`.

6. **Testing & Quality Assurance**:
   - Pytest suite (`backend/tests/test_residents.py`) covering schema validation, CPF check digit validation, auto-linking on signup, manual binding, and strict RBAC isolation (≥ 90% backend coverage).
   - Vitest suite (`frontend/src/features/lot-management/__tests__/ResidentsTab.test.tsx`) covering rendering, form validation, modal state, and RBAC guard rendering (≥ 75% frontend coverage).

---

## Approach

### Data Layer (`backend/app/models/` & `backend/app/schemas/`)

1. **Domain Enum (`backend/app/models/enums.py`)**:
   ```python
   class ResidentRelationship(StrEnum):
       TITULAR = "TITULAR"
       CONJUGE = "CONJUGE"
       FILHO_DEPENDENTE = "FILHO_DEPENDENTE"
       INQUILINO = "INQUILINO"
       PARENTE = "PARENTE"
       OUTRO = "OUTRO"
   ```

2. **SQLModel Entity (`backend/app/models/resident.py`)**:
   ```python
   class Resident(SQLModel, table=True):
       __tablename__ = "resident"

       id: UUID = Field(default_factory=uuid4, primary_key=True)
       lot_id: UUID = Field(foreign_key="lot.id", ondelete="CASCADE", nullable=False, index=True)
       user_id: UUID | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True, index=True)
       full_name: str = Field(nullable=False)
       cpf: str = Field(index=True, nullable=False)
       rg: str | None = Field(default=None)
       birth_date: date | None = Field(default=None)
       phone: str | None = Field(default=None)
       email: str | None = Field(default=None, index=True)
       relationship_type: ResidentRelationship = Field(default=ResidentRelationship.TITULAR, nullable=False)
       is_active: bool = Field(default=True, nullable=False)
       notes: str | None = Field(default=None)
       created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
       updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

       # Relationships
       lot: "Lot" = Relationship(back_populates="residents")
       user: "User | None" = Relationship()
   ```

3. **Pydantic Schemas (`backend/app/schemas/resident.py`)**:
   - `ResidentCreate`: Requires `full_name`, `cpf` (validated via Pydantic validator for Brazilian check digits and format cleaning), optional `rg`, `birth_date`, `phone`, `email`, `relationship_type`, `notes`.
   - `ResidentUpdate`: Optional fields for updating profile attributes.
   - `ResidentRead`: Base response model including all `Resident` table fields.
   - `ResidentDetailRead`: `ResidentRead` with nested `user` summary (`id`, `full_name`, `email`, `role`) and `lot` summary (`id`, `block`, `lot_number`).
   - `LinkUserPayload`: `{ user_id: UUID }`.
   - `PaginatedResidentRead`: `items: list[ResidentRead]`, `total: int`, `skip: int`, `limit: int`.

### Service Layer (`backend/app/services/resident_service.py`)

- `get_residents_by_lot(session, lot_id, current_user, skip, limit)`: Checks visibility rules. Allows request if user is Admin/Director/Manager, or if user is linked to `lot_id` via `UserLotLink` or `Resident.user_id`. Returns paginated list of active residents.
- `create_resident(session, lot_id, resident_in)`: Validates lot existence. Standardizes CPF to numeric string. Checks for duplicate active CPF in the same lot. Creates `Resident` record. Performs immediate auto-match check against existing active `User` records by CPF or email to set `user_id` if found.
- `get_resident_by_id(session, resident_id, current_user)`: Fetches resident by ID, checking lot visibility for standard users. Raises `ResidentNotFoundError` if absent.
- `update_resident(session, db_resident, resident_in, current_user)`: Updates resident fields and `updated_at` timestamp.
- `deactivate_resident(session, db_resident)`: Soft deactivates resident by setting `is_active = False`.
- `link_user(session, resident_id, user_id)`: Verifies target user exists. Sets `Resident.user_id = user_id`.
- `unlink_user(session, resident_id)`: Resets `Resident.user_id = None`.
- `auto_link_user(session, new_user)`: Queries unlinked active `Resident` records (`user_id IS NULL`) where `cpf == clean_cpf(new_user.cpf)` OR `email == new_user.email`. If matched, binds `user_id = new_user.id` and logs an administrative audit notice.

### API & Endpoint Layer (`backend/app/api/v1/endpoints/residents.py`)

- Endpoints:
  - `GET /api/v1/lots/{lot_id}/residents`
  - `POST /api/v1/lots/{lot_id}/residents`
  - `GET /api/v1/residents/{id}`
  - `PUT /api/v1/residents/{id}`
  - `DELETE /api/v1/residents/{id}`
  - `POST /api/v1/residents/{id}/link-user`
  - `POST /api/v1/residents/{id}/unlink-user`
- Signup integration: Update `signup` endpoint in `backend/app/api/v1/endpoints/auth.py` to trigger `ResidentService.auto_link_user(session, db_obj)` post-creation.

### Database Migration

- Alembic revision script creating `resident` table with foreign key constraints (`ON DELETE CASCADE` for lot, `ON DELETE SET NULL` for user), single-column indices on `cpf`, `email`, `lot_id`, and `user_id`.

### Frontend Layer (`frontend/src/features/lot-management/`)

1. **Types & Client**:
   - `frontend/src/types/resident.ts`: TypeScript interfaces for `Resident`, `ResidentRelationship`, `ResidentCreate`, `ResidentUpdate`, `LinkUserPayload`.
   - `frontend/src/api/residents.ts`: Axios API methods.
   - `frontend/src/hooks/useResidents.ts`: TanStack Query hooks (`useLotResidents`, `useResidentDetail`, `useCreateResident`, `useUpdateResident`, `useDeactivateResident`, `useLinkResidentUser`, `useUnlinkResidentUser`).
2. **Components**:
   - `ResidentsTab.tsx`: Rendered inside `LotDetailsView.tsx` as a secondary tab or section ("Moradores").
   - `ResidentTable.tsx`: Displays resident list with columns: Nome, CPF/RG, Grau de Parentesco (badge), Conta de Usuário (linked user tag or "Não Vinculado"), Telefone / E-mail, Status, and Action buttons (Editar, Vincular Conta, Desvincular, Desativar).
   - `ResidentFormModal.tsx`: Dialog form for creating/editing residents with input masking for CPF and phone, datepicker for `birth_date`, select for `relationship_type`, and validation.
   - `LinkUserAccountModal.tsx`: Dialog to search system users by name/email and bind selected user account to the resident profile.
3. **i18n Translation**:
   - Key definitions added under `residents.*` in `pt.json` and `en.json`.

---

## Expected Results

- [ ] Alembic migration script cleanly creates the `resident` table with foreign keys, indexes, and cascades.
- [ ] SQLModel `Resident` model and Pydantic schemas accurately represent all specified fields and relationship enums.
- [ ] CPF validator enforces valid Brazilian check digits and standardizes numeric format.
- [ ] `POST /api/v1/lots/{lot_id}/residents` creates a resident profile tied to the lot and returns `201 Created`.
- [ ] `GET /api/v1/lots/{lot_id}/residents` lists residents of the specified lot for authorized roles.
- [ ] Enforces RBAC visibility: regular residents can list co-residents of their own lot, but receive `403 Forbidden` when requesting residents of a different lot.
- [ ] Auto-linking trigger on `POST /api/v1/auth/signup` binds an unlinked `Resident` profile when new user's CPF or Email matches, logging an admin audit event.
- [ ] `POST /api/v1/residents/{id}/link-user` manually binds a user account to a resident profile for Admin/Director roles.
- [ ] `POST /api/v1/residents/{id}/unlink-user` manually removes user binding (`user_id = None`) without deleting the resident record.
- [ ] `DELETE /api/v1/residents/{id}` deactivates resident (`is_active = False`) without physically purging history.
- [ ] Frontend `LotDetailsView.tsx` includes `ResidentsTab` displaying `ResidentTable`, resident creation button, and user binding options.
- [ ] `ResidentFormModal` handles creation and editing with field validation and masked inputs.
- [ ] `LinkUserAccountModal` allows searching users and linking account to resident profile with immediate UI table updates.
- [ ] Full internationalization keys provided in `pt.json` and `en.json`.
- [ ] Pytest test suite in `backend/tests/test_residents.py` passes with ≥ 90% code coverage.
- [ ] Vitest test suite in `frontend/src/features/lot-management/__tests__/` passes with ≥ 75% code coverage.

---

## Out of Scope

- Photo capture or file attachment service for resident avatars (handled in task T004).
- Visitor pre-authorizations or Portaria access log entries tied to residents (handled in task T003).
- Automatic creation of system `User` credentials upon registering a `Resident`.
- CSV/Excel bulk import of resident records.
