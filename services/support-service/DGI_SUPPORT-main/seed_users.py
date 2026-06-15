"""Seed script: wipe all users and create production-ready accounts.

Usage:
    python seed_users.py
"""
from datetime import datetime, timedelta
from random import randint

from app.db.session import engine, get_db
from app.db.models import Base, User, UserRole, Ticket, TicketStatus, TicketPriority, TicketComment, TicketEvent, TicketAttachment, Equipment, EquipmentCategory, EquipmentStatus, ConsumableType, KbArticle, KbFile, KbCategory, Notification, Broadcast
from app.core.security import hash_password
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# ── Accounts to create ──────────────────────────────────────────────
# Format: (username, full_name, position, role, internal_number, office)
ACCOUNTS = [
    # ── Admin ────────────────────────────────────────────────────────
    ("EvteevAS",    "Евтеев А.С.",   "Администратор системы",             UserRole.admin,   "21-001", "18.01"),
    # ── Engineers (Управление информатизации) ────────────────────────
    ("KozlovDV",    "Козлов Д.В.",   "Инженер техподдержки",              UserRole.engineer, "21-010", "18.05"),
    ("PetrovaEM",   "Петрова Е.М.",  "Инженер техподдержки",              UserRole.engineer, "21-011", "18.06"),
    ("SidorovNA",   "Сидоров Н.А.",  "Старший инженер техподдержки",      UserRole.engineer, "21-012", "18.07"),
    # ── VIP — Руководство ────────────────────────────────────────────
    ("KarpovVI",    "Карпов В.И.",   "Руководитель департамента",         UserRole.user,     "21-000", "01.01"),
    ("OrlovaNS",    "Орлова Н.С.",   "Зам руководителя департамента",     UserRole.user,     "21-001", "01.02"),
    # ── Начальники управлений ────────────────────────────────────────
    ("MikhailovKT", "Михайлов К.Т.", "Начальник управления приватизации", UserRole.user,     "22-001", "12.01"),
    ("ZaitsevaOP",  "Зайцева О.П.",  "Начальник управления аренды",      UserRole.user,     "22-002", "14.01"),
    ("KrylovaDA",   "Крылова Д.А.",  "Начальник управления земельных участков", UserRole.user, "22-003", "10.01"),
    ("BelyaevGS",   "Беляев Г.С.",   "Начальник управления госуслуг",    UserRole.user,     "22-004", "22.01"),
    ("RomanovaEV",  "Романова Е.В.", "Начальник управления КРТ",          UserRole.user,     "22-005", "24.01"),
    # ── Начальники отделов ──────────────────────────────────────────
    ("FedorovRS",   "Фёдоров Р.С.",  "Начальник отдела земель ЦАО",      UserRole.user,     "22-400", "20.10"),
    ("LebedevAP",   "Лебедев А.П.",  "Начальник отдела приватизации нежилых", UserRole.user, "22-410", "12.10"),
    ("SokolovaIM",  "Соколова И.М.", "Зам начальника управления аренды", UserRole.user,     "22-020", "14.05"),
    # ── Ведущие специалисты ─────────────────────────────────────────
    ("IvanovMP",    "Иванов М.П.",   "Ведущий специалист управления приватизации",  UserRole.user, "22-100", "12.02"),
    ("VolkovIG",    "Волков И.Г.",   "Ведущий специалист управления аренды", UserRole.user,  "22-200", "14.03"),
    ("MorozovAP",   "Морозов А.П.",  "Ведущий специалист управления КРТ", UserRole.user,     "22-700", "24.02"),
    # ── Специалисты ────────────────────────────────────────────────
    ("SmirnovaOV",  "Смирнова О.В.", "Специалист управления приватизации", UserRole.user,     "22-101", "12.03"),
    ("NovikovaAT",  "Новикова А.Т.", "Юрисконсульт управления аренды",    UserRole.user,     "22-300", "16.01"),
    ("KuznetsovaLB","Кузнецова Л.Б.","Специалист управления земельных участков", UserRole.user, "22-500", "10.02"),
    ("BelovaNK",    "Белова Н.К.",   "Специалист управления госуслуг",    UserRole.user,     "22-600", "22.03"),
]

