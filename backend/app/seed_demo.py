"""Idempotent seed script to populate APRAS database with realistic demo data.

Safe to run against any database: does not truncate or drop any tables.
Reuses or creates records without duplicates. Populates 100% of all screens
for the primary tenant, plus a secondary tenant with minimal data for switching.
"""

import argparse
import json
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from sqlmodel import Session, create_engine, select

from app.core import clock
from app.core.config import settings
from app.core.money import quantize_money
from app.core.permissions import PERMISSIONS, TOGGLEABLE_MODULES
from app.core.security import get_password_hash
from app.models.access_control import AccessDevice, FacialAccessEvent
from app.models.announcement import Announcement
from app.models.asset import Asset, InventoryMovement
from app.models.category import Category
from app.models.document import AssociationDocument, DocumentFolder
from app.models.enums import (
    AccessDeviceStatus,
    AssemblyStatus,
    AssemblyType,
    AssetCategory,
    AssetCondition,
    AuthorizationStatus,
    AuthorizationType,
    EntityType,
    FeedbackCategory,
    FeedbackStatus,
    InfractionFineMode,
    InfractionRuleOrigin,
    InfractionStepAction,
    LotAssociationType,
    LotStatus,
    MilestoneStatus,
    MovementType,
    OccurrenceCategory,
    OccurrencePriority,
    OccurrenceStatus,
    PackageStatus,
    PhotoApprovalStatus,
    ProjectStatus,
    PurchaseRequestStatus,
    ReservationStatus,
    ResidentRelationship,
    StorageProvider,
    SubscriptionStatus,
    TaskPriority,
    TaskStatus,
    TransactionType,
    VoteKind,
    VoteStatus,
    VoteType,
)
from app.models.feedback import Feedback
from app.models.finance import FinanceCategory, FinancialTransaction
from app.models.infraction import (
    Infraction,
    InfractionContestation,
    InfractionPolicyStep,
    InfractionRule,
    InfractionSettings,
    InfractionStage,
)
from app.models.lot import Lot, UserLotLink
from app.models.media_asset import MediaAsset
from app.models.occurrence import Occurrence
from app.models.package import Package
from app.models.plan import Plan
from app.models.project import ConstructionProject, ProjectMilestone, ProjectUpdate
from app.models.purchase import (
    PurchaseQuote,
    PurchaseQuoteDecision,
    PurchaseQuoteItem,
    PurchaseRequest,
    PurchaseRequestItem,
)
from app.models.reservation import ReservableSpace, SpaceReservation
from app.models.resident import Resident
from app.models.role import Role
from app.models.role_link import UserRoleLink
from app.models.subscription import TenantSubscription
from app.models.task import Task
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from app.models.visitor import Visitor, VisitorAuthorization
from app.models.voting import Assembly, Ballot, Vote, VoteOption
from app.services.tenant_service import TenantService

DEMO_PASSWORD = "demo1234"  # noqa: S105  # demo seed credential, not a real secret
SECONDARY_TENANT_ID = UUID("00000000-0000-0000-0000-000000000002")


def _money(value: float | str) -> Decimal:
    """A seed literal as money: `Decimal` at two decimal places.

    Via `str`, never `Decimal(float)`, so `3840.50` does not carry the binary
    tail of its float literal into a `NUMERIC(12, 2)` column.
    """
    return quantize_money(Decimal(str(value)))


def _ensure_role_permissions(session: Session, tenant_id: UUID) -> dict[str, Role]:
    """Ensure legacy roles exist for a tenant and assign demo permissions."""
    TenantService.ensure_legacy_roles(session, tenant_id)
    session.commit()

    # Clean legacy "(papel)" suffix and deduplicate if clean name already exists
    existing_roles = session.exec(select(Role).where(Role.tenant_id == tenant_id)).all()
    roles_by_name = {r.name: r for r in existing_roles}
    for role_row in existing_roles:
        if " (papel)" in role_row.name:
            clean_name = role_row.name.replace(" (papel)", "").strip()
            if clean_name in roles_by_name:
                target = roles_by_name[clean_name]
                for ur in session.exec(
                    select(UserRoleLink).where(UserRoleLink.role_id == role_row.id)
                ).all():
                    exists = session.exec(
                        select(UserRoleLink).where(
                            UserRoleLink.user_id == ur.user_id,
                            UserRoleLink.role_id == target.id,
                        )
                    ).first()
                    if not exists:
                        session.add(UserRoleLink(user_id=ur.user_id, role_id=target.id))
                    session.delete(ur)
                session.delete(role_row)
            else:
                role_row.name = clean_name
                session.add(role_row)
                roles_by_name[clean_name] = role_row
    session.commit()

    roles_by_name = {
        r.name: r
        for r in session.exec(select(Role).where(Role.tenant_id == tenant_id)).all()
    }

    # Grant catalogue permissions so all demo screens work seamlessly
    all_perms = sorted(PERMISSIONS)
    director_perms = sorted(
        p
        for p in PERMISSIONS
        if not p.startswith("roles:")
        and not p.startswith("tenants:")
        and not p.startswith("users:delete")
    )
    manager_perms = sorted(
        p
        for p in PERMISSIONS
        if p.startswith(
            (
                "tasks:",
                "categories:",
                "occurrences:",
                "packages:",
                "assets:",
                "purchases:read",
                "purchases:create",
                "purchases:quote_create",
                "gate:",
                "visitors:",
                "access_control:",
                "media:",
            )
        )
    )
    porteiro_perms = sorted(
        p
        for p in PERMISSIONS
        if p.startswith(
            (
                "gate:",
                "visitors:",
                "packages:",
                "access_control:read",
                "occurrences:read",
                "occurrences:create",
                "tasks:read",
            )
        )
    )
    morador_perms = sorted(
        p
        for p in PERMISSIONS
        if p.startswith(
            (
                "announcements:read",
                "spaces:",
                "reservations:",
                "feedback:",
                "documents:read",
                "voting:read",
                "votes:",
                "occurrences:read",
                "occurrences:create",
                "visitors:create",
                "visitors:read",
                "infractions:my_lots_read",
                "packages:read",
            )
        )
    )

    if "Administrador" in roles_by_name:
        roles_by_name["Administrador"].permissions = all_perms
        session.add(roles_by_name["Administrador"])
    if "Diretor" in roles_by_name:
        roles_by_name["Diretor"].permissions = director_perms
        session.add(roles_by_name["Diretor"])
    if "Gerente" in roles_by_name:
        roles_by_name["Gerente"].permissions = manager_perms
        session.add(roles_by_name["Gerente"])
    if "Porteiro" in roles_by_name:
        roles_by_name["Porteiro"].permissions = porteiro_perms
        session.add(roles_by_name["Porteiro"])
    if "Morador" in roles_by_name:
        roles_by_name["Morador"].permissions = morador_perms
        session.add(roles_by_name["Morador"])
    session.commit()

    return {
        r.name: r
        for r in session.exec(select(Role).where(Role.tenant_id == tenant_id)).all()
    }


def _seed_tenants(session: Session) -> tuple[Tenant, Tenant]:
    """Ensure both primary and secondary tenants exist."""
    # 1. Primary Tenant (100% full demo)
    t1 = session.exec(select(Tenant).where(Tenant.id == DEFAULT_TENANT_ID)).first()
    if not t1:
        t1 = Tenant(
            id=DEFAULT_TENANT_ID,
            name="Condomínio Residencial Parque das Flores",
            is_active=True,
            disabled_modules=[],
        )
        session.add(t1)
        session.commit()
        session.refresh(t1)
        print(" Created primary Tenant (Condomínio Residencial Parque das Flores).")
    else:
        print(f" Existing primary Tenant: {t1.name}")

    # 2. Secondary Tenant (minimal demo to showcase switching)
    t2 = session.exec(select(Tenant).where(Tenant.id == SECONDARY_TENANT_ID)).first()
    if not t2:
        t2 = Tenant(
            id=SECONDARY_TENANT_ID,
            name="Condomínio Solar da Serra",
            is_active=True,
            disabled_modules=[],
        )
        session.add(t2)
        session.commit()
        session.refresh(t2)
        print(" Created secondary Tenant (Condomínio Solar da Serra).")
    else:
        print(f" Existing secondary Tenant: {t2.name}")

    return t1, t2


def _link_user_to_tenant(
    session: Session,
    user_id: UUID,
    tenant_id: UUID,
    is_admin: bool,
    role: Role | None,
) -> None:
    """Link user to tenant membership and assign role if not already linked."""
    link = session.exec(
        select(UserTenantLink).where(
            UserTenantLink.user_id == user_id,
            UserTenantLink.tenant_id == tenant_id,
        )
    ).first()
    if not link:
        session.add(
            UserTenantLink(
                user_id=user_id,
                tenant_id=tenant_id,
                is_tenant_admin=is_admin,
            )
        )
        session.commit()

    if role:
        existing_ur = session.exec(
            select(UserRoleLink).where(
                UserRoleLink.user_id == user_id, UserRoleLink.role_id == role.id
            )
        ).first()
        if not existing_ur:
            session.add(UserRoleLink(user_id=user_id, role_id=role.id))
            session.commit()


