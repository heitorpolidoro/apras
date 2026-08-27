"""Service layer for the Association Financial Area & Dashboard (APRAS-22)."""

from datetime import date, datetime, timedelta
from uuid import UUID

from sqlmodel import Session, func, select

from app.core.exceptions import (
    BudgetLineAlreadyExistsError,
    BudgetLineNotFoundError,
    FinanceCategoryAlreadyExistsError,
    FinanceCategoryNotFoundError,
    FinanceCategoryTypeMismatchError,
    FinancialTransactionNotFoundError,
    InvalidInvoiceFormatError,
    InvoiceFileTooLargeError,
)
from app.models.enums import TransactionType
from app.models.finance import BudgetLine, FinanceCategory, FinancialTransaction
from app.models.user import User
from app.schemas.finance import (
    BudgetLineCreate,
    BudgetLineRead,
    BudgetLineUpdate,
    BudgetVsActualRead,
    BudgetVsActualRow,
    CashBalanceRead,
    FinanceCategoryCreate,
    FinanceCategoryUpdate,
    FinancialStatementRead,
    FinancialTransactionCreate,
    FinancialTransactionRead,
    FinancialTransactionUpdate,
    MonthlyStatementEntry,
)
from app.services.storage_service import BaseStorageProvider, LocalStorageProvider

MAX_INVOICE_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_INVOICE_MIME_TYPE = "application/pdf"

_storage_provider: BaseStorageProvider = LocalStorageProvider()


