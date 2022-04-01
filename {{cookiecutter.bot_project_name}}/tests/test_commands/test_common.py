from typing import Awaitable, Callable
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from pybotx import (
    AttachmentTypes,
    Bot,
    BotAccount,
    BubbleMarkup,
    Button,
    Chat,
    ChatCreatedEvent,
    ChatCreatedMember,
    ChatTypes,
    IncomingMessage,
    KeyboardMarkup,
    OutgoingMessage,
    UserKinds,
)
from pybotx.models.commands import BotCommand
from sqlalchemy.ext.asyncio import AsyncSession
from pybotx.models.attachments import AttachmentVideo

from app.caching.redis_repo import RedisRepo
from app.db.record.repo import RecordRepo
from app.schemas.record import Record



async def test_answer_error_exception_middleware(
    bot: Bot,
    user_huid: UUID,
    incoming_message_factory: Callable[..., IncomingMessage],
    execute_bot_command: Callable[[Bot, BotCommand], Awaitable[None]],
) -> None:
    # - Arrange -
    message = incoming_message_factory(body="/_test-answer-error")
    bot.send = AsyncMock(return_value=uuid4())

    # - Act -
    await execute_bot_command(bot, message)

    # - Assert -
    bot.send.assert_awaited_once_with(
        message=OutgoingMessage(
            bot_id=message.bot.id,
            chat_id=message.chat.id,
            body="test",
            metadata={"test": 1},
            bubbles=BubbleMarkup([[]]),
            keyboard=KeyboardMarkup([[]]),
            file=AttachmentVideo(
                type=AttachmentTypes.VIDEO,
                filename="test_file.mp4",
                size=len(b"Hello, world!\n"),
                is_async_file=False,
                content=b"Hello, world!\n",
                duration=10,
            ),
            recipients=[user_huid],
            silent_response=False,
            markup_auto_adjust=False,
            stealth_mode=False,
            send_push=False,
            ignore_mute=False,
        ),
        wait_callback=True,
        callback_timeout=1,
    )


async def test_answer_message_error_exception_middleware(
    bot: Bot,
    user_huid: UUID,
    incoming_message_factory: Callable[..., IncomingMessage],
    execute_bot_command: Callable[[Bot, BotCommand], Awaitable[None]],
) -> None:
    # - Arrange -
    message = incoming_message_factory(body="/_test-answer-message-error")

    # - Act -
    await execute_bot_command(bot, message)

    # - Assert -
    bot.answer_message.assert_awaited_once_with(
        body="test",
        metadata={"test": 1},
        bubbles=BubbleMarkup([[]]),
        keyboard=KeyboardMarkup([[]]),
        file=AttachmentVideo(
            type=AttachmentTypes.VIDEO,
            filename="test_file.mp4",
            size=len(b"Hello, world!\n"),
            is_async_file=False,
            content=b"Hello, world!\n",
            duration=10,
        ),
        recipients=[user_huid],
        silent_response=False,
        markup_auto_adjust=False,
        stealth_mode=False,
        send_push=False,
        ignore_mute=False,
        wait_callback=True,
        callback_timeout=1,
    )


async def test_fail_handler_while_shutting_down(
    bot: Bot,
    incoming_message_factory: Callable[..., IncomingMessage],
    execute_bot_command: Callable[[Bot, BotCommand], Awaitable[None]],
) -> None:
    # - Arrange -
    message = incoming_message_factory(body="/_test-fail-shutting-down")

    # - Act -
    await execute_bot_command(bot, message)

    # - Assert -
    bot.answer_message.assert_awaited_once_with(
        (
            "При обработке сообщения или нажатия на кнопку произошла "
            "непредвиденная ошибка.\n"
            "Пожалуйста, сообщите об этом вашему администратору бота."
        ),
        wait_callback=False,
    )


async def test_fail_handler(
    bot: Bot,
    incoming_message_factory: Callable[..., IncomingMessage],
    execute_bot_command: Callable[[Bot, BotCommand], Awaitable[None]],
) -> None:
    # - Arrange -
    message = incoming_message_factory(body="/_test-fail")

    # - Act -
    await execute_bot_command(bot, message)

    # - Assert -
    bot.answer_message.assert_awaited_once_with(
        (
            "При обработке сообщения или нажатия на кнопку произошла "
            "непредвиденная ошибка.\n"
            "Пожалуйста, сообщите об этом вашему администратору бота."
        ),
        wait_callback=True,
    )


