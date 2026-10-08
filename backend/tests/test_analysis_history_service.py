import pytest
from sqlalchemy import select

from app.models.analysis_request import AnalysisRequest
from app.services.analysis_history_service import get_analysis_history


@pytest.fixture
def db():
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        yield session


def test_history_returns_existing_requests(db):
    account_id = db.scalar(
        select(AnalysisRequest.account_id).limit(1)
    )

    if account_id is None:
        pytest.skip("No analysis requests in test database")

    history = get_analysis_history(db, account_id)

    assert isinstance(history, list)
    assert len(history) > 0

    for item in history:
        assert item["request_id"] > 0
        assert item["image_id"] > 0
        assert item["detections_count"] >= 0


def test_history_sorted_newest_first(db):
    account_id = db.scalar(
        select(AnalysisRequest.account_id).limit(1)
    )

    if account_id is None:
        pytest.skip("No analysis requests in test database")

    history = get_analysis_history(db, account_id)

    sorting_keys = [
        (item["created_at"], item["request_id"])
        for item in history
    ]

    assert sorting_keys == sorted(
        sorting_keys,
        reverse=True,
    )


def test_history_pagination(db):
    account_id = db.scalar(
        select(AnalysisRequest.account_id).limit(1)
    )

    if account_id is None:
        pytest.skip("No analysis requests in test database")

    first_page = get_analysis_history(
        db,
        account_id,
        limit=1,
        offset=0,
    )

    second_page = get_analysis_history(
        db,
        account_id,
        limit=1,
        offset=1,
    )

    assert len(first_page) <= 1
    assert len(second_page) <= 1

    if first_page and second_page:
        assert (
            first_page[0]["request_id"]
            != second_page[0]["request_id"]
        )


def test_history_unknown_account(db):
    max_account_id = db.scalar(
        select(AnalysisRequest.account_id)
        .order_by(AnalysisRequest.account_id.desc())
        .limit(1)
    )

    unknown_account_id = (max_account_id or 0) + 1000000

    history = get_analysis_history(
        db,
        unknown_account_id,
    )

    assert history == []


@pytest.mark.parametrize(
    "account_id,limit,offset",
    [
        (0, 20, 0),
        (-1, 20, 0),
        (1, 0, 0),
        (1, 101, 0),
        (1, 20, -1),
    ],
)
def test_history_invalid_parameters(
    db,
    account_id,
    limit,
    offset,
):
    with pytest.raises(ValueError):
        get_analysis_history(
            db,
            account_id,
            limit=limit,
            offset=offset,
        )


def test_history_uses_single_sql_query(db):
    """
    Получение истории должно выполнять один SQL-запрос,
    независимо от количества анализов.
    """
    from sqlalchemy import event

    account_id = db.scalar(
        select(AnalysisRequest.account_id).limit(1)
    )

    if account_id is None:
        pytest.skip("No analysis requests in test database")

    engine = db.get_bind()
    statements = []

    def count_queries(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(
        engine,
        "before_cursor_execute",
        count_queries,
    )

    try:
        history = get_analysis_history(
            db,
            account_id=account_id,
            limit=100,
        )
    finally:
        event.remove(
            engine,
            "before_cursor_execute",
            count_queries,
        )

    assert isinstance(history, list)
    assert len(statements) == 1, (
        f"Ожидался 1 SELECT, получено {len(statements)}"
    )


def test_history_isolated_between_accounts(db):
    """
    Пользователь видит только собственные запросы анализа.
    Созданные тестом данные не сохраняются в базе.
    """
    from uuid import uuid4

    from app.models.account import Account
    from app.models.board import Board
    from app.models.image import Image

    suffix = uuid4().hex

    try:
        account_a = Account(
            login=f"history_a_{suffix}",
            display_name="History Test A",
        )
        account_b = Account(
            login=f"history_b_{suffix}",
            display_name="History Test B",
        )

        db.add_all([account_a, account_b])
        db.flush()

        account_a_id = account_a.account_id
        account_b_id = account_b.account_id

        requests = []

        for account in (account_a, account_b):
            board = Board(
                created_by_account_id=account.account_id,
                board_label=f"history-board-{suffix}",
            )
            db.add(board)
            db.flush()

            image = Image(
                board_id=board.board_id,
                uploaded_by_account_id=account.account_id,
                storage_key=f"history-test/{uuid4().hex}.jpg",
                original_filename="test.jpg",
                mime_type="image/jpeg",
                file_size=123,
            )
            db.add(image)
            db.flush()

            request = AnalysisRequest(
                account_id=account.account_id,
                image_id=image.image_id,
            )
            db.add(request)
            db.flush()

            requests.append(request.analysis_request_id)

        history_a = get_analysis_history(
            db,
            account_id=account_a_id,
        )
        history_b = get_analysis_history(
            db,
            account_id=account_b_id,
        )

        ids_a = {item["request_id"] for item in history_a}
        ids_b = {item["request_id"] for item in history_b}

        assert requests[0] in ids_a
        assert requests[1] not in ids_a

        assert requests[1] in ids_b
        assert requests[0] not in ids_b

        assert ids_a.isdisjoint(ids_b)

    finally:
        db.rollback()
