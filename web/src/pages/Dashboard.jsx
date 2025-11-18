import { useState, useEffect } from 'react';
import { getDashboardSummary, getStudents, getClassOverview } from '../api';
import { Link } from 'react-router-dom';
import LiveCard from '../components/LiveCard';
import MetricsGrid from '../components/MetricsGrid';
import { Activity, Users, AlertCircle, TrendingUp } from 'lucide-react';

function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [students, setStudents] = useState([]);
  const [classMetrics, setClassMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deviceId, setDeviceId] = useState('default');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [summaryRes, studentsRes, metricsRes] = await Promise.all([
        getDashboardSummary(),
        getStudents(),
        getClassOverview(deviceId).catch(() => null)
      ]);
      setSummary(summaryRes.data);
      setStudents(studentsRes.data.students || []);
      if (metricsRes) {
        setClassMetrics(metricsRes.data);
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading dashboard...</div>;
  }

  const stats = summary ? [
    {
      name: 'Active Students',
      value: summary.active_students,
      icon: Users,
      color: 'text-blue-600',
      bg: 'bg-blue-100'
    },
    {
      name: 'Active Devices',
      value: summary.active_devices,
      icon: Activity,
      color: 'text-green-600',
      bg: 'bg-green-100'
    },
    {
      name: 'Avg Engagement',
      value: `${(summary.avg_engagement * 100).toFixed(0)}%`,
      icon: TrendingUp,
      color: 'text-purple-600',
      bg: 'bg-purple-100'
    },
    {
      name: 'Recent Alerts',
      value: summary.recent_alerts,
      icon: AlertCircle,
      color: 'text-red-600',
      bg: 'bg-red-100'
    },
  ] : [];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className={`flex-shrink-0 ${stat.bg} rounded-md p-3`}>
                    <Icon className={`h-6 w-6 ${stat.color}`} />
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">{stat.name}</dt>
                      <dd className="text-2xl font-semibold text-gray-900">{stat.value}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* All 9 Metrics Overview */}
      {classMetrics && (
        <div className="bg-white shadow-sm rounded-xl p-6">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-gray-900">Class Metrics Overview</h2>
            <p className="text-sm text-gray-500 mt-1">Real-time engagement analysis for {deviceId}</p>
          </div>
          <MetricsGrid metrics={classMetrics} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Live Feed */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Live Feed</h2>
            <input
              type="text"
              value={deviceId}
              onChange={(e) => {
                setDeviceId(e.target.value);
                loadData();
              }}
              placeholder="Device ID"
              className="mt-2 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
          <LiveCard deviceId={deviceId} />
        </div>

        {/* Enrolled Students */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Enrolled Students</h2>
          </div>
          <div className="p-6">
            {students.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No students enrolled yet</p>
            ) : (
              <div className="space-y-3">
                {students.slice(0, 10).map((student) => (
                  <Link
                    key={student.student_id}
                    to={`/student/${student.student_id}`}
                    className="block p-3 border border-gray-200 rounded hover:bg-gray-50 transition"
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-medium text-gray-900">{student.name}</p>
                        <p className="text-sm text-gray-500">ID: {student.student_id}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-gray-400">
                          {student.enrolled_at ? new Date(student.enrolled_at).toLocaleDateString() : 'N/A'}
                        </p>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;