"""Service layer for Asset and InventoryMovement business logic."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.core.exceptions import (
    AssetAccessForbiddenError,
    AssetNotFoundError,
    AssetTagAlreadyExistsError,
    InsufficientStockError,
)
from app.models.asset import Asset, InventoryMovement
from app.models.enums import AssetCategory, AssetCondition, MovementType, UserRole
from app.models.user import User
from app.schemas.asset import (
    AssetCreate,
    AssetDetailRead,
    AssetRead,
    AssetSummaryRead,
    AssetUpdate,
    InventoryMovementCreate,
    InventoryMovementRead,
    PaginatedAssetRead,
    PaginatedInventoryMovementRead,
)

_STAFF_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR}
_VIEW_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER}


class AssetService:
    """Service class for Asset and Inventory operations."""

    @staticmethod
    def create_asset(
        session: Session, current_user: User, asset_in: AssetCreate
    ) -> AssetRead:
        """Create a new asset or inventory item."""
        if current_user.role not in _STAFF_ROLES:
            raise AssetAccessForbiddenError(
                "Apenas Administradores e Diretores podem cadastrar ativos."
            )

        if asset_in.asset_tag:
            existing = session.exec(
                select(Asset).where(Asset.asset_tag == asset_in.asset_tag)
            ).first()
            if existing:
                raise AssetTagAlreadyExistsError(asset_in.asset_tag)

        now = datetime.now(UTC)
        asset_data = asset_in.model_dump()
        asset = Asset(
            **asset_data,
            created_at=now,
            updated_at=now,
        )
        session.add(asset)
        session.flush()

        if asset.current_quantity > 0:
            movement = InventoryMovement(
                asset_id=asset.id,
                movement_type=MovementType.ENTRADA,
                quantity=asset.current_quantity,
                previous_quantity=0,
                new_quantity=asset.current_quantity,
                performed_by_id=current_user.id,
                reason="Cadastro inicial do ativo/estoque",
                created_at=now,
            )
            session.add(movement)

        session.commit()
        session.refresh(asset)
        return AssetRead.model_validate(asset)

    @staticmethod
    def list_assets(
        session: Session,
        current_user: User,
        category: AssetCategory | None = None,
        location: str | None = None,
        is_consumable: bool | None = None,
        condition: AssetCondition | None = None,
        search: str | None = None,
        low_stock_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> PaginatedAssetRead:
        """List assets with filtering, searching, and pagination."""
        if current_user.role not in _VIEW_ROLES:
            raise AssetAccessForbiddenError("Acesso ao patrimônio e estoque negado.")

        statement = select(Asset)

        if category:
            statement = statement.where(Asset.category == category)
        if location:
            statement = statement.where(Asset.location.ilike(f"%{location}%"))
        if is_consumable is not None:
            statement = statement.where(Asset.is_consumable == is_consumable)
        if condition:
            statement = statement.where(Asset.condition == condition)
        if low_stock_only:
            statement = statement.where(
                Asset.is_consumable.is_(True),
                Asset.min_quantity.is_not(None),
                Asset.current_quantity <= Asset.min_quantity,
            )
        if search:
            search_pattern = f"%{search}%"
            statement = statement.where(
                or_(
                    Asset.name.ilike(search_pattern),
                    Asset.serial_number.ilike(search_pattern),
                    Asset.asset_tag.ilike(search_pattern),
                    Asset.location.ilike(search_pattern),
                )
            )

        # Count total
        count_statement = select(func.count()).select_from(statement.subquery())
        total = session.exec(count_statement).one()

        # Paginated results
        statement = statement.order_by(Asset.name.asc()).offset(skip).limit(limit)
        items = session.exec(statement).all()

        return PaginatedAssetRead(
            items=[AssetRead.model_validate(a) for a in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_asset_summary(session: Session, current_user: User) -> AssetSummaryRead:
        """Compute aggregate metrics for assets and inventory."""
        if current_user.role not in _VIEW_ROLES:
            raise AssetAccessForbiddenError("Acesso ao patrimônio e estoque negado.")

        all_assets = session.exec(select(Asset)).all()
        total_assets = sum(1 for a in all_assets if not a.is_consumable)
        total_consumables = sum(1 for a in all_assets if a.is_consumable)
        low_stock_count = sum(
            1
            for a in all_assets
            if a.is_consumable
            and a.min_quantity is not None
            and a.current_quantity <= a.min_quantity
        )
        total_patrimonial_value = sum(
            (a.acquisition_value or 0.0)
            for a in all_assets
            if not a.is_consumable and a.condition != AssetCondition.BAIXADO
        )

        return AssetSummaryRead(
            total_assets=total_assets,
            total_consumables=total_consumables,
            low_stock_count=low_stock_count,
            total_patrimonial_value=round(total_patrimonial_value, 2),
        )

    @staticmethod
    def get_asset_by_id(
        session: Session, current_user: User, asset_id: UUID
    ) -> AssetDetailRead:
        """Retrieve detailed asset information with movements."""
        if current_user.role not in _VIEW_ROLES:
            raise AssetAccessForbiddenError("Acesso ao patrimônio e estoque negado.")

        asset = session.get(Asset, asset_id)
        if not asset:
            raise AssetNotFoundError(asset_id)

        # Retrieve movements sorted by created_at desc with performer info
        movements_statement = (
            select(InventoryMovement, User.full_name, User.email)
            .join(User, InventoryMovement.performed_by_id == User.id, isouter=True)
            .where(InventoryMovement.asset_id == asset_id)
            .order_by(InventoryMovement.created_at.desc())
        )
        movement_rows = session.exec(movements_statement).all()

        movement_reads = [
            InventoryMovementRead(
                id=m.id,
                asset_id=m.asset_id,
                movement_type=m.movement_type,
                quantity=m.quantity,
                previous_quantity=m.previous_quantity,
                new_quantity=m.new_quantity,
                performed_by_id=m.performed_by_id,
                performed_by_name=full_name or email,
                asset_name=asset.name,
                reason=m.reason,
                document_number=m.document_number,
                created_at=m.created_at,
            )
            for m, full_name, email in movement_rows
        ]

        asset_read = AssetRead.model_validate(asset)
        return AssetDetailRead(
            **asset_read.model_dump(),
            movements=movement_reads,
        )

    @staticmethod
    def update_asset(
        session: Session,
        current_user: User,
        asset_id: UUID,
        asset_in: AssetUpdate,
    ) -> AssetRead:
        """Update metadata of an existing asset."""
        if current_user.role not in _STAFF_ROLES:
            raise AssetAccessForbiddenError(
                "Apenas Administradores e Diretores podem atualizar ativos."
            )

        asset = session.get(Asset, asset_id)
        if not asset:
            raise AssetNotFoundError(asset_id)

        if asset_in.asset_tag and asset_in.asset_tag != asset.asset_tag:
            existing = session.exec(
                select(Asset).where(
                    Asset.asset_tag == asset_in.asset_tag, Asset.id != asset_id
                )
            ).first()
            if existing:
                raise AssetTagAlreadyExistsError(asset_in.asset_tag)

        update_data = asset_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(asset, key, value)

        asset.updated_at = datetime.now(UTC)
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return AssetRead.model_validate(asset)

    @staticmethod
    def delete_asset(
        session: Session, current_user: User, asset_id: UUID
    ) -> None:
        """Delete an asset and cascade its movements."""
        if current_user.role not in _STAFF_ROLES:
            raise AssetAccessForbiddenError(
                "Apenas Administradores e Diretores podem excluir ativos."
            )

        asset = session.get(Asset, asset_id)
        if not asset:
            raise AssetNotFoundError(asset_id)

        session.delete(asset)
        session.commit()

    @staticmethod
    def record_movement(
        session: Session,
        current_user: User,
        asset_id: UUID,
        movement_in: InventoryMovementCreate,
    ) -> InventoryMovementRead:
        """Record an inventory or asset stock movement."""
        if current_user.role not in _VIEW_ROLES:
            raise AssetAccessForbiddenError("Acesso negado.")

        if current_user.role == UserRole.MANAGER and movement_in.movement_type in {
            MovementType.AJUSTE_INVENTARIO,
            MovementType.BAIXA_PATRIMONIAL,
        }:
            raise AssetAccessForbiddenError(
                "Gerentes só podem registrar entradas e saídas de estoque."
            )

        asset = session.get(Asset, asset_id)
        if not asset:
            raise AssetNotFoundError(asset_id)

        previous_quantity = asset.current_quantity

        if movement_in.movement_type == MovementType.ENTRADA:
            new_quantity = asset.current_quantity + movement_in.quantity
        elif movement_in.movement_type == MovementType.SAIDA:
            if movement_in.quantity > asset.current_quantity:
                raise InsufficientStockError(
                    f"Saldo insuficiente em estoque. "
                    f"Disponível: {asset.current_quantity}, "
                    f"solicitado: {movement_in.quantity}."
                )
            new_quantity = asset.current_quantity - movement_in.quantity
        elif movement_in.movement_type == MovementType.AJUSTE_INVENTARIO:
            new_quantity = movement_in.quantity
        elif movement_in.movement_type == MovementType.BAIXA_PATRIMONIAL:
            new_quantity = max(0, asset.current_quantity - movement_in.quantity)
            asset.condition = AssetCondition.BAIXADO
        else:
            new_quantity = asset.current_quantity

        now = datetime.now(UTC)
        asset.current_quantity = new_quantity
        asset.updated_at = now
        session.add(asset)

        movement = InventoryMovement(
            asset_id=asset.id,
            movement_type=movement_in.movement_type,
            quantity=movement_in.quantity,
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            performed_by_id=current_user.id,
            reason=movement_in.reason,
            document_number=movement_in.document_number,
            created_at=now,
        )
        session.add(movement)
        session.commit()
        session.refresh(movement)

        performer_name = current_user.full_name or current_user.email
        return InventoryMovementRead(
            id=movement.id,
            asset_id=movement.asset_id,
            movement_type=movement.movement_type,
            quantity=movement.quantity,
            previous_quantity=movement.previous_quantity,
            new_quantity=movement.new_quantity,
            performed_by_id=movement.performed_by_id,
            performed_by_name=performer_name,
            asset_name=asset.name,
            reason=movement.reason,
            document_number=movement.document_number,
            created_at=movement.created_at,
        )

    @staticmethod
    def list_inventory_movements(
        session: Session,
        current_user: User,
        asset_id: UUID | None = None,
        movement_type: MovementType | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> PaginatedInventoryMovementRead:
        """List inventory movements across all assets with filtering."""
        if current_user.role not in _VIEW_ROLES:
            raise AssetAccessForbiddenError("Acesso negado.")

        statement = (
            select(
                InventoryMovement,
                Asset.name.label("asset_name"),
                User.full_name.label("user_full_name"),
                User.email.label("user_email"),
            )
            .join(Asset, InventoryMovement.asset_id == Asset.id)
            .join(User, InventoryMovement.performed_by_id == User.id, isouter=True)
        )

        if asset_id:
            statement = statement.where(InventoryMovement.asset_id == asset_id)
        if movement_type:
            statement = statement.where(
                InventoryMovement.movement_type == movement_type
            )

        count_statement = select(func.count()).select_from(
            select(InventoryMovement.id)
            .where(
                *(
                    [InventoryMovement.asset_id == asset_id]
                    if asset_id
                    else []
                ),
                *(
                    [InventoryMovement.movement_type == movement_type]
                    if movement_type
                    else []
                ),
            )
            .subquery()
        )
        total = session.exec(count_statement).one()

        statement = (
            statement.order_by(InventoryMovement.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        rows = session.exec(statement).all()

        items = [
            InventoryMovementRead(
                id=m.id,
                asset_id=m.asset_id,
                movement_type=m.movement_type,
                quantity=m.quantity,
                previous_quantity=m.previous_quantity,
                new_quantity=m.new_quantity,
                performed_by_id=m.performed_by_id,
                performed_by_name=full_name or email,
                asset_name=asset_name,
                reason=m.reason,
                document_number=m.document_number,
                created_at=m.created_at,
            )
            for m, asset_name, full_name, email in rows
        ]

        return PaginatedInventoryMovementRead(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
        )
