from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent
)
from loguru import logger
from aiogram import types
from groupes import groups
import hashlib

from db import db

from datetime import datetime, date, timedelta
from collections import defaultdict

days_map = {
    "MONDAY": "Понедельник",
    "TUESDAY": "Вторник",
    "WEDNESDAY": "Среда",
    "THURSDAY": "Четверг",
    "FRIDAY": "Пятница",
    "SATURDAY": "Суббота"
}


def get_inline_keyboard_disclaimer() -> InlineKeyboardMarkup:
    disclaimer_button = InlineKeyboardButton(
        text="Принять",
        callback_data="disclaimer:accept"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[disclaimer_button]]
    )
    return keyboard


def get_inline_keyboard_select() -> InlineKeyboardMarkup:
    select_group_button = InlineKeyboardButton(
        text="Поиск группы",
        switch_inline_query_current_chat="group:",
    )
    select_teacher_for_schedule = InlineKeyboardButton(
        text="Поиск расписания преподавателя",
        switch_inline_query_current_chat="teacher_schedule:",
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[select_group_button], [select_teacher_for_schedule]]
    )
    return keyboard


def get_days_students_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📅 Сегодня", callback_data="day:TODAY"),
            InlineKeyboardButton(text="📆 Завтра", callback_data="day:TOMORROW")
        ],
        [
            InlineKeyboardButton(text="📋 Неделя", callback_data="day:WEEK")
        ],
        [
            InlineKeyboardButton(text="Понедельник", callback_data="day:MONDAY"),
            InlineKeyboardButton(text="Вторник", callback_data="day:TUESDAY")
        ],
        [
            InlineKeyboardButton(text="Среда", callback_data="day:WEDNESDAY"),
            InlineKeyboardButton(text="Четверг", callback_data="day:THURSDAY")
        ],
        [
            InlineKeyboardButton(text="Пятница", callback_data="day:FRIDAY"),
            InlineKeyboardButton(text="Суббота", callback_data="day:SATURDAY")
        ],
        [
            InlineKeyboardButton(text="🔍 Сменить группу", callback_data="comeback")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_days_teacher_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Понедельник", callback_data="teacher_day:MONDAY"),
            InlineKeyboardButton(text="Вторник", callback_data="teacher_day:TUESDAY")
        ],
        [
            InlineKeyboardButton(text="Среда", callback_data="teacher_day:WEDNESDAY"),
            InlineKeyboardButton(text="Четверг", callback_data="teacher_day:THURSDAY")
        ],
        [
            InlineKeyboardButton(text="Пятница", callback_data="teacher_day:FRIDAY"),
            InlineKeyboardButton(text="Суббота", callback_data="teacher_day:SATURDAY")
        ],
        [
            InlineKeyboardButton(text="Вернуться", callback_data="comeback")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def handle_group_search(query: str):
    results = []
    if query:
        for key, value in groups.items():
            if query.lower() in key.lower() or query.lower() in value.lower():
                result_id = hashlib.md5(key.encode()).hexdigest()
                input_content = InputTextMessageContent(
                    message_text=f"Вы выбрали группу: {key} ({value})"
                )
                result = InlineQueryResultArticle(
                    id=result_id,
                    title=f"Группа: {key}",
                    input_message_content=input_content,
                    description=f"Код группы: {value}"
                )
                results.append(result)

    if query and not results:
        result_id = hashlib.md5(query.encode()).hexdigest()
        input_content = InputTextMessageContent(
            message_text="Группа не найдена. Пожалуйста, введите корректный код группы."
        )
        results.append(
            InlineQueryResultArticle(
                id=result_id,
                title="Группа не найдена",
                input_message_content=input_content,
                description="Нет такой группы."
            )
        )
    return results


async def handle_teacher_inline_search(query: str) -> list[InlineQueryResultArticle]:
    results = []
    search = query.strip().lower()
    if not search:
        return results

    logger.info(f"Searching teachers for query: {search}")

    matched_teachers = await db.search_teachers(search)

    for teacher in matched_teachers:
        name = teacher["full_name"]
        short_hash = teacher.get("hash") or hashlib.md5(name.encode()).hexdigest()

        input_content = InputTextMessageContent(
            message_text=f"Преподаватель: {name}"
        )

        results.append(
            InlineQueryResultArticle(
                id=short_hash,
                title=name,
                input_message_content=input_content,
                description="Нажмите, чтобы посмотреть расписание"
            )
        )

    if not results:
        result_id = hashlib.md5(query.encode()).hexdigest()
        input_content = InputTextMessageContent(
            message_text="Преподаватель не найден. Пожалуйста, введите корректное имя."
        )
        results.append(
            InlineQueryResultArticle(
                id=result_id,
                title="Преподаватель не найден",
                input_message_content=input_content,
                description="Нет совпадений"
            )
        )

    return results


async def handle_teacher_inline_search_names(query: str) -> list[InlineQueryResultArticle]:
    results = []
    search = query.strip().lower()
    if not search:
        return results

    logger.info(f"Searching teachers (names only) for query: {search}")

    matched_teachers = await db.search_teachers(search)

    for teacher in matched_teachers:
        name = teacher["full_name"]
        short_hash = teacher.get("hash") or hashlib.md5(name.encode()).hexdigest()

        input_content = InputTextMessageContent(
            message_text=f"Преподаватель: {name}"
        )

        results.append(
            InlineQueryResultArticle(
                id=short_hash,
                title=name,
                input_message_content=input_content,
                description="Преподаватель"
            )
        )

    if not results:
        result_id = hashlib.md5(query.encode()).hexdigest()
        input_content = InputTextMessageContent(
            message_text="Преподаватель не найден. Пожалуйста, введите корректное имя."
        )
        results.append(
            InlineQueryResultArticle(
                id=result_id,
                title="Преподаватель не найден",
                input_message_content=input_content,
                description="Нет совпадений"
            )
        )

    return results


def get_human_readable_schedule(data):
    days_map = {
        "MONDAY": "Понедельник",
        "TUESDAY": "Вторник",
        "WEDNESDAY": "Среда",
        "THURSDAY": "Четверг",
        "FRIDAY": "Пятница",
        "SATURDAY": "Суббота"
    }

    today = date.today()

    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    week_day_dates = {
        "MONDAY": monday,
        "TUESDAY": monday + timedelta(days=1),
        "WEDNESDAY": monday + timedelta(days=2),
        "THURSDAY": monday + timedelta(days=3),
        "FRIDAY": monday + timedelta(days=4),
        "SATURDAY": monday + timedelta(days=5),
        "SUNDAY": monday + timedelta(days=6),
    }

    week_type = "EVEN" if today.isocalendar().week % 2 == 0 else "ODD"

    schedule_by_day = {name: [] for name in days_map.values()}

    for item in data.get('data', {}).get('scheduleItems', []):
        day_key = item.get('dayOfWeek')
        day_ru = days_map.get(day_key)
        if not day_ru:
            continue

        start_date_str = item.get('startDate')
        if not start_date_str:
            continue
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        if not (monday <= start_date <= sunday):
            continue

        lesson_date = week_day_dates.get(day_key)
        if not lesson_date:
            continue

        subject = item.get('subject', {})
        lesson = {
            "lessonNumber": item.get('lessonNumber'),
            "startTime": item.get('startTime'),
            "endTime": item.get('endTime'),
            "startDate": start_date_str,
            "date": lesson_date.isoformat(),
            "weekType": week_type,
            "subject": subject.get('name'),
            "subjectShort": subject.get('shortName'),
            "teachers": ", ".join(t.get('fullName') for t in item.get('teachers', []) if t.get('fullName')) or None,
            "classrooms": ", ".join(c.get('roomNumber') for c in item.get('classrooms', []) if c.get('roomNumber')) or None,
            "groups": ", ".join(g.get('name') for g in item.get('groups', []) if g.get('name')) or None
        }
        schedule_by_day[day_ru].append(lesson)

    for lessons in schedule_by_day.values():
        lessons.sort(key=lambda x: x['startTime'] or "")

    return schedule_by_day


def get_human_readable_teacher_schedule(data):
    days_map = {
        "MONDAY": "Понедельник",
        "TUESDAY": "Вторник",
        "WEDNESDAY": "Среда",
        "THURSDAY": "Четверг",
        "FRIDAY": "Пятница",
        "SATURDAY": "Суббота"
    }

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    week_day_dates = {
        "MONDAY": monday,
        "TUESDAY": monday + timedelta(days=1),
        "WEDNESDAY": monday + timedelta(days=2),
        "THURSDAY": monday + timedelta(days=3),
        "FRIDAY": monday + timedelta(days=4),
        "SATURDAY": monday + timedelta(days=5),
        "SUNDAY": monday + timedelta(days=6),
    }

    week_type = "EVEN" if today.isocalendar().week % 2 == 0 else "ODD"

    schedule_by_day = {name: [] for name in days_map.values()}

    for item in data.get('data', {}).get('scheduleItems', []):
        day_key = item.get('dayOfWeek')
        day_ru = days_map.get(day_key)
        if not day_ru:
            continue

        start_date_str = item.get('startDate')
        if not start_date_str:
            continue
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        if not (monday <= start_date <= sunday):
            continue

        lesson_date = week_day_dates.get(day_key)
        subject = item.get('subject', {})

        lesson = {
            "lessonNumber": item.get('lessonNumber'),
            "startTime": item.get('startTime'),
            "endTime": item.get('endTime'),
            "startDate": start_date_str,
            "date": lesson_date.isoformat(),
            "weekType": week_type,
            "subject": subject.get('name'),
            "subjectShort": subject.get('shortName'),
            "groups": ", ".join(g.get('name') for g in item.get('groups', []) if g.get('name')) or None,
            "classrooms": ", ".join(c.get('roomNumber') for c in item.get('classrooms', []) if c.get('roomNumber')) or None
        }

        schedule_by_day[day_ru].append(lesson)

    for lessons in schedule_by_day.values():
        lessons.sort(key=lambda x: x['startTime'] or "")

    return schedule_by_day