import MetricsPanel from './MetricsPanel';

function MetricsGrid({ metrics, showTrends = false }) {
  const metricKeys = [
    'engagement',
    'attentiveness',
    'positivity',
    'boredom',
    'frustration',
    'volatility',
    'distraction',
    'fatigue',
    'risk'
  ];

  const getMetricValue = (key) => {
    const value = metrics?.[`avg_${key}`] ?? metrics?.[key];
    return typeof value === 'number' ? value : 0;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {metricKeys.map((key) => (
        <MetricsPanel
          key={key}
          metricKey={key}
          value={getMetricValue(key)}
          showTrend={showTrends}
        />
      ))}
    </div>
  );
}

export default MetricsGrid;
