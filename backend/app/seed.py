import random
import uuid
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.category import Category
from app.models.enums import TaskPriority, TaskStatus
from app.models.task import Task
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.user import User
from app.models.role import Role
from app.services.tenant_service import TenantService
from sqlalchemy import text
from sqlmodel import Session, create_engine, select

#: The three demo profiles' bundles (APRAS-49 §9.1, ER-4).
#:
#: **The dev demo's opinion, not a product default.** F1's "nothing is
#: seeded with permissions" decision binds `ensure_legacy_roles` and every
#: migration; it does not bind this script, whose whole job is to produce a
#: usable demo. `app/` must not read `tests/data/legacy_role_bundles.json`,
#: so the three sets are spelled here, deliberately small and readable rather
#: than a reproduction of the retired enum's 155/144/83 strings.
DEMO_BUNDLES: dict[str, list[str]] = {
    "Administrador (papel)": [
        "roles:read", "roles:create", "roles:update", "roles:delete",
        "users:read", "users:update", "users:update_contact",
        "tasks:read", "tasks:read_all", "tasks:create", "tasks:update",
        "tasks:update_any", "tasks:delete", "tasks:comment",
        "categories:read", "categories:create", "categories:update",
        "categories:delete",
    ],
    "Diretor (papel)": [
        "roles:read", "users:read",
        "tasks:read", "tasks:read_all", "tasks:create", "tasks:update",
        "tasks:update_any", "tasks:comment",
        "categories:read", "categories:create", "categories:update",
        "announcements:read", "announcements:create",
    ],
    "Gerente (papel)": [
        "roles:read", "users:read",
        # Deliberately **no** `tasks:read_all` / `tasks:update_any`: that
        # absence *is* the legacy MANAGER tier, now stored as data instead of
        # compiled into an `if` (APRAS-49 §3.0).
        "tasks:read", "tasks:create", "tasks:update", "tasks:comment",
        "categories:read",
        "occurrences:read", "occurrences:read_assigned",
    ],
}