async def test_redis_handler(
    bot: Bot,
    incoming_message_factory: Callable[..., IncomingMessage],
    execute_bot_command: Callable[[Bot, BotCommand], Awaitable[None]],
    redis_repo: RedisRepo,
) -> None:
    # - Arrange -
    message = incoming_message_factory(body="/_test-redis")

    # - Act -
    await execute_bot_command(bot, message)

    # - Assert -
    assert await redis_repo.rget("test_key") == "test_value"
    assert await redis_repo.get("test_key") is None


@pytest.mark.db
async def test_db_handler(
    bot: Bot,
    incoming_message_factory: Callable[..., IncomingMessage],
    execute_bot_command: Callable[[Bot, BotCommand], Awaitable[None]],
    db_session: AsyncSession,
) -> None:
    # - Arrange -
    message = incoming_message_factory(body="/_test-db")
    record_repo = RecordRepo(db_session)

    # - Act -
    await execute_bot_command(bot, message)

    # - Assert -
    assert await record_repo.get(record_id=1) == Record(
        id=1, record_data="test 1 (updated)"
    )
    assert await record_repo.get_or_none(record_id=2) is None
    assert await record_repo.filter_by_record_data(
        record_data="test not unique data"
    ) == [
        Record(id=3, record_data="test not unique data"),
        Record(id=4, record_data="test not unique data"),
    ]
    assert await record_repo.get_all() == [
        Record(id=1, record_data="test 1 (updated)"),
        Record(id=3, record_data="test not unique data"),
        Record(id=4, record_data="test not unique data"),
    ]


async def test_default_message_handler(
    bot: Bot,
    incoming_message_factory: Callable[..., IncomingMessage],
    execute_bot_command: Callable[[Bot, BotCommand], Awaitable[None]],
) -> None:
    # - Arrange -
    message = incoming_message_factory()

    # - Act -
    await execute_bot_command(bot, message)

    # - Assert -
    bot.answer_message.assert_awaited_once_with("Hello!")


async def test_chat_created_handler(
    bot: Bot,
    bot_id: UUID,
    host: str,
    execute_bot_command: Callable[[Bot, BotCommand], Awaitable[None]],
) -> None:
    # - Arrange -
    command = ChatCreatedEvent(
        sync_id=UUID("2c1a31d6-f47f-5f54-aee2-d0c526bb1d54"),
        bot=BotAccount(
            id=bot_id,
            host=host,
        ),
        chat_name="Feature-party",
        chat=Chat(
            id=UUID("dea55ee4-7a9f-5da0-8c73-079f400ee517"),
            type=ChatTypes.GROUP_CHAT,
        ),
        creator_id=UUID("83fbf1c7-f14b-5176-bd32-ca15cf00d4b7"),
        members=[
            ChatCreatedMember(
                is_admin=True,
                huid=bot_id,
                username="Feature bot",
                kind=UserKinds.BOT,
            ),
            ChatCreatedMember(
                is_admin=False,
                huid=UUID("83fbf1c7-f14b-5176-bd32-ca15cf00d4b7"),
                username="Ivanov Ivan Ivanovich",
                kind=UserKinds.CTS_USER,
            ),
        ],
        raw_command=None,
    )

    # - Act -
    await execute_bot_command(bot, command)

    # - Assert -
    bot.answer_message.assert_awaited_once_with(
        (
            f"Вас приветствует {{cookiecutter.bot_display_name}}!\n\n"
            "Для более подробной информации нажмите кнопку `/help`"
        ),
        bubbles=BubbleMarkup([[Button(command="/help", label="/help")]]),
    )


async def test_help_handler(
    bot: Bot,
    incoming_message_factory: Callable[..., IncomingMessage],
    execute_bot_command: Callable[[Bot, BotCommand], Awaitable[None]],
) -> None:
    # - Arrange -
    message = incoming_message_factory(body="/help")

    # - Act -
    await execute_bot_command(bot, message)

    # - Assert -
    bot.answer_message.assert_awaited_once_with("`/help` -- Get available commands")


async def test_git_commit_sha_handler(
    bot: Bot,
    incoming_message_factory: Callable[..., IncomingMessage],
    execute_bot_command: Callable[[Bot, BotCommand], Awaitable[None]],
) -> None:
    # - Arrange -
    message = incoming_message_factory(body="/_debug:git-commit-sha")

    # - Act -
    await execute_bot_command(bot, message)

    # - Assert -
    bot.answer_message.assert_awaited_once_with("<undefined>")
