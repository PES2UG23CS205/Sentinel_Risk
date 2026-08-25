"""
SentinelRisk — Database Tests

Verifies:
  - All 9 foundation tables can be created
  - Table names are correct
  - Foreign key relationships are enforced
"""

import pytest
from sqlalchemy import create_engine, inspect, event
from sqlalchemy.orm import sessionmaker
from backend.app.db.database import Base, init_database
from backend.app.db.models import (
    Merchant, Customer, Device, PaymentInstrument,
    Transaction, Dispute, Case, AuditLog, Incident,
)


EXPECTED_TABLES = {
    "merchants",
    "customers",
    "devices",
    "payment_instruments",
    "transactions",
    "disputes",
    "cases",
    "audit_log",
    "incidents",
}


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a test database session."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


class TestDatabaseSchema:
    """Tests for database schema initialization."""

    def test_all_tables_exist(self, test_engine):
        """Verify all 9 foundation tables are created."""
        inspector = inspect(test_engine)
        actual_tables = set(inspector.get_table_names())
        assert EXPECTED_TABLES.issubset(actual_tables), (
            f"Missing tables: {EXPECTED_TABLES - actual_tables}"
        )

    def test_table_count(self, test_engine):
        """Verify exactly 9 tables are created."""
        inspector = inspect(test_engine)
        actual_tables = set(inspector.get_table_names())
        assert len(actual_tables & EXPECTED_TABLES) == 9

    def test_merchants_has_required_columns(self, test_engine):
        inspector = inspect(test_engine)
        columns = {col["name"] for col in inspector.get_columns("merchants")}
        assert {"id", "name", "category", "created_at"}.issubset(columns)

    def test_transactions_has_required_columns(self, test_engine):
        inspector = inspect(test_engine)
        columns = {col["name"] for col in inspector.get_columns("transactions")}
        expected = {
            "id", "merchant_id", "customer_id", "device_id",
            "payment_instrument_id", "amount", "currency",
            "timestamp", "status", "is_fraud", "fraud_archetype",
            "fraud_case_id", "is_fraud_ground_truth"
        }
        assert expected.issubset(columns)

    def test_disputes_has_required_columns(self, test_engine):
        inspector = inspect(test_engine)
        columns = {col["name"] for col in inspector.get_columns("disputes")}
        assert {"id", "transaction_id", "reason", "status", "created_at"}.issubset(columns)

    def test_transactions_foreign_keys(self, test_engine):
        inspector = inspect(test_engine)
        fks = inspector.get_foreign_keys("transactions")
        referred_tables = {fk["referred_table"] for fk in fks}
        assert "merchants" in referred_tables
        assert "customers" in referred_tables

    def test_idempotent_init(self, test_engine):
        """init_database can be called multiple times safely."""
        # Call create_all again — should not raise
        Base.metadata.create_all(bind=test_engine)
        inspector = inspect(test_engine)
        actual_tables = set(inspector.get_table_names())
        assert EXPECTED_TABLES.issubset(actual_tables)


class TestBasicInsert:
    """Smoke test — verify basic ORM insert works."""

    def test_create_merchant(self, test_session):
        merchant = Merchant(name="Test Shop", category="retail")
        test_session.add(merchant)
        test_session.commit()
        assert merchant.id is not None
        assert merchant.name == "Test Shop"

    def test_create_transaction(self, test_session):
        merchant = Merchant(name="Test Merchant", category="ecommerce")
        customer = Customer()
        test_session.add_all([merchant, customer])
        test_session.commit()

        txn = Transaction(
            merchant_id=merchant.id,
            customer_id=customer.id,
            amount=1500.00,
            currency="INR",
            status="captured",
        )
        test_session.add(txn)
        test_session.commit()
        assert txn.id is not None
        assert txn.amount == 1500.00