class FinanceService:
    """Service class for the Association Financial Area domain operations."""

    # -------------------------------------------------------------------
    # Formatting helpers
    # -------------------------------------------------------------------

    @staticmethod
    def format_budget_line_read(budget_line: BudgetLine) -> BudgetLineRead:
        return BudgetLineRead(
            id=budget_line.id,
            category_id=budget_line.category_id,
            category_name=budget_line.category.name,
            category_type=budget_line.category.type,
            fiscal_year=budget_line.fiscal_year,
            planned_amount=budget_line.planned_amount,
            notes=budget_line.notes,
            created_at=budget_line.created_at,
            updated_at=budget_line.updated_at,
        )

    @staticmethod
    def format_transaction_read(
        session: Session, transaction: FinancialTransaction
    ) -> FinancialTransactionRead:
        category = transaction.category or session.get(
            FinanceCategory, transaction.category_id
        )
        creator = transaction.created_by or session.get(
            User, transaction.created_by_id
        )
        return FinancialTransactionRead(
            id=transaction.id,
            type=transaction.type,
            category_id=transaction.category_id,
            category_name=category.name if category else "",
            description=transaction.description,
            amount=transaction.amount,
            transaction_date=transaction.transaction_date,
            payment_method=transaction.payment_method,
            invoice_file_url=transaction.invoice_file_url,
            invoice_file_size_bytes=transaction.invoice_file_size_bytes,
            invoice_mime_type=transaction.invoice_mime_type,
            created_by_id=transaction.created_by_id,
            created_by_name=creator.full_name if creator else "",
            created_at=transaction.created_at,
            updated_at=transaction.updated_at,
        )

    # -------------------------------------------------------------------
    # Categories
    # -------------------------------------------------------------------

    @staticmethod
    def list_categories(
        session: Session,
        type_filter: TransactionType | None = None,
        include_inactive: bool = False,
    ) -> list[FinanceCategory]:
        """Lists finance categories, optionally filtered by type/active status."""
        query = select(FinanceCategory)
        if type_filter is not None:
            query = query.where(FinanceCategory.type == type_filter)
        if not include_inactive:
            query = query.where(FinanceCategory.is_active == True)  # noqa: E712
        query = query.order_by(FinanceCategory.name.asc())
        return list(session.exec(query).all())

    @staticmethod
    def create_category(
        session: Session, category_in: FinanceCategoryCreate
    ) -> FinanceCategory:
        """Creates a finance category, raising on duplicate (name, type)."""
        existing = session.exec(
            select(FinanceCategory).where(
                FinanceCategory.name == category_in.name,
                FinanceCategory.type == category_in.type,
            )
        ).first()
        if existing:
            raise FinanceCategoryAlreadyExistsError()

        category = FinanceCategory(
            name=category_in.name,
            type=category_in.type,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(category)
        session.commit()
        session.refresh(category)
        return category

    @staticmethod
    def get_category_by_id(session: Session, category_id: UUID) -> FinanceCategory:
        """Retrieves a category entity or raises FinanceCategoryNotFoundError."""
        category = session.get(FinanceCategory, category_id)
        if not category:
            raise FinanceCategoryNotFoundError(category_id)
        return category

    @classmethod
    def update_category(
        cls,
        session: Session,
        category_id: UUID,
        category_in: FinanceCategoryUpdate,
    ) -> FinanceCategory:
        """Renames and/or toggles a category's active status (soft-deactivate only)."""
        category = cls.get_category_by_id(session, category_id)

        if category_in.name is not None:
            category.name = category_in.name
        if category_in.is_active is not None:
            category.is_active = category_in.is_active

        category.updated_at = datetime.utcnow()
        session.add(category)
        session.commit()
        session.refresh(category)
        return category

    # -------------------------------------------------------------------
    # Budget Lines
    # -------------------------------------------------------------------

    @staticmethod
    def list_budget_lines(session: Session, fiscal_year: int) -> list[BudgetLine]:
        """Lists budget lines for a fiscal year."""
        query = (
            select(BudgetLine)
            .where(BudgetLine.fiscal_year == fiscal_year)
            .order_by(BudgetLine.created_at.asc())
        )
        return list(session.exec(query).all())

    @classmethod
    def create_budget_line(
        cls, session: Session, budget_in: BudgetLineCreate
    ) -> BudgetLine:
        """Creates a budget line, validating category and rejecting duplicates."""
        category = cls.get_category_by_id(session, budget_in.category_id)

        existing = session.exec(
            select(BudgetLine).where(
                BudgetLine.category_id == budget_in.category_id,
                BudgetLine.fiscal_year == budget_in.fiscal_year,
            )
        ).first()
        if existing:
            raise BudgetLineAlreadyExistsError()

        budget_line = BudgetLine(
            category_id=category.id,
            fiscal_year=budget_in.fiscal_year,
            planned_amount=budget_in.planned_amount,
            notes=budget_in.notes,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(budget_line)
        session.commit()
        session.refresh(budget_line)
        return budget_line

    @staticmethod
    def get_budget_line_by_id(session: Session, budget_line_id: UUID) -> BudgetLine:
        """Retrieves a budget line entity or raises BudgetLineNotFoundError."""
        budget_line = session.get(BudgetLine, budget_line_id)
        if not budget_line:
            raise BudgetLineNotFoundError(budget_line_id)
        return budget_line

    @classmethod
    def update_budget_line(
        cls,
        session: Session,
        budget_line_id: UUID,
        budget_in: BudgetLineUpdate,
    ) -> BudgetLine:
        """Updates a budget line's planned amount and/or notes."""
        budget_line = cls.get_budget_line_by_id(session, budget_line_id)

        if budget_in.planned_amount is not None:
            budget_line.planned_amount = budget_in.planned_amount
        if budget_in.notes is not None:
            budget_line.notes = budget_in.notes

        budget_line.updated_at = datetime.utcnow()
        session.add(budget_line)
        session.commit()
        session.refresh(budget_line)
        return budget_line

    @classmethod
    def delete_budget_line(cls, session: Session, budget_line_id: UUID) -> None:
        """Deletes a budget line."""
        budget_line = cls.get_budget_line_by_id(session, budget_line_id)
        session.delete(budget_line)
        session.commit()

    # -------------------------------------------------------------------
    # Transactions
    # -------------------------------------------------------------------

    @staticmethod
    def list_transactions(
        session: Session,
        type_filter: TransactionType | None = None,
        category_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[FinancialTransaction], int]:
        """Lists financial transactions with optional filters and pagination."""
        query = select(FinancialTransaction)
        if type_filter is not None:
            query = query.where(FinancialTransaction.type == type_filter)
        if category_id is not None:
            query = query.where(FinancialTransaction.category_id == category_id)
        if start_date is not None:
            query = query.where(FinancialTransaction.transaction_date >= start_date)
        if end_date is not None:
            query = query.where(FinancialTransaction.transaction_date <= end_date)

        total = session.exec(
            select(func.count()).select_from(query.subquery())
        ).one()

        query = (
            query.order_by(FinancialTransaction.transaction_date.desc())
            .offset(skip)
            .limit(limit)
        )
        transactions = session.exec(query).all()
        return list(transactions), total

    @classmethod
    def create_transaction(
        cls,
        session: Session,
        created_by_id: UUID,
        transaction_in: FinancialTransactionCreate,
    ) -> FinancialTransaction:
        """Creates a financial transaction, validating type/category match."""
        category = cls.get_category_by_id(session, transaction_in.category_id)
        if transaction_in.type != category.type:
            raise FinanceCategoryTypeMismatchError()

        transaction = FinancialTransaction(
            type=transaction_in.type,
            category_id=transaction_in.category_id,
            description=transaction_in.description,
            amount=transaction_in.amount,
            transaction_date=transaction_in.transaction_date,
            payment_method=transaction_in.payment_method,
            created_by_id=created_by_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(transaction)
        session.commit()
        session.refresh(transaction)
        return transaction

    @staticmethod
    def get_transaction_by_id(
        session: Session, transaction_id: UUID
    ) -> FinancialTransaction:
        """Retrieves a transaction entity or raises FinancialTransactionNotFoundError."""
        transaction = session.get(FinancialTransaction, transaction_id)
        if not transaction:
            raise FinancialTransactionNotFoundError(transaction_id)
        return transaction

    @classmethod
    def update_transaction(
        cls,
        session: Session,
        transaction: FinancialTransaction,
        transaction_in: FinancialTransactionUpdate,
    ) -> FinancialTransaction:
        """Updates a transaction, re-validating type/category match if changed."""
        update_data = transaction_in.model_dump(exclude_unset=True)

        new_type = update_data.get("type", transaction.type)
        new_category_id = update_data.get("category_id", transaction.category_id)

        if "type" in update_data or "category_id" in update_data:
            category = cls.get_category_by_id(session, new_category_id)
            if new_type != category.type:
                raise FinanceCategoryTypeMismatchError()

        for key, value in update_data.items():
            setattr(transaction, key, value)

        transaction.updated_at = datetime.utcnow()
        session.add(transaction)
        session.commit()
        session.refresh(transaction)
        return transaction

    @staticmethod
    def delete_transaction(session: Session, transaction: FinancialTransaction) -> None:
        """Deletes a transaction, removing any attached invoice file from disk."""
        if transaction.invoice_file_path:
            _storage_provider.delete_file(transaction.invoice_file_path)

        session.delete(transaction)
        session.commit()

    @staticmethod
    def upload_invoice(
        session: Session,
        transaction: FinancialTransaction,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
    ) -> FinancialTransaction:
        """Attaches (or replaces) a PDF invoice on a transaction."""
        if mime_type != ALLOWED_INVOICE_MIME_TYPE:
            raise InvalidInvoiceFormatError()
        if len(file_bytes) > MAX_INVOICE_FILE_SIZE:
            raise InvoiceFileTooLargeError()

        if transaction.invoice_file_path:
            _storage_provider.delete_file(transaction.invoice_file_path)

        file_path, url = _storage_provider.save_file(file_bytes, filename, mime_type)

        transaction.invoice_file_path = file_path
        transaction.invoice_file_url = url
        transaction.invoice_file_size_bytes = len(file_bytes)
        transaction.invoice_mime_type = mime_type
        transaction.updated_at = datetime.utcnow()

        session.add(transaction)
        session.commit()
        session.refresh(transaction)
        return transaction

    @staticmethod
    def delete_invoice(
        session: Session, transaction: FinancialTransaction
    ) -> FinancialTransaction:
        """Removes the invoice file from disk and clears the invoice fields."""
        if transaction.invoice_file_path:
            _storage_provider.delete_file(transaction.invoice_file_path)

        transaction.invoice_file_path = None
        transaction.invoice_file_url = None
        transaction.invoice_file_size_bytes = None
        transaction.invoice_mime_type = None
        transaction.updated_at = datetime.utcnow()

        session.add(transaction)
        session.commit()
        session.refresh(transaction)
        return transaction

    # -------------------------------------------------------------------
    # Reporting: cash balance, statement, budget vs actual
    # -------------------------------------------------------------------

    @staticmethod
    def get_cash_balance(
        session: Session, as_of: date | None = None
    ) -> CashBalanceRead:
        """Computes the cash balance from all transactions up to `as_of`."""
        as_of = as_of or date.today()

        total_income = session.exec(
            select(func.coalesce(func.sum(FinancialTransaction.amount), 0.0)).where(
                FinancialTransaction.type == TransactionType.INCOME,
                FinancialTransaction.transaction_date <= as_of,
            )
        ).one()
        total_expense = session.exec(
            select(func.coalesce(func.sum(FinancialTransaction.amount), 0.0)).where(
                FinancialTransaction.type == TransactionType.EXPENSE,
                FinancialTransaction.transaction_date <= as_of,
            )
        ).one()

        return CashBalanceRead(
            as_of_date=as_of,
            total_income=float(total_income or 0.0),
            total_expense=float(total_expense or 0.0),
            balance=float((total_income or 0.0) - (total_expense or 0.0)),
        )

    @classmethod
    def get_statement(
        cls, session: Session, start_date: date, end_date: date
    ) -> FinancialStatementRead:
        """Builds the monthly cash inflows/outflows statement for a date range."""
        opening_balance = cls.get_cash_balance(
            session, as_of=start_date - timedelta(days=1)
        ).balance

        transactions = session.exec(
            select(FinancialTransaction).where(
                FinancialTransaction.transaction_date >= start_date,
                FinancialTransaction.transaction_date <= end_date,
            )
        ).all()

        monthly: dict[tuple[int, int], dict[str, float]] = {}
        cursor = date(start_date.year, start_date.month, 1)
        end_marker = date(end_date.year, end_date.month, 1)
        while cursor <= end_marker:
            monthly[(cursor.year, cursor.month)] = {"income": 0.0, "expense": 0.0}
            if cursor.month == 12:
                cursor = date(cursor.year + 1, 1, 1)
            else:
                cursor = date(cursor.year, cursor.month + 1, 1)

        for txn in transactions:
            key = (txn.transaction_date.year, txn.transaction_date.month)
            bucket = monthly.setdefault(key, {"income": 0.0, "expense": 0.0})
            if txn.type == TransactionType.INCOME:
                bucket["income"] += txn.amount
            else:
                bucket["expense"] += txn.amount

        entries: list[MonthlyStatementEntry] = []
        running_balance = opening_balance
        for (year, month) in sorted(monthly.keys()):
            income = monthly[(year, month)]["income"]
            expense = monthly[(year, month)]["expense"]
            net = income - expense
            running_balance += net
            entries.append(
                MonthlyStatementEntry(
                    year=year,
                    month=month,
                    income=income,
                    expense=expense,
                    net=net,
                    running_balance=running_balance,
                )
            )

        closing_balance = cls.get_cash_balance(session, as_of=end_date).balance

        return FinancialStatementRead(
            start_date=start_date,
            end_date=end_date,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            entries=entries,
        )

    @staticmethod
    def get_budget_vs_actual(
        session: Session, fiscal_year: int
    ) -> BudgetVsActualRead:
        """Builds the budget-vs-actual execution table for a fiscal year."""
        budget_lines = session.exec(
            select(BudgetLine).where(BudgetLine.fiscal_year == fiscal_year)
        ).all()

        planned_by_category: dict[UUID, float] = {
            bl.category_id: bl.planned_amount for bl in budget_lines
        }

        category_ids = set(planned_by_category.keys())

        transactions_in_year = session.exec(select(FinancialTransaction)).all()
        transactions_in_year = [
            t for t in transactions_in_year if t.transaction_date.year == fiscal_year
        ]
        for txn in transactions_in_year:
            category_ids.add(txn.category_id)

        rows: list[BudgetVsActualRow] = []
        total_planned = 0.0
        total_executed = 0.0

        for category_id in category_ids:
            category = session.get(FinanceCategory, category_id)
            if category is None:
                continue

            planned_amount = planned_by_category.get(category_id, 0.0)
            category_transactions = [
                t for t in transactions_in_year if t.category_id == category_id
            ]
            executed_amount = sum(t.amount for t in category_transactions)
            transaction_count = len(category_transactions)

            variance_amount = executed_amount - planned_amount
            variance_pct = (
                (variance_amount / planned_amount * 100) if planned_amount > 0 else None
            )

            total_planned += planned_amount
            total_executed += executed_amount

            rows.append(
                BudgetVsActualRow(
                    category_id=category_id,
                    category_name=category.name,
                    category_type=category.type,
                    planned_amount=planned_amount,
                    executed_amount=executed_amount,
                    variance_amount=variance_amount,
                    variance_pct=variance_pct,
                    transaction_count=transaction_count,
                )
            )

        rows.sort(key=lambda r: r.category_name)

        return BudgetVsActualRead(
            fiscal_year=fiscal_year,
            rows=rows,
            total_planned=total_planned,
            total_executed=total_executed,
        )

    @staticmethod
    def list_category_transactions(
        session: Session,
        category_id: UUID,
        fiscal_year: int,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[FinancialTransaction], int]:
        """Lists the transactions backing a budget-vs-actual drill-down row."""
        start_of_year = date(fiscal_year, 1, 1)
        end_of_year = date(fiscal_year, 12, 31)

        query = select(FinancialTransaction).where(
            FinancialTransaction.category_id == category_id,
            FinancialTransaction.transaction_date >= start_of_year,
            FinancialTransaction.transaction_date <= end_of_year,
        )

        total = session.exec(
            select(func.count()).select_from(query.subquery())
        ).one()

        query = (
            query.order_by(FinancialTransaction.transaction_date.desc())
            .offset(skip)
            .limit(limit)
        )
        transactions = session.exec(query).all()
        return list(transactions), total