def _seed_users(
    session: Session,
    t1_id: UUID,
    t2_id: UUID,
    t1_roles: dict[str, Role],
    t2_roles: dict[str, Role],
) -> dict[str, User]:
    """Seed demo user accounts linked to both tenants."""
    users_specs = [
        {
            "email": "admin@apras.com",
            "full_name": "Administrador do Sistema",
            "cpf": "52998224725",
            "is_superuser": True,
            "role": "Administrador",
            "is_tenant_admin": True,
        },
        {
            "email": "sindico@apras.com",
            "full_name": "Carlos Silva (Síndico)",
            "cpf": "11144477735",
            "is_superuser": False,
            "role": "Diretor",
            "is_tenant_admin": True,
        },
        {
            "email": "zelador@apras.com",
            "full_name": "Marcos Oliveira (Zelador)",
            "cpf": "08050681057",
            "is_superuser": False,
            "role": "Gerente",
            "is_tenant_admin": False,
        },
        {
            "email": "porteiro@apras.com",
            "full_name": "José Santos (Portaria)",
            "cpf": "07491723040",
            "is_superuser": False,
            "role": "Porteiro",
            "is_tenant_admin": False,
        },
        {
            "email": "morador@apras.com",
            "full_name": "Ana Souza (Moradora)",
            "cpf": "38812345678",
            "is_superuser": False,
            "role": "Morador",
            "is_tenant_admin": False,
        },
    ]

    users_map: dict[str, User] = {}
    for spec in users_specs:
        user = session.exec(select(User).where(User.email == spec["email"])).first()
        if not user:
            user = User(
                email=spec["email"],
                full_name=spec["full_name"],
                cpf=spec["cpf"],
                hashed_password=get_password_hash(DEMO_PASSWORD),
                is_active=True,
                is_superuser=spec["is_superuser"],
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f" Created user: {user.email}")
        else:
            user.full_name = spec["full_name"]
            user.is_active = True
            user.is_superuser = spec["is_superuser"]
            session.add(user)
            session.commit()
            session.refresh(user)

        _link_user_to_tenant(
            session, user.id, t1_id, spec["is_tenant_admin"], t1_roles.get(spec["role"])
        )
        _link_user_to_tenant(
            session, user.id, t2_id, spec["is_tenant_admin"], t2_roles.get(spec["role"])
        )
        users_map[spec["email"]] = user

    # Ensure operator Heitor has full access if registered
    heitor = session.exec(
        select(User).where(User.email == "heitor.polidoro@gmail.com")
    ).first()
    if heitor:
        for tid, r_dict in [(t1_id, t1_roles), (t2_id, t2_roles)]:
            _link_user_to_tenant(
                session, heitor.id, tid, True, r_dict.get("Administrador")
            )
        print(" Connected operator heitor.polidoro@gmail.com to both tenants.")

    return users_map


def _seed_plans_and_subscriptions(session: Session, t1_id: UUID, t2_id: UUID) -> None:
    """Seed SaaS plan catalogue and assign subscriptions to tenants."""
    plans_data = [
        {
            "name": "Plano Básico",
            "description": (
                "Portaria, controle de acesso, encomendas e tarefas básicas."
            ),
            "base_price": 199.0,
            "included_modules": [
                "tasks",
                "categories",
                "announcements",
                "occurrences",
                "packages",
                "visitors",
                "gate",
                "feedback",
            ],
            "module_prices": {},
        },
        {
            "name": "Plano Profissional",
            "description": (
                "Gestão completa com financeiro, reservas, documentos, obras e "
                "votações."
            ),
            "base_price": 499.0,
            "included_modules": sorted(TOGGLEABLE_MODULES),
            "module_prices": {},
        },
        {
            "name": "Plano Enterprise",
            "description": (
                "Recursos avançados, auditoria estendida e suporte dedicado."
            ),
            "base_price": 899.0,
            "included_modules": sorted(TOGGLEABLE_MODULES),
            "module_prices": {},
        },
    ]

    plans_by_name: dict[str, Plan] = {}
    for p_spec in plans_data:
        plan = session.exec(select(Plan).where(Plan.name == p_spec["name"])).first()
        if not plan:
            plan = Plan(
                name=p_spec["name"],
                description=p_spec["description"],
                base_price=_money(p_spec["base_price"]),
                included_modules=p_spec["included_modules"],
                module_prices=p_spec["module_prices"],
                currency="BRL",
            )
            session.add(plan)
            session.commit()
            session.refresh(plan)
        plans_by_name[p_spec["name"]] = plan
    print(f" Seeded {len(plans_by_name)} SaaS plans.")

    # Primary Tenant -> Plano Profissional
    sub1 = session.exec(
        select(TenantSubscription).where(TenantSubscription.tenant_id == t1_id)
    ).first()
    if not sub1 and "Plano Profissional" in plans_by_name:
        sub1 = TenantSubscription(
            tenant_id=t1_id,
            plan_id=plans_by_name["Plano Profissional"].id,
            status=SubscriptionStatus.ACTIVE,
            courtesy_modules=[],
            notes="Assinatura corporativa ativa com todos os módulos inclusos.",
        )
        session.add(sub1)
        session.commit()

    # Secondary Tenant -> Plano Básico
    sub2 = session.exec(
        select(TenantSubscription).where(TenantSubscription.tenant_id == t2_id)
    ).first()
    if not sub2 and "Plano Básico" in plans_by_name:
        sub2 = TenantSubscription(
            tenant_id=t2_id,
            plan_id=plans_by_name["Plano Básico"].id,
            status=SubscriptionStatus.ACTIVE,
            courtesy_modules=[],
            notes="Assinatura inicial do condomínio secundário.",
        )
        session.add(sub2)
        session.commit()


