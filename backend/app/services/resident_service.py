"""Service layer for Resident management."""

from datetime import datetime
import logging
from uuid import UUID

from app.core.exceptions import (
    DomainError,
    ForbiddenError,
    ResidentAlreadyLinkedError,
    ResidentCPFConflictError,
    ResidentNotFoundError,
)
from app.models.enums import UserRole
from app.models.lot import UserLotLink
from app.models.resident import Resident
from app.models.user import User
from app.schemas.resident import ResidentCreate, ResidentUpdate
from app.services.lot_service import LotService
from sqlmodel import Session, select, func

logger = logging.getLogger(__name__)


class ResidentService:
    @staticmethod
    def _check_lot_access(session: Session, lot_id: UUID, current_user: User) -> None:
        """Check if current user is allowed to access residents of lot_id."""
        if current_user.role in (
            UserRole.ADMINISTRATOR,
            UserRole.DIRECTOR,
            UserRole.MANAGER,
        ):
            return

        # Check if user is linked to lot via UserLotLink
        user_lot_link = session.exec(
            select(UserLotLink).where(
                UserLotLink.user_id == current_user.id,
                UserLotLink.lot_id == lot_id,
            )
        ).first()

        if user_lot_link:
            return

        # Check if user is linked to lot via Resident table
        resident_link = session.exec(
            select(Resident).where(
                Resident.user_id == current_user.id,
                Resident.lot_id == lot_id,
                Resident.is_active == True,  # noqa: E712
            )
        ).first()

        if resident_link:
            return

        raise ForbiddenError("You do not have access to view residents for this lot")

    @staticmethod
    def get_residents_by_lot(
        session: Session,
        lot_id: UUID,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Resident], int]:
        LotService.get_lot_by_id(session, lot_id)
        ResidentService._check_lot_access(session, lot_id, current_user)

        query = select(Resident).where(
            Resident.lot_id == lot_id,
            Resident.is_active == True,  # noqa: E712
        )
        total = session.exec(
            select(func.count()).select_from(query.subquery())
        ).one()

        residents = session.exec(
            query.offset(skip).limit(limit).order_by(Resident.full_name)
        ).all()

        return list(residents), total

    @staticmethod
    def create_resident(
        session: Session, lot_id: UUID, resident_in: ResidentCreate
    ) -> Resident:
        LotService.get_lot_by_id(session, lot_id)

        # Check for existing active resident with same CPF in this lot
        existing = session.exec(
            select(Resident).where(
                Resident.lot_id == lot_id,
                Resident.cpf == resident_in.cpf,
                Resident.is_active == True,  # noqa: E712
            )
        ).first()
        if existing:
            raise ResidentCPFConflictError(resident_in.cpf)

        # Auto-match with existing User by CPF or Email
        user_id = None
        matched_user = session.exec(
            select(User).where(
                (User.cpf == resident_in.cpf)
                | (
                    (User.email == resident_in.email)
                    if resident_in.email
                    else False
                )
            )
        ).first()
        if matched_user:
            user_id = matched_user.id

        resident = Resident(
            lot_id=lot_id,
            user_id=user_id,
            full_name=resident_in.full_name,
            cpf=resident_in.cpf,
            rg=resident_in.rg,
            birth_date=resident_in.birth_date,
            phone=resident_in.phone,
            email=resident_in.email,
            relationship_type=resident_in.relationship_type,
            notes=resident_in.notes,
        )
        session.add(resident)
        session.commit()
        session.refresh(resident)
        return resident

    @staticmethod
    def get_resident_by_id(
        session: Session, resident_id: UUID, current_user: User
    ) -> Resident:
        resident = session.exec(
            select(Resident).where(
                Resident.id == resident_id,
                Resident.is_active == True,  # noqa: E712
            )
        ).first()
        if not resident:
            raise ResidentNotFoundError(resident_id)

        ResidentService._check_lot_access(session, resident.lot_id, current_user)
        return resident

    @staticmethod
    def update_resident(
        session: Session,
        db_resident: Resident,
        resident_in: ResidentUpdate,
        current_user: User,
    ) -> Resident:
        ResidentService._check_lot_access(session, db_resident.lot_id, current_user)

        if resident_in.cpf and resident_in.cpf != db_resident.cpf:
            existing = session.exec(
                select(Resident).where(
                    Resident.lot_id == db_resident.lot_id,
                    Resident.cpf == resident_in.cpf,
                    Resident.is_active == True,  # noqa: E712
                    Resident.id != db_resident.id,
                )
            ).first()
            if existing:
                raise ResidentCPFConflictError(resident_in.cpf)

        update_data = resident_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_resident, key, value)

        db_resident.updated_at = datetime.utcnow()
        session.add(db_resident)
        session.commit()
        session.refresh(db_resident)
        return db_resident

    @staticmethod
    def deactivate_resident(session: Session, db_resident: Resident) -> Resident:
        db_resident.is_active = False
        db_resident.updated_at = datetime.utcnow()
        session.add(db_resident)
        session.commit()
        session.refresh(db_resident)
        return db_resident

    @staticmethod
    def link_user(
        session: Session, resident_id: UUID, user_id: UUID
    ) -> Resident:
        resident = session.exec(
            select(Resident).where(
                Resident.id == resident_id,
                Resident.is_active == True,  # noqa: E712
            )
        ).first()
        if not resident:
            raise ResidentNotFoundError(resident_id)

        user = session.get(User, user_id)
        if not user:
            raise DomainError(f"User with ID {user_id} not found")

        if resident.user_id == user_id:
            raise ResidentAlreadyLinkedError()

        resident.user_id = user_id
        resident.updated_at = datetime.utcnow()
        session.add(resident)
        session.commit()
        session.refresh(resident)
        return resident

    @staticmethod
    def unlink_user(session: Session, resident_id: UUID) -> Resident:
        resident = session.exec(
            select(Resident).where(
                Resident.id == resident_id,
                Resident.is_active == True,  # noqa: E712
            )
        ).first()
        if not resident:
            raise ResidentNotFoundError(resident_id)

        resident.user_id = None
        resident.updated_at = datetime.utcnow()
        session.add(resident)
        session.commit()
        session.refresh(resident)
        return resident

    @staticmethod
    def auto_link_user(session: Session, new_user: User) -> int:
        """Find unlinked Resident records matching CPF or Email of new_user and bind user_id."""
        matching_residents = session.exec(
            select(Resident).where(
                Resident.user_id.is_(None),  # type: ignore[attr-defined]
                Resident.is_active == True,  # noqa: E712
                (Resident.cpf == new_user.cpf)
                | (
                    (Resident.email == new_user.email)
                    if new_user.email
                    else False
                ),
            )
        ).all()

        linked_count = 0
        for resident in matching_residents:
            resident.user_id = new_user.id
            resident.updated_at = datetime.utcnow()
            session.add(resident)
            linked_count += 1
            logger.info(
                f"[Audit Log] Auto-linked Resident '{resident.full_name}' ({resident.id}) to new User ({new_user.id})"
            )

        if linked_count > 0:
            session.commit()

        return linked_count
