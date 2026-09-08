"""Category service layer for business logic."""

from sqlmodel import Session, select

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:
    """Service class for category-related operations."""

    @staticmethod
    def create_category(session: Session, category_in: CategoryCreate) -> Category:
        """Create a new category.

        Args:
            session: Database session.
            category_in: Category data to create.

        Returns:
            Category: The created category.
        """
        db_category = Category.model_validate(category_in)
        session.add(db_category)
        session.commit()
        session.refresh(db_category)
        return db_category

    @staticmethod
    def get_categories(session: Session, only_active: bool = True) -> list[Category]:
        """List categories.

        Args:
            session: Database session.
            only_active: Whether to return only active categories.

        Returns:
            list[Category]: List of categories.
        """
        statement = select(Category)
        if only_active:
            statement = statement.where(Category.is_active.is_(True))
        return session.exec(statement).all()

    @staticmethod
    def update_category(
        session: Session, db_category: Category, category_in: CategoryUpdate
    ) -> Category:
        """Update a category.

        Args:
            session: Database session.
            db_category: Existing category in DB.
            category_in: New data.

        Returns:
            Category: Updated category.
        """
        update_data = category_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_category, key, value)

        session.add(db_category)
        session.commit()
        session.refresh(db_category)
        return db_category

    @staticmethod
    def delete_category(session: Session, db_category: Category) -> None:
        """Deactivate a category (soft delete equivalent for categories).

        Args:
            session: Database session.
            db_category: Category to deactivate.
        """
        db_category.is_active = False
        session.add(db_category)
        session.commit()
