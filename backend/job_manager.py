import uuid
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
from backend.database import AsyncSessionLocal, DBJob, init_db
from sqlalchemy.future import select
from sqlalchemy import delete

@dataclass
class JobRecord:
    job_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    detections: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[Dict[str, Any]] = None

class AsyncJobManager:
    """Thread-safe database store for tracking async detection jobs."""

    def __init__(self):
        self._db_initialized = False

    async def _ensure_init(self):
        if not self._db_initialized:
            await init_db()
            self._db_initialized = True

    async def create_job(self) -> str:
        await self._ensure_init()
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        async with AsyncSessionLocal() as session:
            new_job = DBJob(
                job_id=job_id,
                status="pending",
                detections=[]
            )
            session.add(new_job)
            await session.commit()
        return job_id

    async def get_job(self, job_id: str) -> Optional[JobRecord]:
        await self._ensure_init()
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(DBJob).filter(DBJob.job_id == job_id))
            db_job = result.scalar_one_or_none()
            if not db_job:
                return None
            return JobRecord(
                job_id=db_job.job_id,
                status=db_job.status,
                created_at=db_job.created_at,
                updated_at=db_job.updated_at,
                detections=db_job.detections or [],
                error=db_job.error
            )

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        detections: Optional[List[Dict[str, Any]]] = None,
        error: Optional[Dict[str, Any]] = None
    ) -> bool:
        await self._ensure_init()
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(DBJob).filter(DBJob.job_id == job_id))
            db_job = result.scalar_one_or_none()
            if not db_job:
                return False
            
            db_job.status = status
            if detections is not None:
                db_job.detections = detections
            if error is not None:
                db_job.error = error
                
            await session.commit()
            
            # Fetch updated state for broadcast
            await session.refresh(db_job)
            
            # Broadcast the updated state to any subscribed websockets
            from backend.ws_manager import ws_manager
            asyncio.create_task(ws_manager.broadcast_job_update(
                job_id,
                {
                    "job_id": db_job.job_id,
                    "status": db_job.status,
                    "detections": db_job.detections or [],
                    "error": db_job.error
                }
            ))
            return True

    async def clear_all(self) -> None:
        await self._ensure_init()
        async with AsyncSessionLocal() as session:
            await session.execute(delete(DBJob))
            await session.commit()



    async def get_jobs_history(self, skip: int = 0, limit: int = 50, status_filter: Optional[str] = None) -> List[JobRecord]:
        await self._ensure_init()
        async with AsyncSessionLocal() as session:
            stmt = select(DBJob)
            if status_filter:
                stmt = stmt.filter(DBJob.status == status_filter)
            stmt = stmt.order_by(DBJob.created_at.desc()).offset(skip).limit(limit)
            
            result = await session.execute(stmt)
            db_jobs = result.scalars().all()
            
            return [
                JobRecord(
                    job_id=job.job_id,
                    status=job.status,
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                    detections=job.detections or [],
                    error=job.error
                )
                for job in db_jobs
            ]

    async def update_detection_review(
        self,
        job_id: str,
        detection_id: str,
        review_status: str,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        await self._ensure_init()
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(DBJob).filter(DBJob.job_id == job_id))
            db_job = result.scalar_one_or_none()
            if not db_job:
                return None

            detections = list(db_job.detections or [])
            updated_det = None
            for idx, det in enumerate(detections):
                if det.get("detection_id") == detection_id or det.get("id") == detection_id:
                    detections[idx] = {
                        **det,
                        "review_status": review_status,
                        "reviewed_at": datetime.now(timezone.utc).isoformat(),
                        "operator_notes": notes
                    }
                    updated_det = detections[idx]
                    break

            if updated_det is not None:
                db_job.detections = detections
                await session.commit()
                await session.refresh(db_job)

                from backend.ws_manager import ws_manager
                asyncio.create_task(ws_manager.broadcast_job_update(
                    job_id,
                    {
                        "job_id": db_job.job_id,
                        "status": db_job.status,
                        "detections": db_job.detections or [],
                        "error": db_job.error
                    }
                ))

            return updated_det

job_manager = AsyncJobManager()

