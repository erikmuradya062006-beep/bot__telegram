import logging

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from datetime import datetime, date, timedelta, time as dt_time

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
logger = logging.getLogger(__name__)


def _format_date(value: str | date) -> str:
    if isinstance(value, str):
        return datetime.fromisoformat(value).strftime("%d.%m.%Y")
    return value.strftime("%d.%m.%Y")


def generate_time_slots() -> list[str]:
    """Generate available time slots from 09:00 to 17:00 with 45-minute intervals."""
    slots = []
    current = datetime.strptime(f"{WORK_START_HOUR}:00", "%H:%M")
    end = datetime.strptime(f"{WORK_END_HOUR}:00", "%H:%M")
    delta = timedelta(minutes=SLOT_MINUTES)
    while current + delta <= end + timedelta(minutes=1):  # allow ending around 17:00
        slots.append(current.strftime("%H:%M"))
        current += delta
    return slots


ALL_SLOTS = generate_time_slots()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer(
        f"👋 Welcome to {CLINIC_NAME}!\n\n"
        "You can book a dental appointment here.\n"
        "Choose an action from the menu:",
        reply_markup=main_menu_kb(is_admin),
    )


@router.message(F.text == "📅 Book Appointment")
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(BookingStates.choosing_service)
    await message.answer(
        "Choose a service:",
        reply_markup=services_kb(),
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.edit_text("Main menu. Choose an action below 👇")
    await callback.message.answer(
        "Choose an action:",
        reply_markup=main_menu_kb(is_admin),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("service:"), BookingStates.choosing_service)
async def process_service(callback: CallbackQuery, state: FSMContext):
    service = callback.data.split(":", 1)[1]
    await state.update_data(service=service)
    await state.set_state(BookingStates.choosing_doctor)
    await callback.message.edit_text(
        f"Service: <b>{service}</b>\n\nChoose a doctor:",
        reply_markup=doctors_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_service")
async def back_to_service(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.choosing_service)
    await callback.message.edit_text("Choose a service:", reply_markup=services_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("doctor:"), BookingStates.choosing_doctor)
async def process_doctor(callback: CallbackQuery, state: FSMContext):
    doctor = callback.data.split(":", 1)[1]
    await state.update_data(doctor=doctor)
    await state.set_state(BookingStates.choosing_date)
    await callback.message.edit_text(
        f"Doctor: <b>{doctor}</b>\n\nChoose a date:",
        reply_markup=dates_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_doctor")
async def back_to_doctor(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.choosing_doctor)
    data = await state.get_data()
    await callback.message.edit_text(
        f"Service: <b>{data.get('service')}</b>\n\nChoose a doctor:",
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

    # If the selected date is today, remove past slots
    today = datetime.now().date().isoformat()
    if date_str == today:
        now = datetime.now()
        available = [
            t for t in available
            if datetime.strptime(t, "%H:%M").time() > (now + timedelta(minutes=30)).time()
        ]

    if not available:
        await callback.answer("No available slots on that date 😔", show_alert=True)
        return

    await state.set_state(BookingStates.choosing_time)
    date_display = _format_date(date_str)
    await callback.message.edit_text(
        f"Date: <b>{date_display}</b>\nDoctor: <b>{doctor}</b>\n\nChoose a time:",
        reply_markup=times_kb(available),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_date")
async def back_to_date(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.choosing_date)
    data = await state.get_data()
    await callback.message.edit_text(
        f"Doctor: <b>{data.get('doctor')}</b>\n\nChoose a date:",
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

    # Check again in case the slot was taken while the user was selecting
    if await is_slot_taken(doctor, date_str, time_str):
        await callback.answer("This time was just taken. Please choose another.", show_alert=True)
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
            await callback.message.edit_text("Unfortunately, there are no more free slots.")
            return
        await callback.message.edit_text(
            "Choose another time:",
            reply_markup=times_kb(available),
        )
        return

    await state.update_data(time=time_str)
    await state.set_state(BookingStates.entering_name)
    await callback.message.edit_text(
        "Enter your full name (as on your ID or how you prefer):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(BookingStates.entering_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("Name is too short. Please enter your full name:")
        return
    await state.update_data(full_name=name)
    await state.set_state(BookingStates.entering_phone)
    await message.answer(
        "Enter your contact phone number:\n"
        "For example: +1 555 123 4567 or 555-123-4567"
    )


@router.message(BookingStates.entering_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip().replace(" ", "").replace("-", "")
    # Простая проверка
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 9:
        await message.answer("Invalid phone number. Please try again:")
        return

    await state.update_data(phone=phone)
    data = await state.get_data()

    date_display = _format_date(data["date"])
    text = (
        f"📋 <b>Review your booking details:</b>\n\n"
        f"Service: <b>{data['service']}</b>\n"
        f"Doctor: <b>{data['doctor']}</b>\n"
        f"Date: <b>{date_display}</b>\n"
        f"Time: <b>{data['time']}</b>\n"
        f"Full name: <b>{data['full_name']}</b>\n"
        f"Phone: <b>{data['phone']}</b>\n\n"
        f"Is everything correct?"
    )
    await state.set_state(BookingStates.confirming)
    await message.answer(text, reply_markup=confirm_kb(), parse_mode="HTML")


@router.callback_query(F.data == "confirm_yes", BookingStates.confirming)
async def confirm_booking(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    doctor = data["doctor"]
    date_str = data["date"]
    time_str = data["time"]

    logger.info(
        "confirm_booking start: user_id=%s doctor=%s date=%s time=%s",
        callback.from_user.id,
        doctor,
        date_str,
        time_str,
    )

    # Final slot check
    if await is_slot_taken(doctor, date_str, time_str):
        logger.warning(
            "Slot already taken at confirmation: user_id=%s doctor=%s date=%s time=%s",
            callback.from_user.id,
            doctor,
            date_str,
            time_str,
        )
        await callback.message.edit_text(
            "😔 Unfortunately, this time was just taken.\n"
            "Please start the booking again."
        )
        await state.clear()
        await callback.answer()
        return

    try:
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
        logger.info(
            "Appointment confirmed: id=%s user_id=%s doctor=%s date=%s time=%s",
            appointment_id,
            callback.from_user.id,
            doctor,
            date_str,
            time_str,
        )
    except Exception:
        logger.exception(
            "Failed to add appointment: user_id=%s doctor=%s date=%s time=%s",
            callback.from_user.id,
            doctor,
            date_str,
            time_str,
        )
        await callback.message.edit_text(
            "❌ An error occurred while saving your appointment. Please try again later."
        )
        await state.clear()
        await callback.answer()
        return

    date_display = _format_date(date_str)
    await callback.message.edit_text(
        f"✅ <b>Your appointment is confirmed!</b>\n\n"
        f"Booking number: <code>#{appointment_id}</code>\n"
        f"Service: {data['service']}\n"
        f"Doctor: {doctor}\n"
        f"Date: {date_display}\n"
        f"Time: {time_str}\n\n"
        f"We look forward to seeing you! Use the menu to cancel if needed.",
        parse_mode="HTML",
    )

    # Notify admins
    admin_text = (
        f"🆕 <b>New appointment #{appointment_id}</b>\n\n"
        f"Client: {data['full_name']}\n"
        f"Phone: {data['phone']}\n"
        f"Username: @{callback.from_user.username or '—'}\n"
        f"Service: {data['service']}\n"
        f"Doctor: {doctor}\n"
        f"Date: {date_display} at {time_str}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, parse_mode="HTML")
        except Exception:
            pass

    await state.clear()
    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.answer(
        "Main menu:",
        reply_markup=main_menu_kb(is_admin),
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_no", BookingStates.confirming)
async def cancel_confirm(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.edit_text("Appointment cancelled.")
    await callback.message.answer(
        "Choose an action:",
        reply_markup=main_menu_kb(is_admin),
    )
    await callback.answer()


@router.message(F.text == "📋 My Appointments")
async def my_appointments(message: Message):
    appointments = await get_user_appointments(message.from_user.id)
    if not appointments:
        await message.answer("You have no active appointments.")
        return

    text = "📋 <b>Your appointments:</b>\n\n"
    for ap in appointments:
        date_display = _format_date(ap["date"])
        text += (
            f"#{ap['id']} — {date_display} at {ap['time']}\n"
            f"   {ap['service']} / {ap['doctor']}\n\n"
        )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "❌ Cancel Appointment")
async def cancel_start(message: Message):
    appointments = await get_user_appointments(message.from_user.id)
    if not appointments:
        await message.answer("You have no active appointments to cancel.")
        return
    await message.answer(
        "Choose the appointment you want to cancel:",
        reply_markup=cancel_appointments_kb(appointments),
    )


@router.callback_query(F.data.startswith("cancel:"))
async def process_cancel(callback: CallbackQuery, bot: Bot):
    appointment_id = int(callback.data.split(":")[1])
    ap = await get_appointment_by_id(appointment_id)
    success = await cancel_appointment(appointment_id, callback.from_user.id)
    if success and ap:
        await callback.message.edit_text(f"✅ Appointment #{appointment_id} cancelled.")
        date_display = _format_date(ap["date"])
        admin_text = (
            f"❌ Client cancelled appointment #{appointment_id}\n\n"
            f"Client: {ap['full_name']} ({ap['phone']})\n"
            f"Username: @{callback.from_user.username or '—'}\n"
            f"Service: {ap['service']}\n"
            f"Doctor: {ap['doctor']}\n"
            f"Date: {date_display} at {ap['time']}"
        )
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, admin_text)
            except Exception:
                pass
    else:
        await callback.message.edit_text("Failed to cancel the appointment (it may already be cancelled).")
    await callback.answer()
    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.answer(
        "Main menu:",
        reply_markup=main_menu_kb(is_admin),
    )
