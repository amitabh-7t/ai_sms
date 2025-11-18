import { useState, useEffect, useRef } from 'react';
import LiveFeedWebSocket from '../ws';
import { Radio } from 'lucide-react';

function LiveCard({ deviceId }) {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    // Connect to WebSocket
    wsRef.current = new LiveFeedWebSocket(
      deviceId,
      (data) => {
        setEvents(prev => [data, ...prev].slice(0, 20)); // Keep last 20 events
      },
      (error) => {
        console.error('WebSocket error:', error);
        setConnected(false);
      }
    );

    wsRef.current.connect();
    setConnected(true);

    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
    };
  }, [deviceId]);

  return (
    <div className="p-6">
      <div className="flex items-center space-x-2 mb-4">
        <Radio className={`h-5 w-5 ${connected ? 'text-green-500' : 'text-gray-400'}`} />
        <span className="text-sm text-gray-600">
          {connected ? 'Connected' : 'Disconnected'} - {events.length} events
        </span>
      </div>

      {events.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          Waiting for live events from device: {deviceId}
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {events.map((event, idx) => {
            const timestamp = event.timestamp || new Date().toISOString();
            const emotion = event.emotion || 'Unknown';
            const engagement = event.metrics?.engagement 
              ? (event.metrics.engagement * 100).toFixed(0) 
              : 'N/A';
            const studentId = event.student_id || 'Unknown';

            return (
              <div 
                key={idx} 
                className="p-3 border border-gray-200 rounded bg-gray-50 hover:bg-gray-100 transition"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-gray-900">
                        {studentId !== 'Unknown' ? `Student ${studentId}` : 'Unknown Student'}
                      </span>
                      <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                        {emotion}
                      </span>
                    </div>
                    <div className="mt-1 text-sm text-gray-600">
                      Engagement: {engagement}%
                    </div>
                    {event.metrics && (
                      <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                        <span className="text-emerald-600">Eng: {(event.metrics.engagement * 100).toFixed(0)}%</span>
                        <span className="text-blue-600">Att: {((event.metrics.attentiveness || 0) * 100).toFixed(0)}%</span>
                        <span className="text-amber-600">Pos: {((event.metrics.positivity || 0) * 100).toFixed(0)}%</span>
                        <span className="text-gray-600">Bore: {(event.metrics.boredom * 100).toFixed(0)}%</span>
                        <span className="text-orange-600">Frus: {(event.metrics.frustration * 100).toFixed(0)}%</span>
                        <span className="text-red-600">Risk: {((event.metrics.risk || 0) * 100).toFixed(0)}%</span>
                      </div>
                    )}
                  </div>
                  <div className="text-right text-xs text-gray-400">
                    {new Date(timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default LiveCard;