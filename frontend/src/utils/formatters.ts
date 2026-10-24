/**
 * Number and date formatting utilities for energy intelligence analytics.
 */

export function formatMw(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '—';
  }
  return `${value.toLocaleString('en-GB', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })} MW`;
}

export function formatMwWithSign(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '—';
  }
  const formatted = Math.abs(value).toLocaleString('en-GB', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  if (value > 0) return `+${formatted} MW`;
  if (value < 0) return `-${formatted} MW`;
  return `0.0 MW`;
}

export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '—';
  }
  return `${value.toLocaleString('en-GB', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}%`;
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const monthIndex = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const dt = new Date(Date.UTC(year, monthIndex, day));
      return dt.toLocaleDateString('en-GB', {
        timeZone: 'UTC',
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      });
    }
  } catch {
    // fallback
  }
  return dateStr;
}

export function formatDateTime(isoStr: string | null | undefined): string {
  if (!isoStr) return '—';
  try {
    const dt = new Date(isoStr);
    return dt.toLocaleString('en-GB', {
      timeZone: 'UTC',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }) + ' UTC';
  } catch {
    return isoStr;
  }
}

export function formatTimeOnly(isoStr: string | null | undefined): string {
  if (!isoStr) return '—';
  try {
    const dt = new Date(isoStr);
    return dt.toLocaleTimeString('en-GB', {
      timeZone: 'UTC',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return isoStr;
  }
}

export function calculateLeadHours(publishTimeStr: string, deliveryTimeStr: string): string {
  try {
    const pub = new Date(publishTimeStr).getTime();
    const deliv = new Date(deliveryTimeStr).getTime();
    const diffHours = (deliv - pub) / (1000 * 60 * 60);
    if (diffHours < 0) {
      const postHours = Math.abs(diffHours).toFixed(1);
      return `${postHours}h post-delivery`;
    }
    if (diffHours >= 24) {
      const days = (diffHours / 24).toFixed(1);
      return `${days}d ahead (${Math.round(diffHours)}h)`;
    }
    return `${diffHours.toFixed(1)}h ahead`;
  } catch {
    return '—';
  }
}
