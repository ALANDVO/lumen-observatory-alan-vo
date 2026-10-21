from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, REGISTRY
from backend.app.models.actor import ActorState


# Use the default registry so metrics appear on /metrics endpoint
_metrics_registry = REGISTRY


class ActorMetricsService:
    def __init__(self, registry: CollectorRegistry = None):
        self.registry = registry or _metrics_registry
        self.actors_gauge = Gauge(
            "ate_actors",
            "Number of actors by status and template",
            ["actor_template_namespace", "actor_template_name", "status"],
            registry=self.registry,
        )
        self.actor_crashes = Counter(
            "ate_actor_crashes_total",
            "Total number of actor crashes",
            ["actor_template_namespace", "actor_template_name"],
            registry=self.registry,
        )
        self.state_transitions = Counter(
            "ate_actor_state_transitions_total",
            "Total number of actor state transitions",
            ["from_state", "to_state", "actor_template_namespace", "actor_template_name"],
            registry=self.registry,
        )
        self.pause_duration = Histogram(
            "ate_actor_pause_duration_seconds",
            "Duration actors spend in PAUSED state",
            ["actor_template_namespace", "actor_template_name"],
            registry=self.registry,
        )
        self.suspend_duration = Histogram(
            "ate_actor_suspend_duration_seconds",
            "Duration actors spend in SUSPENDED state",
            ["actor_template_namespace", "actor_template_name"],
            registry=self.registry,
        )
        self.running_duration = Histogram(
            "ate_actor_running_duration_seconds",
            "Duration actors spend in RUNNING state",
            ["actor_template_namespace", "actor_template_name"],
            registry=self.registry,
        )

        self._current_counts = {}

    def increment_actor(self, template_namespace: str, template_name: str, status: ActorState):
        key = (template_namespace, template_name, status.value)
        self._current_counts[key] = self._current_counts.get(key, 0) + 1
        self.actors_gauge.labels(
            actor_template_namespace=template_namespace,
            actor_template_name=template_name,
            status=status.value
        ).inc()

    def decrement_actor(self, template_namespace: str, template_name: str, status: ActorState):
        key = (template_namespace, template_name, status.value)
        current = self._current_counts.get(key, 0)
        if current > 0:
            self._current_counts[key] = current - 1
            self.actors_gauge.labels(
                actor_template_namespace=template_namespace,
                actor_template_name=template_name,
                status=status.value
            ).dec()

    def record_crash(self, template_namespace: str, template_name: str):
        self.actor_crashes.labels(
            actor_template_namespace=template_namespace,
            actor_template_name=template_name
        ).inc()

    def record_transition(
        self,
        from_state: ActorState,
        to_state: ActorState,
        template_namespace: str,
        template_name: str
    ):
        self.state_transitions.labels(
            from_state=from_state.value,
            to_state=to_state.value,
            actor_template_namespace=template_namespace,
            actor_template_name=template_name
        ).inc()

    def record_pause_duration(self, template_namespace: str, template_name: str, duration_seconds: float):
        self.pause_duration.labels(
            actor_template_namespace=template_namespace,
            actor_template_name=template_name
        ).observe(duration_seconds)

    def record_suspend_duration(self, template_namespace: str, template_name: str, duration_seconds: float):
        self.suspend_duration.labels(
            actor_template_namespace=template_namespace,
            actor_template_name=template_name
        ).observe(duration_seconds)

    def record_running_duration(self, template_namespace: str, template_name: str, duration_seconds: float):
        self.running_duration.labels(
            actor_template_namespace=template_namespace,
            actor_template_name=template_name
        ).observe(duration_seconds)

    def get_current_count(self, template_namespace: str, template_name: str, status: ActorState) -> int:
        key = (template_namespace, template_name, status.value)
        return self._current_counts.get(key, 0)


actor_metrics = ActorMetricsService()