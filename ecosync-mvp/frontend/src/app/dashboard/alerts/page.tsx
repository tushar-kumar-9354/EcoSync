'use client';

import { useAlerts, useAlertStats } from '@/hooks/useData';
import { Card, Badge, Button, Spinner } from '@/components/ui';
import { SeverityDistributionChart } from '@/components/charts';
import { SEVERITY_COLORS, ALERT_TYPE_LABELS } from '@/lib/constants';
import { useState } from 'react';

export default function AlertsDashboard() {
  const [filter, setFilter] = useState({ severity: '', status: 'ACTIVE' });
  const [selectedAlert, setSelectedAlert] = useState<string | null>(null);
  const { data: alerts, isLoading, refetch } = useAlerts({ ...filter, limit: 100 });
  const { data: stats } = useAlertStats();

  const handleAcknowledge = async (id: string) => {
    await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/alerts/${id}/acknowledge`, { method: 'PUT' });
    refetch();
  };

  const handleResolve = async (id: string) => {
    await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/alerts/${id}/resolve`, { method: 'PUT' });
    refetch();
  };

  const filteredAlerts = alerts?.alerts || [];
  const criticalCount = stats?.by_severity?.CRITICAL || 0;
  const highCount = stats?.by_severity?.HIGH || 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Alert Management</h1>
          <p className="text-sm text-gray-400 mt-1">Monitor, acknowledge, and resolve system alerts</p>
        </div>
        <div className="flex gap-3">
          {/* Severity Filter */}
          <div className="flex gap-1 bg-bg-secondary rounded-lg p-1">
            {['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(sev => (
              <button key={sev} onClick={() => setFilter({ ...filter, severity: sev })}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  filter.severity === sev
                    ? sev === 'CRITICAL' ? 'bg-red-500/20 text-red-400'
                    : sev === 'HIGH' ? 'bg-orange-500/20 text-orange-400'
                    : sev === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-400'
                    : sev === 'LOW' ? 'bg-green-500/20 text-green-400'
                    : 'bg-primary/20 text-primary'
                    : 'text-gray-400 hover:text-white'
                }`}>
                {sev || 'All'}
              </button>
            ))}
          </div>
          {/* Status Filter */}
          <div className="flex gap-1 bg-bg-secondary rounded-lg p-1">
            {['ACTIVE', 'ACKNOWLEDGED', 'RESOLVED'].map(s => (
              <button key={s} onClick={() => setFilter({ ...filter, status: s })}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  filter.status === s ? 'bg-primary/20 text-primary' : 'text-gray-400 hover:text-white'
                }`}>
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-5 gap-4">
        <Card className="text-center py-4">
          <p className="text-3xl font-bold" style={{ color: '#E6EDF3' }}>{stats?.total_active || 0}</p>
          <p className="text-xs text-gray-400 mt-1">Total Active</p>
        </Card>
        <Card className="text-center py-4">
          <p className="text-3xl font-bold" style={{ color: SEVERITY_COLORS.CRITICAL }}>{criticalCount}</p>
          <p className="text-xs text-gray-400 mt-1">Critical</p>
        </Card>
        <Card className="text-center py-4">
          <p className="text-3xl font-bold" style={{ color: SEVERITY_COLORS.HIGH }}>{highCount}</p>
          <p className="text-xs text-gray-400 mt-1">High</p>
        </Card>
        <Card className="text-center py-4">
          <p className="text-3xl font-bold text-yellow-400">{stats?.acknowledged || 0}</p>
          <p className="text-xs text-gray-400 mt-1">Acknowledged</p>
        </Card>
        <Card className="text-center py-4">
          <p className="text-3xl font-bold text-green-400">{stats?.resolved_today || 0}</p>
          <p className="text-xs text-gray-400 mt-1">Resolved Today</p>
        </Card>
      </div>

      {/* Severity Distribution */}
      {stats && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Severity Distribution</h3>
          <SeverityDistributionChart stats={stats.by_severity} height={80} />
        </Card>
      )}

      {/* Alert List */}
      <div className="space-y-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Spinner className="text-primary" />
          </div>
        ) : filteredAlerts.length === 0 ? (
          <Card className="text-center py-12">
            <svg className="w-16 h-16 text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-gray-500">No alerts match your filter criteria</p>
          </Card>
        ) : (
          filteredAlerts.map((alert: any) => (
            <Card
              key={alert.id}
              className={`hover:border-gray-600 transition-all cursor-pointer ${
                selectedAlert === alert.id ? 'border-primary ring-1 ring-primary' : ''
              }`}
              onClick={() => setSelectedAlert(selectedAlert === alert.id ? null : alert.id)}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: SEVERITY_COLORS[alert.severity as keyof typeof SEVERITY_COLORS] || '#888' }} />
                    <Badge variant={
                      alert.severity === 'CRITICAL' ? 'critical' :
                      alert.severity === 'HIGH' ? 'high' :
                      alert.severity === 'MEDIUM' ? 'medium' : 'low'
                    }>
                      {alert.severity}
                    </Badge>
                    <Badge variant={alert.status === 'ACTIVE' ? 'high' : alert.status === 'ACKNOWLEDGED' ? 'medium' : 'low'}>
                      {alert.status}
                    </Badge>
                    <span className="text-xs text-gray-500">{ALERT_TYPE_LABELS[alert.type] || alert.type}</span>
                    <span className="text-xs text-gray-600">•</span>
                    <span className="text-xs text-gray-500 font-mono">{alert.id}</span>
                  </div>

                  <h3 className="text-base font-medium text-white">{alert.title}</h3>
                  <p className="text-sm text-gray-400 mt-1">{alert.message}</p>

                  {/* Expanded Details */}
                  {selectedAlert === alert.id && (
                    <div className="mt-4 pt-4 border-t border-bg-tertiary">
                      <div className="grid grid-cols-4 gap-4">
                        <div>
                          <p className="text-xs text-gray-500">Location</p>
                          <p className="text-sm text-white mt-1">{alert.location?.address || 'N/A'}</p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {alert.location?.lat?.toFixed(4)}, {alert.location?.lng?.toFixed(4)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Current Value</p>
                          <p className="text-sm font-medium text-white mt-1">
                            {alert.current_value} {alert.unit}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Threshold</p>
                          <p className="text-sm font-medium text-white mt-1">
                            {alert.threshold} {alert.unit}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Triggered</p>
                          <p className="text-sm text-white mt-1">
                            {new Date(alert.triggered_at).toLocaleString()}
                          </p>
                          {alert.acknowledged_at && (
                            <p className="text-xs text-gray-500 mt-0.5">
                              Ack: {new Date(alert.acknowledged_at).toLocaleString()}
                            </p>
                          )}
                          {alert.resolved_at && (
                            <p className="text-xs text-gray-500 mt-0.5">
                              Resolved: {new Date(alert.resolved_at).toLocaleString()}
                            </p>
                          )}
                        </div>
                      </div>
                      {alert.tags && alert.tags.length > 0 && (
                        <div className="mt-3 flex gap-2">
                          {alert.tags.map((tag: string) => (
                            <span key={tag} className="px-2 py-0.5 bg-bg-tertiary rounded text-xs text-gray-400">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      {alert.location?.address}
                    </span>
                    <span>Triggered: {new Date(alert.triggered_at).toLocaleString()}</span>
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  {alert.status === 'ACTIVE' && (
                    <>
                      <Button size="sm" variant="secondary" onClick={(e: React.MouseEvent) => { e.stopPropagation(); handleAcknowledge(alert.id); }}>
                        Acknowledge
                      </Button>
                      <Button size="sm" variant="default" onClick={(e: React.MouseEvent) => { e.stopPropagation(); handleResolve(alert.id); }}>
                        Resolve
                      </Button>
                    </>
                  )}
                  {alert.status === 'ACKNOWLEDGED' && (
                    <Button size="sm" variant="default" onClick={(e: React.MouseEvent) => { e.stopPropagation(); handleResolve(alert.id); }}>
                      Resolve
                    </Button>
                  )}
                  {alert.status === 'RESOLVED' && (
                    <span className="text-xs text-green-400 text-center py-2">Resolved</span>
                  )}
                </div>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Resolved Today Summary */}
      {stats?.resolved_today && stats.resolved_today > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Recently Resolved Today</h3>
          <div className="text-xs text-gray-500">
            {stats.resolved_today} alert{stats.resolved_today !== 1 ? 's' : ''} resolved. Average resolution time: 2.4 hours.
          </div>
        </Card>
      )}
    </div>
  );
}
