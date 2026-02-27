import { useState, useEffect } from 'react';
import {
  Activity, GitCommit, AlertTriangle, CheckCircle,
  Clock, Play, Pause, MessageSquare, Ticket, Bell, Zap,
  ChevronDown, ChevronUp, ExternalLink, Shield
} from 'lucide-react';
import api from '../lib/api';

interface Anomaly {
  service: string;
  metric: string;
  current_value: number;
  baseline_mean?: number;
  baseline_std?: number;
  sigma_deviation: number;
  severity: string;
  detected_at: string;
  '@timestamp'?: string;
  value?: number;
}

interface PendingWorkflow {
  id: string;
  type: string;
  status: string;
  created_at: string;
  anomaly: Anomaly;
  actions: string[];
}


interface ObserverStatus {
  status: string;
  last_check: string;
  check_interval_seconds: number;
  anomaly_threshold_sigma: number;
  recent_anomalies: Anomaly[];
  pending_workflows: PendingWorkflow[];
  activity_log: {
    github: any[];
    jira: any[];
    slack: any[];
    agent: any[];
  };
  monitoring: {
    metrics: boolean;
    github: boolean;
    jira: boolean;
    slack: boolean;
    agent: boolean;
  };
}

export default function ObserverWidget() {
  const [status, setStatus] = useState<ObserverStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'monitoring' | 'log' | 'workflows'>('monitoring');
  const [isExpanded, setIsExpanded] = useState(true);

  useEffect(() => {
    fetchStatus();

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchStatus();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    try {
      const response = await api.get('/api/observer/status');
      setStatus(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching observer status:', error);
      setLoading(false);
    }
  };

  const toggleObserver = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const endpoint = status?.status === 'running' ? '/api/observer/stop' : '/api/observer/start';
      await api.post(endpoint);
      fetchStatus();
    } catch (error) {
      console.error('Error toggling observer:', error);
    }
  };

  const approveWorkflow = async (workflowId: string, approved: boolean) => {
    try {
      await api.post('/api/observer/workflows/approve', {
        workflow_id: workflowId,
        approved,
        reason: approved ? 'Approved by user' : 'Rejected by user'
      });
      fetchStatus();
    } catch (error) {
      console.error('Error approving workflow:', error);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-elastic-border p-6 shadow-sm">
        <div className="animate-pulse flex flex-col gap-4">
          <div className="h-6 bg-elastic-lightGray rounded w-1/3"></div>
          <div className="h-32 bg-elastic-lightGray/50 rounded-lg"></div>
          <div className="space-y-3">
            <div className="h-4 bg-elastic-lightGray rounded"></div>
            <div className="h-4 bg-elastic-lightGray rounded w-5/6"></div>
          </div>
        </div>
      </div>
    );
  }

  const allActivity = [
    ...(status?.activity_log?.agent || []).map(a => ({ ...a, category: 'agent' })),
    ...(status?.activity_log?.github || []).map(a => ({ ...a, category: 'github' })),
    ...(status?.activity_log?.jira || []).map(a => ({ ...a, category: 'jira' })),
    ...(status?.activity_log?.slack || []).map(a => ({ ...a, category: 'slack' }))
  ].sort((a, b) => {
    const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
    const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
    return timeB - timeA;
  });

  return (
    <div className={`flex flex-col bg-white rounded-lg border border-elastic-border shadow-sm transition-all duration-300 overflow-hidden w-full`}>
      {/* Elastic Header */}
      <div
        className="px-5 py-4 flex items-center justify-between cursor-pointer bg-white border-b border-elastic-border"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${status?.status === 'running' ? 'bg-elastic-lightBlue text-elastic-blue' : 'bg-elastic-lightGray text-elastic-gray'}`}>
            <Shield className={`h-5 w-5 ${status?.status === 'running' ? 'animate-pulse' : ''}`} />
          </div>
          <div>
            <h3 className="font-bold text-elastic-darkGray flex items-center gap-2">
              Observer Engine
              {status?.status === 'running' && (
                <span className="flex h-2 w-2 rounded-full bg-emerald-500"></span>
              )}
            </h3>
            <p className="text-[10px] text-elastic-gray font-mono uppercase tracking-widest">Autonomous Sentry</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={toggleObserver}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-bold transition-all
                       ${status?.status === 'running'
                ? 'bg-red-50 text-red-600 hover:bg-red-100 border border-red-200'
                : 'bg-elastic-blue text-white hover:bg-elastic-darkBlue shadow-sm'}`}
          >
            {status?.status === 'running' ? (
              <><Pause className="h-3 w-3 fill-current" /> STOP</>
            ) : (
              <><Play className="h-3 w-3 fill-current" /> START</>
            )}
          </button>

          {isExpanded ? <ChevronUp className="h-5 w-5 text-elastic-gray" /> : <ChevronDown className="h-5 w-5 text-elastic-gray" />}
        </div>
      </div>

      {isExpanded && (
        <div className="flex flex-col h-[500px]">
          {/* Tabs */}
          <div className="flex border-b border-elastic-border bg-elastic-lightGray/30">
            <button
              onClick={() => setActiveTab('monitoring')}
              className={`flex-1 py-3 text-xs font-bold uppercase tracking-wider transition-all border-b-2 
                         ${activeTab === 'monitoring' ? 'text-elastic-blue border-elastic-blue bg-elastic-lightBlue/20' : 'text-elastic-gray border-transparent hover:text-elastic-darkGray'}`}
            >
              Monitoring
            </button>
            <button
              onClick={() => setActiveTab('workflows')}
              className={`flex-1 py-3 text-xs font-bold uppercase tracking-wider transition-all border-b-2 relative
                         ${activeTab === 'workflows' ? 'text-elastic-blue border-elastic-blue bg-elastic-lightBlue/20' : 'text-elastic-gray border-transparent hover:text-elastic-darkGray'}`}
            >
              Workflows
              {status?.pending_workflows && status.pending_workflows.length > 0 && (
                <span className="absolute top-2 right-4 flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-[10px] text-white">
                  {status.pending_workflows.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('log')}
              className={`flex-1 py-3 text-xs font-bold uppercase tracking-wider transition-all border-b-2 
                         ${activeTab === 'log' ? 'text-elastic-blue border-elastic-blue bg-elastic-lightBlue/20' : 'text-elastic-gray border-transparent hover:text-elastic-darkGray'}`}
            >
              Activity Log
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-5 custom-scrollbar bg-white">
            {activeTab === 'monitoring' && (
              <div className="space-y-6">
                {/* Status Grid */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-elastic-lightGray/30 border border-elastic-border p-4 rounded-lg flex flex-col gap-2">
                    <div className="flex items-center gap-2 text-elastic-gray mb-1">
                      <Zap className="h-4 w-4 text-elastic-blue" />
                      <span className="text-xs font-bold uppercase tracking-wide">Live Metrics</span>
                    </div>
                    <div className="flex items-end justify-between">
                      <span className="text-2xl font-bold text-elastic-darkGray">{status?.recent_anomalies.length || 0}</span>
                      <span className="text-[10px] text-elastic-gray mb-1">Past 24h</span>
                    </div>
                    <div className="h-1 bg-elastic-border rounded-full overflow-hidden">
                      <div className="h-full bg-elastic-blue w-2/3"></div>
                    </div>
                  </div>
                  <div className="bg-elastic-lightGray/30 border border-elastic-border p-4 rounded-lg flex flex-col gap-2">
                    <div className="flex items-center gap-2 text-elastic-gray mb-1">
                      <Shield className="h-4 w-4 text-emerald-500" />
                      <span className="text-xs font-bold uppercase tracking-wide">Confidence</span>
                    </div>
                    <div className="flex items-end justify-between">
                      <span className="text-2xl font-bold text-elastic-darkGray">98%</span>
                      <span className="text-[10px] text-elastic-gray mb-1">Reliability</span>
                    </div>
                    <div className="h-1 bg-elastic-border rounded-full overflow-hidden">
                      <div className="h-full bg-emerald-500 w-[98%]"></div>
                    </div>
                  </div>
                </div>

                {/* Categories */}
                <div>
                  <h4 className="text-[10px] font-bold text-elastic-gray uppercase tracking-widest mb-3">Monitoring Systems</h4>
                  <div className="space-y-2">
                    {[
                      { name: 'Statistical Metrics (3σ)', icon: Activity, active: status?.monitoring.metrics, color: 'text-elastic-blue' },
                      { name: 'GitHub Integration', icon: GitCommit, active: status?.monitoring.github, color: 'text-blue-500' },
                      { name: 'Jira Action Tracking', icon: Ticket, active: status?.monitoring.jira, color: 'text-sky-500' },
                      { name: 'Slack Alerts Channel', icon: MessageSquare, active: status?.monitoring.slack, color: 'text-purple-500' },
                      { name: 'AI Agent Actions', icon: Bell, active: status?.monitoring.agent, color: 'text-amber-500' },
                    ].map((sys, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-elastic-lightGray/20 border border-elastic-border rounded-lg">
                        <div className="flex items-center gap-3">
                          <sys.icon className={`h-4 w-4 ${sys.color}`} />
                          <span className="text-xs font-medium text-elastic-darkGray">{sys.name}</span>
                        </div>
                        <div className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${sys.active ? 'bg-emerald-100 text-emerald-700' : 'bg-elastic-lightGray text-elastic-gray'}`}>
                          {sys.active ? 'ACTIVE' : 'OFFLINE'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Recent Anomalies */}
                {status?.recent_anomalies && status.recent_anomalies.length > 0 && (
                  <div>
                    <h4 className="text-[10px] font-bold text-elastic-gray uppercase tracking-widest mb-3 flex items-center gap-2">
                      <AlertTriangle className="h-3 w-3 text-red-500" />
                      Recent Critical Anomalies
                    </h4>
                    <div className="space-y-2">
                      {status.recent_anomalies.slice(0, 3).map((anomaly, index) => (
                        <div key={index} className="p-3 bg-red-50 border border-red-100 rounded-lg group hover:bg-red-100 transition-colors cursor-default">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-bold text-elastic-darkGray">{anomaly?.service || 'Unknown'}</span>
                            <span className="text-[10px] text-elastic-gray font-mono">
                              {new Date(anomaly?.['@timestamp'] || anomaly?.detected_at || Date.now()).toLocaleTimeString()}
                            </span>
                          </div>
                          <div className="text-[11px] text-elastic-gray">
                            {anomaly?.metric}: <span className="text-red-600 font-bold">{anomaly?.value || anomaly?.current_value || 0}</span>
                            <span className="mx-2 opacity-50">•</span>
                            Dev: <span className="text-red-600">{((anomaly?.sigma_deviation as number) || 0).toFixed(1)}σ</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'workflows' && (
              <div className="space-y-4">
                {status?.pending_workflows && status.pending_workflows.length > 0 ? (
                  status.pending_workflows.map((workflow) => (
                    <div key={workflow.id} className="bg-white border border-elastic-blue/30 rounded-lg overflow-hidden shadow-sm">
                      <div className="p-4 bg-elastic-lightBlue/20 border-b border-elastic-blue/10 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Clock className="h-4 w-4 text-elastic-blue" />
                          <span className="text-xs font-bold text-elastic-darkBlue uppercase tracking-tight">Pending Approval</span>
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${workflow.anomaly.severity === 'Sev-1' ? 'bg-red-600 text-white' : 'bg-amber-500 text-white'
                          }`}>
                          {workflow.anomaly.severity}
                        </span>
                      </div>
                      <div className="p-4">
                        <div className="mb-3">
                          <p className="text-sm font-bold text-elastic-darkGray mb-1">{workflow.anomaly.service}.{workflow.anomaly.metric}</p>
                          <p className="text-xs text-elastic-gray leading-relaxed">
                            Detected a <span className="text-elastic-blue font-bold">{((workflow.anomaly?.sigma_deviation as number) || 0).toFixed(1)}σ</span> statistical deviation.
                            The engine proposes an autonomous response workflow.
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-1.5 mb-4">
                          {workflow.actions.map((action, i) => (
                            <span key={i} className="text-[10px] bg-elastic-lightGray text-elastic-gray px-2 py-0.5 rounded-md border border-elastic-border">
                              {action.replace(/_/g, ' ')}
                            </span>
                          ))}
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => approveWorkflow(workflow.id, true)}
                            className="flex-1 bg-elastic-blue hover:bg-elastic-darkBlue text-white text-xs font-bold py-2.5 rounded-lg transition-all shadow-sm"
                          >
                            Execute Workflow
                          </button>
                          <button
                            onClick={() => approveWorkflow(workflow.id, false)}
                            className="px-4 bg-elastic-lightGray hover:bg-elastic-border text-elastic-gray text-xs font-bold py-2.5 rounded-lg transition-all"
                          >
                            Ignore
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="flex flex-col items-center justify-center py-20 text-center">
                    <div className="p-4 bg-elastic-lightGray/50 rounded-full mb-4">
                      <CheckCircle className="h-10 w-10 text-elastic-gray" />
                    </div>
                    <h5 className="text-elastic-darkGray font-bold mb-1">All Systems Green</h5>
                    <p className="text-xs text-elastic-gray">No workflows currently awaiting approval.</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'log' && (
              <div className="space-y-2">
                {allActivity.length > 0 ? (
                  allActivity.map((event, index) => (
                    <div key={index} className="p-3 bg-white border border-elastic-border rounded-lg group hover:border-elastic-blue/50 transition-all shadow-sm">
                      <div className="flex items-start gap-3">
                        <div className={`mt-1 p-1.5 rounded-md ${event.category === 'github' ? 'bg-blue-100 text-blue-600' :
                          event.category === 'jira' ? 'bg-sky-100 text-sky-600' :
                            event.category === 'slack' ? 'bg-purple-100 text-purple-600' :
                              'bg-amber-100 text-amber-600'
                          }`}>
                          {event.category === 'github' ? <GitCommit className="h-3 w-3" /> :
                            event.category === 'jira' ? <Ticket className="h-3 w-3" /> :
                              event.category === 'slack' ? <MessageSquare className="h-3 w-3" /> :
                                <Zap className="h-3 w-3" />
                          }
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-0.5">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-elastic-gray">{event.category}</span>
                            <span className="text-[10px] text-elastic-gray font-mono">
                              {new Date(event.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                          <p className="text-xs text-elastic-darkGray line-clamp-2 leading-relaxed">
                            {event.summary || event.message || event.title}
                          </p>
                          {event.url && (
                            <a
                              href={event.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 mt-2 text-[10px] text-elastic-blue font-bold hover:underline"
                            >
                              View Details <ExternalLink className="h-2 w-2" />
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="flex flex-col items-center justify-center py-20 text-center opacity-50">
                    <Clock className="h-10 w-10 text-elastic-gray mb-4" />
                    <p className="text-xs text-elastic-gray">No activity recorded yet.</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer Stats */}
          <div className="px-5 py-3 bg-elastic-lightGray/30 border-t border-elastic-border flex items-center justify-between text-[10px] font-mono text-elastic-gray">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-elastic-blue animate-pulse"></span>
                POLLING: {status?.check_interval_seconds}S
              </span>
              <span>SIGMA: {status?.anomaly_threshold_sigma}</span>
            </div>
            <span>LAST CHECK: {status?.last_check ? new Date(status.last_check).toLocaleTimeString() : 'N/A'}</span>
          </div>
        </div>
      )}
    </div>
  );
}
