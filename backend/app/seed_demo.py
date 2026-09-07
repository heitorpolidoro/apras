"""Idempotent seed script to populate APRAS database with realistic demo data.

Safe to run against any database: does not truncate or drop any tables.
Reuses or creates records without duplicates.
"""

import argparse
import sys
import uuid
from datetime import date, datetime, timedelta

from sqlmodel import Session, create_engine, select

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.announcement import Announcement
from app.models.category import Category
from app.models.enums import (
    AuthorizationStatus,
    AuthorizationType,
    LotAssociationType,
    LotStatus,
    OccurrenceCategory,
    OccurrencePriority,
    OccurrenceStatus,
    PackageStatus,
    ReservationStatus,
    TaskPriority,
    TaskStatus,
    TransactionType,
)
from app.models.finance import FinanceCategory, FinancialTransaction
from app.models.lot import Lot, UserLotLink
from app.models.occurrence import Occurrence
from app.models.package import Package
from app.models.reservation import ReservableSpace, SpaceReservation
from app.models.role import Role
from app.models.task import Task
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from app.models.visitor import Visitor, VisitorAuthorization
from app.services.tenant_service import TenantService

DEMO_PASSWORD = "demo1234"


def run_seed(db_url: str | None = None) -> None:
    target_url = db_url or settings.database_url
    print("Connecting to database...")
    engine = create_engine(target_url)

    with Session(engine) as session:
        print("Starting idempotent demo seeding...")

        # 1. Tenant
        tenant = session.exec(
            select(Tenant).where(Tenant.id == DEFAULT_TENANT_ID)
        ).first()
        if not tenant:
            tenant = Tenant(
                id=DEFAULT_TENANT_ID,
                name="Condomínio Residencial Parque das Flores",
                is_active=True,
            )
            session.add(tenant)
            session.commit()
            session.refresh(tenant)
            print(" Created default Tenant.")
        else:
            print(f" Existing Tenant: {tenant.name}")

        tenant_id = tenant.id

        # 2. Legacy Roles
        TenantService.ensure_legacy_roles(session, tenant_id)
        session.commit()

        roles_by_name = {
            r.name: r
            for r in session.exec(select(Role).where(Role.tenant_id == tenant_id)).all()
        }
        print(f" Loaded {len(roles_by_name)} roles.")

        # 3. Ensure Heitor has Administrador role
        heitor = session.exec(
            select(User).where(User.email == "heitor.polidoro@gmail.com")
        ).first()
        if heitor:
            admin_role = roles_by_name.get("Administrador (papel)")
            if admin_role and admin_role not in heitor.roles:
                heitor.roles.append(admin_role)
                session.add(heitor)
                session.commit()
                print(f" Assigned Administrador role to {heitor.email}.")

        # 4. Demo Users
        users_specs = [
            {
                "email": "admin@apras.com",
                "full_name": "Administrador do Sistema",
                "cpf": "52998224725",
                "is_superuser": True,
                "role": "Administrador (papel)",
            },
            {
                "email": "sindico@apras.com",
                "full_name": "Carlos Silva (Síndico)",
                "cpf": "11144477735",
                "is_superuser": False,
                "role": "Diretor (papel)",
            },
            {
                "email": "zelador@apras.com",
                "full_name": "Marcos Oliveira (Zelador)",
                "cpf": "08050681057",
                "is_superuser": False,
                "role": "Gerente (papel)",
            },
            {
                "email": "porteiro@apras.com",
                "full_name": "José Santos (Portaria)",
                "cpf": "07491723040",
                "is_superuser": False,
                "role": "Porteiro (papel)",
            },
            {
                "email": "morador@apras.com",
                "full_name": "Ana Souza (Moradora)",
                "cpf": "38812345678",
                "is_superuser": False,
                "role": "Morador (papel)",
            },
        ]

        users_map: dict[str, User] = {}
        for spec in users_specs:
            user = session.exec(
                select(User).where(User.email == spec["email"])
            ).first()
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
                session.add(user)
                session.commit()
                session.refresh(user)

            # Link role
            role_obj = roles_by_name.get(spec["role"])
            if role_obj and role_obj not in user.roles:
                user.roles.append(role_obj)
                session.add(user)
                session.commit()

            # Link tenant
            link = session.exec(
                select(UserTenantLink).where(
                    UserTenantLink.user_id == user.id,
                    UserTenantLink.tenant_id == tenant_id,
                )
            ).first()
            if not link:
                session.add(
                    UserTenantLink(user_id=user.id, tenant_id=tenant_id)
                )
                session.commit()

            users_map[spec["email"]] = user

        # 5. Lots / Units
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

        # Link morador to Bloco A 101
        morador_user = users_map.get("morador@apras.com")
        lot_101 = lots_map.get(("Bloco A", "101"))
        if morador_user and lot_101:
            u_link = session.exec(
                select(UserLotLink).where(
                    UserLotLink.user_id == morador_user.id,
                    UserLotLink.lot_id == lot_101.id,
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

        # 6. Task Categories
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
                    Category.tenant_id == tenant_id,
                    Category.name == c_data["name"],
                )
            ).first()
            if not cat:
                cat = Category(
                    tenant_id=tenant_id,
                    name=c_data["name"],
                    color=c_data["color"],
                )
                session.add(cat)
                session.commit()
                session.refresh(cat)
            cats_map[c_data["name"]] = cat
        print(f" Loaded {len(cats_map)} task categories.")

        # 7. Tasks
        now = datetime.utcnow()
        tasks_specs = [
            {
                "title": "Vistoria periódica dos para-raios e laudo SPDA",
                "description": "Contratar empresa credenciada para medição ôhmica e renovação do laudo técnico de para-raios.",
                "status": TaskStatus.IN_PROGRESS,
                "priority": TaskPriority.HIGH,
                "category": "Manutenção Predial",
                "assigned_email": "sindico@apras.com",
                "due_days": 12,
            },
            {
                "title": "Manutenção preventiva das bombas de recalque da caixa d'água",
                "description": "Verificar rolamentos, vedação mecânica e alternância automática do conjunto motobomba.",
                "status": TaskStatus.PENDING,
                "priority": TaskPriority.URGENT,
                "category": "Manutenção Predial",
                "assigned_email": "zelador@apras.com",
                "due_days": 3,
            },
            {
                "title": "Substituição de lâmpadas de emergência nas escadarias",
                "description": "Testar baterias das luminárias autônomas de emergência nos blocos A e B.",
                "status": TaskStatus.IN_PROGRESS,
                "priority": TaskPriority.MEDIUM,
                "category": "Segurança & Portaria",
                "assigned_email": "zelador@apras.com",
                "due_days": 7,
            },
            {
                "title": "Cotação para modernização do sistema de interfonia",
                "description": "Solicitar 3 orçamentos para migração do cabeamento analógico para interfonia IP/digital.",
                "status": TaskStatus.PENDING,
                "priority": TaskPriority.MEDIUM,
                "category": "Administrativo & Financeiro",
                "assigned_email": "sindico@apras.com",
                "due_days": 15,
            },
            {
                "title": "Dedetização semestral das áreas comuns e garagens",
                "description": "Aplicação de barreira química contra insetos e roedores no subsolo e lixeiras.",
                "status": TaskStatus.COMPLETED,
                "priority": TaskPriority.LOW,
                "category": "Limpeza & Conservação",
                "assigned_email": "zelador@apras.com",
                "due_days": -4,
            },
            {
                "title": "Pintura e demarcação das vagas de garagem do subsolo",
                "description": "Refazer faixas amarelas e sinalização de vagas preferenciais e vagas de moto.",
                "status": TaskStatus.PENDING,
                "priority": TaskPriority.LOW,
                "category": "Manutenção Predial",
                "assigned_email": "zelador@apras.com",
                "due_days": 20,
            },
        ]

        for t_spec in tasks_specs:
            existing_task = session.exec(
                select(Task).where(
                    Task.tenant_id == tenant_id, Task.title == t_spec["title"]
                )
            ).first()
            if not existing_task:
                assigned_user = users_map.get(t_spec["assigned_email"])
                cat = cats_map.get(t_spec["category"])
                admin_user = users_map.get("admin@apras.com") or heitor
                task = Task(
                    tenant_id=tenant_id,
                    title=t_spec["title"],
                    description=t_spec["description"],
                    status=t_spec["status"],
                    priority=t_spec["priority"],
                    category_id=cat.id if cat else None,
                    created_by_id=admin_user.id,
                    assigned_to_id=assigned_user.id if assigned_user else None,
                    due_date=now + timedelta(days=t_spec["due_days"]),
                )
                session.add(task)
                session.commit()
        print(" Seeded tasks.")

        # 8. Announcements
        announcements_specs = [
            {
                "title": "Manutenção Preventiva dos Elevadores - Bloco A e B",
                "content": "Informamos que na próxima terça-feira (10h às 14h) a empresa Atlas realizará a manutenção periódica e lubrificação dos elevadores de passageiros. Durante o período, pedimos que utilizem o elevador de serviço.",
                "author_email": "sindico@apras.com",
            },
            {
                "title": "Campanha de Conscientização: Coleta Seletiva e Descarte de Resíduos",
                "content": "Pedimos a colaboração de todos os moradores para separar os materiais recicláveis (papel, plástico, vidro e metal) nos coletores identificados no subsolo. Caixas de papelão devem ser dobradas antes do descarte.",
                "author_email": "sindico@apras.com",
            },
            {
                "title": "Assembleia Geral Ordinária - Prestação de Contas 2026",
                "content": "Convocamos todos os condôminos para a AGO no dia 25 do próximo mês às 19h no Salão de Festas, com transmissão online. Pauta: prestação de contas do exercício anterior e votação orçamentária.",
                "author_email": "sindico@apras.com",
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
                author = users_map.get(a_spec["author_email"]) or users_map.get("admin@apras.com")
                ann = Announcement(
                    tenant_id=tenant_id,
                    title=a_spec["title"],
                    content=a_spec["content"],
                    author_id=author.id,
                )
                session.add(ann)
                session.commit()
        print(" Seeded announcements.")

        # 9. Reservable Spaces
        spaces_data = [
            {
                "name": "Salão de Festas Principal",
                "description": "Espaço climatizado com cozinha completa, mesas, cadeiras e sistema de som.",
                "capacity": 80,
                "requires_approval": True,
            },
            {
                "name": "Espaço Gourmet & Churrasqueira",
                "description": "Área coberta com churrasqueira a carvão, bancada em granito e freezer.",
                "capacity": 30,
                "requires_approval": False,
            },
            {
                "name": "Quadra Poliesportiva",
                "description": "Quadra com iluminação LED para futebol, basquete e vôlei.",
                "capacity": 20,
                "requires_approval": False,
            },
            {
                "name": "Sala de Jogos & Coworking",
                "description": "Mesa de bilhar, mesa de cartas, bancadas de trabalho e Wi-Fi de alta velocidade.",
                "capacity": 15,
                "requires_approval": False,
            },
        ]

        spaces_map: dict[str, ReservableSpace] = {}
        for s_data in spaces_data:
            space = session.exec(
                select(ReservableSpace).where(
                    ReservableSpace.tenant_id == tenant_id,
                    ReservableSpace.name == s_data["name"],
                )
            ).first()
            if not space:
                space = ReservableSpace(
                    tenant_id=tenant_id,
                    name=s_data["name"],
                    description=s_data["description"],
                    capacity=s_data["capacity"],
                    requires_approval=s_data["requires_approval"],
                    is_active=True,
                )
                session.add(space)
                session.commit()
                session.refresh(space)
            spaces_map[s_data["name"]] = space
        print(f" Loaded {len(spaces_map)} reservable spaces.")

        # Space reservation
        salao = spaces_map.get("Salão de Festas Principal")
        if salao and morador_user and lot_101:
            res_start = (now + timedelta(days=5)).replace(
                hour=14, minute=0, second=0
            )
            res_end = (now + timedelta(days=5)).replace(
                hour=22, minute=0, second=0
            )
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

        # 10. Packages (Encomendas)
        packages_specs = [
            {
                "lot": ("Bloco A", "101"),
                "carrier": "Amazon Logística",
                "description": "Caixa média (rastreio AMZ-98218)",
                "status": PackageStatus.AWAITING_PICKUP,
                "days_ago": 1,
            },
            {
                "lot": ("Bloco A", "201"),
                "carrier": "Mercado Livre",
                "description": "Pacote amarelo Mercado Envios",
                "status": PackageStatus.AWAITING_PICKUP,
                "days_ago": 2,
            },
            {
                "lot": ("Bloco B", "102"),
                "carrier": "Correios",
                "description": "Sedex envelope pardo",
                "status": PackageStatus.PICKED_UP,
                "days_ago": 3,
            },
            {
                "lot": ("Bloco B", "202"),
                "carrier": "Magazine Luiza",
                "description": "Caixa grande eletrodoméstico",
                "status": PackageStatus.AWAITING_PICKUP,
                "days_ago": 0,
            },
        ]

        porteiro_user = users_map.get("porteiro@apras.com")
        for p_spec in packages_specs:
            p_lot = lots_map.get(p_spec["lot"])
            if not p_lot:
                continue
            existing_pkg = session.exec(
                select(Package).where(
                    Package.tenant_id == tenant_id,
                    Package.lot_id == p_lot.id,
                    Package.description == p_spec["description"],
                )
            ).first()
            if not existing_pkg:
                recv_time = now - timedelta(days=p_spec["days_ago"], hours=3)
                pkg = Package(
                    tenant_id=tenant_id,
                    lot_id=p_lot.id,
                    received_by_id=porteiro_user.id if porteiro_user else None,
                    carrier=p_spec["carrier"],
                    description=p_spec["description"],
                    status=p_spec["status"],
                    received_at=recv_time,
                    picked_up_at=(
                        recv_time + timedelta(hours=5)
                        if p_spec["status"] == PackageStatus.PICKED_UP
                        else None
                    ),
                )
                session.add(pkg)
                session.commit()
        print(" Seeded packages.")

        # 11. Occurrences (Livro de Ocorrências)
        occurrences_specs = [
            {
                "protocol": "OC-2026-001",
                "category": OccurrenceCategory.MAINTENANCE,
                "title": "Vazamento na torneira do jardim próximo ao playground",
                "description": "A torneira externa está gotejando continuamente, acumulando poça de água perto da área infantil.",
                "status": OccurrenceStatus.OPEN,
                "priority": OccurrencePriority.LOW,
                "lot": ("Bloco A", "101"),
            },
            {
                "protocol": "OC-2026-002",
                "category": OccurrenceCategory.NOISE,
                "title": "Música alta após o horário de silêncio (22h)",
                "description": "Música e conversa em tom elevado no Bloco B unidade 202 na noite de sexta-feira.",
                "status": OccurrenceStatus.RESOLVED,
                "priority": OccurrencePriority.MEDIUM,
                "lot": ("Bloco B", "202"),
                "resolution_notes": "Portaria entrou em contato com o morador, que prontamente reduziu o volume.",
            },
            {
                "protocol": "OC-2026-003",
                "category": OccurrenceCategory.PARKING,
                "title": "Veículo estacionado sobre a faixa de pedestres da garagem",
                "description": "Carro prata estacionado obstruindo a rampa de acesso do subsolo.",
                "status": OccurrenceStatus.IN_PROGRESS,
                "priority": OccurrencePriority.HIGH,
                "lot": ("Bloco A", "201"),
            },
        ]

        for o_spec in occurrences_specs:
            occ = session.exec(
                select(Occurrence).where(
                    Occurrence.tenant_id == tenant_id,
                    Occurrence.protocol_number == o_spec["protocol"],
                )
            ).first()
            if not occ:
                o_lot = lots_map.get(o_spec["lot"])
                occ = Occurrence(
                    tenant_id=tenant_id,
                    protocol_number=o_spec["protocol"],
                    category=o_spec["category"],
                    title=o_spec["title"],
                    description=o_spec["description"],
                    status=o_spec["status"],
                    priority=o_spec["priority"],
                    lot_id=o_lot.id if o_lot else None,
                    reporter_user_id=morador_user.id if morador_user else None,
                    resolution_notes=o_spec.get("resolution_notes"),
                    resolved_at=(
                        now
                        if o_spec["status"] == OccurrenceStatus.RESOLVED
                        else None
                    ),
                )
                session.add(occ)
                session.commit()
        print(" Seeded occurrences.")

        # 12. Visitors and Gate Authorizations
        visitors_specs = [
            {
                "full_name": "Mariana Ferreira Costa",
                "cpf": "29182374619",
                "phone": "(11) 98765-4321",
                "vehicle_plate": "ABC1D23",
                "lot": ("Bloco A", "101"),
            },
            {
                "full_name": "Rodrigo Silva (Técnico Vivo Fibra)",
                "company_name": "Vivo Telecomunicações",
                "cpf": "19283746502",
                "phone": "(11) 97654-3210",
                "lot": ("Bloco A", "201"),
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
                    company_name=v_spec.get("company_name"),
                    vehicle_plate=v_spec.get("vehicle_plate"),
                )
                session.add(vis)
                session.commit()
                session.refresh(vis)

            v_lot = lots_map.get(v_spec["lot"])
            if v_lot and morador_user:
                auth = session.exec(
                    select(VisitorAuthorization).where(
                        VisitorAuthorization.visitor_id == vis.id,
                        VisitorAuthorization.lot_id == v_lot.id,
                    )
                ).first()
                if not auth:
                    session.add(
                        VisitorAuthorization(
                            tenant_id=tenant_id,
                            visitor_id=vis.id,
                            lot_id=v_lot.id,
                            authorizer_user_id=morador_user.id,
                            auth_type=AuthorizationType.SINGLE,
                            status=AuthorizationStatus.ACTIVE,
                            start_date=now - timedelta(hours=1),
                            end_date=now + timedelta(hours=8),
                        )
                    )
                    session.commit()
        print(" Seeded visitors and authorizations.")

        # 13. Finance (Categories and Transactions)
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
                    tenant_id=tenant_id,
                    name=fc_name,
                    type=fc_type,
                    is_active=True,
                )
                session.add(fc)
                session.commit()
                session.refresh(fc)
            fin_cats_map[fc_name] = fc
        print(f" Loaded {len(fin_cats_map)} finance categories.")

        # Financial Transactions
        admin_author = users_map.get("sindico@apras.com") or users_map.get("admin@apras.com")
        if admin_author:
            today = date.today()
            transactions_data = [
                ("Taxa Condominial Ordinária", "Arrecadação de cotas condominiais - Mês corrente", 28500.0, TransactionType.INCOME, today - timedelta(days=5)),
                ("Fundo de Reserva", "Aporte mensal no fundo de reserva (5%)", 1425.0, TransactionType.INCOME, today - timedelta(days=5)),
                ("Energia Elétrica (Áreas Comuns)", "Fatura Enel - Áreas comuns e bombas", 3840.50, TransactionType.EXPENSE, today - timedelta(days=8)),
                ("Água e Esgoto (Sabesp)", "Conta Sabesp hidrômetro coletivo", 2980.20, TransactionType.EXPENSE, today - timedelta(days=10)),
                ("Manutenção de Elevadores", "Mensalidade contrato de conservação Atlas Schindler", 1450.0, TransactionType.EXPENSE, today - timedelta(days=12)),
                ("Materiais de Limpeza e Higiene", "Compra mensal de produtos de limpeza e sacos de lixo", 680.0, TransactionType.EXPENSE, today - timedelta(days=14)),
            ]

            for cat_name, desc, amount, t_type, t_date in transactions_data:
                fc = fin_cats_map.get(cat_name)
                if not fc:
                    continue
                existing_tx = session.exec(
                    select(FinancialTransaction).where(
                        FinancialTransaction.tenant_id == tenant_id,
                        FinancialTransaction.description == desc,
                        FinancialTransaction.transaction_date == t_date,
                    )
                ).first()
                if not existing_tx:
                    tx = FinancialTransaction(
                        tenant_id=tenant_id,
                        type=t_type,
                        category_id=fc.id,
                        description=desc,
                        amount=amount,
                        transaction_date=t_date,
                        payment_method="BOLETO" if t_type == TransactionType.EXPENSE else "TRANSFERENCIA",
                        created_by_id=admin_author.id,
                    )
                    session.add(tx)
                    session.commit()
            print(" Seeded financial transactions.")

        print("\n🎉 Seed demo finalizado com sucesso!")
        print("Usuários criados para teste (senha para todos: demo1234):")
        for u in users_specs:
            print(f"  • {u['email']} — {u['full_name']} ({u['role']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed APRAS with demo data.")
    parser.add_argument(
        "--db-url",
        dest="db_url",
        default=None,
        help="PostgreSQL connection string (defaults to POSTGRES_URL from environment/settings).",
    )
    args = parser.parse_args()
    run_seed(args.db_url)
