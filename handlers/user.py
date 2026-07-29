from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta, time as dt_time

from config import ADMIN_IDS, CLINIC_NAME, WORK_START_HOUR, WORK_END_HOUR, SLOT_MINUTES
from states import BookingStates
from keyboards import (
    main_menu_kb,
    services_kb,
    doctors_kb,
    dates_kb,
    times_kb,
    confirm_kb,
    cancel_appointments_kb,
)
from database import (
    add_appointment,
    get_user_appointments,
    get_appointment_by_id,
    cancel_appointment,
    is_slot_taken,
    get_booked_slots,
)

router = Router()


def generate_time_slots() -> list[str]:
    """Генерирует слоты с 09:00 до 17:00 с интервалом 45 мин"""
    slots = []
    current = datetime.strptime(f"{WORK_START_HOUR}:00", "%H:%M")
    end = datetime.strptime(f"{WORK_END_HOUR}:00", "%H:%M")
    delta = timedelta(minutes=SLOT_MINUTES)
    while current + delta <= end + timedelta(minutes=1):  # допускаем окончание около 17:00
        slots.append(current.strftime("%H:%M"))
        current += delta
    return slots


ALL_SLOTS = generate_time_slots()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer(
        f"👋 Добро пожаловать в {CLINIC_NAME}!\n\n"
        "Здесь вы можете записаться на приём к стоматологу.\n"
        "Выберите действие в меню:",
        reply_markup=main_menu_kb(is_admin),
    )


