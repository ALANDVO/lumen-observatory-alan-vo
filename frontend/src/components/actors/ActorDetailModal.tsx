import { useState, useEffect } from 'react';
import { Actor, ActorSnapshot, ActorTransitionLog, ActorState } from '../../types/actor';
import { api } from '../../api/client';
import { Modal } from '../common/Modal';
import { format } from 'date-fns';

interface ActorDetailModalProps {
  actor: Actor | null;
  isOpen: boolean;
  onClose: () => void;
  onTransition: (actorUid: string, toState: ActorState, reason?: string) => Promise<void>;
  onPause: (actorUid: string, timerSeconds?: number) => Promise<void>;
  onCommit: (actorUid: string, tag?: string, scope?: 'full' | 'data') => Promise<void>;
  onResume: (actorUid: string, nodeName?: string) => Promise<void>;
  onRevert: (actorUid: string, tag: string) => Promise<void>;
  onDump: (actorUid: string, tag: string) => Promise<void>;
  onDelete: (actorUid: string) => Promise<void>;
}

function getBadgeClass(state: ActorState): string {
  switch (state) {
    case 'RUNNING': return 'badge-running';
    case 'PAUSED': return 'badge-paused';
    case 'SUSPENDED': return 'badge-suspended';
    case 'CRASHED': return 'badge-crashed';
  }
}

function getValidTransitions(state: ActorState): ActorState[] {
  switch (state) {
    case 'SUSPENDED': return ['RUNNING'];
    case 'RUNNING': return ['RUNNING', 'PAUSED', 'SUSPENDED', 'CRASHED'];
    case 'PAUSED': return ['RUNNING', 'SUSPENDED', 'PAUSED', 'CRASHED'];
    case 'CRASHED': return ['SUSPENDED'];
  }
}