def _seed_primary_tenant_data(  # noqa: PLR0912, PLR0915  # comprehensive population for all screens of primary tenant
    session: Session,
    tenant_id: UUID,
    users_map: dict[str, User],
    roles_by_name: dict[str, Role],
) -> None:
    """Populate 100% of all screens and domain models for the primary tenant."""
    now = clock.db_now()
    today = clock.today_utc()
    admin_user = users_map["admin@apras.com"]
    sindico_user = users_map["sindico@apras.com"]
    zelador_user = users_map["zelador@apras.com"]
    porteiro_user = users_map["porteiro@apras.com"]
    morador_user = users_map["morador@apras.com"]

    # 1. Lots / Units
    lots_data = [
        ("Bloco A", "101"),
        ("Bloco A", "102"),
        ("Bloco A", "201"),
        ("Bloco A", "202"),
        ("Bloco A", "301"),
        ("Bloco A", "Cobertura 401"),
        ("Bloco B", "101"),
        ("Bloco B", "102"),
        ("Bloco B", "201"),
        ("Bloco B", "202"),
        ("Bloco B", "Cobertura 301"),
    ]
    lots_map: dict[tuple[str, str], Lot] = {}
    for block, lot_number in lots_data:
        lot = session.exec(
            select(Lot).where(
                Lot.tenant_id == tenant_id,
                Lot.block == block,
                Lot.lot_number == lot_number,
            )
        ).first()
        if not lot:
            lot = Lot(
                tenant_id=tenant_id,
                block=block,
                lot_number=lot_number,
                status=LotStatus.OCCUPIED,
                area_sqm=78.5,
            )
            session.add(lot)
            session.commit()
            session.refresh(lot)
        lots_map[(block, lot_number)] = lot
    print(f" Loaded {len(lots_map)} lots.")

    # Link Morador and Síndico to units
    lot_101 = lots_map[("Bloco A", "101")]
    lot_102 = lots_map[("Bloco A", "102")]
    lot_201 = lots_map[("Bloco A", "201")]

    u_link = session.exec(
        select(UserLotLink).where(
            UserLotLink.user_id == morador_user.id, UserLotLink.lot_id == lot_101.id
        )
    ).first()
    if not u_link:
        session.add(
            UserLotLink(
                user_id=morador_user.id,
                lot_id=lot_101.id,
                association_type=LotAssociationType.PROPRIETARIO,
                is_primary=True,
            )
        )
        session.commit()

    u_link_sindico = session.exec(
        select(UserLotLink).where(
            UserLotLink.user_id == sindico_user.id, UserLotLink.lot_id == lot_102.id
        )
    ).first()
    if not u_link_sindico:
        session.add(
            UserLotLink(
                user_id=sindico_user.id,
                lot_id=lot_102.id,
                association_type=LotAssociationType.PROPRIETARIO,
                is_primary=True,
            )
        )
        session.commit()

    # 2. Residents (Moradores detalhados para /lots e controle de acesso)
    residents_data = [
        {
            "full_name": "Ana Souza",
            "cpf": "38812345678",
            "email": "morador@apras.com",
            "phone": "(11) 98765-1122",
            "lot": lot_101,
            "user_id": morador_user.id,
            "relationship": ResidentRelationship.TITULAR,
        },
        {
            "full_name": "Lucas Souza",
            "cpf": "41298765432",
            "email": "lucas.souza@example.com",
            "phone": "(11) 98765-1123",
            "lot": lot_101,
            "user_id": None,
            "relationship": ResidentRelationship.FILHO_DEPENDENTE,
        },
        {
            "full_name": "Carlos Silva",
            "cpf": "11144477735",
            "email": "sindico@apras.com",
            "phone": "(11) 99887-6655",
            "lot": lot_102,
            "user_id": sindico_user.id,
            "relationship": ResidentRelationship.TITULAR,
        },
        {
            "full_name": "Roberto Alves",
            "cpf": "22233344455",
            "email": "roberto.alves@example.com",
            "phone": "(11) 97766-5544",
            "lot": lot_201,
            "user_id": None,
            "relationship": ResidentRelationship.TITULAR,
        },
    ]
    residents_map: dict[str, Resident] = {}
    for r_spec in residents_data:
        res = session.exec(
            select(Resident).where(
                Resident.tenant_id == tenant_id, Resident.cpf == r_spec["cpf"]
            )
        ).first()
        if not res:
            res = Resident(
                tenant_id=tenant_id,
                lot_id=r_spec["lot"].id,
                user_id=r_spec["user_id"],
                full_name=r_spec["full_name"],
                cpf=r_spec["cpf"],
                email=r_spec["email"],
                phone=r_spec["phone"],
                relationship_type=r_spec["relationship"],
                is_active=True,
            )
            session.add(res)
            session.commit()
            session.refresh(res)
        residents_map[r_spec["full_name"]] = res
    print(f" Seeded {len(residents_map)} residents.")

    # 3. Task Categories & Tasks
    categories_data = [
        {"name": "Manutenção Predial", "color": "#ea580c"},
        {"name": "Segurança & Portaria", "color": "#dc2626"},
        {"name": "Jardinagem & Paisagismo", "color": "#16a34a"},
        {"name": "Limpeza & Conservação", "color": "#0891b2"},
        {"name": "Administrativo & Financeiro", "color": "#2563eb"},
        {"name": "Jurídico & Compliance", "color": "#9333ea"},
    ]
    cats_map: dict[str, Category] = {}
    for c_data in categories_data:
        cat = session.exec(
            select(Category).where(
                Category.tenant_id == tenant_id, Category.name == c_data["name"]
            )
        ).first()
        if not cat:
            cat = Category(
                tenant_id=tenant_id, name=c_data["name"], color=c_data["color"]
            )
            session.add(cat)
            session.commit()
            session.refresh(cat)
        cats_map[c_data["name"]] = cat

    tasks_specs = [
        {
            "title": "Vistoria periódica dos para-raios e laudo SPDA",
            "description": (
                "Contratar empresa credenciada para medição ôhmica e renovação do "
                "laudo técnico de para-raios."
            ),
            "status": TaskStatus.IN_PROGRESS,
            "priority": TaskPriority.HIGH,
            "category": "Manutenção Predial",
            "assigned": sindico_user,
            "due_days": 12,
        },
        {
            "title": "Manutenção preventiva das bombas de recalque da caixa d'água",
            "description": (
                "Verificar rolamentos, vedação mecânica e alternância automática do "
                "conjunto motobomba."
            ),
            "status": TaskStatus.PENDING,
            "priority": TaskPriority.URGENT,
            "category": "Manutenção Predial",
            "assigned": zelador_user,
            "due_days": 3,
        },
        {
            "title": "Substituição de lâmpadas de emergência nas escadarias",
            "description": (
                "Testar baterias das luminárias autônomas de emergência nos "
                "blocos A e B."
            ),
            "status": TaskStatus.IN_PROGRESS,
            "priority": TaskPriority.MEDIUM,
            "category": "Segurança & Portaria",
            "assigned": zelador_user,
            "due_days": 7,
        },
        {
            "title": "Cotação para modernização do sistema de interfonia",
            "description": (
                "Solicitar 3 orçamentos para migração do cabeamento analógico para "
                "interfonia IP/digital."
            ),
            "status": TaskStatus.PENDING,
            "priority": TaskPriority.MEDIUM,
            "category": "Administrativo & Financeiro",
            "assigned": sindico_user,
            "due_days": 15,
        },
        {
            "title": "Dedetização semestral das áreas comuns e garagens",
            "description": (
                "Aplicação de barreira química contra insetos e roedores no subsolo e "
                "lixeiras."
            ),
            "status": TaskStatus.COMPLETED,
            "priority": TaskPriority.LOW,
            "category": "Limpeza & Conservação",
            "assigned": zelador_user,
            "due_days": -4,
        },
    ]
    for t_spec in tasks_specs:
        existing_task = session.exec(
            select(Task).where(
                Task.tenant_id == tenant_id, Task.title == t_spec["title"]
            )
        ).first()
        if not existing_task:
            cat = cats_map.get(t_spec["category"])
            task = Task(
                tenant_id=tenant_id,
                title=t_spec["title"],
                description=t_spec["description"],
                status=t_spec["status"],
                priority=t_spec["priority"],
                category_id=cat.id if cat else None,
                created_by_id=admin_user.id,
                assigned_to_id=t_spec["assigned"].id,
                due_date=now + timedelta(days=t_spec["due_days"]),
            )
            session.add(task)
            session.commit()
    print(" Seeded tasks.")

    # 4. Announcements (Comunicados)
    announcements_specs = [
        {
            "title": "Manutenção Preventiva dos Elevadores - Bloco A e B",
            "content": (
                "Informamos que na próxima terça-feira (10h às 14h) a empresa "
                "Atlas Schindler realizará a manutenção periódica e lubrificação dos "
                "elevadores de passageiros."
            ),
            "author": sindico_user,
        },
        {
            "title": "Campanha: Coleta Seletiva e Descarte de Resíduos",
            "content": (
                "Pedimos a colaboração de todos os moradores para separar os materiais "
                "recicláveis (papel, plástico, vidro e metal) nos coletores "
                "identificados no subsolo."
            ),
            "author": sindico_user,
        },
        {
            "title": "Assembleia Geral Ordinária - Prestação de Contas 2026",
            "content": (
                "Convocamos todos os condôminos para a AGO no dia 25 do próximo mês "
                "às 19h no Salão de Festas, com transmissão online."
            ),
            "author": sindico_user,
        },
    ]
    for a_spec in announcements_specs:
        ann = session.exec(
            select(Announcement).where(
                Announcement.tenant_id == tenant_id,
                Announcement.title == a_spec["title"],
            )
        ).first()
        if not ann:
            session.add(
                Announcement(
                    tenant_id=tenant_id,
                    title=a_spec["title"],
                    content=a_spec["content"],
                    author_id=a_spec["author"].id,
                )
            )
            session.commit()
    print(" Seeded announcements.")

    # 5. Reservable Spaces & Reservations
    spaces_data = [
        {
            "name": "Salão de Festas Principal",
            "description": (
                "Espaço climatizado com cozinha completa, mesas, cadeiras e som."
            ),
            "capacity": 80,
            "requires_approval": True,
        },
        {
            "name": "Espaço Gourmet & Churrasqueira",
            "description": (
                "Área coberta com churrasqueira a carvão, bancada em granito e freezer."
            ),
            "capacity": 30,
            "requires_approval": False,
        },
        {
            "name": "Quadra Poliesportiva",
            "description": (
                "Quadra com iluminação LED para futebol, basquete e vôlei."
            ),
            "capacity": 20,
            "requires_approval": False,
        },
        {
            "name": "Sala de Jogos & Coworking",
            "description": (
                "Mesa de bilhar, mesa de cartas, bancadas de trabalho e Wi-Fi veloz."
            ),
            "capacity": 15,
            "requires_approval": False,
        },
    ]
    spaces_map: dict[str, ReservableSpace] = {}
    for s_data in spaces_data:
        sp = session.exec(
            select(ReservableSpace).where(
                ReservableSpace.tenant_id == tenant_id,
                ReservableSpace.name == s_data["name"],
            )
        ).first()
        if not sp:
            sp = ReservableSpace(
                tenant_id=tenant_id,
                name=s_data["name"],
                description=s_data["description"],
                capacity=s_data["capacity"],
                requires_approval=s_data["requires_approval"],
                is_active=True,
            )
            session.add(sp)
            session.commit()
            session.refresh(sp)
        spaces_map[s_data["name"]] = sp

    salao = spaces_map.get("Salão de Festas Principal")
    if salao:
        res_start = (now + timedelta(days=5)).replace(hour=14, minute=0, second=0)
        res_end = (now + timedelta(days=5)).replace(hour=22, minute=0, second=0)
        existing_res = session.exec(
            select(SpaceReservation).where(
                SpaceReservation.space_id == salao.id,
                SpaceReservation.reserved_by_id == morador_user.id,
            )
        ).first()
        if not existing_res:
            session.add(
                SpaceReservation(
                    tenant_id=tenant_id,
                    space_id=salao.id,
                    reserved_by_id=morador_user.id,
                    lot_id=lot_101.id,
                    start_time=res_start,
                    end_time=res_end,
                    status=ReservationStatus.CONFIRMED,
                    notes="Comemoração de aniversário familiar.",
                )
            )
            session.commit()
    print(" Seeded reservable spaces and reservations.")

    # 6. Packages (Encomendas)
    packages_specs = [
        {
            "lot": lot_101,
            "carrier": "Amazon Logística",
            "desc": "Caixa média (rastreio AMZ-98218)",
            "status": PackageStatus.AWAITING_PICKUP,
            "days_ago": 1,
        },
        {
            "lot": lot_201,
            "carrier": "Mercado Livre",
            "desc": "Pacote amarelo Mercado Envios",
            "status": PackageStatus.AWAITING_PICKUP,
            "days_ago": 2,
        },
        {
            "lot": lots_map[("Bloco B", "102")],
            "carrier": "Correios",
            "desc": "Sedex envelope pardo",
            "status": PackageStatus.PICKED_UP,
            "days_ago": 3,
        },
    ]
    for p_spec in packages_specs:
        existing_pkg = session.exec(
            select(Package).where(
                Package.tenant_id == tenant_id,
                Package.lot_id == p_spec["lot"].id,
                Package.description == p_spec["desc"],
            )
        ).first()
        if not existing_pkg:
            recv_time = now - timedelta(days=p_spec["days_ago"], hours=3)
            session.add(
                Package(
                    tenant_id=tenant_id,
                    lot_id=p_spec["lot"].id,
                    received_by_id=porteiro_user.id,
                    carrier=p_spec["carrier"],
                    description=p_spec["desc"],
                    status=p_spec["status"],
                    received_at=recv_time,
                    picked_up_at=(
                        recv_time + timedelta(hours=5)
                        if p_spec["status"] == PackageStatus.PICKED_UP
                        else None
                    ),
                )
            )
            session.commit()
    print(" Seeded packages.")

    # 7. Occurrences (Ocorrências)
    occurrences_specs = [
        {
            "protocol": "OC-2026-001",
            "category": OccurrenceCategory.MAINTENANCE,
            "title": "Vazamento na torneira do jardim próximo ao playground",
            "desc": (
                "A torneira externa está gotejando continuamente, acumulando poça de "
                "água perto da área infantil."
            ),
            "status": OccurrenceStatus.OPEN,
            "priority": OccurrencePriority.LOW,
            "lot": lot_101,
        },
        {
            "protocol": "OC-2026-002",
            "category": OccurrenceCategory.NOISE,
            "title": "Música alta após o horário de silêncio (22h)",
            "desc": (
                "Música e conversa em tom elevado no Bloco B unidade 202 na noite de "
                "sexta-feira."
            ),
            "status": OccurrenceStatus.RESOLVED,
            "priority": OccurrencePriority.MEDIUM,
            "lot": lots_map[("Bloco B", "202")],
            "res_notes": (
                "Portaria contatou o morador, que prontamente reduziu o volume."
            ),
        },
        {
            "protocol": "OC-2026-003",
            "category": OccurrenceCategory.PARKING,
            "title": "Veículo estacionado sobre a faixa de pedestres da garagem",
            "desc": (
                "Carro prata estacionado obstruindo a rampa de acesso do subsolo."
            ),
            "status": OccurrenceStatus.IN_PROGRESS,
            "priority": OccurrencePriority.HIGH,
            "lot": lot_201,
        },
    ]
    occurrences_map: dict[str, Occurrence] = {}
    for o_spec in occurrences_specs:
        occ = session.exec(
            select(Occurrence).where(
                Occurrence.tenant_id == tenant_id,
                Occurrence.protocol_number == o_spec["protocol"],
            )
        ).first()
        if not occ:
            occ = Occurrence(
                tenant_id=tenant_id,
                protocol_number=o_spec["protocol"],
                category=o_spec["category"],
                title=o_spec["title"],
                description=o_spec["desc"],
                status=o_spec["status"],
                priority=o_spec["priority"],
                lot_id=o_spec["lot"].id,
                reporter_user_id=morador_user.id,
                resolution_notes=o_spec.get("res_notes"),
                resolved_at=now
                if o_spec["status"] == OccurrenceStatus.RESOLVED
                else None,
            )
            session.add(occ)
            session.commit()
            session.refresh(occ)
        occurrences_map[o_spec["protocol"]] = occ
    print(" Seeded occurrences.")

    # 8. Visitors & Gate Authorizations
    visitors_specs = [
        {
            "full_name": "Mariana Ferreira Costa",
            "cpf": "29182374619",
            "phone": "(11) 98765-4321",
            "vehicle_plate": "ABC1D23",
            "lot": lot_101,
        },
        {
            "full_name": "Rodrigo Silva (Técnico Vivo Fibra)",
            "company": "Vivo Telecomunicações",
            "cpf": "19283746502",
            "phone": "(11) 97654-3210",
            "lot": lot_201,
        },
    ]
    for v_spec in visitors_specs:
        vis = session.exec(
            select(Visitor).where(
                Visitor.tenant_id == tenant_id,
                Visitor.full_name == v_spec["full_name"],
            )
        ).first()
        if not vis:
            vis = Visitor(
                tenant_id=tenant_id,
                full_name=v_spec["full_name"],
                cpf=v_spec.get("cpf"),
                phone=v_spec.get("phone"),
                company_name=v_spec.get("company"),
                vehicle_plate=v_spec.get("vehicle_plate"),
            )
            session.add(vis)
            session.commit()
            session.refresh(vis)

        auth = session.exec(
            select(VisitorAuthorization).where(
                VisitorAuthorization.visitor_id == vis.id,
                VisitorAuthorization.lot_id == v_spec["lot"].id,
            )
        ).first()
        if not auth:
            session.add(
                VisitorAuthorization(
                    tenant_id=tenant_id,
                    visitor_id=vis.id,
                    lot_id=v_spec["lot"].id,
                    authorizer_user_id=morador_user.id,
                    auth_type=AuthorizationType.SINGLE,
                    status=AuthorizationStatus.ACTIVE,
                    start_date=now - timedelta(hours=1),
                    end_date=now + timedelta(hours=8),
                )
            )
            session.commit()
    print(" Seeded visitors and authorizations.")

    # 9. Finance (Categories & Transactions)
    fin_cats_data = [
        ("Taxa Condominial Ordinária", TransactionType.INCOME),
        ("Fundo de Reserva", TransactionType.INCOME),
        ("Energia Elétrica (Áreas Comuns)", TransactionType.EXPENSE),
        ("Água e Esgoto (Sabesp)", TransactionType.EXPENSE),
        ("Manutenção de Elevadores", TransactionType.EXPENSE),
        ("Materiais de Limpeza e Higiene", TransactionType.EXPENSE),
    ]
    fin_cats_map: dict[str, FinanceCategory] = {}
    for fc_name, fc_type in fin_cats_data:
        fc = session.exec(
            select(FinanceCategory).where(
                FinanceCategory.tenant_id == tenant_id,
                FinanceCategory.name == fc_name,
            )
        ).first()
        if not fc:
            fc = FinanceCategory(
                tenant_id=tenant_id, name=fc_name, type=fc_type, is_active=True
            )
            session.add(fc)
            session.commit()
            session.refresh(fc)
        fin_cats_map[fc_name] = fc

    transactions_data = [
        (
            "Taxa Condominial Ordinária",
            "Arrecadação de cotas condominiais - Mês corrente",
            28500.0,
            TransactionType.INCOME,
            today - timedelta(days=5),
        ),
        (
            "Fundo de Reserva",
            "Aporte mensal no fundo de reserva (5%)",
            1425.0,
            TransactionType.INCOME,
            today - timedelta(days=5),
        ),
        (
            "Energia Elétrica (Áreas Comuns)",
            "Fatura Enel - Áreas comuns e bombas",
            3840.50,
            TransactionType.EXPENSE,
            today - timedelta(days=8),
        ),
        (
            "Água e Esgoto (Sabesp)",
            "Conta Sabesp hidrômetro coletivo",
            2980.20,
            TransactionType.EXPENSE,
            today - timedelta(days=10),
        ),
        (
            "Manutenção de Elevadores",
            "Mensalidade contrato de conservação Atlas Schindler",
            1450.0,
            TransactionType.EXPENSE,
            today - timedelta(days=12),
        ),
    ]
    for cat_name, desc, amount, t_type, t_date in transactions_data:
        fc = fin_cats_map.get(cat_name)
        if fc:
            existing_tx = session.exec(
                select(FinancialTransaction).where(
                    FinancialTransaction.tenant_id == tenant_id,
                    FinancialTransaction.description == desc,
                    FinancialTransaction.transaction_date == t_date,
                )
            ).first()
            if not existing_tx:
                session.add(
                    FinancialTransaction(
                        tenant_id=tenant_id,
                        type=t_type,
                        category_id=fc.id,
                        description=desc,
                        amount=_money(amount),
                        transaction_date=t_date,
                        payment_method="BOLETO"
                        if t_type == TransactionType.EXPENSE
                        else "TRANSFERENCIA",
                        created_by_id=sindico_user.id,
                    )
                )
                session.commit()
    print(" Seeded finance categories and transactions.")

    # 10. Feedback (/feedback)
    feedbacks_data = [
        {
            "category": FeedbackCategory.SUGGESTION,
            "message": (
                "Sugiro a instalação de um bicicletário coberto próximo ao Bloco B "
                "para acomodar melhor as bicicletas dos moradores."
            ),
            "status": FeedbackStatus.ANSWERED,
            "response": (
                "Excelente sugestão! A diretoria já solicitou 2 orçamentos "
                "para execução da cobertura."
            ),
            "responded_by": sindico_user,
            "days_ago": 6,
        },
        {
            "category": FeedbackCategory.CRITICISM,
            "message": (
                "A água da piscina estava bastante turva no último domingo à tarde, "
                "aparentando falta de filtragem preventiva."
            ),
            "status": FeedbackStatus.ANSWERED,
            "response": (
                "Agradecemos o aviso. O técnico terceirizado reforçou a rotina de "
                "cloração aos sábados pela manhã."
            ),
            "responded_by": sindico_user,
            "days_ago": 4,
        },
        {
            "category": FeedbackCategory.COMPLIMENT,
            "message": (
                "Gostaria de parabenizar toda a equipe de limpeza e portaria pela "
                "organização impecável durante o evento!"
            ),
            "status": FeedbackStatus.PENDING,
            "response": None,
            "responded_by": None,
            "days_ago": 2,
        },
    ]
    for fb in feedbacks_data:
        existing_fb = session.exec(
            select(Feedback).where(
                Feedback.tenant_id == tenant_id, Feedback.message == fb["message"]
            )
        ).first()
        if not existing_fb:
            session.add(
                Feedback(
                    tenant_id=tenant_id,
                    reporter_user_id=morador_user.id,
                    is_anonymous=False,
                    category=fb["category"],
                    message=fb["message"],
                    status=fb["status"],
                    board_response=fb["response"],
                    responded_by_id=fb["responded_by"].id
                    if fb["responded_by"]
                    else None,
                    responded_at=(
                        now - timedelta(days=fb["days_ago"] - 1)
                        if fb["status"] == FeedbackStatus.ANSWERED
                        else None
                    ),
                    created_at=now - timedelta(days=fb["days_ago"]),
                )
            )
            session.commit()
    print(" Seeded feedbacks.")

    # 11. Document Center (/documents)
    all_role_ids_json = json.dumps([str(r.id) for r in roles_by_name.values()])
    folders_data = [
        (
            "Atas de Assembleia",
            "Atas registradas das assembleias ordinárias e extraordinárias",
        ),
        (
            "Regimento Interno e Convenção",
            "Documentos regulatórios e convenção condominial",
        ),
        (
            "Prestação de Contas Mensal",
            "Balancetes contábeis e demonstrativos financeiros",
        ),
        (
            "Manuais e Contratos",
            "Contratos de prestadores e manuais de equipamentos",
        ),
    ]
    folders_map: dict[str, DocumentFolder] = {}
    for f_name, f_desc in folders_data:
        folder = session.exec(
            select(DocumentFolder).where(
                DocumentFolder.tenant_id == tenant_id, DocumentFolder.name == f_name
            )
        ).first()
        if not folder:
            folder = DocumentFolder(
                tenant_id=tenant_id,
                name=f_name,
                description=f_desc,
                allowed_role_ids_json=all_role_ids_json,
            )
            session.add(folder)
            session.commit()
            session.refresh(folder)
        folders_map[f_name] = folder

    docs_data = [
        {
            "folder": "Atas de Assembleia",
            "title": "Ata da Assembleia Geral Ordinária 2025.pdf",
            "desc": "Ata homologada com aprovação das contas de 2025",
            "year": 2025,
            "month": 3,
            "tags": ["ata", "ago", "2025"],
            "size": 2450000,
        },
        {
            "folder": "Regimento Interno e Convenção",
            "title": "Regimento Interno Consolidado 2024.pdf",
            "desc": (
                "Texto integral das regras de convivência, uso de áreas comuns "
                "e silêncio"
            ),
            "year": 2024,
            "month": 1,
            "tags": ["regimento", "normas", "convivencia"],
            "size": 1820000,
        },
        {
            "folder": "Regimento Interno e Convenção",
            "title": "Convenção Condominial Registrada.pdf",
            "desc": "Instrumento de convenção registrado em cartório de imóveis",
            "year": 2020,
            "month": 6,
            "tags": ["convencao", "juridico"],
            "size": 3890000,
        },
        {
            "folder": "Prestação de Contas Mensal",
            "title": "Balancete Mensal - Janeiro 2026.pdf",
            "desc": (
                "Demonstrativo detalhado de receitas ordinárias e despesas operacionais"
            ),
            "year": 2026,
            "month": 1,
            "tags": ["financeiro", "balancete", "contabilidade"],
            "size": 950000,
        },
    ]
    for d_spec in docs_data:
        f = folders_map.get(d_spec["folder"])
        if f:
            existing_doc = session.exec(
                select(AssociationDocument).where(
                    AssociationDocument.tenant_id == tenant_id,
                    AssociationDocument.folder_id == f.id,
                    AssociationDocument.title == d_spec["title"],
                )
            ).first()
            if not existing_doc:
                session.add(
                    AssociationDocument(
                        tenant_id=tenant_id,
                        folder_id=f.id,
                        title=d_spec["title"],
                        description=d_spec["desc"],
                        file_url=f"https://apras-docs.example.com/{d_spec['title']}",
                        file_size_bytes=d_spec["size"],
                        mime_type="application/pdf",
                        publication_year=d_spec["year"],
                        publication_month=d_spec["month"],
                        tags_json=json.dumps(d_spec["tags"]),
                        uploaded_by_id=sindico_user.id,
                    )
                )
                session.commit()
    print(" Seeded document folders and documents.")

    # 12. Construction Projects (/projects)
    projects_data = [
        {
            "title": "Reforma da Fachada e Pintura Externa",
            "desc": (
                "Restauração de pastilhas, lavagem técnica por hidrojato e pintura "
                "impermeabilizante em ambos os blocos."
            ),
            "contractor": "Construtora Silva & Filhos Engenharia",
            "total_budget": 120000.0,
            "executed_budget": 54000.0,
            "progress": 45.0,
            "status": ProjectStatus.IN_PROGRESS,
            "start": today - timedelta(days=40),
            "est_completion": today + timedelta(days=60),
            "milestones": [
                (
                    "Lavagem com hidrojato e raspagem do reboco danificado",
                    MilestoneStatus.DONE,
                    today - timedelta(days=20),
                ),
                (
                    "Aplicação de selador e primeira demão de tinta",
                    MilestoneStatus.IN_PROGRESS,
                    today + timedelta(days=15),
                ),
                (
                    "Segunda demão, rejunte e acabamento de esquadrias",
                    MilestoneStatus.NEXT_STEPS,
                    today + timedelta(days=50),
                ),
            ],
            "update_text": (
                "Fase 1 concluída com sucesso. Realizado o teste de aderência da "
                "massa acrílica e iniciada a pintura do Bloco A."
            ),
        },
        {
            "title": "Modernização da Iluminação para LED nas Garagens",
            "desc": (
                "Substituição de reatores e lâmpadas fluorescentes por luminárias "
                "LED com sensor de presença integrado."
            ),
            "contractor": "EletroLuz Serviços Elétricos",
            "total_budget": 18500.0,
            "executed_budget": 18500.0,
            "progress": 100.0,
            "status": ProjectStatus.COMPLETED,
            "start": today - timedelta(days=90),
            "est_completion": today - timedelta(days=10),
            "milestones": [
                (
                    "Instalação dos novos circuitos e disjuntores",
                    MilestoneStatus.DONE,
                    today - timedelta(days=45),
                ),
                (
                    "Substituição das 120 luminárias LED",
                    MilestoneStatus.DONE,
                    today - timedelta(days=15),
                ),
            ],
            "update_text": (
                "Obra entregue. Economia estimada em 40% na conta de energia das "
                "áreas comuns."
            ),
        },
        {
            "title": "Instalação de Sistema Solar Fotovoltaico",
            "desc": (
                "Implementação de 48 painéis solares no telhado para geração "
                "destinada à portaria e bombas."
            ),
            "contractor": "SolarTech Energia Renovável",
            "total_budget": 85000.0,
            "executed_budget": 0.0,
            "progress": 0.0,
            "status": ProjectStatus.PLANNED,
            "start": today + timedelta(days=30),
            "est_completion": today + timedelta(days=120),
            "milestones": [
                (
                    "Homologação do projeto junto à concessionária de energia",
                    MilestoneStatus.NEXT_STEPS,
                    today + timedelta(days=45),
                ),
                (
                    "Montagem dos suportes de alumínio e placas solares",
                    MilestoneStatus.NEXT_STEPS,
                    today + timedelta(days=80),
                ),
            ],
            "update_text": None,
        },
    ]
    for p_spec in projects_data:
        proj = session.exec(
            select(ConstructionProject).where(
                ConstructionProject.tenant_id == tenant_id,
                ConstructionProject.title == p_spec["title"],
            )
        ).first()
        if not proj:
            proj = ConstructionProject(
                tenant_id=tenant_id,
                title=p_spec["title"],
                description=p_spec["desc"],
                contractor_name=p_spec["contractor"],
                total_budget=_money(p_spec["total_budget"]),
                executed_budget=_money(p_spec["executed_budget"]),
                physical_progress_pct=p_spec["progress"],
                status=p_spec["status"],
                start_date=p_spec["start"],
                estimated_completion_date=p_spec["est_completion"],
                actual_completion_date=p_spec["est_completion"]
                if p_spec["status"] == ProjectStatus.COMPLETED
                else None,
            )
            session.add(proj)
            session.commit()
            session.refresh(proj)

            for idx, (m_title, m_status, m_due) in enumerate(p_spec["milestones"]):
                session.add(
                    ProjectMilestone(
                        project_id=proj.id,
                        title=m_title,
                        status=m_status,
                        due_date=m_due,
                        display_order=idx + 1,
                    )
                )
            if p_spec["update_text"]:
                session.add(
                    ProjectUpdate(
                        project_id=proj.id,
                        author_id=sindico_user.id,
                        title="Relatório Semanal de Andamento",
                        content=p_spec["update_text"],
                    )
                )
            session.commit()
    print(" Seeded construction projects, milestones and updates.")

    # 13. Photo Approvals (/admin/photo-approvals)
    media_specs = [
        {
            "entity_type": EntityType.RESIDENT,
            "path": "photos/resident_ana_pending.jpg",
            "url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400",
            "status": PhotoApprovalStatus.PENDING_APPROVAL,
            "uploaded_by": morador_user,
            "approved_by": None,
        },
        {
            "entity_type": EntityType.OCCURRENCE,
            "path": "photos/occ_vazamento_pending.jpg",
            "url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=400",
            "status": PhotoApprovalStatus.PENDING_APPROVAL,
            "uploaded_by": morador_user,
            "approved_by": None,
        },
        {
            "entity_type": EntityType.RESIDENT,
            "path": "photos/resident_carlos_approved.jpg",
            "url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400",
            "status": PhotoApprovalStatus.APPROVED,
            "uploaded_by": sindico_user,
            "approved_by": admin_user,
        },
    ]
    for m_spec in media_specs:
        existing_m = session.exec(
            select(MediaAsset).where(
                MediaAsset.tenant_id == tenant_id,
                MediaAsset.file_path == m_spec["path"],
            )
        ).first()
        if not existing_m:
            session.add(
                MediaAsset(
                    tenant_id=tenant_id,
                    entity_type=m_spec["entity_type"],
                    storage_provider=StorageProvider.LOCAL_DISK,
                    file_path=m_spec["path"],
                    url=m_spec["url"],
                    file_size_bytes=380000,
                    mime_type="image/jpeg",
                    status=m_spec["status"],
                    uploaded_by_id=m_spec["uploaded_by"].id,
                    approved_by_id=m_spec["approved_by"].id
                    if m_spec["approved_by"]
                    else None,
                    approved_at=now
                    if m_spec["status"] == PhotoApprovalStatus.APPROVED
                    else None,
                )
            )
            session.commit()
    print(" Seeded media assets for photo approval queue.")

    # 14. Access Control & Gate Monitor (/admin/access-control, /gate-monitor)
    devices_data = [
        (
            "Totem Facial - Portaria Social",
            "Entrada Social de Pedestres",
            "DEV-SOCIAL-01",
            AccessDeviceStatus.ONLINE,
        ),
        (
            "Leitor Facial - Garagem Subsolo 1",
            "Acesso de Veículos Portão 1",
            "DEV-GARAGEM-01",
            AccessDeviceStatus.ONLINE,
        ),
        (
            "Totem Facial - Entrada de Serviço",
            "Guarita Lateral / Serviços",
            "DEV-SERVICO-01",
            AccessDeviceStatus.OFFLINE,
        ),
    ]
    devices_map: dict[str, AccessDevice] = {}
    for d_name, d_loc, d_key, d_status in devices_data:
        dev = session.exec(
            select(AccessDevice).where(
                AccessDevice.tenant_id == tenant_id, AccessDevice.name == d_name
            )
        ).first()
        if not dev:
            dev = AccessDevice(
                tenant_id=tenant_id,
                name=d_name,
                location=d_loc,
                device_key=d_key,
                status=d_status,
                last_seen_at=now
                if d_status == AccessDeviceStatus.ONLINE
                else now - timedelta(days=2),
                created_by_id=admin_user.id,
            )
            session.add(dev)
            session.commit()
            session.refresh(dev)
        devices_map[d_name] = dev

    totem_social = devices_map.get("Totem Facial - Portaria Social")
    leitor_garagem = devices_map.get("Leitor Facial - Garagem Subsolo 1")
    ana_res = residents_map.get("Ana Souza")
    carlos_res = residents_map.get("Carlos Silva")

    if totem_social and ana_res:
        existing_event = session.exec(
            select(FacialAccessEvent).where(
                FacialAccessEvent.device_id == totem_social.id,
                FacialAccessEvent.resident_id == ana_res.id,
            )
        ).first()
        if not existing_event:
            session.add(
                FacialAccessEvent(
                    device_id=totem_social.id,
                    resident_id=ana_res.id,
                    matched=True,
                    confidence_score=0.98,
                    access_granted=True,
                    event_time=now - timedelta(minutes=25),
                )
            )
            session.add(
                FacialAccessEvent(
                    device_id=totem_social.id,
                    resident_id=None,
                    matched=False,
                    confidence_score=0.38,
                    access_granted=False,
                    event_time=now - timedelta(minutes=45),
                    raw_payload="Acesso não reconhecido na base biométrica",
                )
            )
            session.commit()

    if leitor_garagem and carlos_res:
        existing_event_garagem = session.exec(
            select(FacialAccessEvent).where(
                FacialAccessEvent.device_id == leitor_garagem.id,
                FacialAccessEvent.resident_id == carlos_res.id,
            )
        ).first()
        if not existing_event_garagem:
            session.add(
                FacialAccessEvent(
                    device_id=leitor_garagem.id,
                    resident_id=carlos_res.id,
                    matched=True,
                    confidence_score=0.96,
                    access_granted=True,
                    event_time=now - timedelta(hours=1, minutes=10),
                )
            )
            session.commit()
    print(" Seeded access control devices and access events.")

    # 15. Infractions & Rules (/infractions, /infraction-rules, /my-infractions)
    inf_settings = session.exec(
        select(InfractionSettings).where(InfractionSettings.tenant_id == tenant_id)
    ).first()
    if not inf_settings:
        session.add(
            InfractionSettings(
                tenant_id=tenant_id,
                condo_fee_amount=Decimal("650.00"),
                updated_by_id=sindico_user.id,
            )
        )
        session.commit()

    # Rule 1: Noise / Barulho
    rule_ruido = session.exec(
        select(InfractionRule).where(
            InfractionRule.tenant_id == tenant_id,
            InfractionRule.article == "Art. 18",
        )
    ).first()
    if not rule_ruido:
        rule_ruido = InfractionRule(
            tenant_id=tenant_id,
            article="Art. 18",
            origin=InfractionRuleOrigin.REGIMENTO_INTERNO,
            description=(
                "Perturbação do sossego com som excessivo ou algazarra após 22h."
            ),
            recidivism_window_days=90,
            is_active=True,
        )
        session.add(rule_ruido)
        session.commit()
        session.refresh(rule_ruido)

        session.add(
            InfractionPolicyStep(
                rule_id=rule_ruido.id,
                step_order=1,
                action=InfractionStepAction.AVISO,
                defense_deadline_days=7,
                note="Advertência preliminar orientativa",
            )
        )
        session.add(
            InfractionPolicyStep(
                rule_id=rule_ruido.id,
                step_order=2,
                action=InfractionStepAction.NOTIFICACAO,
                defense_deadline_days=10,
                fine_mode=InfractionFineMode.FIXED,
                fine_fixed_amount=Decimal("200.00"),
                note="Notificação formal com aplicação de multa leve",
            )
        )
        session.add(
            InfractionPolicyStep(
                rule_id=rule_ruido.id,
                step_order=3,
                action=InfractionStepAction.MULTA,
                defense_deadline_days=15,
                fine_mode=InfractionFineMode.MULTIPLE,
                fine_fee_multiplier=Decimal("1.0000"),
                note="Multa por reincidência equivalente a 1 cota condominial",
            )
        )
        session.commit()

    # Rule 2: Parking / Garagem
    rule_garagem = session.exec(
        select(InfractionRule).where(
            InfractionRule.tenant_id == tenant_id,
            InfractionRule.article == "Art. 24",
        )
    ).first()
    if not rule_garagem:
        rule_garagem = InfractionRule(
            tenant_id=tenant_id,
            article="Art. 24",
            origin=InfractionRuleOrigin.REGIMENTO_INTERNO,
            description=(
                "Estacionamento em local proibido, faixa de circulação ou vaga alheia."
            ),
            recidivism_window_days=60,
            is_active=True,
        )
        session.add(rule_garagem)
        session.commit()
        session.refresh(rule_garagem)

        session.add(
            InfractionPolicyStep(
                rule_id=rule_garagem.id,
                step_order=1,
                action=InfractionStepAction.AVISO,
                defense_deadline_days=5,
                note="Aviso orientativo ao condômino para desobstrução imediata",
            )
        )
        session.add(
            InfractionPolicyStep(
                rule_id=rule_garagem.id,
                step_order=2,
                action=InfractionStepAction.NOTIFICACAO,
                defense_deadline_days=10,
                fine_mode=InfractionFineMode.FIXED,
                fine_fixed_amount=Decimal("150.00"),
                note="Notificação com multa de vaga de garagem",
            )
        )
        session.commit()

    # Create Infractions: one on unit 101 for /my-infractions test, one on unit 201
    if rule_ruido and ana_res:
        existing_inf1 = session.exec(
            select(Infraction).where(
                Infraction.tenant_id == tenant_id,
                Infraction.lot_id == lot_101.id,
                Infraction.rule_id == rule_ruido.id,
            )
        ).first()
        if not existing_inf1:
            inf1 = Infraction(
                tenant_id=tenant_id,
                rule_id=rule_ruido.id,
                lot_id=lot_101.id,
                responsible_resident_id=ana_res.id,
                registered_by_id=sindico_user.id,
                occurred_on=today - timedelta(days=6),
                description=(
                    "Reunião com som alto e instrumentos na varanda gourmet após 23h30."
                ),
            )
            session.add(inf1)
            session.commit()
            session.refresh(inf1)

            st1 = InfractionStage(
                infraction_id=inf1.id,
                action=InfractionStepAction.AVISO,
                applied_on=today - timedelta(days=5),
                note="Advertência por escrito emitida após reclamações de vizinhos.",
                actor_id=sindico_user.id,
            )
            session.add(st1)
            session.commit()
            session.refresh(st1)

            st2 = InfractionStage(
                infraction_id=inf1.id,
                action=InfractionStepAction.NOTIFICACAO,
                applied_on=today - timedelta(days=2),
                fine_amount=Decimal("200.00"),
                defense_due_on=today + timedelta(days=8),
                note=("Notificação com multa de R$ 200,00 após reincidência de ruído."),
                actor_id=sindico_user.id,
            )
            session.add(st2)
            session.commit()
            session.refresh(st2)

            session.add(
                InfractionContestation(
                    infraction_id=inf1.id,
                    stage_id=st2.id,
                    body=(
                        "Esclareço que o ruído excessivo não partiu da minha unidade, "
                        "mas sim de vizinhos confraternizando. Peço a reconsideração."
                    ),
                    submitted_by_id=morador_user.id,
                )
            )
            session.commit()

    roberto_res = residents_map.get("Roberto Alves")
    if rule_garagem and roberto_res:
        existing_inf2 = session.exec(
            select(Infraction).where(
                Infraction.tenant_id == tenant_id,
                Infraction.lot_id == lot_201.id,
                Infraction.rule_id == rule_garagem.id,
            )
        ).first()
        if not existing_inf2:
            inf2 = Infraction(
                tenant_id=tenant_id,
                rule_id=rule_garagem.id,
                lot_id=lot_201.id,
                responsible_resident_id=roberto_res.id,
                registered_by_id=zelador_user.id,
                occurred_on=today - timedelta(days=4),
                description=(
                    "Veículo estacionado sobre faixa amarela impedindo passagem."
                ),
            )
            session.add(inf2)
            session.commit()
            session.refresh(inf2)

            session.add(
                InfractionStage(
                    infraction_id=inf2.id,
                    action=InfractionStepAction.AVISO,
                    applied_on=today - timedelta(days=3),
                    note="Primeiro aviso deixado no para-brisa do automóvel.",
                    actor_id=zelador_user.id,
                )
            )
            session.commit()
    print(" Seeded infraction rules, infractions, stages and contestation.")

    # 16. Assembly & Voting (/voting)
    existing_assembly = session.exec(
        select(Assembly).where(
            Assembly.tenant_id == tenant_id,
            Assembly.title == "AGO 2026 - Assembleia Geral Ordinária",
        )
    ).first()
    if not existing_assembly:
        existing_assembly = Assembly(
            tenant_id=tenant_id,
            title="AGO 2026 - Assembleia Geral Ordinária",
            type=AssemblyType.AGO,
            held_on=today + timedelta(days=15),
            agenda=(
                "1. Prestação de contas 2025; 2. Previsão 2026; 3. Eleição diretoria."
            ),
            status=AssemblyStatus.OPEN,
            created_by_id=sindico_user.id,
        )
        session.add(existing_assembly)
        session.commit()
        session.refresh(existing_assembly)

    # Vote 1: Assembly item
    vote_ago = session.exec(
        select(Vote).where(
            Vote.tenant_id == tenant_id,
            Vote.title == "Aprovação das Contas do Exercício de 2025",
        )
    ).first()
    if not vote_ago:
        vote_ago = Vote(
            tenant_id=tenant_id,
            assembly_id=existing_assembly.id,
            kind=VoteKind.ASSEMBLEIA,
            title="Aprovação das Contas do Exercício de 2025",
            description=(
                "Votação formal sobre parecer do conselho fiscal e aprovação de contas."
            ),
            vote_type=VoteType.SINGLE_CHOICE,
            status=VoteStatus.OPEN,
            is_anonymous=False,
            opens_at=now - timedelta(days=1),
            closes_at=now + timedelta(days=16),
            created_by_id=sindico_user.id,
        )
        session.add(vote_ago)
        session.commit()
        session.refresh(vote_ago)

        opt1 = VoteOption(
            vote_id=vote_ago.id,
            label="Aprovar integralmente sem ressalvas",
            order_index=1,
        )
        opt2 = VoteOption(
            vote_id=vote_ago.id,
            label="Aprovar com as ressalvas do Conselho Fiscal",
            order_index=2,
        )
        opt3 = VoteOption(
            vote_id=vote_ago.id,
            label="Rejeitar a prestação de contas",
            order_index=3,
        )
        session.add_all([opt1, opt2, opt3])
        session.commit()
        session.refresh(opt1)

        # Cast test ballot from Morador
        session.add(
            Ballot(
                vote_id=vote_ago.id,
                voter_key=f"lot:{lot_101.id}",
                lot_id=lot_101.id,
                voter_user_id=morador_user.id,
                fraction_ideal_at_cast=0.045,
                selected_option_ids_json=json.dumps([str(opt1.id)]),
            )
        )
        session.commit()

    # Vote 2: Standalone Poll (Enquete)
    vote_enquete = session.exec(
        select(Vote).where(
            Vote.tenant_id == tenant_id,
            Vote.title == "Instalação de Carregadores para Carros Elétricos nas Vagas",
        )
    ).first()
    if not vote_enquete:
        vote_enquete = Vote(
            tenant_id=tenant_id,
            assembly_id=None,
            kind=VoteKind.ENQUETE,
            title="Instalação de Carregadores para Carros Elétricos nas Vagas",
            description=(
                "Enquete consultiva para avaliar interesse em pontos de recarga."
            ),
            vote_type=VoteType.SINGLE_CHOICE,
            status=VoteStatus.OPEN,
            is_anonymous=False,
            opens_at=now - timedelta(days=2),
            closes_at=now + timedelta(days=20),
            created_by_id=sindico_user.id,
        )
        session.add(vote_enquete)
        session.commit()
        session.refresh(vote_enquete)

        opt_e1 = VoteOption(
            vote_id=vote_enquete.id,
            label="Favorável com rateio geral da infraestrutura básica",
            order_index=1,
        )
        opt_e2 = VoteOption(
            vote_id=vote_enquete.id,
            label="Favorável com custo 100% individual por usuário interessado",
            order_index=2,
        )
        opt_e3 = VoteOption(
            vote_id=vote_enquete.id,
            label="Desfavorável à instalação neste momento",
            order_index=3,
        )
        session.add_all([opt_e1, opt_e2, opt_e3])
        session.commit()
    print(" Seeded assembly sessions, votes and ballots.")

    # 17. Assets & Inventory (/assets)
    assets_data = [
        {
            "name": "Cortador de Grama Trapp a Gasolina 6.5HP",
            "cat": AssetCategory.FERRAMENTAS,
            "tag": "PAT-00101",
            "loc": "DML / Casa de Máquinas",
            "val": 2450.0,
            "consumable": False,
            "qty": 1,
            "cond": AssetCondition.BOM,
        },
        {
            "name": "Lavadora de Alta Pressão Kärcher HD 585 Industrial",
            "cat": AssetCategory.FERRAMENTAS,
            "tag": "PAT-00102",
            "loc": "DML Subsolo",
            "val": 3200.0,
            "consumable": False,
            "qty": 1,
            "cond": AssetCondition.BOM,
        },
        {
            "name": "Gerador de Energia Cummins 50kVA Silenciado",
            "cat": AssetCategory.MANUTENCAO,
            "tag": "PAT-00103",
            "loc": "Sala de Força Subsolo 2",
            "val": 48000.0,
            "consumable": False,
            "qty": 1,
            "cond": AssetCondition.NOVO,
        },
        {
            "name": "Lâmpadas LED Tubulares T8 18W Bivolt",
            "cat": AssetCategory.MANUTENCAO,
            "tag": None,
            "loc": "Almoxarifado Portaria",
            "val": 14.50,
            "consumable": True,
            "qty": 24,
            "cond": AssetCondition.NOVO,
        },
        {
            "name": "Sacos de Lixo Reforçados 100 Litros",
            "cat": AssetCategory.LIMPEZA,
            "tag": None,
            "loc": "Almoxarifado Subsolo",
            "val": 0.85,
            "consumable": True,
            "qty": 150,
            "cond": AssetCondition.NOVO,
        },
    ]
    for a_data in assets_data:
        asset = session.exec(
            select(Asset).where(
                Asset.tenant_id == tenant_id, Asset.name == a_data["name"]
            )
        ).first()
        if not asset:
            asset = Asset(
                tenant_id=tenant_id,
                name=a_data["name"],
                category=a_data["cat"],
                asset_tag=a_data["tag"],
                location=a_data["loc"],
                acquisition_value=_money(a_data["val"]),
                acquisition_date=today - timedelta(days=180),
                condition=a_data["cond"],
                is_consumable=a_data["consumable"],
                current_quantity=a_data["qty"],
                min_quantity=10 if a_data["consumable"] else None,
                unit_of_measure="un",
            )
            session.add(asset)
            session.commit()
            session.refresh(asset)

            if a_data["consumable"]:
                session.add(
                    InventoryMovement(
                        tenant_id=tenant_id,
                        asset_id=asset.id,
                        movement_type=MovementType.ENTRADA,
                        quantity=a_data["qty"] + 10,
                        previous_quantity=0,
                        new_quantity=a_data["qty"] + 10,
                        performed_by_id=zelador_user.id,
                        reason="Compra de reposição de estoque mensal",
                        created_at=now - timedelta(days=10),
                    )
                )
                session.add(
                    InventoryMovement(
                        tenant_id=tenant_id,
                        asset_id=asset.id,
                        movement_type=MovementType.SAIDA,
                        quantity=10,
                        previous_quantity=a_data["qty"] + 10,
                        new_quantity=a_data["qty"],
                        performed_by_id=zelador_user.id,
                        reason="Consumo para manutenção das áreas comuns",
                        created_at=now - timedelta(days=3),
                    )
                )
                session.commit()
    print(" Seeded assets and inventory movements.")

    # 18. Purchases & Quotations (/purchases)
    req1 = session.exec(
        select(PurchaseRequest).where(
            PurchaseRequest.tenant_id == tenant_id,
            PurchaseRequest.title
            == "Aquisição de 4 Câmeras Speed Dome IP para o Perímetro",
        )
    ).first()
    if not req1:
        req1 = PurchaseRequest(
            tenant_id=tenant_id,
            title="Aquisição de 4 Câmeras Speed Dome IP para o Perímetro",
            description=(
                "Substituição de câmeras antigas com falha e "
                "eliminação de pontos cegos."
            ),
            general_notes=(
                "Cotação aberta com 3 fornecedores especializados em CFTV condominial."
            ),
            status=PurchaseRequestStatus.OPEN,
            requested_by_id=sindico_user.id,
        )
        session.add(req1)
        session.commit()
        session.refresh(req1)

        # APRAS-73: the request enumerates the lines and each quote prices
        # them. The demo deliberately shows all three states the grid has --
        # a line one supplier skipped, a supplier's own extra line, and an
        # offered model that differs between columns.
        req1.items = [
            PurchaseRequestItem(
                description="Câmera Speed Dome IP 4MP", quantity=4, position=0
            ),
            PurchaseRequestItem(
                description="Instalação e configuração", quantity=1, position=1
            ),
            PurchaseRequestItem(
                description="Cabo UTP CAT6 (rolo de 100 m)", quantity=2, position=2
            ),
        ]
        session.commit()
        session.refresh(req1)
        camera, install, cable = req1.items

        complete_quote = PurchaseQuote(
            purchase_request_id=req1.id,
            supplier_name="SegurMax Soluções em Segurança",
            supplier_contact="(11) 3456-7890 - Carlos Vendas",
            notes="Entrega em 5 dias úteis. Garantia estendida de 2 anos inclusa.",
            created_by_id=sindico_user.id,
        )
        complete_quote.items = [
            PurchaseQuoteItem(
                request_item_id=camera.id,
                model="Intelbras VIP 5432 SD IA",
                unit_price=Decimal("1450.00"),
                position=0,
            ),
            PurchaseQuoteItem(
                request_item_id=install.id,
                unit_price=Decimal("1200.00"),
                position=1,
            ),
            PurchaseQuoteItem(
                request_item_id=cable.id,
                model="Furukawa CAT6 U/UTP",
                unit_price=Decimal("480.00"),
                position=2,
            ),
        ]
        session.add(complete_quote)

        partial_quote = PurchaseQuote(
            purchase_request_id=req1.id,
            supplier_name="CFTV Express Distribuidora",
            supplier_contact="(11) 4567-8901 - Amanda",
            notes="Inclui suportes de parede e conectores blindados de brinde.",
            created_by_id=sindico_user.id,
        )
        partial_quote.items = [
            PurchaseQuoteItem(
                request_item_id=camera.id,
                model="Hikvision DS-2DE4A425IW",
                unit_price=Decimal("1620.00"),
                position=0,
            ),
            PurchaseQuoteItem(
                request_item_id=cable.id,
                unit_price=Decimal("440.00"),
                position=1,
            ),
            # The supplier's own line: no `request_item_id`, so it counts
            # toward the total and never toward coverage.
            PurchaseQuoteItem(
                description="Nobreak 1,2 kVA para o rack",
                quantity=1,
                unit_price=Decimal("890.00"),
                position=2,
            ),
        ]
        session.add(partial_quote)
        session.commit()

    req2 = session.exec(
        select(PurchaseRequest).where(
            PurchaseRequest.tenant_id == tenant_id,
            PurchaseRequest.title == "Troca da Areia e Válvulas dos Filtros da Piscina",
        )
    ).first()
    if not req2:
        req2 = PurchaseRequest(
            tenant_id=tenant_id,
            title="Troca da Areia e Válvulas dos Filtros da Piscina",
            description=(
                "Manutenção preventiva dos filtros de areia para a temporada de verão."
            ),
            general_notes=(
                "Orçamento aprovado após análise técnica da equipe de conservação."
            ),
            status=PurchaseRequestStatus.DECIDED,
            requested_by_id=zelador_user.id,
        )
        session.add(req2)
        session.commit()
        session.refresh(req2)

        req2.items = [
            PurchaseRequestItem(
                description="Troca da carga de areia e das crepinas",
                quantity=1,
                position=0,
            )
        ]
        session.commit()
        session.refresh(req2)

        chosen_q = PurchaseQuote(
            purchase_request_id=req2.id,
            supplier_name="Piscinas Cristalinas Manutenção Ltda",
            supplier_contact="(11) 98888-2233 - Roberto",
            notes=(
                "Serviço completo incluindo remoção de carga antiga, areia e crepinas."
            ),
            created_by_id=zelador_user.id,
        )
        chosen_q.items = [
            PurchaseQuoteItem(
                request_item_id=req2.items[0].id,
                unit_price=Decimal("2800.00"),
                position=0,
            )
        ]
        session.add(chosen_q)
        session.commit()
        session.refresh(chosen_q)

        session.add(
            PurchaseQuoteDecision(
                purchase_request_id=req2.id,
                quote_id=chosen_q.id,
                decided_by_id=sindico_user.id,
                justification=(
                    "Fornecedor homologado com excelente histórico no condomínio."
                ),
            )
        )
        session.commit()
    print(" Seeded purchase requests, quotes and decisions.")


