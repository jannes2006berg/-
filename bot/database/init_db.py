from datetime import date, time, timedelta
from sqlalchemy import select
from bot.database.models import Base, Service, Master, AvailableSlot, Portfolio
from bot.database.session import engine, SessionLocal


async def init_db(seed: bool = True) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if seed:
        await seed_demo_data()


async def seed_demo_data() -> None:
    async with SessionLocal() as session:
        if (await session.execute(select(Service))).first():
            return
        services = [
            Service(title="Маникюр без покрытия", description="Аккуратная обработка ногтей и кутикулы.", price=1500, duration_minutes=60),
            Service(title="Маникюр с гель-лаком", description="Маникюр, выравнивание и стойкое покрытие.", price=2500, duration_minutes=120),
            Service(title="Наращивание ногтей", description="Моделирование формы и длины под ваш стиль.", price=4200, duration_minutes=180),
            Service(title="Коррекция", description="Обновление формы и покрытия после наращивания.", price=3000, duration_minutes=150),
            Service(title="Педикюр", description="Комплексный уход за стопами и ногтями.", price=2800, duration_minutes=90),
            Service(title="Дизайн ногтей", description="Френч, стемпинг, стразы, рисунки и трендовые дизайны.", price=500, duration_minutes=30),
        ]
        masters = [Master(name="Анна", description="Топ-мастер, 6 лет опыта"), Master(name="Мария", description="Мастер дизайна и френча")]
        session.add_all(services + masters)
        await session.flush()
        today = date.today()
        for master in masters:
            for day in range(1, 15):
                d = today + timedelta(days=day)
                for hour in (10, 12, 14, 16, 18):
                    session.add(AvailableSlot(master_id=master.id, date=d, time=time(hour, 0)))
        for cat in ["Маникюр", "Наращивание", "Дизайн", "Френч", "Педикюр"]:
            session.add(Portfolio(category=cat, url="https://placehold.co/800x600/png", caption=f"Пример работы: {cat}"))
        await session.commit()
