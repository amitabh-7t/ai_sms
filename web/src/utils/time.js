const pluralize = (value, unit) => {
  const rounded = Math.floor(value);
  return `${rounded} ${unit}${rounded !== 1 ? 's' : ''}`;
};

export const timeAgo = (timestamp) => {
  if (!timestamp) return 'Never';
  const date = new Date(timestamp);
  const diff = Date.now() - date.getTime();

  if (diff < 0) return 'Just now';

  const seconds = diff / 1000;
  if (seconds < 60) return 'Just now';
  const minutes = seconds / 60;
  if (minutes < 60) return `${pluralize(minutes, 'minute')} ago`;
  const hours = minutes / 60;
  if (hours < 24) return `${pluralize(hours, 'hour')} ago`;
  const days = hours / 24;
  if (days < 7) return `${pluralize(days, 'day')} ago`;
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
  }).format(date);
};

export const formatDuration = (seconds = 0) => {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  const parts = [];
  if (hrs) parts.push(`${hrs}h`);
  if (mins || hrs) parts.push(`${mins}m`);
  parts.push(`${secs}s`);
  return parts.join(' ');
};

export const formatDateTime = (timestamp) => {
  if (!timestamp) return '—';
  const date = new Date(timestamp);
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
  }).format(date);
};

