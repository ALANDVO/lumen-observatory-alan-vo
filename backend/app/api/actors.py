from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.models.actor import ActorStatus, ActorState, SnapshotScope, ActorSnapshot, ActorTransitionLog
from backend.app.services.actor_service import ActorService
from backend.app.services.actor_metrics import actor_metrics

router = APIRouter(prefix="/actors", tags=["actors"])


class ActorCreate(BaseModel):
    actor_uid: str
    actor_name: str
    actor_atespace: str
    actor_template_namespace: str
    actor_template_name: str
    container_name: str
    snapshot_scope: SnapshotScope = SnapshotScope.DATA
    from_tag: Optional[str] = None


class ActorResponse(BaseModel):
    actor_uid: str
    actor_name: str
    actor_atespace: str
    actor_template_namespace: str
    actor_template_name: str
    container_name: str
    state: ActorState
    snapshot_scope: SnapshotScope
    node_name: Optional[str]
    worker_pod: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_snapshot_at: Optional[datetime]
    tags: Optional[str]

    class Config:
        from_attributes = True


class ActorTransitionRequest(BaseModel):
    to_state: ActorState
    reason: Optional[str] = None


class ActorPauseRequest(BaseModel):
    timer_seconds: Optional[int] = None


class ActorCommitRequest(BaseModel):
    tag: Optional[str] = None
    scope: Optional[SnapshotScope] = None


class ActorResumeRequest(BaseModel):
    node_name: Optional[str] = None


class ActorRevertRequest(BaseModel):
    tag: str


class ActorDumpRequest(BaseModel):
    tag: str


class ActorSnapshotResponse(BaseModel):
    id: int
    actor_uid: str
    scope: SnapshotScope
    tag: Optional[str]
    storage_path: str
    checksum: Optional[str]
    size_bytes: int
    created_at: datetime

    class Config:
        from_attributes = True


class ActorTransitionLogResponse(BaseModel):
    id: int
    actor_uid: str
    from_state: Optional[ActorState]
    to_state: ActorState
    triggered_by: Optional[str]
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ActorListResponse(BaseModel):
    items: List[ActorResponse]
    total: int
    skip: int
    limit: int


