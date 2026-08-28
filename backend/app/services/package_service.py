"""Package (encomendas) service layer handling business logic and authorization checks."""

from datetime import datetime
from uuid import UUID

from sqlmodel import Session, func, select

from app.core.exceptions import (
    LotNotFoundError,
    PackageAccessForbiddenError,
    PackageAlreadyPickedUpError,
    PackageNotFoundError,
)
from app.models.enums import PackageStatus, UserRole
from app.models.lot import Lot
from app.models.package import Package
from app.models.user import User
from app.schemas.package import (
    LotSummaryRead,
    PackageCreate,
    PackagePickup,
    PackageRead,
)
from app.services.visitor_service import VisitorService


class PackageService:
    """Service class for Package domain operations."""

    _GATEKEEPER_ROLES = (
        UserRole.ADMINISTRATOR,
        UserRole.DIRECTOR,
        UserRole.MANAGER,
        UserRole.PORTEIRO,
    )

    @staticmethod
    def _build_package_read(session: Session, package: Package) -> PackageRead:
        """Helper to convert Package model into sanitized PackageRead schema."""
        lot_summary = None
        lot = session.get(Lot, package.lot_id)
        if lot:
            lot_summary = LotSummaryRead(
                id=lot.id, block=lot.block, lot_number=lot.lot_number
            )

        received_by_name = None
        if package.received_by_id:
            received_by = session.get(User, package.received_by_id)
            if received_by:
                received_by_name = received_by.full_name or received_by.email

        picked_up_by_name = None
        if package.picked_up_by_id:
            picked_up_by = session.get(User, package.picked_up_by_id)
            if picked_up_by:
                picked_up_by_name = picked_up_by.full_name or picked_up_by.email

        return PackageRead(
            id=package.id,
            lot_id=package.lot_id,
            lot_summary=lot_summary,
            received_by_id=package.received_by_id,
            received_by_name=received_by_name,
            description=package.description,
            carrier=package.carrier,
            received_at=package.received_at,
            status=package.status,
            picked_up_at=package.picked_up_at,
            picked_up_by_id=package.picked_up_by_id,
            picked_up_by_name=picked_up_by_name,
            picked_up_by_notes=package.picked_up_by_notes,
        )

    @staticmethod
    def _assert_gatekeeper_role(current_user: User) -> None:
        """Raise unless current_user holds a gatekeeper-desk role."""
        if current_user.role not in PackageService._GATEKEEPER_ROLES:
            raise PackageAccessForbiddenError(
                "Apenas administradores, diretores, gerentes e porteiros podem registrar encomendas."
            )

    @staticmethod
    def _assert_lot_access(session: Session, lot_id: UUID, current_user: User) -> None:
        """Gatekeeper roles: unrestricted. GUEST: always denied. Everyone else: must be linked to lot_id."""
        if current_user.role in PackageService._GATEKEEPER_ROLES:
            return
        if current_user.role == UserRole.GUEST:
            # Explicit reject before the linked-lots lookup below: GUEST accounts are not
            # barred from having a UserLotLink/Resident row at the data-model level (see
            # backend/app/services/visitor_service.py and
            # backend/app/services/lot_service.py's link_user — neither prevents a
            # GUEST-role user from being linked to a lot), so relying on
            # get_user_linked_lot_ids alone would silently grant a linked GUEST access.
            # GUEST must never see or act on package data regardless of any lot linkage
            # it happens to have.
            raise PackageAccessForbiddenError()
        linked_lot_ids = VisitorService.get_user_linked_lot_ids(session, current_user)
        if lot_id not in linked_lot_ids:
            raise PackageAccessForbiddenError()

    @classmethod
    def create_package(
        cls, session: Session, current_user: User, package_in: PackageCreate
    ) -> PackageRead:
        """Log a new package's arrival for a lot."""
        cls._assert_gatekeeper_role(current_user)
        lot = session.get(Lot, package_in.lot_id)
        if not lot:
            raise LotNotFoundError(package_in.lot_id)
        package = Package(
            lot_id=package_in.lot_id,
            received_by_id=current_user.id,
            description=package_in.description,
            carrier=package_in.carrier,
            received_at=datetime.utcnow(),
            status=PackageStatus.AWAITING_PICKUP,
        )
        session.add(package)
        session.commit()
        session.refresh(package)
        return cls._build_package_read(session, package)

    @classmethod
    def get_packages_for_lot(
        cls,
        session: Session,
        current_user: User,
        lot_id: UUID,
        status: PackageStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[PackageRead], int]:
        """List packages for a specific lot, if caller has access to it."""
        cls._assert_lot_access(session, lot_id, current_user)

        query = select(Package).where(Package.lot_id == lot_id)
        if status:
            query = query.where(Package.status == status)

        total = session.exec(select(func.count()).select_from(query.subquery())).one()
        query = query.order_by(Package.received_at.desc()).offset(skip).limit(limit)  # type: ignore[attr-defined]
        packages = session.exec(query).all()

        items = [cls._build_package_read(session, pkg) for pkg in packages]
        return items, total

    @classmethod
    def get_awaiting_pickup_queue(
        cls,
        session: Session,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[PackageRead], int]:
        """List all AWAITING_PICKUP packages across lots (gatekeeper queue)."""
        cls._assert_gatekeeper_role(current_user)

        query = select(Package).where(Package.status == PackageStatus.AWAITING_PICKUP)
        total = session.exec(select(func.count()).select_from(query.subquery())).one()
        query = query.order_by(Package.received_at.asc()).offset(skip).limit(limit)  # type: ignore[attr-defined]
        packages = session.exec(query).all()

        items = [cls._build_package_read(session, pkg) for pkg in packages]
        return items, total

    @classmethod
    def get_package_by_id(
        cls, session: Session, current_user: User, package_id: UUID
    ) -> PackageRead:
        """Retrieve a single package by ID if the caller has access to its lot."""
        package = session.get(Package, package_id)
        if not package:
            raise PackageNotFoundError(package_id)
        cls._assert_lot_access(session, package.lot_id, current_user)
        return cls._build_package_read(session, package)

    @classmethod
    def mark_picked_up(
        cls,
        session: Session,
        current_user: User,
        package_id: UUID,
        pickup_in: PackagePickup,
    ) -> PackageRead:
        """Mark a package as picked up (terminal, one-way transition)."""
        package = session.get(Package, package_id)
        if not package:
            raise PackageNotFoundError(package_id)
        cls._assert_lot_access(session, package.lot_id, current_user)
        if package.status == PackageStatus.PICKED_UP:
            raise PackageAlreadyPickedUpError()
        package.status = PackageStatus.PICKED_UP
        package.picked_up_at = datetime.utcnow()
        package.picked_up_by_id = current_user.id
        package.picked_up_by_notes = pickup_in.picked_up_by_notes
        session.add(package)
        session.commit()
        session.refresh(package)
        return cls._build_package_read(session, package)

    @classmethod
    def get_my_lots(cls, session: Session, current_user: User) -> list[LotSummaryRead]:
        """Return the caller's own linked lots (non-gatekeeper, non-GUEST callers)."""
        if current_user.role in PackageService._GATEKEEPER_ROLES:
            raise PackageAccessForbiddenError(
                "Use /packages/queue para ver encomendas de todos os lotes."
            )
        if current_user.role == UserRole.GUEST:
            raise PackageAccessForbiddenError()
        lot_ids = VisitorService.get_user_linked_lot_ids(session, current_user)
        if not lot_ids:
            return []
        lots = session.exec(select(Lot).where(Lot.id.in_(lot_ids))).all()  # type: ignore[attr-defined]
        return [
            LotSummaryRead(id=lot.id, block=lot.block, lot_number=lot.lot_number)
            for lot in lots
        ]