def _seed_secondary_tenant_data(
    session: Session,
    tenant_id: UUID,
    users_map: dict[str, User],
) -> None:
    """Populate minimal demo data for secondary tenant to showcase switching."""
    now = clock.db_now()
    admin_user = users_map["admin@apras.com"]
    zelador_user = users_map["zelador@apras.com"]

    # 1. Two lots
    lots_data = [("Quadra A", "Lote 01"), ("Quadra A", "Lote 02")]
    for block, lot_number in lots_data:
        lot = session.exec(
            select(Lot).where(
                Lot.tenant_id == tenant_id,
                Lot.block == block,
                Lot.lot_number == lot_number,
            )
        ).first()
        if not lot:
            session.add(
                Lot(
                    tenant_id=tenant_id,
                    block=block,
                    lot_number=lot_number,
                    status=LotStatus.OCCUPIED,
                    area_sqm=350.0,
                )
            )
            session.commit()
    print(" Seeded minimal lots for secondary tenant.")

    # 2. Category & Single Task
    cat = session.exec(
        select(Category).where(
            Category.tenant_id == tenant_id, Category.name == "Manutenção Geral"
        )
    ).first()
    if not cat:
        cat = Category(tenant_id=tenant_id, name="Manutenção Geral", color="#ea580c")
        session.add(cat)
        session.commit()
        session.refresh(cat)

    task = session.exec(
        select(Task).where(
            Task.tenant_id == tenant_id,
            Task.title == "Vistoria da cerca perimetral e portão de acesso",
        )
    ).first()
    if not task:
        session.add(
            Task(
                tenant_id=tenant_id,
                title="Vistoria da cerca perimetral e portão de acesso",
                description=(
                    "Verificação dos sensores de infravermelho e concertina perimetral."
                ),
                status=TaskStatus.PENDING,
                priority=TaskPriority.MEDIUM,
                category_id=cat.id,
                created_by_id=admin_user.id,
                assigned_to_id=zelador_user.id,
                due_date=now + timedelta(days=5),
            )
        )
        session.commit()
    print(" Seeded minimal task for secondary tenant.")

    # 3. Single Announcement
    ann = session.exec(
        select(Announcement).where(
            Announcement.tenant_id == tenant_id,
            Announcement.title == "Boas-vindas ao Condomínio Solar da Serra",
        )
    ).first()
    if not ann:
        session.add(
            Announcement(
                tenant_id=tenant_id,
                title="Boas-vindas ao Condomínio Solar da Serra",
                content=(
                    "Ambiente digital ativado com sucesso para gestão da "
                    "Associação de Moradores Solar da Serra."
                ),
                author_id=admin_user.id,
            )
        )
        session.commit()
    print(" Seeded minimal announcement for secondary tenant.")