@router.post("", response_model=ActorResponse, status_code=201)
async def create_actor(request: ActorCreate, db: Session = Depends(get_db)):
    service = ActorService(db)
    try:
        actor = service.create_actor(
            actor_uid=request.actor_uid,
            actor_name=request.actor_name,
            actor_atespace=request.actor_atespace,
            actor_template_namespace=request.actor_template_namespace,
            actor_template_name=request.actor_template_name,
            container_name=request.container_name,
            snapshot_scope=request.snapshot_scope,
            from_tag=request.from_tag,
        )
        actor_metrics.increment_actor(
            actor.actor_template_namespace,
            actor.actor_template_name,
            actor.state,
        )
        return actor
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=ActorListResponse)
async def list_actors(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    state: Optional[ActorState] = None,
    template_namespace: Optional[str] = None,
    template_name: Optional[str] = None,
    node_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    service = ActorService(db)
    actors = service.list_actors(skip, limit, state, template_namespace, template_name, node_name)
    total = service.count_actors(state, template_namespace, template_name)
    return ActorListResponse(items=actors, total=total, skip=skip, limit=limit)


@router.get("/{actor_uid}", response_model=ActorResponse)
async def get_actor(actor_uid: str, db: Session = Depends(get_db)):
    service = ActorService(db)
    actor = service.get_actor(actor_uid)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    return actor


@router.post("/{actor_uid}/transition", response_model=ActorResponse)
async def transition_actor(actor_uid: str, request: ActorTransitionRequest, db: Session = Depends(get_db)):
    service = ActorService(db)
    try:
        from_state = service.get_actor(actor_uid).state
        actor = service.transition_actor(actor_uid, request.to_state, "api", request.reason)
        actor_metrics.record_transition(from_state, request.to_state, actor.actor_template_namespace, actor.actor_template_name)
        actor_metrics.decrement_actor(actor.actor_template_namespace, actor.actor_template_name, from_state)
        actor_metrics.increment_actor(actor.actor_template_namespace, actor.actor_template_name, request.to_state)
        if request.to_state == ActorState.CRASHED:
            actor_metrics.record_crash(actor.actor_template_namespace, actor.actor_template_name)
        return actor
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{actor_uid}/pause", response_model=ActorResponse)
async def pause_actor(actor_uid: str, request: ActorPauseRequest, db: Session = Depends(get_db)):
    service = ActorService(db)
    try:
        from_state = service.get_actor(actor_uid).state
        actor = service.pause_actor(actor_uid, request.timer_seconds, "api")
        actor_metrics.record_transition(from_state, ActorState.PAUSED, actor.actor_template_namespace, actor.actor_template_name)
        actor_metrics.decrement_actor(actor.actor_template_namespace, actor.actor_template_name, from_state)
        actor_metrics.increment_actor(actor.actor_template_namespace, actor.actor_template_name, ActorState.PAUSED)
        return actor
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{actor_uid}/commit", response_model=ActorResponse)
async def commit_actor(actor_uid: str, request: ActorCommitRequest, db: Session = Depends(get_db)):
    service = ActorService(db)
    try:
        from_state = service.get_actor(actor_uid).state
        actor = service.commit_actor(actor_uid, request.tag, request.scope, "api")
        actor_metrics.record_transition(from_state, ActorState.SUSPENDED, actor.actor_template_namespace, actor.actor_template_name)
        actor_metrics.decrement_actor(actor.actor_template_namespace, actor.actor_template_name, from_state)
        actor_metrics.increment_actor(actor.actor_template_namespace, actor.actor_template_name, ActorState.SUSPENDED)
        return actor
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{actor_uid}/resume", response_model=ActorResponse)
async def resume_actor(actor_uid: str, request: ActorResumeRequest, db: Session = Depends(get_db)):
    service = ActorService(db)
    try:
        from_state = service.get_actor(actor_uid).state
        actor = service.resume_actor(actor_uid, request.node_name, "api")
        actor_metrics.record_transition(from_state, ActorState.RUNNING, actor.actor_template_namespace, actor.actor_template_name)
        actor_metrics.decrement_actor(actor.actor_template_namespace, actor.actor_template_name, from_state)
        actor_metrics.increment_actor(actor.actor_template_namespace, actor.actor_template_name, ActorState.RUNNING)
        return actor
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{actor_uid}/revert", response_model=ActorResponse)
async def revert_actor(actor_uid: str, request: ActorRevertRequest, db: Session = Depends(get_db)):
    service = ActorService(db)
    try:
        from_state = service.get_actor(actor_uid).state
        actor = service.revert_actor(actor_uid, request.tag, "api")
        actor_metrics.record_transition(from_state, ActorState.SUSPENDED, actor.actor_template_namespace, actor.actor_template_name)
        actor_metrics.decrement_actor(actor.actor_template_namespace, actor.actor_template_name, from_state)
        actor_metrics.increment_actor(actor.actor_template_namespace, actor.actor_template_name, ActorState.SUSPENDED)
        return actor
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{actor_uid}/dump", response_model=ActorResponse)
async def dump_actor(actor_uid: str, request: ActorDumpRequest, db: Session = Depends(get_db)):
    service = ActorService(db)
    try:
        from_state = service.get_actor(actor_uid).state
        actor = service.dump_actor(actor_uid, request.tag, "api")
        actor_metrics.record_transition(from_state, ActorState.SUSPENDED, actor.actor_template_namespace, actor.actor_template_name)
        actor_metrics.decrement_actor(actor.actor_template_namespace, actor.actor_template_name, from_state)
        actor_metrics.increment_actor(actor.actor_template_namespace, actor.actor_template_name, ActorState.SUSPENDED)
        return actor
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{actor_uid}", status_code=204)
async def delete_actor(actor_uid: str, db: Session = Depends(get_db)):
    service = ActorService(db)
    actor = service.get_actor(actor_uid)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    actor_metrics.decrement_actor(actor.actor_template_namespace, actor.actor_template_name, actor.state)
    service.delete_actor(actor_uid)


@router.get("/{actor_uid}/snapshots", response_model=List[ActorSnapshotResponse])
async def get_actor_snapshots(actor_uid: str, db: Session = Depends(get_db)):
    service = ActorService(db)
    actor = service.get_actor(actor_uid)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    return actor.snapshots


@router.get("/{actor_uid}/transitions", response_model=List[ActorTransitionLogResponse])
async def get_actor_transitions(actor_uid: str, db: Session = Depends(get_db)):
    service = ActorService(db)
    actor = service.get_actor(actor_uid)
    if not actor:
        raise HTTPException(status_code=404, detail="Actor not found")
    return actor.transitions