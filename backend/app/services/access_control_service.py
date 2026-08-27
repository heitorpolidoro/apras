"""Service layer for AccessDevice, FacialTemplate, and FacialAccessEvent management."""

import secrets
from datetime import datetime
from uuid import UUID

from sqlmodel import Session, func, select

from app.core.exceptions import (
    AccessDeviceNotFoundError,
    DuplicateDeviceNameError,
    ForbiddenError,
    InvalidDeviceKeyError,
    NoApprovedPhotoError,
    ResidentNotFoundError,
)
from app.models.access_control import AccessDevice, FacialAccessEvent, FacialTemplate
from app.models.enums import (
    AccessDeviceStatus,
    EntityType,
    FacialTemplateSyncStatus,
    PhotoApprovalStatus,
    UserRole,
)
from app.models.media_asset import MediaAsset
from app.models.resident import Resident
from app.models.user import User
from app.schemas.access_control import (
    AccessDeviceCreate,
    AccessDeviceStatusUpdate,
    FacialVerificationWebhookIn,
)


def _assert_admin_or_director(current_user: User) -> None:
    if current_user.role not in (UserRole.ADMINISTRATOR, UserRole.DIRECTOR):
        raise ForbiddenError("Only Administrators and Directors can manage access control devices")


def _assert_admin_director_or_manager(current_user: User) -> None:
    if current_user.role not in (UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER):
        raise ForbiddenError("Only Administrators, Directors, and Managers can view access control data")


