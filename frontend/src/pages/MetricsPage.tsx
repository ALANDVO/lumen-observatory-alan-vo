import { useEffect, useState } from 'react';
import { Card } from '../components/common/Card';

export function MetricsPage() {
  const [metricsText, setMetricsText] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await fetch('/metrics');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const text = await response.text();
        setMetricsText(text);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Prometheus Metrics</h1>
      <Card title="Metrics Endpoint" subtitle="Raw Prometheus exposition format">
        {error && <div className="alert alert-error mb-4">{error}</div>}
        {loading ? (
          <div className="loading"><div className="spinner" /></div>
        ) : (
          <pre className="font-mono text-sm bg-gray-900 text-green-300 p-4 rounded overflow-auto max-h-[600px]">
            {metricsText || 'No metrics available'}
          </pre>
        )}
      </Card>
    </div>
  );
}