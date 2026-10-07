from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.board import Board
from app.models.image import Image


DEMO_ACCOUNT_LOGIN = "demo"


def get_demo_account(db: Session) -> Account:
    account = db.scalar(
        select(Account).where(
            Account.login == DEMO_ACCOUNT_LOGIN,
            Account.is_active.is_(True),
        )
    )

    if account is None:
        raise RuntimeError(
            "Demo account not found. Run initial seed first."
        )

    return account


def create_board_for_upload(
    db: Session,
    account_id: int,
    original_filename: str,
) -> Board:
    board = Board(
        created_by_account_id=account_id,
        board_label=original_filename,
    )

    db.add(board)
    db.flush()

    return board


def create_image(
    db: Session,
    *,
    board_id: int,
    account_id: int,
    storage_key: str,
    original_filename: str,
    mime_type: str,
    file_size: int,
) -> Image:
    image = Image(
        board_id=board_id,
        uploaded_by_account_id=account_id,
        storage_key=storage_key,
        original_filename=original_filename,
        mime_type=mime_type,
        file_size=file_size,
    )

    db.add(image)
    db.flush()

    return image


def get_image(db: Session, image_id: int) -> Image | None:
    return db.get(Image, image_id)