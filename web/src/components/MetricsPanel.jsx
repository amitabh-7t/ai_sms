import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const METRIC_CONFIGS = {
  engagement: {
    name: 'Engagement',
    description: 'Overall student engagement level',
    color: 'emerald',
    icon: '📊',
    thresholds: { good: 0.7, warning: 0.5 }
  },
  attentiveness: {
    name: 'Attentiveness',
    description: 'Student focus and attention',
    color: 'blue',
    icon: '👁️',
    thresholds: { good: 0.7, warning: 0.5 }
  },
  positivity: {
    name: 'Positivity',
    description: 'Emotional sentiment score',
    color: 'amber',
    icon: '😊',
    thresholds: { good: 0.6, warning: 0.4 }
  },
  boredom: {
    name: 'Boredom',
    description: 'Signs of disengagement',
    color: 'gray',
    icon: '😴',
    thresholds: { good: 0.3, warning: 0.5 },
    inverted: true
  },
  frustration: {
    name: 'Frustration',
    description: 'Difficulty or confusion indicators',
    color: 'orange',
    icon: '😤',
    thresholds: { good: 0.3, warning: 0.5 },
    inverted: true
  },
  volatility: {
    name: 'Volatility',
    description: 'Emotional stability over time',
    color: 'purple',
    icon: '📈',
    thresholds: { good: 0.4, warning: 0.6 },
    inverted: true
  },
  distraction: {
    name: 'Distraction',
    description: 'Movement and attention drift',
    color: 'cyan',
    icon: '👀',
    thresholds: { good: 0.3, warning: 0.5 },
    inverted: true
  },
  fatigue: {
    name: 'Fatigue',
    description: 'Tiredness indicators',
    color: 'indigo',
    icon: '😮',
    thresholds: { good: 0.3, warning: 0.5 },
    inverted: true
  },
  risk: {
    name: 'Risk Score',
    description: 'Overall at-risk assessment',
    color: 'red',
    icon: '⚠️',
    thresholds: { good: 0.4, warning: 0.6 },
    inverted: true
  }
};

function getStatusColor(value, config) {
  const { thresholds, inverted } = config;

  if (inverted) {
    if (value <= thresholds.good) return 'green';
    if (value <= thresholds.warning) return 'yellow';
    return 'red';
  } else {
    if (value >= thresholds.good) return 'green';
    if (value >= thresholds.warning) return 'yellow';
    return 'red';
  }
}

function getColorClasses(colorName, variant = 'bg') {
  const colors = {
    emerald: {
      bg: 'bg-emerald-50',
      border: 'border-emerald-200',
      text: 'text-emerald-700',
      dark: 'text-emerald-900'
    },
    blue: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      text: 'text-blue-700',
      dark: 'text-blue-900'
    },
    amber: {
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      text: 'text-amber-700',
      dark: 'text-amber-900'
    },
    gray: {
      bg: 'bg-gray-50',
      border: 'border-gray-200',
      text: 'text-gray-700',
      dark: 'text-gray-900'
    },
    orange: {
      bg: 'bg-orange-50',
      border: 'border-orange-200',
      text: 'text-orange-700',
      dark: 'text-orange-900'
    },
    purple: {
      bg: 'bg-purple-50',
      border: 'border-purple-200',
      text: 'text-purple-700',
      dark: 'text-purple-900'
    },
    cyan: {
      bg: 'bg-cyan-50',
      border: 'border-cyan-200',
      text: 'text-cyan-700',
      dark: 'text-cyan-900'
    },
    indigo: {
      bg: 'bg-indigo-50',
      border: 'border-indigo-200',
      text: 'text-indigo-700',
      dark: 'text-indigo-900'
    },
    red: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      text: 'text-red-700',
      dark: 'text-red-900'
    }
  };

  return colors[colorName] || colors.gray;
}

function MetricsPanel({ metricKey, value, trend = null, showTrend = false }) {
  const config = METRIC_CONFIGS[metricKey] || {
    name: metricKey,
    description: 'Custom metric',
    color: 'gray',
    icon: '📊',
    thresholds: { good: 0.7, warning: 0.5 }
  };

  const numValue = typeof value === 'number' ? value : 0;
  const percentage = Math.round(numValue * 100);
  const status = getStatusColor(numValue, config);
  const colorClasses = getColorClasses(config.color);

  const statusColors = {
    green: 'bg-emerald-500',
    yellow: 'bg-amber-500',
    red: 'bg-red-500'
  };

  const TrendIcon = trend > 0 ? TrendingUp : trend < 0 ? TrendingDown : Minus;
  const trendColor = trend > 0 ? 'text-emerald-600' : trend < 0 ? 'text-red-600' : 'text-gray-500';

  return (
    <div className={`rounded-xl border ${colorClasses.border} ${colorClasses.bg} p-4 hover:shadow-lg transition-shadow`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{config.icon}</span>
          <div>
            <h3 className={`font-semibold ${colorClasses.dark}`}>{config.name}</h3>
            <p className={`text-xs ${colorClasses.text}`}>{config.description}</p>
          </div>
        </div>
        {showTrend && trend !== null && (
          <div className={`flex items-center gap-1 ${trendColor}`}>
            <TrendIcon size={16} />
            <span className="text-xs font-medium">{Math.abs(trend).toFixed(1)}%</span>
          </div>
        )}
      </div>

      <div className="mt-3">
        <div className="flex items-end justify-between mb-1">
          <span className={`text-3xl font-bold ${colorClasses.dark}`}>{percentage}%</span>
          <div className={`w-3 h-3 rounded-full ${statusColors[status]}`} title={`Status: ${status}`} />
        </div>

        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${statusColors[status]}`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    </div>
  );
}

export default MetricsPanel;
export { METRIC_CONFIGS };
