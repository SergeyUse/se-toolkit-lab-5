from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func
from typing import List, Dict, Any
from datetime import date

from app.database import get_session
from app.models.item import ItemRecord
from app.models.interaction import InteractionLog
from app.models.learner import Learner

router = APIRouter()

@router.get("/scores")
async def get_scores(
    lab: str,
    session: AsyncSession = Depends(get_session)
) -> List[Dict[str, Any]]:
    # 1. Найти lab по title (преобразуем lab-04 → Lab 04)
    lab_title = lab.replace("-", " ").title()
    lab_item = await session.execute(
        select(ItemRecord).where(
            ItemRecord.type == "lab",
            ItemRecord.title.contains(lab_title)
        )
    )
    lab_item = lab_item.scalar_one_or_none()
    if not lab_item:
        # Если lab не найдена, возвращаем пустые корзины
        return [
            {"bucket": "0-25", "count": 0},
            {"bucket": "26-50", "count": 0},
            {"bucket": "51-75", "count": 0},
            {"bucket": "76-100", "count": 0}
        ]
    
    # 2. Найти все task для этой lab
    tasks = await session.execute(
        select(ItemRecord).where(
            ItemRecord.type == "task",
            ItemRecord.parent_id == lab_item.id
        )
    )
    task_ids = [t.id for t in tasks.scalars().all()]
    
    if not task_ids:
        return [
            {"bucket": "0-25", "count": 0},
            {"bucket": "26-50", "count": 0},
            {"bucket": "51-75", "count": 0},
            {"bucket": "76-100", "count": 0}
        ]
    
    # 3. Подсчет скора по корзинам
    result = await session.execute(
        select(
            func.count().filter(InteractionLog.score <= 25).label("bucket1"),
            func.count().filter(InteractionLog.score.between(26, 50)).label("bucket2"),
            func.count().filter(InteractionLog.score.between(51, 75)).label("bucket3"),
            func.count().filter(InteractionLog.score.between(76, 100)).label("bucket4")
        ).where(
            InteractionLog.item_id.in_(task_ids),
            InteractionLog.score.isnot(None)
        )
    )
    row = result.one()
    
    return [
        {"bucket": "0-25", "count": row[0] or 0},
        {"bucket": "26-50", "count": row[1] or 0},
        {"bucket": "51-75", "count": row[2] or 0},
        {"bucket": "76-100", "count": row[3] or 0}
    ]


@router.get("/pass-rates")
async def get_pass_rates(
    lab: str,
    session: AsyncSession = Depends(get_session)
) -> List[Dict[str, Any]]:
    # Найти lab
    lab_title = lab.replace("-", " ").title()
    lab_item = await session.execute(
        select(ItemRecord).where(
            ItemRecord.type == "lab",
            ItemRecord.title.contains(lab_title)
        )
    )
    lab_item = lab_item.scalar_one_or_none()
    if not lab_item:
        return []
    
    # Найти все task с агрегацией
    result = await session.execute(
        select(
            ItemRecord.title,
            func.round(func.avg(InteractionLog.score), 1).label("avg_score"),
            func.count(InteractionLog.id).label("attempts")
        )
        .join(InteractionLog, InteractionLog.item_id == ItemRecord.id)
        .where(
            ItemRecord.type == "task",
            ItemRecord.parent_id == lab_item.id,
            InteractionLog.score.isnot(None)
        )
        .group_by(ItemRecord.id, ItemRecord.title)
        .order_by(ItemRecord.title)
    )
    
    return [
        {"task": title, "avg_score": float(avg), "attempts": attempts}
        for title, avg, attempts in result.all()
    ]


@router.get("/timeline")
async def get_timeline(
    lab: str,
    session: AsyncSession = Depends(get_session)
) -> List[Dict[str, Any]]:
    # Найти lab
    lab_title = lab.replace("-", " ").title()
    lab_item = await session.execute(
        select(ItemRecord).where(
            ItemRecord.type == "lab",
            ItemRecord.title.contains(lab_title)
        )
    )
    lab_item = lab_item.scalar_one_or_none()
    if not lab_item:
        return []
    
    # Найти все task для этой lab
    tasks = await session.execute(
        select(ItemRecord).where(
            ItemRecord.type == "task",
            ItemRecord.parent_id == lab_item.id
        )
    )
    task_ids = [t.id for t in tasks.scalars().all()]
    
    if not task_ids:
        return []
    
    # Группировка по дате
    result = await session.execute(
        select(
            func.date(InteractionLog.created_at).label("date"),
            func.count().label("submissions")
        )
        .where(InteractionLog.item_id.in_(task_ids))
        .group_by(func.date(InteractionLog.created_at))
        .order_by("date")
    )
    
    return [
        {"date": str(date), "submissions": count}
        for date, count in result.all()
    ]


@router.get("/groups")
async def get_groups(
    lab: str,
    session: AsyncSession = Depends(get_session)
) -> List[Dict[str, Any]]:
    # Найти lab
    lab_title = lab.replace("-", " ").title()
    lab_item = await session.execute(
        select(ItemRecord).where(
            ItemRecord.type == "lab",
            ItemRecord.title.contains(lab_title)
        )
    )
    lab_item = lab_item.scalar_one_or_none()
    if not lab_item:
        return []
    
    # Найти все task для этой lab
    tasks = await session.execute(
        select(ItemRecord).where(
            ItemRecord.type == "task",
            ItemRecord.parent_id == lab_item.id
        )
    )
    task_ids = [t.id for t in tasks.scalars().all()]
    
    if not task_ids:
        return []
    
    # Join с Learner для получения группы
    result = await session.execute(
        select(
            Learner.student_group,
            func.round(func.avg(InteractionLog.score), 1).label("avg_score"),
            func.count(func.distinct(Learner.id)).label("students")
        )
        .join(InteractionLog, InteractionLog.learner_id == Learner.id)
        .where(
            InteractionLog.item_id.in_(task_ids),
            InteractionLog.score.isnot(None)
        )
        .group_by(Learner.student_group)
        .order_by(Learner.student_group)
    )
    
    return [
        {"group": group, "avg_score": float(avg), "students": students}
        for group, avg, students in result.all()
    ]