class AccessControlService:
    """Business logic for access devices, facial templates, and verification events."""

    # -------------------------------------------------------------------------
    # Device Management
    # -------------------------------------------------------------------------

    @staticmethod
    def create_device(
        session: Session, device_in: AccessDeviceCreate, current_user: User
    ) -> AccessDevice:
        """Register a new access-control device with a server-generated secret key."""
        _assert_admin_or_director(current_user)

        existing = session.exec(
            select(AccessDevice).where(AccessDevice.name == device_in.name)
        ).first()
        if existing:
            raise DuplicateDeviceNameError(device_in.name)

        device = AccessDevice(
            name=device_in.name,
            location=device_in.location,
            device_key=secrets.token_urlsafe(32),
            status=AccessDeviceStatus.OFFLINE,
            created_by_id=current_user.id,
        )
        session.add(device)
        session.commit()
        session.refresh(device)
        return device

    @staticmethod
    def list_devices(session: Session, current_user: User) -> list[AccessDevice]:
        """List all registered access-control devices."""
        _assert_admin_director_or_manager(current_user)
        devices = session.exec(select(AccessDevice).order_by(AccessDevice.name)).all()
        return list(devices)

    @staticmethod
    def get_device_by_id(session: Session, device_id: UUID) -> AccessDevice:
        """Get a device by ID or raise AccessDeviceNotFoundError."""
        device = session.get(AccessDevice, device_id)
        if not device:
            raise AccessDeviceNotFoundError(device_id)
        return device

    @staticmethod
    def update_device_status(
        session: Session,
        device_id: UUID,
        status_in: AccessDeviceStatusUpdate,
        current_user: User,
    ) -> AccessDevice:
        """Manually update a device's status."""
        _assert_admin_or_director(current_user)
        device = AccessControlService.get_device_by_id(session, device_id)
        device.status = status_in.status
        device.updated_at = datetime.utcnow()
        session.add(device)
        session.commit()
        session.refresh(device)
        return device

    @staticmethod
    def regenerate_device_key(
        session: Session, device_id: UUID, current_user: User
    ) -> AccessDevice:
        """Rotate a device's secret key."""
        _assert_admin_or_director(current_user)
        device = AccessControlService.get_device_by_id(session, device_id)
        device.device_key = secrets.token_urlsafe(32)
        device.updated_at = datetime.utcnow()
        session.add(device)
        session.commit()
        session.refresh(device)
        return device

    # -------------------------------------------------------------------------
    # Facial Template Sync
    # -------------------------------------------------------------------------

    @staticmethod
    def sync_facial_template(
        session: Session, resident_id: UUID, current_user: User
    ) -> FacialTemplate:
        """Sync (simulated) a resident's template from their latest approved photo."""
        _assert_admin_or_director(current_user)

        resident = session.get(Resident, resident_id)
        if not resident:
            raise ResidentNotFoundError(resident_id)

        approved_photo = session.exec(
            select(MediaAsset)
            .where(
                MediaAsset.entity_type == EntityType.RESIDENT,
                MediaAsset.entity_id == resident_id,
                MediaAsset.status == PhotoApprovalStatus.APPROVED,
            )
            .order_by(MediaAsset.created_at.desc())  # type: ignore[attr-defined]
        ).first()
        if not approved_photo:
            raise NoApprovedPhotoError

        template = session.exec(
            select(FacialTemplate).where(FacialTemplate.resident_id == resident_id)
        ).first()

        now = datetime.utcnow()
        if template:
            template.media_asset_id = approved_photo.id
            template.sync_status = FacialTemplateSyncStatus.SYNCED
            template.synced_at = now
            template.failure_reason = None
            template.updated_at = now
        else:
            template = FacialTemplate(
                resident_id=resident_id,
                media_asset_id=approved_photo.id,
                sync_status=FacialTemplateSyncStatus.SYNCED,
                synced_at=now,
            )

        session.add(template)
        session.commit()
        session.refresh(template)
        return template

    @staticmethod
    def get_facial_template(
        session: Session, resident_id: UUID, current_user: User
    ) -> FacialTemplate | None:
        """Return the resident's current facial template, or None if not synced."""
        _assert_admin_director_or_manager(current_user)
        return session.exec(
            select(FacialTemplate).where(FacialTemplate.resident_id == resident_id)
        ).first()

    # -------------------------------------------------------------------------
    # Verification Webhook & Event Feed
    # -------------------------------------------------------------------------

    @staticmethod
    def process_verification_webhook(
        session: Session, device_key: str | None, payload: FacialVerificationWebhookIn
    ) -> FacialAccessEvent:
        """Process an inbound verification event reported by a physical device."""
        if not device_key:
            raise InvalidDeviceKeyError

        device = session.exec(
            select(AccessDevice).where(AccessDevice.device_key == device_key)
        ).first()
        if not device:
            raise InvalidDeviceKeyError

        now = datetime.utcnow()
        device.status = AccessDeviceStatus.ONLINE
        device.last_seen_at = now
        session.add(device)

        matched = False
        access_granted = False
        resident: Resident | None = None

        if payload.resident_id is not None:
            resident = session.get(Resident, payload.resident_id)
            template = session.exec(
                select(FacialTemplate).where(
                    FacialTemplate.resident_id == payload.resident_id,
                    FacialTemplate.sync_status == FacialTemplateSyncStatus.SYNCED,
                )
            ).first()
            if template:
                matched = True
                if resident is not None and resident.is_active:
                    access_granted = True

        event = FacialAccessEvent(
            device_id=device.id,
            resident_id=payload.resident_id,
            matched=matched,
            confidence_score=payload.confidence_score,
            access_granted=access_granted,
            event_time=now,
            raw_payload=payload.model_dump_json(),
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event

    @staticmethod
    def list_events(
        session: Session,
        current_user: User,
        device_id: UUID | None = None,
        resident_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[FacialAccessEvent], int]:
        """List facial access events, most recent first, with optional filters."""
        _assert_admin_director_or_manager(current_user)

        query = select(FacialAccessEvent)
        if device_id:
            query = query.where(FacialAccessEvent.device_id == device_id)
        if resident_id:
            query = query.where(FacialAccessEvent.resident_id == resident_id)

        total = session.exec(select(func.count()).select_from(query.subquery())).one()
        events = session.exec(
            query.offset(skip).limit(limit).order_by(FacialAccessEvent.event_time.desc())  # type: ignore[attr-defined]
        ).all()

        return list(events), total
