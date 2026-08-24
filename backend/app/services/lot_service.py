"""Service layer for Lot and UserLotLink management."""

from datetime import datetime
from uuid import UUID

from app.core.exceptions import (
    DomainError,
    LotAlreadyExistsError,
    LotNotFoundError,
    UserLotLinkAlreadyExistsError,
    UserLotLinkNotFoundError,
)
from app.models.enums import LotStatus
from app.models.lot import Lot, UserLotLink
from app.models.user import User
from app.schemas.lot import (
    LotCreate,
    LotDetailRead,
    LotRead,
    LotUpdate,
    UserLotLinkCreate,
    UserLotLinkRead,
    UserSummaryRead,
)
from sqlalchemy import func
from sqlmodel import Session, select


class LotService:
    """Service handling business logic for lots and user assignments."""

    @staticmethod
    def get_lots(
        session: Session,
        block: str | None = None,
        status: LotStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Lot], int]:
        """List active lots with optional filtering and pagination."""
        query = select(Lot).where(Lot.is_deleted == False)

        if block:
            query = query.where(Lot.block == block)
        if status:
            query = query.where(Lot.status == status)

        # Count total matching records
        count_query = select(func.count()).select_from(query.subquery())
        total = session.exec(count_query).one()

        # Paginated items
        items_query = query.order_by(Lot.block, Lot.lot_number).offset(skip).limit(limit)
        items = list(session.exec(items_query).all())

        return items, total

    @staticmethod
    def create_lot(session: Session, lot_in: LotCreate) -> Lot:
        """Create a new lot ensuring block and lot_number uniqueness."""
        existing = session.exec(
            select(Lot).where(
                Lot.block == lot_in.block,
                Lot.lot_number == lot_in.lot_number,
                Lot.is_deleted == False,
            )
        ).first()

        if existing:
            raise LotAlreadyExistsError(block=lot_in.block, lot_number=lot_in.lot_number)

        db_lot = Lot.model_validate(lot_in)
        now = datetime.utcnow()
        db_lot.created_at = now
        db_lot.updated_at = now

        session.add(db_lot)
        session.commit()
        session.refresh(db_lot)
        return db_lot

    @staticmethod
    def get_lot_by_id(session: Session, lot_id: UUID) -> Lot:
        """Retrieve an active lot by ID."""
        lot = session.exec(
            select(Lot).where(Lot.id == lot_id, Lot.is_deleted == False)
        ).first()

        if not lot:
            raise LotNotFoundError(lot_id=lot_id)

        return lot

    @staticmethod
    def get_lot_detail(session: Session, lot_id: UUID) -> LotDetailRead:
        """Retrieve detailed lot info with linked users."""
        lot = LotService.get_lot_by_id(session, lot_id)

        links = session.exec(
            select(UserLotLink).where(UserLotLink.lot_id == lot_id)
        ).all()

        user_link_reads: list[UserLotLinkRead] = []
        for link in links:
            user = session.get(User, link.user_id)
            if user:
                user_summary = UserSummaryRead(
                    id=user.id,
                    full_name=user.full_name,
                    email=user.email,
                    role=user.role,
                )
                user_link_reads.append(
                    UserLotLinkRead(
                        id=link.id,
                        user_id=link.user_id,
                        lot_id=link.lot_id,
                        association_type=link.association_type,
                        is_primary=link.is_primary,
                        start_date=link.start_date,
                        end_date=link.end_date,
                        created_at=link.created_at,
                        user=user_summary,
                    )
                )

        lot_read = LotRead.model_validate(lot)
        return LotDetailRead(
            **lot_read.model_dump(),
            users=user_link_reads,
        )

    @staticmethod
    def update_lot(session: Session, db_lot: Lot, lot_in: LotUpdate) -> Lot:
        """Update lot attributes."""
        update_data = lot_in.model_dump(exclude_unset=True)

        new_block = update_data.get("block", db_lot.block)
        new_lot_number = update_data.get("lot_number", db_lot.lot_number)

        if new_block != db_lot.block or new_lot_number != db_lot.lot_number:
            existing = session.exec(
                select(Lot).where(
                    Lot.block == new_block,
                    Lot.lot_number == new_lot_number,
                    Lot.id != db_lot.id,
                    Lot.is_deleted == False,
                )
            ).first()
            if existing:
                raise LotAlreadyExistsError(block=new_block, lot_number=new_lot_number)

        for key, value in update_data.items():
            setattr(db_lot, key, value)

        db_lot.updated_at = datetime.utcnow()
        session.add(db_lot)
        session.commit()
        session.refresh(db_lot)
        return db_lot

    @staticmethod
    def delete_lot(session: Session, db_lot: Lot) -> Lot:
        """Soft-delete a lot."""
        db_lot.is_deleted = True
        db_lot.updated_at = datetime.utcnow()
        session.add(db_lot)
        session.commit()
        session.refresh(db_lot)
        return db_lot

    @staticmethod
    def link_user(session: Session, lot_id: UUID, link_in: UserLotLinkCreate) -> UserLotLink:
        """Link a user to a lot."""
        db_lot = LotService.get_lot_by_id(session, lot_id)

        user = session.get(User, link_in.user_id)
        if not user:
            raise DomainError(f"User with ID {link_in.user_id} not found")

        existing_link = session.exec(
            select(UserLotLink).where(
                UserLotLink.user_id == link_in.user_id,
                UserLotLink.lot_id == lot_id,
            )
        ).first()

        if existing_link:
            raise UserLotLinkAlreadyExistsError(user_id=link_in.user_id, lot_id=lot_id)

        db_link = UserLotLink(
            user_id=link_in.user_id,
            lot_id=lot_id,
            association_type=link_in.association_type,
            is_primary=link_in.is_primary,
            start_date=link_in.start_date,
            end_date=link_in.end_date,
            created_at=datetime.utcnow(),
        )
        session.add(db_link)

        # Auto-update status to OCCUPIED if lot was VACANT
        if db_lot.status == LotStatus.VACANT:
            db_lot.status = LotStatus.OCCUPIED
            db_lot.updated_at = datetime.utcnow()
            session.add(db_lot)

        session.commit()
        session.refresh(db_link)
        return db_link

    @staticmethod
    def unlink_user(session: Session, lot_id: UUID, user_id: UUID) -> None:
        """Unlink a user from a lot."""
        db_lot = LotService.get_lot_by_id(session, lot_id)

        link = session.exec(
            select(UserLotLink).where(
                UserLotLink.lot_id == lot_id,
                UserLotLink.user_id == user_id,
            )
        ).first()

        if not link:
            raise UserLotLinkNotFoundError(user_id=user_id, lot_id=lot_id)

        session.delete(link)
        session.flush()

        # Check remaining user links for this lot
        remaining_count = session.exec(
            select(func.count()).select_from(
                select(UserLotLink).where(UserLotLink.lot_id == lot_id).subquery()
            )
        ).one()

        if remaining_count == 0 and db_lot.status == LotStatus.OCCUPIED:
            db_lot.status = LotStatus.VACANT
            db_lot.updated_at = datetime.utcnow()
            session.add(db_lot)

        session.commit()
