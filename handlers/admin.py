from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from datetime import datetime

from config import ADMIN_IDS
from keyboards import admin_menu_kb, main_menu_kb
from database import get_all_active_appointments, get_appointments_by_date

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(F.text == "🛠 Админ-панель")
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа.")
        return
    await message.answer(
        "🛠 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_today")
async def admin_today(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    today = datetime.now().date().isoformat()
    appointments = await get_appointments_by_date(today)

    if not appointments:
        text = f"📅 На сегодня ({datetime.now().strftime('%d.%m.%Y')}) записей нет."
    else:
        text = f"📅 <b>Записи на сегодня ({datetime.now().strftime('%d.%m.%Y')}):</b>\n\n"
        for ap in appointments:
            text += (
                f"⏰ <b>{ap['time']}</b> — {ap['service']}\n"
                f"   Врач: {ap['doctor']}\n"
                f"   Клиент: {ap['full_name']} ({ap['phone']})\n"
                f"   ID: #{ap['id']}\n\n"
            )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_all")
async def admin_all(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    appointments = await get_all_active_appointments(limit=30)

    if not appointments:
        text = "Ближайших активных записей нет."
    else:
        text = "📋 <b>Ближайшие записи:</b>\n\n"
        for ap in appointments:
            date_display = datetime.fromisoformat(ap["date"]).strftime("%d.%m")
            text += (
                f"#{ap['id']} | {date_display} {ap['time']}\n"
                f"   {ap['service']} / {ap['doctor']}\n"
                f"   {ap['full_name']} — {ap['phone']}\n\n"
            )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_menu_kb())
    await callback.answer()
