import { Edit2, Trash2, Radio } from 'lucide-react';
import StatusIndicator from './StatusIndicator';
import { timeAgo } from '../utils/time';

function DeviceCard({ device, statusInfo, onEdit, onDelete }) {
  const {
    device_id,
    name,
    location,
    status,
    last_seen,
  } = device;

  const eventsCount = statusInfo?.events_count ?? 0;
  const isCapturing = statusInfo?.is_capturing ?? false;
  const lastEvent = statusInfo?.last_event_time || last_seen;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-gray-500">Device</p>
          <h3 className="text-xl font-semibold text-gray-900">{name || 'Unnamed Device'}</h3>
          <p className="text-sm text-gray-500 mt-1">{device_id}</p>
        </div>
        <div className="flex items-center gap-2 text-gray-400">
          <button
            onClick={() => onEdit(device)}
            className="p-2 hover:text-gray-600 transition-colors"
            aria-label="Edit device"
          >
            <Edit2 size={18} />
          </button>
          <button
            onClick={() => onDelete(device)}
            className="p-2 hover:text-red-500 transition-colors"
            aria-label="Delete device"
          >
            <Trash2 size={18} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mt-6">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">Location</p>
          <p className="text-sm text-gray-900 mt-1">{location || 'Not set'}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">Status</p>
          <div className="mt-1">
            <StatusIndicator
              status={isCapturing ? 'capturing' : status}
              label={isCapturing ? 'Capturing' : status}
              animate={isCapturing}
            />
          </div>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">Events (1h)</p>
          <p className="text-sm text-gray-900 mt-1 font-medium">{eventsCount}</p>
        </div>
        <div className="flex flex-col">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Last Seen</p>
          <p className="text-sm text-gray-900 mt-1">{lastEvent ? timeAgo(lastEvent) : 'Never'}</p>
        </div>
      </div>

      <div className="mt-6 flex items-center gap-2 text-sm text-gray-500">
        <Radio size={16} />
        <span>Device health monitored</span>
      </div>
    </div>
  );
}

export default DeviceCard;

