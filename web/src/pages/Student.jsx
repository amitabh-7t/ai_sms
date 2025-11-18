import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getStudentMetrics } from '../api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { ArrowLeft } from 'lucide-react';
import MetricsGrid from '../components/MetricsGrid';

function Student() {
  const { id } = useParams();
  const [metrics, setMetrics] = useState([]);
  const [latestMetrics, setLatestMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('1h');

  useEffect(() => {
    loadMetrics();
  }, [id, timeRange]);

  const loadMetrics = async () => {
    try {
      const now = new Date();
      let from = new Date(now);
      
      switch (timeRange) {
        case '1h':
          from.setHours(from.getHours() - 1);
          break;
        case '4h':
          from.setHours(from.getHours() - 4);
          break;
        case '24h':
          from.setHours(from.getHours() - 24);
          break;
        default:
          from.setHours(from.getHours() - 1);
      }

      const response = await getStudentMetrics(
        id,
        from.toISOString(),
        now.toISOString(),
        'minute'
      );

      const data = response.data.metrics.map(m => ({
        time: new Date(m.timestamp).toLocaleTimeString(),
        engagement: (m.avg_engagement * 100).toFixed(1),
        boredom: (m.avg_boredom * 100).toFixed(1),
        frustration: (m.avg_frustration * 100).toFixed(1),
        attentiveness: ((m.avg_attentiveness || 0) * 100).toFixed(1),
        positivity: ((m.avg_positivity || 0) * 100).toFixed(1),
        volatility: ((m.avg_volatility || 0) * 100).toFixed(1),
        distraction: ((m.avg_distraction || 0) * 100).toFixed(1),
        fatigue: ((m.avg_fatigue || 0) * 100).toFixed(1),
        risk: ((m.avg_risk || 0) * 100).toFixed(1),
      }));

      setMetrics(data);

      // Set latest metrics for grid display
      if (response.data.metrics.length > 0) {
        const latest = response.data.metrics[response.data.metrics.length - 1];
        setLatestMetrics({
          avg_engagement: latest.avg_engagement || 0,
          avg_attentiveness: latest.avg_attentiveness || 0,
          avg_positivity: latest.avg_positivity || 0,
          avg_boredom: latest.avg_boredom || 0,
          avg_frustration: latest.avg_frustration || 0,
          avg_volatility: latest.avg_volatility || 0,
          avg_distraction: latest.avg_distraction || 0,
          avg_fatigue: latest.avg_fatigue || 0,
          avg_risk: latest.avg_risk || 0,
        });
      }
    } catch (error) {
      console.error('Failed to load student metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link to="/" className="text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-6 w-6" />
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">Student {id}</h1>
        </div>
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          className="block pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
        >
          <option value="1h">Last Hour</option>
          <option value="4h">Last 4 Hours</option>
          <option value="24h">Last 24 Hours</option>
        </select>
      </div>

      {/* Latest Metrics Grid */}
      {latestMetrics && !loading && (
        <div className="bg-white shadow-sm rounded-xl p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Current Metrics Snapshot</h2>
          <MetricsGrid metrics={latestMetrics} />
        </div>
      )}

      {/* Primary Metrics Chart */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Primary Engagement Metrics</h2>
        {loading ? (
          <div className="text-center py-8">Loading metrics...</div>
        ) : metrics.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No data available for this time range</div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={metrics}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis label={{ value: 'Percentage', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="engagement" stroke="#10b981" name="Engagement" strokeWidth={2} />
              <Line type="monotone" dataKey="attentiveness" stroke="#3b82f6" name="Attentiveness" />
              <Line type="monotone" dataKey="positivity" stroke="#f59e0b" name="Positivity" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Negative Indicators Chart */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Negative Indicators</h2>
        {loading ? (
          <div className="text-center py-8">Loading metrics...</div>
        ) : metrics.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No data available for this time range</div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={metrics}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis label={{ value: 'Percentage', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="boredom" stroke="#6b7280" name="Boredom" />
              <Line type="monotone" dataKey="frustration" stroke="#f97316" name="Frustration" />
              <Line type="monotone" dataKey="distraction" stroke="#06b6d4" name="Distraction" />
              <Line type="monotone" dataKey="fatigue" stroke="#6366f1" name="Fatigue" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Risk Score Chart */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Risk Assessment & Volatility</h2>
        {loading ? (
          <div className="text-center py-8">Loading metrics...</div>
        ) : metrics.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No data available for this time range</div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={metrics}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis label={{ value: 'Percentage', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="risk" stroke="#ef4444" name="Risk Score" strokeWidth={2} />
              <Line type="monotone" dataKey="volatility" stroke="#a855f7" name="Volatility" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Recent Events */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Recent Events</h2>
        {metrics.length > 0 ? (
          <div className="space-y-3">
            {metrics.slice(-10).reverse().map((m, idx) => (
              <div key={idx} className="flex justify-between items-center p-3 border border-gray-200 rounded">
                <span className="text-sm text-gray-600">{m.time}</span>
                <div className="flex space-x-4 text-sm">
                  <span className="text-green-600">Eng: {m.engagement}%</span>
                  <span className="text-amber-600">Bore: {m.boredom}%</span>
                  <span className="text-red-600">Frus: {m.frustration}%</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-4">No recent events</p>
        )}
      </div>
    </div>
  );
}

export default Student;