# All accounts get the same default password (meets policy: 8+ chars, 1 upper, 1 digit, 1 special)
DEFAULT_PASSWORD = "Dgi2025!"


def seed() -> None:
    db: Session = next(get_db())

    # ── Wipe dependent tables first, then users ─────────────────────
    print("Wiping existing data...")
    db.query(Notification).delete()
    db.query(Broadcast).delete()
    db.query(TicketAttachment).delete()
    db.query(TicketComment).delete()
    db.query(TicketEvent).delete()
    db.query(Ticket).delete()
    db.query(Equipment).delete()
    db.query(KbFile).delete()
    db.query(KbArticle).delete()
    db.query(User).delete()
    db.commit()
    print("  All users, tickets, equipment, KB, notifications wiped.")

    # ── Create accounts ─────────────────────────────────────────────
    for username, full_name, position, role, int_num, office in ACCOUNTS:
        u = User(
            username=username,
            password_hash=hash_password(DEFAULT_PASSWORD),
            full_name=full_name,
            position=position,
            role=role,
            internal_number=int_num,
            office=office,
            is_active=1,
            needs_approval=0,
        )
        db.add(u)
        print(f"  Created: {username} ({role.value}) — {full_name}, {position}")

    db.commit()
    print(f"  {len(ACCOUNTS)} accounts created. Default password: {DEFAULT_PASSWORD}")

    # ── Seed FAQ articles ────────────────────────────────────────────
    admin_user = db.query(User).filter(User.username == "EvteevAS").one()

    faq_articles = [
        KbArticle(
            title="Как сменить пароль",
            body="1. Нажмите Ctrl+Alt+Del на клавиатуре\n2. Выберите «Сменить пароль»\n3. Введите текущий пароль и новый пароль\n4. Новый пароль должен содержать минимум 8 символов, одну заглавную букву, одну цифру и один специальный символ\n5. Нажмите «ОК»\n\nЕсли вы забыли текущий пароль — обратитесь в техподдержку.",
            category=KbCategory.faq,
            is_published=1,
            author_id=admin_user.id,
        ),
        KbArticle(
            title="Как подключиться к корпоративной сети Wi-Fi",
            body="1. Выберите сеть DGI-Staff в списке доступных Wi-Fi сетей\n2. Введите ваш логин и пароль от учётной записи\n3. При появлении сертификата — нажмите «Доверять»\n4. Подключение установлено\n\nЕсли не удаётся подключиться — убедитесь, что MAC-адрес вашего устройства зарегистрирован в системе. Обратитесь к инженеру техподдержки.",
            category=KbCategory.faq,
            is_published=1,
            author_id=admin_user.id,
        ),
        KbArticle(
            title="Как настроить Outlook для корпоративной почты",
            body="1. Откройте Outlook\n2. Файл → Добавить учётную запись\n3. Введите ваш email: логин@mos.ru\n4. Выберите «Ручная настройка» → Exchange\n5. Сервер: mail.mos.ru\n6. Введите логин и пароль\n7. Дождитесь завершения настройки\n\nПри проблемах — убедитесь, что вы подключены к корпоративной сети.",
            category=KbCategory.guide,
            is_published=1,
            author_id=admin_user.id,
        ),
        KbArticle(
            title="Как установить принтер",
            body="1. Пуск → Параметры → Устройства → Принтеры и сканеры\n2. Нажмите «Добавить принтер»\n3. Выберите принтер из списка (по кабинету)\n4. Дождитесь установки драйверов\n\nЕсли нужного принтера нет в списке — создайте заявку в техподдержку с указанием модели и кабинета.",
            category=KbCategory.guide,
            is_published=1,
            author_id=admin_user.id,
        ),
        KbArticle(
            title="Политика информационной безопасности",
            body="Основные правила:\n\n• Запрещена установка несанкционированного ПО\n• Запрещено использование личных USB-накопителей\n• Пароль должен соответствовать политике (минимум 8 символов, заглавная буква, цифра, спецсимвол)\n• Пароль меняется каждые 90 дней\n• Запрещена передача пароля третьим лицам\n• При обнаружении подозрительной активности — немедленно обратитесь в техподдержку\n\nПолный текст политики доступен в разделе файлов.",
            category=KbCategory.policy,
            is_published=1,
            author_id=admin_user.id,
        ),
    ]

    for a in faq_articles:
        db.add(a)
    db.commit()
    print(f"  {len(faq_articles)} KB articles created.")

    # ── Seed equipment ────────────────────────────────────────────────
    from app.db.models import EquipmentCategory as EC, EquipmentStatus as ES

    # Собираем маппинг: кабинет → пользователь
    office_user = {}
    for u in db.query(User).all():
        if u.office:
            office_user[u.office] = u.id

    monoblock_model = "HP EliteOne 800 G6"
    printer_models = [
        ("HP LaserJet Pro M404dn", "Принтер HP M404dn"),
        ("HP LaserJet Pro MFP 4101fdw", "МФУ HP 4101fdw"),
        ("HP Color LaserJet Pro MFP 3301fdw", "Цветное МФУ HP 3301fdw"),
        ("Kyocera ECOSYS P2235dn", "Принтер Kyocera P2235dn"),
    ]

    eq_items = []
    sn_counter = 1000

    # ── Моноблоки: по кабинетам пользователей ────────────────────────
    # Каждый пользователь с кабинетом получает 1 моноблок
    # В больших кабинетах (18.x, 12.x, 10.x) — по 2
    user_offices = [
        ("18.01", "EvteevAS"),   ("18.05", "KozlovDV"),  ("18.06", "PetrovaEM"),
        ("18.07", "SidorovNA"),
        ("10.01", "KrylovaDA"),  ("10.02", "KuznetsovaLB"),
        ("12.01", "MikhailovKT"),("12.02", "IvanovMP"),  ("12.03", "SmirnovaOV"),
        ("12.10", "LebedevAP"),
        ("14.01", "ZaitsevaOP"), ("14.03", "VolkovIG"),  ("14.05", "SokolovaIM"),
        ("16.01", "NovikovaAT"),
        ("20.10", "FedorovRS"),
        ("22.01", "BelyaevGS"),  ("22.03", "BelovaNK"),
        ("24.01", "RomanovaEV"), ("24.02", "MorozovAP"),
    ]

    # Основной моноблок каждому пользователю
    for office, username in user_offices:
        uid = office_user.get(office)
        sn = f"CZC{sn_counter:06d}"
        sn_counter += 1
        eq_items.append(Equipment(
            category=EC.monoblock,
            model=monoblock_model,
            serial_number=sn,
            name=f"Моноблок {monoblock_model}",
            status=ES.assigned,
            assigned_to_user_id=uid,
            location=office,
            is_warehouse=False,
        ))

    # Дополнительные моноблоки в больших кабинетах (2-й рабочий место)
    extra_monoblocks = [
        ("18.01", None), ("18.05", None), ("18.06", None), ("18.08", None),
        ("10.01", None), ("10.03", None), ("10.05", None),
        ("12.01", None), ("12.05", None), ("12.10", None),
        ("14.01", None), ("14.04", None),
    ]
    for office, uid in extra_monoblocks:
        sn = f"CZC{sn_counter:06d}"
        sn_counter += 1
        eq_items.append(Equipment(
            category=EC.monoblock,
            model=monoblock_model,
            serial_number=sn,
            name=f"Моноблок {monoblock_model}",
            status=ES.assigned,
            assigned_to_user_id=uid,
            location=office,
            is_warehouse=False,
        ))

    # Моноблоки на складе — 8 штук
    for i in range(8):
        sn = f"CZC{sn_counter:06d}"
        sn_counter += 1
        eq_items.append(Equipment(
            category=EC.monoblock,
            model=monoblock_model,
            serial_number=sn,
            name=f"Моноблок {monoblock_model}",
            status=ES.in_stock,
            location="Склад",
            is_warehouse=True,
        ))

    # ── Принтеры: в кабинеты + привязка к пользователю кабинета ──────
    printer_placements = [
        ("10.01", 0, "KrylovaDA"),   ("10.05", 1, None),
        ("12.01", 0, "MikhailovKT"), ("12.05", 2, None), ("12.10", 3, "LebedevAP"),
        ("14.01", 1, "ZaitsevaOP"),  ("14.04", 0, None),
        ("16.01", 2, "NovikovaAT"),
        ("18.01", 0, "EvteevAS"),    ("18.05", 1, "KozlovDV"), ("18.08", 3, None),
        ("20.01", 0, None),          ("20.10", 1, "FedorovRS"),
        ("22.01", 2, "BelyaevGS"),
        ("24.01", 3, "RomanovaEV"),
    ]
    for office, model_idx, username in printer_placements:
        model_name, display_name = printer_models[model_idx]
        uid = None
        if username:
            u = db.query(User).filter(User.username == username).first()
            uid = u.id if u else None
        sn = f"PRN{sn_counter:06d}"
        sn_counter += 1
        eq_items.append(Equipment(
            category=EC.printer,
            model=model_name,
            serial_number=sn,
            name=display_name,
            status=ES.assigned,
            assigned_to_user_id=uid,
            location=office,
            is_warehouse=False,
        ))

    # Принтеры на складе — 4 штуки
    for i, (model_name, display_name) in enumerate(printer_models):
        sn = f"PRN{sn_counter:06d}"
        sn_counter += 1
        eq_items.append(Equipment(
            category=EC.printer,
            model=model_name,
            serial_number=sn,
            name=display_name,
            status=ES.in_stock,
            location="Склад",
            is_warehouse=True,
        ))

    # ── Расходные материалы: всё на складе, при выдаче списываются ─────
    # Расходники не привязываются к людям — они на складе, при выдаче списываются

    # Картриджи
    cartridge_stock = [
        # HP M404dn → картридж 26A
        ("Картридж HP 26A (CF226A)", "HP LaserJet M404/M428", 15),
        # HP MFP 4101 → картридж 32A
        ("Картридж HP 32A (CF232A)", "HP MFP 4101", 10),
        # HP Color 3301 → картриджи 134A
        ("Картридж HP 134A (W1340A)", "HP Color LaserJet 3301 чёрный", 8),
        ("Картридж HP 134A (W1341C)", "HP Color LaserJet 3301 голубой", 5),
        ("Картридж HP 134A (W1342M)", "HP Color LaserJet 3301 пурпурный", 5),
        ("Картридж HP 134A (W1343Y)", "HP Color LaserJet 3301 жёлтый", 5),
        # Kyocera → TK-2235
        ("Картридж Kyocera TK-2235", "Kyocera ECOSYS P2235", 8),
    ]

    for name, model, qty in cartridge_stock:
        eq_items.append(Equipment(
            category=EC.consumable,
            consumable_type=ConsumableType.cartridge,
            model=model,
            serial_number=None,
            name=name,
            status=ES.in_stock,
            assigned_to_user_id=None,
            location="Склад",
            is_warehouse=True,
            notes=f"Количество: {qty} шт." if qty > 1 else None,
        ))

    # Периферия, кабели, аксессуары — всё на складе
    consumable_stock = [
        # Периферия
        ("Мышь проводная HP USB", None, ConsumableType.peripheral, 20),
        ("Мышь беспроводная HP", None, ConsumableType.peripheral, 10),
        ("Клавиатура HP USB", None, ConsumableType.peripheral, 15),
        ("Клавиатура беспроводная HP", None, ConsumableType.peripheral, 8),
        # Кабели
        ("Кабель HDMI 1.5м", None, ConsumableType.cable, 12),
        ("Кабель DisplayPort 1.5м", None, ConsumableType.cable, 10),
        ("Кабель USB-C 1м", None, ConsumableType.cable, 15),
        # Аксессуары
        ("Блок питания HP 65Вт", None, ConsumableType.accessory, 6),
        ("Веб-камера HP USB", None, ConsumableType.accessory, 4),
        ("Наушники с микрофоном", None, ConsumableType.accessory, 5),
    ]

    for name, model, ctype, qty in consumable_stock:
        eq_items.append(Equipment(
            category=EC.consumable,
            consumable_type=ctype,
            model=model,
            serial_number=None,
            name=name,
            status=ES.in_stock,
            assigned_to_user_id=None,
            location="Склад",
            is_warehouse=True,
            notes=f"Количество: {qty} шт." if qty > 1 else None,
        ))

    for eq in eq_items:
        db.add(eq)
    db.commit()
    print(f"  {len(eq_items)} equipment items created.")

    # ── Seed tickets with history and comments ────────────────────────
    def _user(username):
        return db.query(User).filter(User.username == username).first()

    admin = _user("EvteevAS")
    eng1 = _user("KozlovDV")
    eng2 = _user("PetrovaEM")
    eng3 = _user("SidorovNA")

    now = datetime.utcnow()

    ticket_data = [
        # (title, description, creator, assignee, status, priority, days_ago, comments, events)
        (
            "Не работает принтер HP M404dn в каб. 10.01",
            "Принтер не печатает, индикатор мигает красным. Бумага есть, картридж новый.",
            "KrylovaDA", "KozlovDV", TicketStatus.resolved, TicketPriority.normal, 14,
            [("KrylovaDA", "Проверила — картридж стоит правильно, но всё равно не печатает"),
             ("KozlovDV", "Подключился удалённо — драйвер слетел. Переустановил, проверил печать тестовой страницы — работает"),
             ("KrylovaDA", "Спасибо, всё печатает!")],
            [("new", None, "in_progress"), ("in_progress", None, "assigned"), ("assigned", None, "resolved")],
        ),
        (
            "Моноблок не включается в каб. 12.02",
            "Чёрный экран при включении, вентилятор крутится. Индикатор питания горит.",
            "IvanovMP", "PetrovaEM", TicketStatus.resolved, TicketPriority.normal, 12,
            [("IvanovMP", "Попробовал другой кабель — не помогло"),
             ("PetrovaEM", "Проблема с оперативной памятью. Переставила модули — заработало"),
             ("IvanovMP", "Работает, спасибо!")],
            [("new", None, "in_progress"), ("in_progress", None, "resolved")],
        ),
        (
            "Нет доступа к сетевому диску",
            "Не могу подключиться к \\\\server\\public, пишет «нет доступа». Вчера всё работало.",
            "SmirnovaOV", "SidorovNA", TicketStatus.resolved, TicketPriority.high, 10,
            [("SmirnovaOV", "У коллег в 12.03 тоже нет доступа"),
             ("SidorovNA", "Сетевой контроллер перезагрузил, права обновил. Проверьте"),
             ("SmirnovaOV", "Работает, спасибо!")],
            [("new", None, "in_progress"), ("in_progress", None, "resolved")],
        ),
        (
            "Сломалась мышь — двойной клик при одинарном",
            "Мышь проводная HP, при одном клике срабатывает двойной. Очень мешает работе.",
            "VolkovIG", "KozlovDV", TicketStatus.resolved, TicketPriority.low, 9,
            [("KozlovDV", "Заменил мышь на новую со склада, старую — в утиль")],
            [("new", None, "in_progress"), ("in_progress", None, "resolved")],
        ),
        (
            "Не работает VPN из дома",
            "При подключении к VPN ошибка 789. До пятницы подключалось нормально.",
            "NovikovaAT", "SidorovNA", TicketStatus.closed, TicketPriority.normal, 20,
            [("NovikovaAT", "Перезапустила компьютер — не помогло"),
             ("SidorovNA", "Обновил сертификат на сервере VPN. Переподключитесь"),
             ("NovikovaAT", "Подключилось, спасибо"),
             ("SidorovNA", "Закрываю заявку")],
            [("new", None, "in_progress"), ("in_progress", None, "resolved"), ("resolved", None, "closed")],
        ),
        (
            "Принтер печатает полосами в каб. 14.01",
            "МФУ HP 4101 выдаёт чёрные полосы на каждом листе. Картридж меняли на прошлой неделе.",
            "ZaitsevaOP", "PetrovaEM", TicketStatus.resolved, TicketPriority.normal, 7,
            [("ZaitsevaOP", "Пробовала чистку из меню принтера — не помогло"),
             ("PetrovaEM", "Очистил барабан картриджа, провёл калибровку. Проверьте печать"),
             ("ZaitsevaOP", "Полосы пропали, отлично")],
            [("new", None, "in_progress"), ("in_progress", None, "resolved")],
        ),
        (
            "Сбой 1С при проведении документа",
            "1С:Бухгалтерия выдаёт ошибку при попытке провести документ «Поступление товаров». Код ошибки: 8.3.23.1732",
            "SokolovaIM", "EvteevAS", TicketStatus.in_progress, TicketPriority.high, 2,
            [("SokolovaIM", "Перезапуск 1С не помог, база на сервере"),
             ("EvteevAS", "Проверяю логи сервера, похоже на повреждение индексов. Начинаю пересчёт")],
            [("new", None, "in_progress")],
        ),
        (
            "Нет звука на моноблоке каб. 22.03",
            "Динамики не работают, в настройках Windows пишет «аудиоустройство не обнаружено».",
            "BelovaNK", "KozlovDV", TicketStatus.in_progress, TicketPriority.low, 1,
            [("BelovaNK", "Перезагружала — не помогло"),
             ("KozlovDV", "Смотрю удалённо, драйвер аудио слетел")],
            [("new", None, "in_progress")],
        ),
        (
            "Зависает компьютер при открытии Outlook",
            "Outlook 2016 намертво зависает при загрузке папки «Входящие». Компьютер не реагирует.",
            "MikhailovKT", "SidorovNA", TicketStatus.waiting_user, TicketPriority.normal, 3,
            [("SidorovNA", "Почистил PST-файл, сжал базу. Попробуйте открыть"),
             ("MikhailovKT", "Стало лучше, но иногда подтормаживает"),
             ("SidorovNA", "Нужно обновить версию Outlook. Пришлю ссылку на установщик"),
             ("MikhailovKT", "Ок, жду")],
            [("new", None, "in_progress"), ("in_progress", None, "waiting_user")],
        ),
        (
            "Запрос на новый моноблок для нового сотрудника",
            "В управление госуслуг выходит новый сотрудник, нужен моноблок и периферия.",
            "BelyaevGS", "EvteevAS", TicketStatus.in_progress, TicketPriority.normal, 4,
            [("BelyaevGS", "Сотрудник выходит 28 мая, нужно подготовить рабочее место в каб. 22.02"),
             ("EvteevAS", "Взял моноблок со склада, начинаю настройку")],
            [("new", None, "in_progress")],
        ),
        (
            "Потеря связи с сервером БД",
            "Все пользователи не могут подключиться к базе данных. Критично для работы!",
            "KarpovVI", "EvteevAS", TicketStatus.resolved, TicketPriority.urgent, 15,
            [("KarpovVI", "Срочно! Весь департамент не может работать"),
             ("EvteevAS", "Сервер БД перезагружен, соединение восстановлено. Причина — переполнение tempdb"),
             ("EvteevAS", "Увеличил размер tempdb, настроил автоочистку. Повторяться не должно"),
             ("KarpovVI", "Спасибо за оперативность")],
            [("new", None, "in_progress"), ("in_progress", None, "resolved")],
        ),
        (
            "Клавиатура залипает — клавиши не нажимаются",
            "Клавиша «Пробел» и «Enter» нажимаются через раз. Клавиатура HP USB.",
            "KuznetsovaLB", "PetrovaEM", TicketStatus.new, TicketPriority.low, 0,
            [],
            [],
        ),
        (
            "Цветное МФУ не сканирует",
            "Сканер HP Color LaserJet 3301fdw в каб. 22.01 не сканирует, пишет «ошибка связи».",
            "BelyaevGS", None, TicketStatus.new, TicketPriority.normal, 0,
            [("BelyaevGS", "Печатает нормально, а сканировать не хочет")],
            [],
        ),
        (
            "Нужно настроить подписку ЭЦП",
            "Не работает электронная подпись в КонсультантПлюс. Сертификат установлен, но подпись не формируется.",
            "FedorovRS", "SidorovNA", TicketStatus.in_progress, TicketPriority.high, 1,
            [("FedorovRS", "КриптоПро установлена, но плагин в браузере не видит ключ"),
             ("SidorovNA", "Обновляю плагин КриптоПро для браузера, проверяю настройки")],
            [("new", None, "in_progress")],
        ),
        (
            "Блок питания перегревается",
            "Блок питания моноблока очень горячий, запах горелого пластика. Каб. 24.02",
            "MorozovAP", "KozlovDV", TicketStatus.resolved, TicketPriority.high, 5,
            [("MorozovAP", "Выключил моноблок, боюсь что загорится!"),
             ("KozlovDV", "Заменил блок питания на новый со склада. Старый — списан. Проверил температуру — в норме"),
             ("MorozovAP", "Температура нормальная, спасибо за быструю реакцию!")],
            [("new", None, "in_progress"), ("in_progress", None, "resolved")],
        ),
        (
            "Не открывается портал госуслуг",
            "При входе на gosuslugi.ru выдаёт ошибку сертификата. Другие сайты работают.",
            "BelovaNK", "PetrovaEM", TicketStatus.closed, TicketPriority.normal, 18,
            [("BelovaNK", "Пробовала другой браузер — та же ошибка"),
             ("PetrovaEM", "Обновила корневые сертификаты Windows. Проверьте"),
             ("BelovaNK", "Открывается, спасибо!")],
            [("new", None, "in_progress"), ("in_progress", None, "resolved"), ("resolved", None, "closed")],
        ),
        (
            "Перенос данных на новый сервер",
            "Необходимо перенести общие папки с файлового сервера FS01 на FS02 до конца месяца.",
            "OrlovaNS", "EvteevAS", TicketStatus.in_progress, TicketPriority.high, 6,
            [("OrlovaNS", "Срок — 31 мая, нужно согласовать время простоя"),
             ("EvteevAS", "Начал копирование данных, на выходные запланирую переключение")],
            [("new", None, "in_progress")],
        ),
        (
            "Не подключается второй монитор",
            "Каб. 18.05 — пытаюсь подключить второй монитор через HDMI, но он не определяется.",
            "KozlovDV", "SidorovNA", TicketStatus.resolved, TicketPriority.low, 8,
            [("SidorovNA", "Обновил драйвер видеокарты, включил режим «Расширить». Проверьте"),
             ("KozlovDV", "Оба монитора работают, спасибо")],
            [("new", None, "in_progress"), ("in_progress", None, "resolved")],
        ),
        (
            "Восстановление удалённых файлов",
            "Случайно удалила папку с документами на сетевом диске. Очень нужно восстановить!",
            "SmirnovaOV", "EvteevAS", TicketStatus.resolved, TicketPriority.high, 3,
            [("SmirnovaOV", "Папка по пути \\\\server\\public\\Приватизация\\2025\\Май"),
             ("EvteevAS", "Восстановил из теневой копии. Папка на месте, проверьте"),
             ("SmirnovaOV", "Все файлы на месте, огромное спасибо!")],
            [("new", None, "in_progress"), ("in_progress", None, "resolved")],
        ),
        (
            "Настройка видеоконференцсвязи",
            "Нужна веб-камера и наушники для участия в совещаниях онлайн. Каб. 01.01.",
            "KarpovVI", "KozlovDV", TicketStatus.resolved, TicketPriority.normal, 11,
            [("KozlovDV", "Установил веб-камеру и наушники, настроил Zoom и Teams"),
             ("KarpovVI", "Всё работает, провёл тестовый звонок")],
            [("new", None, "in_progress"), ("in_progress", None, "resolved")],
        ),
        (
            "Ошибка при входе в систему",
            "При входе в Windows пишет «Профиль пользователя не загружен». Вхожу под временным профилем.",
            "LebedevAP", "PetrovaEM", TicketStatus.closed, TicketPriority.normal, 21,
            [("LebedevAP", "Файлы на рабочем столе пропали!"),
             ("PetrovaEM", "Повреждён реестр профиля. Восстановила из резервной копии, файлы на месте"),
             ("LebedevAP", "Всё вернулось, спасибо")],
            [("new", None, "in_progress"), ("in_progress", None, "resolved"), ("resolved", None, "closed")],
        ),
        (
            "Запрос картриджа для Kyocera",
            "Принтер Kyocera в каб. 12.10 показывает «Мало тонера». Нужен картридж TK-2235.",
            "LebedevAP", "KozlovDV", TicketStatus.resolved, TicketPriority.low, 6,
            [("KozlovDV", "Принёс картридж со склада, заменил. Напечатал тестовую страницу — качество нормальное")],
            [("new", None, "in_progress"), ("in_progress", None, "resolved")],
        ),
        (
            "Не работает Wi-Fi в переговорной 18.08",
            "Ноутбуки не подключаются к Wi-Fi в переговорной. Точка доступа не видна.",
            "RomanovaEV", "SidorovNA", TicketStatus.new, TicketPriority.normal, 0,
            [("RomanovaEV", "Совещание через час, нужно срочно!")],
            [],
        ),
        (
            "Обновление Windows мешает работе",
            "Windows каждый раз при перезагрузке ставит обновления по 30 минут. Можно ли отложить?",
            "VolkovIG", "EvteevAS", TicketStatus.waiting_user, TicketPriority.low, 4,
            [("EvteevAS", "Настроил отложенные обновления — будут ставиться только в пятницу вечером. Перезагрузите компьютер"),
             ("VolkovIG", "Ок, перезагружу в пятницу")],
            [("new", None, "in_progress"), ("in_progress", None, "waiting_user")],
        ),
    ]

    ticket_count = 0
    for title, desc, creator, assignee, status, priority, days_ago, comments, events in ticket_data:
        c_user = _user(creator)
        a_user = _user(assignee) if assignee else None
        created = now - timedelta(days=days_ago, hours=randint(0, 8))

        t = Ticket(
            title=title,
            description=desc,
            status=status,
            priority=priority,
            created_by_id=c_user.id,
            assigned_to_id=a_user.id if a_user else None,
            created_at=created,
            updated_at=created + timedelta(hours=randint(1, 24)),
        )
        if status in (TicketStatus.resolved, TicketStatus.closed):
            t.resolution = "Проблема устранена."
        db.add(t)
        db.flush()

        # Events
        for ev_type, old_val, new_val in events:
            db.add(TicketEvent(
                ticket_id=t.id,
                author_id=a_user.id if a_user else c_user.id,
                event_type="status_change",
                old_value=old_val,
                new_value=new_val,
                created_at=created + timedelta(hours=randint(1, 8)),
            ))

        # Comments
        for i, (commenter, body) in enumerate(comments):
            cm_user = _user(commenter)
            db.add(TicketComment(
                ticket_id=t.id,
                author_id=cm_user.id,
                body=body,
                created_at=created + timedelta(hours=i + 1, minutes=randint(0, 59)),
            ))

        ticket_count += 1

    db.commit()
    print(f"  {ticket_count} tickets created with history.")

    # ── Seed broadcasts + notifications ────────────────────────────────
    broadcasts_data = [
        (
            "Сбой почтового сервера",
            "В настоящее время наблюдаются проблемы с отправкой/получением почты. Почтовая команда работает над устранением. Ориентировочное время восстановления — 16:00.",
            7,
        ),
        (
            "Обновление системы электронного документооборота",
            "В выходные 31 мая — 1 июня будет проведено обновление СЭД. В субботу с 09:00 до 14:00 система будет недоступна. Просим завершить все работы в пятницу.",
            5,
        ),
        (
            "Защита от вируса-шифровальщика",
            "Зафиксированы попытки фишинговых атак на сотрудников департамента. Не открывайте подозрительные ссылки и вложения! При обнаружении странных писем — обращайтесь в техподдержку.",
            3,
        ),
        (
            "Новая версия портала техподдержки",
            "Обновлён интерфейс портала техподдержки: добавлен раздел «Оборудование», улучшен поиск, добавлены уведомления. При возникновении проблем — создавайте заявку.",
            1,
        ),
    ]

    all_users = db.query(User).filter(User.is_active == 1).all()
    bc_count = 0
    for title, body, days_ago in broadcasts_data:
        bc = Broadcast(
            author_id=admin.id,
            title=title,
            body=body,
            created_at=now - timedelta(days=days_ago),
        )
        db.add(bc)
        db.flush()
        bc_count += 1

        # Notification for each user (some already read)
        for i, u in enumerate(all_users):
            is_read = 1 if (days_ago > 2 and i % 3 != 0) else 0
            db.add(Notification(
                user_id=u.id,
                title=title,
                body=body,
                broadcast_id=bc.id,
                is_read=is_read,
                created_at=bc.created_at,
            ))

    db.commit()
    print(f"  {bc_count} broadcasts created with notifications.")

    print(f"\nDone. Default password: {DEFAULT_PASSWORD}")
    db.close()


if __name__ == "__main__":
    seed()
