function StatusIndicator({ status = 'inactive', label, animate = false }) {
  const isActive = status === 'active' || status === 'capturing';
  const color = isActive ? 'bg-emerald-500' : 'bg-gray-400';
  const animation = animate ? 'animate-ping' : '';

  return (
    <div className="flex items-center gap-2">
      <span className="relative flex h-3 w-3">
        {animate && (
          <span
            className={`absolute inline-flex h-full w-full rounded-full ${color} opacity-75 ${animation}`}
          ></span>
        )}
        <span className={`relative inline-flex h-3 w-3 rounded-full ${color}`}></span>
      </span>
      {label && <span className="text-sm text-gray-600">{label}</span>}
    </div>
  );
}

export default StatusIndicator;

