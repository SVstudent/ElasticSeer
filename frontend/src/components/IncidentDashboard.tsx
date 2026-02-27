import { useState, useEffect } from 'react';
import { AlertCircle, Activity, TrendingUp, Clock, ExternalLink, RefreshCw, ChevronRight, ChevronLeft } from 'lucide-react';
import api from '../lib/api';

interface Incident {
  id: string;
  title: string;
  service: string;
  severity: string;
  status: string;
  region: string;
  created_at: string;
  resolved_at?: string;
  mttr_minutes?: number;
  description: string;
  diagnosis?: {
    root_cause: string;
    confidence: number;
  };
  remediation?: {
    pr_url: string;
  };
  tags?: {
    user_registered?: boolean;
  };
}

interface IncidentDashboardProps {
  onIncidentClick: (incidentId: string) => void;
}

export default function IncidentDashboard({ onIncidentClick }: IncidentDashboardProps) {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'all' | 'active' | 'resolved'>('all');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchIncidents = async () => {
    try {
      const response = await api.get('/api/incidents/list?limit=50');
      if (response.data.success) {
        setIncidents(response.data.incidents);
        setLastUpdate(new Date());
      }
    } catch (error) {
      console.error('Failed to fetch incidents:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchIncidents, 30000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const filteredIncidents = incidents.filter((inc) => {
    if (activeTab === 'active') {
      return inc.status === 'investigating' || inc.status === 'in_progress' || inc.status === 'remediating';
    }
    if (activeTab === 'resolved') {
      return inc.status === 'resolved' || inc.status === 'closed';
    }
    return true;
  });

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'Sev-1':
        return 'bg-red-100 text-red-700 border-red-300';
      case 'Sev-2':
        return 'bg-orange-100 text-orange-700 border-orange-300';
      case 'Sev-3':
        return 'bg-yellow-100 text-yellow-700 border-yellow-300';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-300';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'investigating':
        return 'bg-blue-100 text-blue-700';
      case 'in_progress':
        return 'bg-purple-100 text-purple-700';
      case 'remediating':
        return 'bg-indigo-100 text-indigo-700';
      case 'resolved':
        return 'bg-green-100 text-green-700';
      case 'closed':
        return 'bg-gray-100 text-gray-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'investigating':
      case 'in_progress':
        return <Activity className="h-3 w-3" />;
      case 'remediating':
        return <TrendingUp className="h-3 w-3" />;
      case 'resolved':
      case 'closed':
        return <Clock className="h-3 w-3" />;
      default:
        return <AlertCircle className="h-3 w-3" />;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const stats = {
    total: incidents.length,
    active: incidents.filter((i) => ['investigating', 'in_progress', 'remediating'].includes(i.status)).length,
    resolved: incidents.filter((i) => ['resolved', 'closed'].includes(i.status)).length,
    sev1: incidents.filter((i) => i.severity === 'Sev-1').length,
  };

  if (loading) {
    return (
      <div className={`bg-white border border-elastic-border rounded-lg shadow-sm transition-all duration-300 ${isCollapsed ? 'w-12' : 'w-full'}`}>
        <div className="flex items-center justify-center p-6">
          <RefreshCw className="h-5 w-5 animate-spin text-elastic-blue" />
          {!isCollapsed && <span className="ml-2 text-sm text-elastic-gray">Loading incidents...</span>}
        </div>
      </div>
    );
  }

  // Collapsed view
  if (isCollapsed) {
    return (
      <div className="bg-white border border-elastic-border rounded-lg shadow-sm w-12 flex flex-col items-center py-4 gap-4">
        <button
          onClick={() => setIsCollapsed(false)}
          className="p-2 rounded-md hover:bg-elastic-lightGray text-elastic-gray hover:text-elastic-darkGray transition-colors"
          title="Expand incident dashboard"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>

        <div className="flex flex-col items-center gap-2">
          <AlertCircle className="h-5 w-5 text-elastic-blue" />
          <div className="text-xs font-semibold text-elastic-darkGray writing-mode-vertical">
            {stats.total}
          </div>
        </div>

        {stats.active > 0 && (
          <div className="flex flex-col items-center gap-1">
            <Activity className="h-4 w-4 text-blue-600" />
            <div className="text-xs font-semibold text-blue-700">{stats.active}</div>
          </div>
        )}

        {stats.sev1 > 0 && (
          <div className="flex flex-col items-center gap-1">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <div className="text-xs font-semibold text-red-700">{stats.sev1}</div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white border border-elastic-border rounded-lg shadow-sm">
      {/* Header */}
      <div className="border-b border-elastic-border px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-elastic-blue" />
            <h2 className="text-base font-semibold text-elastic-darkGray">Incident Dashboard</h2>
            <span className="text-xs text-elastic-gray">
              ({lastUpdate.toLocaleTimeString()})
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => {
                setAutoRefresh(!autoRefresh);
                if (!autoRefresh) fetchIncidents();
              }}
              className={`p-1.5 rounded-md transition-colors ${autoRefresh
                ? 'bg-elastic-lightBlue text-elastic-blue'
                : 'text-elastic-gray hover:bg-elastic-lightGray'
                }`}
              title={autoRefresh ? 'Auto-refresh enabled (30s)' : 'Auto-refresh disabled'}
            >
              <RefreshCw className={`h-4 w-4 ${autoRefresh ? 'animate-spin-slow' : ''}`} />
            </button>
            <button
              onClick={() => setIsCollapsed(true)}
              className="p-1.5 rounded-md text-elastic-gray hover:bg-elastic-lightGray hover:text-elastic-darkGray transition-colors"
              title="Collapse dashboard"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-3 mt-3">
          <div className="bg-elastic-lightGray rounded-md px-3 py-2">
            <div className="text-xs text-elastic-gray">Total</div>
            <div className="text-lg font-semibold text-elastic-darkGray">{stats.total}</div>
          </div>
          <div className="bg-blue-50 rounded-md px-3 py-2">
            <div className="text-xs text-blue-600">Active</div>
            <div className="text-lg font-semibold text-blue-700">{stats.active}</div>
          </div>
          <div className="bg-green-50 rounded-md px-3 py-2">
            <div className="text-xs text-green-600">Resolved</div>
            <div className="text-lg font-semibold text-green-700">{stats.resolved}</div>
          </div>
          <div className="bg-red-50 rounded-md px-3 py-2">
            <div className="text-xs text-red-600">Sev-1</div>
            <div className="text-lg font-semibold text-red-700">{stats.sev1}</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-elastic-border px-4">
        <div className="flex gap-1">
          {(['all', 'active', 'resolved'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === tab
                ? 'border-elastic-blue text-elastic-blue'
                : 'border-transparent text-elastic-gray hover:text-elastic-darkGray'
                }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
              <span className="ml-1.5 text-xs">
                ({tab === 'all' ? stats.total : tab === 'active' ? stats.active : stats.resolved})
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Incident List */}
      <div className="max-h-96 overflow-y-auto">
        {filteredIncidents.length === 0 ? (
          <div className="p-8 text-center text-elastic-gray">
            <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No incidents found</p>
          </div>
        ) : (
          <div className="divide-y divide-elastic-border">
            {filteredIncidents.map((incident, index) => (
              <div
                key={`${incident.id}-${index}`}
                onClick={() => onIncidentClick(incident.id)}
                className="p-4 hover:bg-elastic-lightGray cursor-pointer transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    {/* Incident ID and Title */}
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono font-semibold text-elastic-blue">
                        {incident.id}
                      </span>
                      {incident.tags?.user_registered && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-700">
                          User
                        </span>
                      )}
                    </div>
                    <h3 className="text-sm font-medium text-elastic-darkGray truncate mb-1">
                      {incident.title}
                    </h3>

                    {/* Service and Region */}
                    <div className="flex items-center gap-2 text-xs text-elastic-gray mb-2">
                      <span className="font-medium">{incident.service}</span>
                      <span>•</span>
                      <span>{incident.region}</span>
                      <span>•</span>
                      <span>{formatTimestamp(incident.created_at)}</span>
                    </div>

                    {/* Root Cause (if available) */}
                    {incident.diagnosis?.root_cause && (
                      <p className="text-xs text-elastic-gray line-clamp-1 mb-2">
                        🔍 {incident.diagnosis.root_cause}
                      </p>
                    )}

                    {/* PR Link (if available) */}
                    {incident.remediation?.pr_url && (
                      <a
                        href={incident.remediation.pr_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="inline-flex items-center gap-1 text-xs text-elastic-blue hover:underline"
                      >
                        <ExternalLink className="h-3 w-3" />
                        View PR
                      </a>
                    )}
                  </div>

                  {/* Badges */}
                  <div className="flex flex-col items-end gap-1.5">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full border font-medium ${getSeverityColor(
                        incident.severity
                      )}`}
                    >
                      {incident.severity}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium flex items-center gap-1 ${getStatusColor(
                        incident.status
                      )}`}
                    >
                      {getStatusIcon(incident.status)}
                      {incident.status}
                    </span>
                    {incident.mttr_minutes && (
                      <span className="text-xs text-elastic-gray flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {incident.mttr_minutes}m
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
