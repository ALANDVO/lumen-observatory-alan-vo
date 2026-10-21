export type ActorState = 'RUNNING' | 'PAUSED' | 'SUSPENDED' | 'CRASHED';
export type SnapshotScope = 'full' | 'data';

export interface Actor {
  actor_uid: string;
  actor_name: string;
  actor_atespace: string;
  actor_template_namespace: string;
  actor_template_name: string;
  container_name: string;
  state: ActorState;
  snapshot_scope: SnapshotScope;
  node_name: string | null;
  worker_pod: string | null;
  created_at: string;
  updated_at: string;
  last_snapshot_at: string | null;
  tags: string | null;
}

export interface ActorListResponse {
  items: Actor[];
  total: number;
  skip: number;
  limit: number;
}

export interface ActorSnapshot {
  id: number;
  actor_uid: string;
  scope: SnapshotScope;
  tag: string | null;
  storage_path: string;
  checksum: string | null;
  size_bytes: number;
  created_at: string;
}

export interface ActorTransitionLog {
  id: number;
  actor_uid: string;
  from_state: ActorState | null;
  to_state: ActorState;
  triggered_by: string | null;
  reason: string | null;
  created_at: string;
}

export interface ActorCreate {
  actor_uid: string;
  actor_name: string;
  actor_atespace: string;
  actor_template_namespace: string;
  actor_template_name: string;
  container_name: string;
  snapshot_scope: SnapshotScope;
  from_tag?: string;
}

export interface ActorTransitionRequest {
  to_state: ActorState;
  reason?: string;
}

export interface ActorPauseRequest {
  timer_seconds?: number;
}

export interface ActorCommitRequest {
  tag?: string;
  scope?: SnapshotScope;
}

export interface ActorResumeRequest {
  node_name?: string;
}

export interface ActorRevertRequest {
  tag: string;
}

export interface ActorDumpRequest {
  tag: string;
}