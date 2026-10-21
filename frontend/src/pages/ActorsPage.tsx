import { useState, useEffect, useCallback } from 'react';
import { api } from "../api/client";
import { ActorTable } from "../components/actors/ActorTable";
import { ActorDetailModal } from "../components/actors/ActorDetailModal";
import { Card } from "../components/common/Card";
import { Modal } from "../components/common/Modal";
import type { Actor, ActorCreate, ActorState } from "../types/actor";

export function ActorsPage() {
  const [actors, setActors] = useState<Actor[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [skip, setSkip] = useState(0);
  const [limit] = useState(20);
  const [filters, setFilters] = useState({
    state: '',
    template_namespace: '',
    template_name: '',
    node_name: '',
  });
  const [selectedActor, setSelectedActor] = useState<Actor | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState<ActorCreate>({
    actor_uid: '',
    actor_name: '',
    actor_atespace: 'default',
    actor_template_namespace: 'default',
    actor_template_name: 'example',
    container_name: 'main',
    snapshot_scope: 'data',
  });

  const fetchActors = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listActors({
        skip,
        limit,
        state: filters.state || undefined,
        template_namespace: filters.template_namespace || undefined,
        template_name: filters.template_name || undefined,
        node_name: filters.node_name || undefined,
      });
      setActors(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch actors');
    } finally {
      setLoading(false);
    }
  }, [skip, limit, filters]);

  useEffect(() => {
    fetchActors();
  }, [fetchActors]);

  const handleTransition = async (actorUid: string, toState: ActorState, reason?: string) => {
    try {
      await api.transitionActor(actorUid, { to_state: toState, reason });
      fetchActors();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Transition failed');
    }
  };

  const handlePause = async (actorUid: string, timerSeconds?: number) => {
    try {
      await api.pauseActor(actorUid, { timer_seconds: timerSeconds });
      fetchActors();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Pause failed');
    }
  };

  const handleCommit = async (actorUid: string, tag?: string, scope?: 'full' | 'data') => {
    try {
      await api.commitActor(actorUid, { tag, scope });
      fetchActors();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Commit failed');
    }
  };

  const handleResume = async (actorUid: string, nodeName?: string) => {
    try {
      await api.resumeActor(actorUid, { node_name: nodeName });
      fetchActors();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Resume failed');
    }
  };

  const handleRevert = async (actorUid: string, tag: string) => {
    try {
      await api.revertActor(actorUid, { tag });
      fetchActors();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Revert failed');
    }
  };

  const handleDump = async (actorUid: string, tag: string) => {
    try {
      await api.dumpActor(actorUid, { tag });
      fetchActors();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Dump failed');
    }
  };

  const handleDelete = async (actorUid: string) => {
    if (!confirm('Delete this actor? This cannot be undone.')) return;
    try {
      await api.deleteActor(actorUid);
      fetchActors();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  const handleCreateActor = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createActor(createForm);
      setShowCreateModal(false);
      setCreateForm({
        actor_uid: '',
        actor_name: '',
        actor_atespace: 'default',
        actor_template_namespace: 'default',
        actor_template_name: 'example',
        container_name: 'main',
        snapshot_scope: 'data',
      });
      fetchActors();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Create failed');
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Actors</h1>
          <p className="text-gray-500 mt-1">Manage actor lifecycle and state transitions</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 3a1 1 0 011 1v5h5a1 1 0 010 2H9v5a1 1 0 01-2 0V9H2a1 1 0 110-2h5V4a1 1 0 011-1z"/>
          </svg>
          Create Actor
        </button>
      </div>

      {error && <div className="alert alert-error mb-4">{error}</div>}

      <Card title="Filters" subtitle={`${total} actors total`}>
        <div className="filter-bar">
          <div className="filter-group">
            <label className="form-label">State</label>
            <select
              className="form-select"
              value={filters.state}
              onChange={(e) => setFilters({ ...filters, state: e.target.value })}
            >
              <option value="">All</option>
              <option value="RUNNING">Running</option>
              <option value="PAUSED">Paused</option>
              <option value="SUSPENDED">Suspended</option>
              <option value="CRASHED">Crashed</option>
            </select>
          </div>
          <div className="filter-group">
            <label className="form-label">Template Namespace</label>
            <input
              className="form-input"
              placeholder="namespace"
              value={filters.template_namespace}
              onChange={(e) => setFilters({ ...filters, template_namespace: e.target.value })}
            />
          </div>
          <div className="filter-group">
            <label className="form-label">Template Name</label>
            <input
              className="form-input"
              placeholder="name"
              value={filters.template_name}
              onChange={(e) => setFilters({ ...filters, template_name: e.target.value })}
            />
          </div>
          <div className="filter-group">
            <label className="form-label">Node</label>
            <input
              className="form-input"
              placeholder="node name"
              value={filters.node_name}
              onChange={(e) => setFilters({ ...filters, node_name: e.target.value })}
            />
          </div>
        </div>
      </Card>

      <Card>
        {loading ? (
          <div className="loading"><div className="spinner" /></div>
        ) : (
          <ActorTable
            actors={actors}
            onActorClick={setSelectedActor}
            onTransition={handleTransition}
            onPause={handlePause}
            onCommit={handleCommit}
            onResume={handleResume}
          />
        )}
      </Card>

      {total > limit && (
        <div className="pagination">
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setSkip(Math.max(0, skip - limit))}
            disabled={skip === 0}
          >
            Previous
          </button>
          <span className="page-info">
            Page {Math.floor(skip / limit) + 1} of {Math.ceil(total / limit)}
          </span>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setSkip(skip + limit)}
            disabled={skip + limit >= total}
          >
            Next
          </button>
        </div>
      )}

      <ActorDetailModal
        actor={selectedActor}
        isOpen={!!selectedActor}
        onClose={() => setSelectedActor(null)}
        onTransition={handleTransition}
        onPause={handlePause}
        onCommit={handleCommit}
        onResume={handleResume}
        onRevert={handleRevert}
        onDump={handleDump}
        onDelete={handleDelete}
      />

      <Modal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} title="Create Actor" size="md">
        <form onSubmit={handleCreateActor} className="space-y-4">
          <div className="form-group">
            <label className="form-label">Actor UID *</label>
            <input
              className="form-input"
              placeholder="auto-generated if empty"
              value={createForm.actor_uid}
              onChange={(e) => setCreateForm({ ...createForm, actor_uid: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Name *</label>
            <input
              className="form-input"
              placeholder="my-actor"
              value={createForm.actor_name}
              onChange={(e) => setCreateForm({ ...createForm, actor_name: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Atespace *</label>
            <input
              className="form-input"
              value={createForm.actor_atespace}
              onChange={(e) => setCreateForm({ ...createForm, actor_atespace: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Template Namespace *</label>
            <input
              className="form-input"
              value={createForm.actor_template_namespace}
              onChange={(e) => setCreateForm({ ...createForm, actor_template_namespace: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Template Name *</label>
            <input
              className="form-input"
              value={createForm.actor_template_name}
              onChange={(e) => setCreateForm({ ...createForm, actor_template_name: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Container Name *</label>
            <input
              className="form-input"
              value={createForm.container_name}
              onChange={(e) => setCreateForm({ ...createForm, container_name: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Snapshot Scope</label>
            <select
              className="form-select"
              value={createForm.snapshot_scope}
              onChange={(e) => setCreateForm({ ...createForm, snapshot_scope: e.target.value as 'full' | 'data' })}
            >
              <option value="data">Data only</option>
              <option value="full">Full</option>
            </select>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>Create</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}