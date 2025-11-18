import { useState, useEffect, useMemo } from 'react';
import { Plus } from 'lucide-react';
import {
  getDevices,
  createDevice,
  updateDevice,
  deleteDevice,
  getDeviceStatus,
} from '../api';
import DeviceCard from '../components/DeviceCard';

const initialFormState = {
  device_id: '',
  name: '',
  location: '',
  status: 'inactive',
};

function Devices() {
  const [devices, setDevices] = useState([]);
  const [deviceStatuses, setDeviceStatuses] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingDevice, setEditingDevice] = useState(null);
  const [formData, setFormData] = useState(initialFormState);
  const [saving, setSaving] = useState(false);

  const hasDevices = useMemo(() => devices.length > 0, [devices]);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      await fetchDevices();
      if (mounted) setLoading(false);
    };
    load();

    const interval = setInterval(() => {
      fetchStatuses();
    }, 10000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const fetchDevices = async () => {
    try {
      setError('');
      const response = await getDevices();
      setDevices(response.data || []);
      await fetchStatuses(response.data || []);
    } catch (err) {
      console.error('Failed to load devices', err);
      setError('Failed to load devices. Please try again.');
    }
  };

  const fetchStatuses = async (deviceList = devices) => {
    if (!deviceList.length) return;
    try {
      const statusEntries = await Promise.all(
        deviceList.map(async (device) => {
          try {
            const statusResponse = await getDeviceStatus(device.device_id);
            return [device.device_id, statusResponse.data];
          } catch (err) {
            console.error(`Failed to load status for ${device.device_id}`, err);
            return [device.device_id, null];
          }
        })
      );
      setDeviceStatuses((prev) => {
        const next = { ...prev };
        statusEntries.forEach(([id, status]) => {
          next[id] = status || prev[id];
        });
        return next;
      });
    } catch (err) {
      console.error('Failed to refresh statuses', err);
    }
  };

  const openModal = (device = null) => {
    if (device) {
      setEditingDevice(device);
      setFormData({
        device_id: device.device_id,
        name: device.name || '',
        location: device.location || '',
        status: device.status || 'inactive',
      });
    } else {
      setEditingDevice(null);
      setFormData(initialFormState);
    }
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingDevice(null);
    setFormData(initialFormState);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      if (editingDevice) {
        await updateDevice(editingDevice.device_id, {
          name: formData.name,
          location: formData.location,
          status: formData.status,
        });
      } else {
        await createDevice(formData);
      }
      await fetchDevices();
      closeModal();
    } catch (err) {
      console.error('Failed to save device', err);
      setError('Failed to save device. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (device) => {
    const confirmed = window.confirm(
      `Delete device ${device.name || device.device_id}? This cannot be undone.`
    );
    if (!confirmed) return;

    try {
      await deleteDevice(device.device_id);
      await fetchDevices();
    } catch (err) {
      console.error('Failed to delete device', err);
      setError('Failed to delete device. Please try again.');
    }
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex justify-center py-20">
          <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
        </div>
      );
    }

    if (error) {
      return (
        <div className="bg-red-50 text-red-700 px-4 py-3 rounded">{error}</div>
      );
    }

    if (!hasDevices) {
      return (
        <div className="text-center py-20">
          <p className="text-gray-500 mb-4">No devices found.</p>
          <button
            onClick={() => openModal()}
            className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition"
          >
            <Plus size={18} className="mr-2" />
            Add your first device
          </button>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
        {devices.map((device) => (
          <DeviceCard
            key={device.device_id}
            device={device}
            statusInfo={deviceStatuses[device.device_id]}
            onEdit={openModal}
            onDelete={handleDelete}
          />
        ))}
      </div>
    );
  };

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Devices</h1>
          <p className="text-gray-500 mt-1">
            Manage capture devices and monitor their health.
          </p>
        </div>
        <button
          onClick={() => openModal()}
          className="mt-4 sm:mt-0 inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg shadow hover:bg-indigo-500 transition"
        >
          <Plus size={18} className="mr-2" />
          Add Device
        </button>
      </div>

      {renderContent()}

      {showModal && (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              {editingDevice ? 'Edit Device' : 'Add Device'}
            </h2>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Device ID
                </label>
                <input
                  type="text"
                  value={formData.device_id}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, device_id: e.target.value }))
                  }
                  disabled={!!editingDevice}
                  required
                  className="mt-1 w-full rounded-lg border-gray-300 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="e.g. lab_cam_01"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, name: e.target.value }))
                  }
                  className="mt-1 w-full rounded-lg border-gray-300 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Physics Lab Camera"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Location
                </label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, location: e.target.value }))
                  }
                  className="mt-1 w-full rounded-lg border-gray-300 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Lab A"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Status
                </label>
                <select
                  value={formData.status}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, status: e.target.value }))
                  }
                  className="mt-1 w-full rounded-lg border-gray-300 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-60"
                >
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Devices;

