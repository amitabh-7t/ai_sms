import { useState, useEffect } from 'react';
import { Play, Square } from 'lucide-react';
import {
  getDevices,
  createCaptureSession,
  stopCaptureSession,
  getCaptureSessions,
  getCaptureStatus,
} from '../api';
import StatusIndicator from '../components/StatusIndicator';
import { formatDuration, formatDateTime } from '../utils/time';

function Capture() {
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [capturing, setCapturing] = useState(false);
  const [currentSession, setCurrentSession] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [duration, setDuration] = useState(0);
  const [processStatus, setProcessStatus] = useState(null);
  const [eventCount, setEventCount] = useState(0);
  const [loadingDevices, setLoadingDevices] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [error, setError] = useState('');

  // Load devices on mount
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      await fetchDevices();
      if (mounted) setLoadingDevices(false);
    };
    load();

    return () => {
      mounted = false;
    };
  }, []);

  // Load sessions periodically
  useEffect(() => {
    const load = async () => {
      await fetchSessions();
      setLoadingSessions(false);
    };
    load();
    const interval = setInterval(fetchSessions, 5000);
    return () => clearInterval(interval);
  }, []);

  // Duration counter
  useEffect(() => {
    if (!capturing || !currentSession) return undefined;
    const startTime = new Date(currentSession.started_at).getTime();
    setDuration(Math.floor((Date.now() - startTime) / 1000));
    const interval = setInterval(() => {
      setDuration(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [capturing, currentSession]);

  // Poll capture process status when capturing
  useEffect(() => {
    if (!capturing || !selectedDevice) {
      setProcessStatus(null);
      setEventCount(0);
      return undefined;
    }

    const loadStatus = async () => {
      try {
        const response = await getCaptureStatus(selectedDevice);
        setProcessStatus(response.data);
        setEventCount(response.data.events_count || 0);
      } catch (err) {
        console.error('Failed to fetch capture status', err);
      }
    };

    loadStatus();
    const interval = setInterval(loadStatus, 2000);
    return () => clearInterval(interval);
  }, [capturing, selectedDevice]);

  const fetchDevices = async () => {
    try {
      const response = await getDevices();
      setDevices(response.data || []);
      if (!selectedDevice && response.data?.length) {
        setSelectedDevice(response.data[0].device_id);
      }
    } catch (err) {
      console.error('Failed to fetch devices', err);
      setError('Failed to load devices. Try again later.');
    }
  };

  const fetchSessions = async () => {
    try {
      const response = await getCaptureSessions();
      const data = response.data || [];
      setSessions(data);
      const running = data.find((session) => session.status === 'running');
      if (running) {
        setCurrentSession(running);
        setCapturing(true);
        if (running.device_id) {
          setSelectedDevice(running.device_id);
        }
      } else {
        setCurrentSession(null);
        setCapturing(false);
        setDuration(0);
      }
    } catch (err) {
      console.error('Failed to fetch sessions', err);
      setError('Failed to load capture sessions.');
    }
  };

  const handleStartCapture = async () => {
    if (!selectedDevice) return;
    try {
      setError('');
      const response = await createCaptureSession({
        device_id: selectedDevice,
      });
      setCurrentSession(response.data);
      setCapturing(true);
      setDuration(0);
      setProcessStatus(null);
      setEventCount(0);
      await fetchSessions();
    } catch (err) {
      console.error('Failed to start capture', err);
      setError('Failed to start capture session.');
    }
  };

  const handleStopCapture = async () => {
    if (!currentSession) return;
    try {
      setError('');
      const response = await stopCaptureSession(currentSession.id);
      setCapturing(false);
      setCurrentSession(response.data);
      setDuration(0);
      setProcessStatus(null);
      setEventCount(0);
      await fetchSessions();
    } catch (err) {
      console.error('Failed to stop capture', err);
      setError('Failed to stop capture session.');
    }
  };

  const renderSessionsTable = () => {
    if (loadingSessions) {
      return (
        <div className="flex justify-center py-10">
          <div className="w-8 h-8 border-4 border-gray-200 border-t-indigo-600 rounded-full animate-spin" />
        </div>
      );
    }

    if (!sessions.length) {
      return <p className="text-gray-500">No capture sessions yet.</p>;
    }

    return (
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Device
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Started
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Stopped
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Duration
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sessions.slice(0, 20).map((session) => {
              const started = formatDateTime(session.started_at);
              const stopped = session.stopped_at ? formatDateTime(session.stopped_at) : '—';
              const durationSeconds = session.stopped_at
                ? (new Date(session.stopped_at) - new Date(session.started_at)) / 1000
                : (Date.now() - new Date(session.started_at)) / 1000;

              return (
                <tr key={session.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {session.device_id || '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">{started}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{stopped}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {formatDuration(durationSeconds)}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <span
                      className={`inline-flex px-3 py-1 rounded-full text-xs font-medium ${
                        session.status === 'running'
                          ? 'bg-emerald-50 text-emerald-600'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {session.status}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col lg:flex-row gap-6">
        <div className="bg-white rounded-2xl shadow-sm p-6 flex-1 border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Capture Control</h2>
          {error && (
            <div className="mb-4 bg-red-50 text-red-700 px-4 py-2 rounded">{error}</div>
          )}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Select Device
              </label>
              <select
                value={selectedDevice}
                onChange={(e) => setSelectedDevice(e.target.value)}
                disabled={loadingDevices || capturing}
                className="w-full rounded-lg border-gray-300 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="">Select a device</option>
                {devices.map((device) => (
                  <option key={device.device_id} value={device.device_id}>
                    {device.name || device.device_id}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              <button
                onClick={handleStartCapture}
                disabled={!selectedDevice || capturing}
                className="flex-1 inline-flex items-center justify-center px-4 py-3 rounded-xl bg-emerald-600 text-white font-medium hover:bg-emerald-500 disabled:opacity-60"
              >
                <Play size={18} className="mr-2" />
                Start Capture
              </button>
              <button
                onClick={handleStopCapture}
                disabled={!capturing || !currentSession}
                className="flex-1 inline-flex items-center justify-center px-4 py-3 rounded-xl bg-red-500 text-white font-medium hover:bg-red-400 disabled:opacity-60"
              >
                <Square size={18} className="mr-2" />
                Stop Capture
              </button>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-6 w-full lg:w-96 border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Status</h2>
          {capturing && currentSession ? (
            <div className="space-y-4">
              <StatusIndicator status="capturing" label="Capturing" animate />
              <p className="text-sm text-gray-500">
                Device:{' '}
                <span className="text-gray-900 font-medium">
                  {devices.find((d) => d.device_id === selectedDevice)?.name || selectedDevice}
                </span>
              </p>
              <p className="text-sm text-gray-500">
                Started:{' '}
                <span className="text-gray-900 font-medium">
                  {formatDateTime(currentSession.started_at)}
                </span>
              </p>
              <p className="text-sm text-gray-500">
                Duration:{' '}
                <span className="text-gray-900 font-medium">{formatDuration(duration)}</span>
              </p>
              {processStatus && (
                <div className="mt-2 p-3 bg-emerald-50 rounded-lg border border-emerald-100 text-sm">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <span className="text-gray-600">Events:</span>
                      <span className="ml-2 font-semibold text-gray-900">{eventCount}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Uptime:</span>
                      <span className="ml-2 font-semibold text-gray-900">
                        {formatDuration(processStatus.uptime || 0)}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Process ID:</span>
                      <span className="ml-2 font-mono text-xs text-gray-900">
                        {processStatus.pid || '—'}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Errors:</span>
                      <span className="ml-2 font-semibold text-red-600">
                        {processStatus.error_count || 0}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-sm text-gray-500">
              <StatusIndicator status="inactive" label="Stopped" />
              <p className="mt-2">No active capture session.</p>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm p-6 border border-gray-100">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Session History</h2>
            <p className="text-sm text-gray-500">Auto-refreshes every 5 seconds.</p>
          </div>
        </div>
        {renderSessionsTable()}
      </div>
    </div>
  );
}

export default Capture;