@router.message(F.text == "📅 Записаться")
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(BookingStates.choosing_service)
    await message.answer(
        "Выберите услугу:",
        reply_markup=services_kb(),
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.edit_text("Главное меню. Выберите действие ниже 👇")
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=main_menu_kb(is_admin),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("service:"), BookingStates.choosing_service)
async def process_service(callback: CallbackQuery, state: FSMContext):
    service = callback.data.split(":", 1)[1]
    await state.update_data(service=service)
    await state.set_state(BookingStates.choosing_doctor)
    await callback.message.edit_text(
        f"Услуга: <b>{service}</b>\n\nВыберите врача:",
        reply_markup=doctors_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_service")
async def back_to_service(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.choosing_service)
    await callback.message.edit_text("Выберите услугу:", reply_markup=services_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("doctor:"), BookingStates.choosing_doctor)
async def process_doctor(callback: CallbackQuery, state: FSMContext):
    doctor = callback.data.split(":", 1)[1]
    await state.update_data(doctor=doctor)
    await state.set_state(BookingStates.choosing_date)
    await callback.message.edit_text(
        f"Врач: <b>{doctor}</b>\n\nВыберите дату:",
        reply_markup=dates_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_doctor")
async def back_to_doctor(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.choosing_doctor)
    data = await state.get_data()
    await callback.message.edit_text(
        f"Услуга: <b>{data.get('service')}</b>\n\nВыберите врача:",
        reply_markup=doctors_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("date:"), BookingStates.choosing_date)
async def process_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split(":", 1)[1]
    await state.update_data(date=date_str)
    data = await state.get_data()
    doctor = data["doctor"]

    booked = await get_booked_slots(doctor, date_str)
    available = [t for t in ALL_SLOTS if t not in booked]

    # Если сегодня — убираем прошедшие слоты
    today = datetime.now().date().isoformat()
    if date_str == today:
        now = datetime.now()
        available = [
            t for t in available
            if datetime.strptime(t, "%H:%M").time() > (now + timedelta(minutes=30)).time()
        ]

    if not available:
        await callback.answer("На эту дату нет свободных слотов 😔", show_alert=True)
        return

    await state.set_state(BookingStates.choosing_time)
    date_display = datetime.fromisoformat(date_str).strftime("%d.%m.%Y")
    await callback.message.edit_text(
        f"Дата: <b>{date_display}</b>\nВрач: <b>{doctor}</b>\n\nВыберите время:",
        reply_markup=times_kb(available),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_date")
async def back_to_date(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.choosing_date)
    data = await state.get_data()
    await callback.message.edit_text(
        f"Врач: <b>{data.get('doctor')}</b>\n\nВыберите дату:",
        reply_markup=dates_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("time:"), BookingStates.choosing_time)
async def process_time(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.split(":", 1)[1]
    data = await state.get_data()
    doctor = data["doctor"]
    date_str = data["date"]

    # Проверка, не заняли ли слот пока выбирали
    if await is_slot_taken(doctor, date_str, time_str):
        await callback.answer("Это время только что заняли. Выберите другое.", show_alert=True)
        booked = await get_booked_slots(doctor, date_str)
        available = [t for t in ALL_SLOTS if t not in booked]
        today = datetime.now().date().isoformat()
        if date_str == today:
            now = datetime.now()
            available = [
                t for t in available
                if datetime.strptime(t, "%H:%M").time() > (now + timedelta(minutes=30)).time()
            ]
        if not available:
            await callback.message.edit_text("К сожалению, свободных слотов больше нет.")
            return
        await callback.message.edit_text(
            "Выберите другое время:",
            reply_markup=times_kb(available),
        )
        return

    await state.update_data(time=time_str)
    await state.set_state(BookingStates.entering_name)
    await callback.message.edit_text(
        "Введите ваше <b>ФИО</b> (как в паспорте или как удобно):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(BookingStates.entering_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("Слишком короткое имя. Введите ФИО полностью:")
        return
    await state.update_data(full_name=name)
    await state.set_state(BookingStates.entering_phone)
    await message.answer(
        "Введите номер телефона для связи:\n"
        "Например: +79001234567 или 89001234567"
    )


@router.message(BookingStates.entering_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip().replace(" ", "").replace("-", "")
    # Простая проверка
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        await message.answer("Некорректный номер. Попробуйте ещё раз:")
        return

    await state.update_data(phone=phone)
    data = await state.get_data()

    date_display = datetime.fromisoformat(data["date"]).strftime("%d.%m.%Y")
    text = (
        f"📋 <b>Проверьте данные записи:</b>\n\n"
        f"Услуга: <b>{data['service']}</b>\n"
        f"Врач: <b>{data['doctor']}</b>\n"
        f"Дата: <b>{date_display}</b>\n"
        f"Время: <b>{data['time']}</b>\n"
        f"ФИО: <b>{data['full_name']}</b>\n"
        f"Телефон: <b>{data['phone']}</b>\n\n"
        f"Всё верно?"
    )
    await state.set_state(BookingStates.confirming)
    await message.answer(text, reply_markup=confirm_kb(), parse_mode="HTML")


@router.callback_query(F.data == "confirm_yes", BookingStates.confirming)
async def confirm_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    doctor = data["doctor"]
    date_str = data["date"]
    time_str = data["time"]

    # Финальная проверка слота
    if await is_slot_taken(doctor, date_str, time_str):
        await callback.message.edit_text(
            "😔 К сожалению, это время только что заняли.\n"
            "Пожалуйста, начните запись заново."
        )
        await state.clear()
        await callback.answer()
        return

    appointment_id = await add_appointment(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        full_name=data["full_name"],
        phone=data["phone"],
        service=data["service"],
        doctor=doctor,
        date=date_str,
        time=time_str,
    )

    date_display = datetime.fromisoformat(date_str).strftime("%d.%m.%Y")
    await callback.message.edit_text(
        f"✅ <b>Вы успешно записаны!</b>\n\n"
        f"Номер записи: <code>#{appointment_id}</code>\n"
        f"Услуга: {data['service']}\n"
        f"Врач: {doctor}\n"
        f"Дата: {date_display}\n"
        f"Время: {time_str}\n\n"
        f"Мы ждём вас! Если нужно отменить — используйте меню.",
        parse_mode="HTML",
    )

    # Уведомление админам
    admin_text = (
        f"🆕 <b>Новая запись #{appointment_id}</b>\n\n"
        f"Клиент: {data['full_name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Username: @{callback.from_user.username or '—'}\n"
        f"Услуга: {data['service']}\n"
        f"Врач: {doctor}\n"
        f"Дата: {date_display} в {time_str}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, parse_mode="HTML")
        except Exception:
            pass

    await state.clear()
    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_menu_kb(is_admin),
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_no", BookingStates.confirming)
async def cancel_confirm(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.edit_text("Запись отменена.")
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=main_menu_kb(is_admin),
    )
    await callback.answer()


@router.message(F.text == "📋 Мои записи")
async def my_appointments(message: Message):
    appointments = await get_user_appointments(message.from_user.id)
    if not appointments:
        await message.answer("У вас нет активных записей.")
        return

    text = "📋 <b>Ваши записи:</b>\n\n"
    for ap in appointments:
        date_display = datetime.fromisoformat(ap["date"]).strftime("%d.%m.%Y")
        text += (
            f"#{ap['id']} — {date_display} в {ap['time']}\n"
            f"   {ap['service']} / {ap['doctor']}\n\n"
        )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "❌ Отменить запись")
async def cancel_start(message: Message):
    appointments = await get_user_appointments(message.from_user.id)
    if not appointments:
        await message.answer("У вас нет активных записей для отмены.")
        return
    await message.answer(
        "Выберите запись, которую хотите отменить:",
        reply_markup=cancel_appointments_kb(appointments),
    )


@router.callback_query(F.data.startswith("cancel:"))
async def process_cancel(callback: CallbackQuery, bot: Bot):
    appointment_id = int(callback.data.split(":")[1])
    ap = await get_appointment_by_id(appointment_id)
    success = await cancel_appointment(appointment_id, callback.from_user.id)
    if success and ap:
        await callback.message.edit_text(f"✅ Запись #{appointment_id} отменена.")
        date_display = datetime.fromisoformat(ap["date"]).strftime("%d.%m.%Y")
        admin_text = (
            f"❌ Клиент отменил запись #{appointment_id}\n\n"
            f"Клиент: {ap['full_name']} ({ap['phone']})\n"
            f"Username: @{callback.from_user.username or '—'}\n"
            f"Услуга: {ap['service']}\n"
            f"Врач: {ap['doctor']}\n"
            f"Дата: {date_display} в {ap['time']}"
        )
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, admin_text)
            except Exception:
                pass
    else:
        await callback.message.edit_text("Не удалось отменить запись (возможно, она уже отменена).")
    await callback.answer()
    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_menu_kb(is_admin),
    )