export function ActorDetailModal({
  actor,
  isOpen,
  onClose,
  onTransition,
  onPause,
  onCommit,
  onResume,
  onRevert,
  onDump,
}: ActorDetailModalProps) {
  const [snapshots, setSnapshots] = useState<ActorSnapshot[]>([]);
  const [transitions, setTransitions] = useState<ActorTransitionLog[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'snapshots' | 'transitions'>('overview');
  const [loading, setLoading] = useState(false);
  const [revertTag, setRevertTag] = useState('');
  const [dumpTag, setDumpTag] = useState('');
  const [commitTag, setCommitTag] = useState('');
  const [commitScope, setCommitScope] = useState<'full' | 'data'>('data');
  const [pauseTimer] = useState<number | undefined>(undefined);

  useEffect(() => {
    if (actor && isOpen) {
      loadDetails();
    }
  }, [actor, isOpen]);

  const loadDetails = async () => {
    if (!actor) return;
    setLoading(true);
    try {
      const [snaps, trans] = await Promise.all([
        api.getSnapshots(actor.actor_uid),
        api.getTransitions(actor.actor_uid),
      ]);
      setSnapshots(snaps);
      setTransitions(trans);
    } catch (error) {
      console.error('Failed to load actor details:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (action: () => Promise<void>) => {
    try {
      await action();
      onClose();
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Action failed');
    }
  };

  if (!actor) return null;

  const transitions_list = getValidTransitions(actor.state);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Actor: ${actor.actor_name}`} size="lg">
      <div className="space-y-4">
        <div className="tabs" role="tablist">
          <button
            role="tab"
            className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
            aria-selected={activeTab === 'overview'}
          >
            Overview
          </button>
          <button
            role="tab"
            className={`tab ${activeTab === 'snapshots' ? 'active' : ''}`}
            onClick={() => setActiveTab('snapshots')}
            aria-selected={activeTab === 'snapshots'}
          >
            Snapshots ({snapshots.length})
          </button>
          <button
            role="tab"
            className={`tab ${activeTab === 'transitions' ? 'active' : ''}`}
            onClick={() => setActiveTab('transitions')}
            aria-selected={activeTab === 'transitions'}
          >
            Transitions ({transitions.length})
          </button>
        </div>

        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div className="flex items-center gap-4">
              <span className={`badge ${getBadgeClass(actor.state)} text-lg px-3 py-1`}>
                {actor.state}
              </span>
              <span className="text-sm text-gray-500">Scope: {actor.snapshot_scope}</span>
            </div>

            <div className="detail-section">
              <h3>Identity</h3>
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">Actor UID</span>
                  <span className="detail-value font-mono text-sm">{actor.actor_uid}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Name</span>
                  <span className="detail-value">{actor.actor_name}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Atespace</span>
                  <span className="detail-value">{actor.actor_atespace}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Container</span>
                  <span className="detail-value">{actor.container_name}</span>
                </div>
              </div>
            </div>

            <div className="detail-section">
              <h3>Template</h3>
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">Namespace</span>
                  <span className="detail-value">{actor.actor_template_namespace}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Name</span>
                  <span className="detail-value">{actor.actor_template_name}</span>
                </div>
              </div>
            </div>

            <div className="detail-section">
              <h3>Runtime</h3>
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">Node</span>
                  <span className="detail-value">{actor.node_name || 'Not assigned'}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Worker Pod</span>
                  <span className="detail-value">{actor.worker_pod || '—'}</span>
                </div>
              </div>
            </div>

            <div className="detail-section">
              <h3>Timestamps</h3>
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">Created</span>
                  <span className="detail-value">
                    {actor.created_at ? format(new Date(actor.created_at), 'MMM d, yyyy HH:mm:ss') : '—'}
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Updated</span>
                  <span className="detail-value">
                    {actor.updated_at ? format(new Date(actor.updated_at), 'MMM d, yyyy HH:mm:ss') : '—'}
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Last Snapshot</span>
                  <span className="detail-value">
                    {actor.last_snapshot_at ? format(new Date(actor.last_snapshot_at), 'MMM d, yyyy HH:mm:ss') : '—'}
                  </span>
                </div>
              </div>
            </div>

            {actor.tags && (
              <div className="detail-section">
                <h3>Tags</h3>
                <div className="detail-value font-mono text-sm">{actor.tags}</div>
              </div>
            )}

            <div className="detail-section">
              <h3>Actions</h3>
              <div className="flex flex-wrap gap-2">
                {transitions_list.includes('RUNNING') && actor.state !== 'RUNNING' && (
                  <button
                    className="btn btn-primary"
                    onClick={() => handleAction(() => onResume(actor.actor_uid))}
                    disabled={loading}
                  >
                    Resume
                  </button>
                )}
                {transitions_list.includes('PAUSED') && actor.state === 'RUNNING' && (
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleAction(() => onPause(actor.actor_uid, pauseTimer))}
                    disabled={loading}
                  >
                    Pause{pauseTimer ? ` (${pauseTimer}s)` : ''}
                  </button>
                )}
                {transitions_list.includes('SUSPENDED') && ['RUNNING', 'PAUSED'].includes(actor.state) && (
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleAction(() => onCommit(actor.actor_uid, commitTag, commitScope))}
                    disabled={loading}
                  >
                    Commit
                  </button>
                )}
                {transitions_list.includes('CRASHED') && ['RUNNING', 'PAUSED'].includes(actor.state) && (
                  <button
                    className="btn btn-danger"
                    onClick={() => {
                      if (confirm(`Force crash actor ${actor.actor_name}?`)) {
                        handleAction(() => onTransition(actor.actor_uid, 'CRASHED', 'manual crash'));
                      }
                    }}
                    disabled={loading}
                  >
                    Crash
                  </button>
                )}
                {transitions_list.includes('SUSPENDED') && actor.state === 'CRASHED' && (
                  <>
                    <input
                      type="text"
                      placeholder="Revert tag"
                      value={revertTag}
                      onChange={(e) => setRevertTag(e.target.value)}
                      className="form-input"
                      style={{ width: 'auto', minWidth: '150px' }}
                    />
                    <button
                      className="btn btn-secondary"
                      onClick={() => handleAction(() => onRevert(actor.actor_uid, revertTag))}
                      disabled={loading || !revertTag}
                    >
                      Revert
                    </button>
                  </>
                )}
                {actor.state !== 'SUSPENDED' && (
                  <>
                    <input
                      type="text"
                      placeholder="Dump tag"
                      value={dumpTag}
                      onChange={(e) => setDumpTag(e.target.value)}
                      className="form-input"
                      style={{ width: 'auto', minWidth: '150px' }}
                    />
                    <button
                      className="btn btn-secondary"
                      onClick={() => handleAction(() => onDump(actor.actor_uid, dumpTag))}
                      disabled={loading || !dumpTag}
                    >
                      Dump
                    </button>
                  </>
                )}
                {['RUNNING', 'PAUSED'].includes(actor.state) && (
                  <>
                    <input
                      type="text"
                      placeholder="Commit tag (optional)"
                      value={commitTag}
                      onChange={(e) => setCommitTag(e.target.value)}
                      className="form-input"
                      style={{ width: 'auto', minWidth: '180px' }}
                    />
                    <select
                      value={commitScope}
                      onChange={(e) => setCommitScope(e.target.value as 'full' | 'data')}
                      className="form-select"
                      style={{ width: 'auto' }}
                    >
                      <option value="data">Data only</option>
                      <option value="full">Full</option>
                    </select>
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'snapshots' && (
          <div>
            {loading ? (
              <div className="loading"><div className="spinner" /></div>
            ) : snapshots.length === 0 ? (
              <div className="empty-state">
                <p>No snapshots</p>
              </div>
            ) : (
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Tag</th>
                      <th>Scope</th>
                      <th>Size</th>
                      <th>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {snapshots.map((snap) => (
                      <tr key={snap.id}>
                        <td className="font-mono text-sm">{snap.tag || '—'}</td>
                        <td>{snap.scope}</td>
                        <td>{(snap.size_bytes / 1024 / 1024).toFixed(2)} MB</td>
                        <td>{format(new Date(snap.created_at), 'MMM d, yyyy HH:mm:ss')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'transitions' && (
          <div>
            {loading ? (
              <div className="loading"><div className="spinner" /></div>
            ) : transitions.length === 0 ? (
              <div className="empty-state">
                <p>No transitions</p>
              </div>
            ) : (
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>From</th>
                      <th>To</th>
                      <th>Triggered By</th>
                      <th>Reason</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transitions.map((t) => (
                      <tr key={t.id}>
                        <td>
                          <span className={`badge ${t.from_state ? getBadgeClass(t.from_state) : ''}`}>
                            {t.from_state || '—'}
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${getBadgeClass(t.to_state)}`}>{t.to_state}</span>
                        </td>
                        <td className="text-sm">{t.triggered_by || '—'}</td>
                        <td className="text-sm text-gray-500">{t.reason || '—'}</td>
                        <td className="text-sm">{format(new Date(t.created_at), 'MMM d, yyyy HH:mm:ss')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}