def run_seed(db_url: str | None = None) -> None:
    """Run idempotent seed populating both tenants and 100% of screens."""
    target_url = db_url or settings.database_url
    print(f"Connecting to database: {target_url}...")
    engine = create_engine(target_url)

    with Session(engine) as session:
        print("\n🚀 Starting comprehensive demo seeding...")

        # 1. Tenants
        t1, t2 = _seed_tenants(session)

        # 2. Roles & Permissions
        t1_roles = _ensure_role_permissions(session, t1.id)
        t2_roles = _ensure_role_permissions(session, t2.id)
        print(
            f" Loaded {len(t1_roles)} roles for primary and "
            f"{len(t2_roles)} for secondary tenant."
        )

        # 3. Users with links to both tenants
        users_map = _seed_users(session, t1.id, t2.id, t1_roles, t2_roles)

        # 4. SaaS Plans & Subscriptions
        _seed_plans_and_subscriptions(session, t1.id, t2.id)

        # 5. Primary Tenant: 100% full dataset across all modules
        print(
            "\n📦 Populating 100% of screens for Primary Tenant (Parque das Flores)..."
        )
        _seed_primary_tenant_data(session, t1.id, users_map, t1_roles)

        # 6. Secondary Tenant: minimal dataset to demonstrate switching
        print(
            "\n📦 Populating minimal demo data for Secondary Tenant (Solar da Serra)..."
        )
        _seed_secondary_tenant_data(session, t2.id, users_map)

        print("\n🎉 Seed demo finalizado com sucesso!")
        print("Associações criadas:")
        print(f"  1. {t1.name} (100% populada para todas as telas)")
        print(f"  2. {t2.name} (dados mínimos para demonstrar a troca)")
        print("\nUsuários criados para teste (senha para todos: demo1234):")
        print(
            "  • admin@apras.com — Administrador do Sistema (Administrador, superuser)"
        )
        print("  • sindico@apras.com — Carlos Silva (Diretor / Síndico)")
        print("  • zelador@apras.com — Marcos Oliveira (Gerente / Zelador)")
        print("  • porteiro@apras.com — José Santos (Porteiro)")
        print("  • morador@apras.com — Ana Souza (Morador)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed APRAS with demo data.")
    parser.add_argument(
        "--db-url",
        dest="db_url",
        default=None,
        help="PostgreSQL connection string (defaults to POSTGRES_URL from settings).",
    )
    args = parser.parse_args()
    run_seed(args.db_url)