def seed_db() -> None:  # noqa: PLR0915
    engine = create_engine(settings.database_url)
    with Session(engine) as session:
        print("🌱 Iniciando seed de desenvolvimento...")

        # 1. Limpar banco
        session.execute(text("TRUNCATE TABLE task CASCADE;"))
        session.execute(text('TRUNCATE TABLE "user" CASCADE;'))
        session.execute(text("TRUNCATE TABLE category CASCADE;"))
        session.execute(text("TRUNCATE TABLE role CASCADE;"))
        session.execute(text("TRUNCATE TABLE user_role_link CASCADE;"))
        session.commit()

        # 2. Categorias
        categories_data = [
            {"name": "Jurídico", "color": "#dc2626"},
            {"name": "Financeiro", "color": "#16a34a"},
            {"name": "TI", "color": "#2563eb"},
            {"name": "RH", "color": "#9333ea"},
            {"name": "Operacional", "color": "#ea580c"},
        ]

        categories: dict[str, Category] = {}
        for c_data in categories_data:
            cat = Category(name=c_data["name"], color=c_data["color"])
            session.add(cat)
            categories[c_data["name"]] = cat

        session.commit()
        for cat in categories.values():
            session.refresh(cat)
        print(f"✅ {len(categories)} categorias criadas.")

        # 3. Papéis
        #
        # The TRUNCATE above wiped every role row, so the six historically
        # named ones are recreated first and the demo bundles are written
        # onto three of them. `app/` must not read a test fixture, so
        # `DEMO_BUNDLES` below is a literal in this file: it is **the dev
        # demo's opinion, not a product default**. Nothing outside this
        # script ever seeds a permission — `ensure_legacy_roles` and every
        # migration except `0033` insert `permissions = []` (APRAS-49 §9.1).
        TenantService.ensure_legacy_roles(session, DEFAULT_TENANT_ID)

        roles_data = [
            "Diretor Comercial",
            "Diretor Financeiro",
            "Gerente Operacional",
            "Coordenador",
            "Analista",
        ]

        roles: dict[str, Role] = {}
        for type_name in roles_data:
            ut = Role(name=type_name)
            session.add(ut)
            roles[type_name] = ut
        session.commit()
        for ut in roles.values():
            session.refresh(ut)

        by_name: dict[str, Role] = {
            role.name: role for role in session.exec(select(Role)).all()
        }
        for name, bundle in DEMO_BUNDLES.items():
            by_name[name].permissions = sorted(bundle)
            session.add(by_name[name])
        # The two landing preferences the enum switch used to hard-code
        # (APRAS-49 §10.4), so the dev demo shows the feature.
        by_name["Porteiro (papel)"].landing_path = "/gate"
        by_name["Convidado (papel)"].landing_path = "/welcome"
        session.add(by_name["Porteiro (papel)"])
        session.add(by_name["Convidado (papel)"])
        session.commit()
        print(f"✅ {len(by_name)} papéis criados.")

        # 4. Usuários
        admin = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            email="admin@apras.com",
            hashed_password=get_password_hash("test_admin_password"),
            full_name="Administrador do Sistema",
            is_superuser=True,
            is_active=True,
            cpf="52998224725",
            roles=[by_name["Administrador (papel)"]],
        )
        session.add(admin)

        diretores_data = [
            {
                "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
                "email": "diretor1@apras.com",
                "full_name": "Diretor Comercial",
                "cpf": "11144477735",
            },
            {
                "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
                "email": "diretor2@apras.com",
                "full_name": "Diretor Financeiro",
                "cpf": "08050681057",
            },
        ]

        diretores: list[User] = []
        for d_data in diretores_data:
            user = User(
                id=d_data["id"],
                email=d_data["email"],
                hashed_password=get_password_hash("test_user_password"),
                full_name=d_data["full_name"],
                is_active=True,
                cpf=d_data["cpf"],
                roles=[by_name["Diretor (papel)"], roles[d_data["full_name"]]],
            )
            session.add(user)
            diretores.append(user)

        manager = User(
            id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            email="gerente1@apras.com",
            hashed_password=get_password_hash("test_user_password"),
            full_name="Gerente Operacional",
            roles=[by_name["Gerente (papel)"], roles["Gerente Operacional"]],
            is_active=True,
            cpf="07491723040",
        )
        session.add(manager)
        session.commit()

        # Explicit membership of the default tenant for every seeded user, so
        # the dev environment matches what migration 0028 produced for real
        # installs and `get_current_tenant` resolves through the
        # one-membership branch rather than the zero-membership fallback
        # (APRAS-42 §8.3). This session is a plain `Session(engine)`: it
        # carries no request-scoped marker, so the tenant filter, the write
        # stamp and the fail-closed guard are all inert here and every row
        # still lands in the default tenant through the model default.
        for seeded_user in [admin, *diretores, manager]:
            session.add(
                UserTenantLink(
                    user_id=seeded_user.id, tenant_id=DEFAULT_TENANT_ID
                )
            )
        session.commit()
        print(f"✅ {1 + len(diretores) + 1} usuários criados.")
        # The model at a glance: who holds what, printed per profile.
        for seeded_user in [admin, *diretores, manager]:
            session.refresh(seeded_user)
            names = ", ".join(sorted(role.name for role in seeded_user.roles))
            flag = " [is_superuser]" if seeded_user.is_superuser else ""
            print(f"   • {seeded_user.email}: {names or '(sem papéis)'}{flag}")

        # 5. Tarefas
        now = datetime.now()
        tasks_data = [
            {
                "title": "Migração de Servidor",
                "description": "Realizar a migração dos dados para o novo servidor PostgreSQL 16.",
                "status": TaskStatus.IN_PROGRESS,
                "priority": TaskPriority.HIGH,
                "assigned_to_id": diretores[0].id,
                "due_date": now + timedelta(days=5),
                "category_id": categories["TI"].id,
            },
            {
                "title": "Relatório Trimestral",
                "description": "Consolidar os gastos do primeiro trimestre para a diretoria.",
                "status": TaskStatus.PENDING,
                "priority": TaskPriority.MEDIUM,
                "assigned_to_id": diretores[1].id,
                "due_date": now + timedelta(days=10),
                "category_id": categories["Financeiro"].id,
            },
            {
                "title": "Treinamento de Equipe",
                "description": "Treinar novos funcionários no uso do APRAS.",
                "status": TaskStatus.COMPLETED,
                "priority": TaskPriority.LOW,
                "assigned_to_id": diretores[0].id,
                "due_date": now - timedelta(days=2),
                "category_id": categories["RH"].id,
            },
            {
                "title": "Revisão de Segurança",
                "description": "Auditoria completa nos logs de acesso do sistema.",
                "status": TaskStatus.PENDING,
                "priority": TaskPriority.URGENT,
                "assigned_to_id": diretores[1].id,
                "due_date": now + timedelta(days=1),
                "category_id": categories["TI"].id,
            },
            {
                "title": "Implementação do Kanban",
                "description": "Finalizar a visualização em colunas no dashboard do frontend.",
                "status": TaskStatus.COMPLETED,
                "priority": TaskPriority.HIGH,
                "assigned_to_id": diretores[0].id,
                "due_date": now,
                "category_id": categories["TI"].id,
            },
            {
                "title": "Ajuste de Budget",
                "description": "Redefinir as metas orçamentárias para o próximo semestre.",
                "status": TaskStatus.CANCELED,
                "priority": TaskPriority.LOW,
                "assigned_to_id": diretores[1].id,
                "due_date": None,
                "category_id": categories["Financeiro"].id,
            },
            {
                "title": "Dependência de Terceiros",
                "description": "Aguardando liberação da API do parceiro para continuar integração.",
                "status": TaskStatus.BLOCKED,
                "priority": TaskPriority.HIGH,
                "assigned_to_id": diretores[0].id,
                "due_date": now + timedelta(days=3),
                "category_id": categories["Operacional"].id,
            },
            {
                "title": "Revisão de Contrato",
                "description": "Verificar cláusulas de rescisão do contrato de aluguel.",
                "status": TaskStatus.PENDING,
                "priority": TaskPriority.HIGH,
                "assigned_to_id": diretores[1].id,
                "due_date": now + timedelta(days=7),
                "category_id": categories["Jurídico"].id,
            },
            {
                "title": "Tarefa sem Categoria",
                "description": "Esta tarefa não possui categoria atribuída.",
                "status": TaskStatus.PENDING,
                "priority": TaskPriority.LOW,
                "assigned_to_id": diretores[0].id,
                "due_date": None,
                "category_id": None,
            },
        ]

        tasks_data += [
            {
                "title": "Controle de Estoque",
                "description": "Atualizar planilha de controle de materiais do almoxarifado.",
                "status": TaskStatus.PENDING,
                "priority": TaskPriority.MEDIUM,
                "assigned_to_id": manager.id,
                "due_date": now + timedelta(days=4),
                "category_id": categories["Operacional"].id,
            },
            {
                "title": "Relatório de Equipe",
                "description": "Compilar métricas de desempenho da equipe operacional.",
                "status": TaskStatus.IN_PROGRESS,
                "priority": TaskPriority.HIGH,
                "assigned_to_id": manager.id,
                "due_date": now + timedelta(days=2),
                "category_id": categories["RH"].id,
            },
        ]

        for t_data in tasks_data:
            task = Task(
                title=t_data["title"],
                description=t_data["description"],
                status=t_data["status"],
                priority=t_data["priority"],
                assigned_to_id=t_data["assigned_to_id"],
                created_by_id=random.choice(diretores).id,
                due_date=t_data["due_date"],
                category_id=t_data.get("category_id"),
            )
            session.add(task)

        session.commit()
        print(f"✅ {len(tasks_data)} tarefas criadas.")

        # 6. Os seis papéis históricos, em *todos* os tenants.
        # The TRUNCATE above wiped them and tenants created before APRAS-42
        # never had them. Idempotent, so the default tenant (already done in
        # step 3) contributes nothing here.
        seeded_roles = 0
        for tenant in session.exec(select(Tenant)).all():
            seeded_roles += TenantService.ensure_legacy_roles(session, tenant.id)
        print(f"✅ {seeded_roles} papéis históricos garantidos nos demais tenants.")

        print("🚀 Seed concluído com sucesso!")


if __name__ == "__main__":
    seed_db()
