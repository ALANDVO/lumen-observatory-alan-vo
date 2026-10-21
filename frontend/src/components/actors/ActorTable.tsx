import { Actor, ActorState } from '../../types/actor';
import { format } from 'date-fns';

interface ActorTableProps {
  actors: Actor[];
  onActorClick: (actor: Actor) => void;
  onTransition: (actorUid: string, toState: ActorState, reason?: string) => Promise<void>;
  onPause: (actorUid: string, timerSeconds?: number) => Promise<void>;
  onCommit: (actorUid: string, tag?: string, scope?: 'full' | 'data') => Promise<void>;
  onResume: (actorUid: string, nodeName?: string) => Promise<void>;
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

export function ActorTable({
  actors,
  onActorClick,
  onTransition,
  onPause,
  onCommit,
  onResume,
}: ActorTableProps) {
  if (actors.length === 0) {
    return (
      <div className="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
        <p>No actors found</p>
      </div>
    );
  }

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>UID</th>
            <th>Name</th>
            <th>Atespace</th>
            <th>Template</th>
            <th>State</th>
            <th>Node</th>
            <th>Updated</th>
            <th className="text-center">Actions</th>
          </tr>
        </thead>
        <tbody>
          {actors.map((actor) => (
            <tr key={actor.actor_uid} onClick={() => onActorClick(actor)} style={{ cursor: 'pointer' }}>
              <td className="font-mono text-sm">{actor.actor_uid.slice(0, 12)}…</td>
              <td className="font-medium">{actor.actor_name}</td>
              <td className="text-sm text-gray-500">{actor.actor_atespace}</td>
              <td className="text-sm">
                {actor.actor_template_namespace}/{actor.actor_template_name}
              </td>
              <td>
                <span className={`badge ${getBadgeClass(actor.state)}`}>{actor.state}</span>
              </td>
              <td className="text-sm text-gray-500">{actor.node_name || '—'}</td>
              <td className="text-sm text-gray-500">
                {actor.updated_at ? format(new Date(actor.updated_at), 'MMM d, HH:mm') : '—'}
              </td>
              <td className="text-center">
                <div className="flex items-center justify-center gap-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      const transitions = getValidTransitions(actor.state);
                      if (transitions.includes('RUNNING') && actor.state !== 'RUNNING') {
                        onResume(actor.actor_uid);
                      } else if (transitions.includes('PAUSED') && actor.state === 'RUNNING') {
                        onPause(actor.actor_uid);
                      } else if (transitions.includes('SUSPENDED') && ['RUNNING', 'PAUSED'].includes(actor.state)) {
                        onCommit(actor.actor_uid);
                      } else if (transitions.includes('CRASHED') && ['RUNNING', 'PAUSED'].includes(actor.state)) {
                        if (confirm(`Crash actor ${actor.actor_name}?`)) {
                          onTransition(actor.actor_uid, 'CRASHED', 'manual crash');
                        }
                      }
                    }}
                    className="btn btn-primary btn-sm"
                    title="Primary action"
                  >
                    {actor.state === 'SUSPENDED' ? 'Resume' : actor.state === 'RUNNING' ? 'Pause' : 'Commit'}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onActorClick(actor);
                    }}
                    className="btn btn-secondary btn-sm"
                    title="Details"
                  >
                    Details
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}