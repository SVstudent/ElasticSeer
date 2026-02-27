import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Shield, Activity, GitPullRequest, MessageSquare, Ticket,
  AlertTriangle, CheckCircle, Zap, ArrowRight, Bot,
  Radio, Clock, TrendingUp, Server, GitCommit, ChevronRight
} from 'lucide-react';
import api from '../lib/api';

interface Stats {
  total_incidents: number;
  active_incidents: number;
  resolved_incidents: number;
  sev1_count: number;
  anomalies_24h: number;
  autonomous_actions: number;
  mean_response_seconds: number;
  uptime_percent: number;
  services_monitored: number;
  integrations_active: number;
  github_prs: number;
  slack_alerts: number;
  jira_tickets: number;
  recent_actions: any[];
}

function AnimatedCounter({ target, duration = 1500, suffix = '' }: { target: number; duration?: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (target === 0) return;
    let start = 0;
    const increment = target / (duration / 16);
    const timer = setInterval(() => {
      start += increment;
      if (start >= target) {
        setCount(target);
        clearInterval(timer);
      } else {
        setCount(Math.floor(start));
      }
    }, 16);
    return () => clearInterval(timer);
  }, [target, duration]);
  return <>{count}{suffix}</>;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Stats | null>(null);
  const [observerStatus, setObserverStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, observerRes] = await Promise.allSettled([
          api.get('/api/stats/overview'),
          api.get('/api/observer/status'),
        ]);
        if (statsRes.status === 'fulfilled') setStats(statsRes.value.data);
        if (observerRes.status === 'fulfilled') setObserverStatus(observerRes.value.data);
      } catch (e) {
        console.error('Dashboard fetch error:', e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const integrations = [
    { name: 'Elasticsearch', icon: Server, status: true, color: 'text-yellow-500', bg: 'bg-yellow-50', desc: 'Search & Analytics' },
    { name: 'GitHub', icon: GitCommit, status: true, color: 'text-gray-800', bg: 'bg-gray-50', desc: 'PRs & Code Sync' },
    { name: 'Slack', icon: MessageSquare, status: true, color: 'text-purple-500', bg: 'bg-purple-50', desc: 'Team Alerts' },
    { name: 'Jira', icon: Ticket, status: true, color: 'text-blue-500', bg: 'bg-blue-50', desc: 'Ticket Tracking' },
  ];

  const getActionIcon = (type: string) => {
    if (type?.includes('github') || type?.includes('pr')) return <GitPullRequest className="h-3 w-3" />;
    if (type?.includes('slack')) return <MessageSquare className="h-3 w-3" />;
    if (type?.includes('jira')) return <Ticket className="h-3 w-3" />;
    return <Zap className="h-3 w-3" />;
  };

  const getActionColor = (type: string) => {
    if (type?.includes('github') || type?.includes('pr')) return 'text-gray-700 bg-gray-100';
    if (type?.includes('slack')) return 'text-purple-600 bg-purple-100';
    if (type?.includes('jira')) return 'text-blue-600 bg-blue-100';
    return 'text-amber-600 bg-amber-100';
  };

  return (
    <div className="min-h-screen bg-elastic-lightGray">
      {/* Hero Section */}
      <div className="relative overflow-hidden bg-gradient-to-br from-[#003B64] via-[#0077CC] to-[#00BFB3] animate-gradient">
        {/* Subtle grid overlay */}
        <div className="absolute inset-0 opacity-[0.07]" style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)`,
          backgroundSize: '40px 40px'
        }} />

        <div className="relative max-w-7xl mx-auto px-6 py-16 flex items-center justify-between">
          <div className="animate-fade-in-up">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-white/15 backdrop-blur-sm rounded-xl border border-white/20">
                <Shield className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold text-white tracking-tight">ElasticSeer</h1>
                <p className="text-blue-100 text-sm font-medium tracking-wide">Autonomous Incident Response Platform</p>
              </div>
            </div>
            <p className="text-blue-100/80 text-lg max-w-xl mt-2 leading-relaxed">
              From detection to fix in <span className="text-white font-bold">30 seconds</span>.
              Multi-agent system that detects anomalies, reasons through incidents, and autonomously remediates — creating PRs, Slack alerts, and Jira tickets.
            </p>
            <div className="flex items-center gap-4 mt-8">
              <button
                onClick={() => navigate('/chat')}
                className="flex items-center gap-2 px-6 py-3 bg-white text-[#0077CC] font-bold rounded-lg hover:bg-blue-50 transition-all shadow-lg shadow-black/10 group"
              >
                <Bot className="h-5 w-5" />
                Start Agent Chat
                <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </button>
              <div className="flex items-center gap-2 px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-lg text-white text-sm">
                <Radio className="h-4 w-4 animate-pulse" />
                <span className="font-medium">
                  {observerStatus?.status === 'running' ? 'Observer Active' : 'Observer Standby'}
                </span>
              </div>
            </div>
          </div>

          {/* Right side: live stats mini-cluster */}
          <div className="hidden lg:flex flex-col gap-3 animate-fade-in-up delay-300" style={{ opacity: 0 }}>
            <div className="bg-white/10 backdrop-blur-sm border border-white/15 rounded-xl px-6 py-4 text-center min-w-[180px]">
              <div className="text-3xl font-bold text-white">
                {stats ? <AnimatedCounter target={stats.total_incidents} /> : '—'}
              </div>
              <div className="text-blue-200 text-xs font-bold uppercase tracking-widest mt-1">Total Incidents</div>
            </div>
            <div className="bg-white/10 backdrop-blur-sm border border-white/15 rounded-xl px-6 py-4 text-center">
              <div className="text-3xl font-bold text-emerald-300">
                {stats ? <><AnimatedCounter target={stats.uptime_percent} suffix="%" /></> : '—'}
              </div>
              <div className="text-blue-200 text-xs font-bold uppercase tracking-widest mt-1">Uptime</div>
            </div>
            <div className="bg-white/10 backdrop-blur-sm border border-white/15 rounded-xl px-6 py-4 text-center">
              <div className="text-3xl font-bold text-amber-300">
                {stats ? <><AnimatedCounter target={stats.mean_response_seconds} suffix="s" /></> : '—'}
              </div>
              <div className="text-blue-200 text-xs font-bold uppercase tracking-widest mt-1">Mean Response</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="max-w-7xl mx-auto px-6 -mt-8 pb-12">
        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Active Incidents', value: stats?.active_incidents ?? 0, icon: AlertTriangle, color: 'text-red-500', bg: 'bg-red-50', ring: 'ring-red-100' },
            { label: 'Resolved', value: stats?.resolved_incidents ?? 0, icon: CheckCircle, color: 'text-emerald-500', bg: 'bg-emerald-50', ring: 'ring-emerald-100' },
            { label: 'Anomalies (24h)', value: stats?.anomalies_24h ?? 0, icon: Activity, color: 'text-amber-500', bg: 'bg-amber-50', ring: 'ring-amber-100' },
            { label: 'Sev-1 Critical', value: stats?.sev1_count ?? 0, icon: Zap, color: 'text-red-600', bg: 'bg-red-50', ring: 'ring-red-100' },
          ].map((kpi, i) => (
            <div
              key={kpi.label}
              className={`bg-white rounded-xl border border-elastic-border shadow-sm p-5 animate-fade-in-up delay-${(i + 1) * 100}`}
              style={{ opacity: 0 }}
            >
              <div className="flex items-center justify-between mb-3">
                <div className={`p-2 rounded-lg ${kpi.bg} ring-1 ${kpi.ring}`}>
                  <kpi.icon className={`h-5 w-5 ${kpi.color}`} />
                </div>
                <span className="text-3xl font-bold text-elastic-darkGray">
                  {loading ? '—' : <AnimatedCounter target={kpi.value} />}
                </span>
              </div>
              <p className="text-xs font-bold text-elastic-gray uppercase tracking-wider">{kpi.label}</p>
            </div>
          ))}
        </div>

        {/* Two Column: Integrations + Activity Feed */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Integrations & System Topology */}
          <div className="lg:col-span-1 space-y-6">
            {/* Connected Systems */}
            <div className="bg-white rounded-xl border border-elastic-border shadow-sm p-5 animate-fade-in-up delay-300" style={{ opacity: 0 }}>
              <h3 className="text-xs font-bold text-elastic-gray uppercase tracking-widest mb-4 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-elastic-blue" />
                Connected Systems
              </h3>
              <div className="space-y-3">
                {integrations.map((int) => (
                  <div key={int.name} className="flex items-center justify-between p-3 bg-elastic-lightGray/30 border border-elastic-border rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${int.bg}`}>
                        <int.icon className={`h-4 w-4 ${int.color}`} />
                      </div>
                      <div>
                        <span className="text-sm font-semibold text-elastic-darkGray">{int.name}</span>
                        <p className="text-[10px] text-elastic-gray">{int.desc}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-glow-ring"></span>
                      <span className="text-[10px] font-bold text-emerald-600">LIVE</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Agent Capabilities */}
            <div className="bg-white rounded-xl border border-elastic-border shadow-sm p-5 animate-fade-in-up delay-400" style={{ opacity: 0 }}>
              <h3 className="text-xs font-bold text-elastic-gray uppercase tracking-widest mb-4 flex items-center gap-2">
                <Bot className="h-4 w-4 text-elastic-blue" />
                Agent Capabilities
              </h3>
              <div className="space-y-2">
                {[
                  'Incident Detection & Classification',
                  'Codebase Search & Analysis',
                  'AI-Powered Code Fixes',
                  'GitHub PR Auto-Creation',
                  'Slack Team Notifications',
                  'Jira Ticket Management',
                  'Statistical Anomaly Detection (3σ)',
                  'Reasoning Trace Transparency',
                ].map((cap) => (
                  <div key={cap} className="flex items-center gap-2 text-sm text-elastic-darkGray">
                    <CheckCircle className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0" />
                    <span>{cap}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Activity Feed + Actions Stats */}
          <div className="lg:col-span-2 space-y-6">
            {/* Autonomous Actions Summary */}
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: 'GitHub PRs', value: stats?.github_prs ?? 0, icon: GitPullRequest, color: 'text-gray-700', bg: 'bg-gray-100' },
                { label: 'Slack Alerts', value: stats?.slack_alerts ?? 0, icon: MessageSquare, color: 'text-purple-600', bg: 'bg-purple-100' },
                { label: 'Jira Tickets', value: stats?.jira_tickets ?? 0, icon: Ticket, color: 'text-blue-600', bg: 'bg-blue-100' },
              ].map((action, i) => (
                <div
                  key={action.label}
                  className={`bg-white rounded-xl border border-elastic-border shadow-sm p-4 animate-fade-in-up delay-${(i + 2) * 100}`}
                  style={{ opacity: 0 }}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className={`p-2 rounded-lg ${action.bg}`}>
                      <action.icon className={`h-4 w-4 ${action.color}`} />
                    </div>
                    <span className="text-2xl font-bold text-elastic-darkGray">
                      {loading ? '—' : <AnimatedCounter target={action.value} />}
                    </span>
                  </div>
                  <p className="text-[10px] font-bold text-elastic-gray uppercase tracking-wider">{action.label}</p>
                </div>
              ))}
            </div>

            {/* Recent Activity Feed */}
            <div className="bg-white rounded-xl border border-elastic-border shadow-sm p-5 animate-fade-in-up delay-500" style={{ opacity: 0 }}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-bold text-elastic-gray uppercase tracking-widest flex items-center gap-2">
                  <Clock className="h-4 w-4 text-elastic-blue" />
                  Recent Autonomous Actions
                </h3>
                <button
                  onClick={() => navigate('/chat')}
                  className="text-xs text-elastic-blue font-bold hover:underline flex items-center gap-1"
                >
                  View all in chat <ChevronRight className="h-3 w-3" />
                </button>
              </div>

              {stats?.recent_actions && stats.recent_actions.length > 0 ? (
                <div className="space-y-3">
                  {stats.recent_actions.slice(0, 8).map((action: any, i: number) => (
                    <div key={i} className="flex items-start gap-3 p-3 bg-elastic-lightGray/20 border border-elastic-border rounded-lg hover:bg-elastic-lightGray/50 transition-colors">
                      <div className={`mt-0.5 p-1.5 rounded-md ${getActionColor(action.type)}`}>
                        {getActionIcon(action.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-elastic-gray">
                            {action.type?.replace(/_/g, ' ') || 'action'}
                          </span>
                          <span className="text-[10px] text-elastic-gray font-mono">
                            {action.timestamp ? new Date(action.timestamp).toLocaleTimeString() : ''}
                          </span>
                        </div>
                        <p className="text-xs text-elastic-darkGray line-clamp-2">
                          {action.summary || action.message || action.title || 'Autonomous action executed'}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="p-4 bg-elastic-lightGray/50 rounded-full mb-4">
                    <Activity className="h-10 w-10 text-elastic-gray" />
                  </div>
                  <h5 className="text-elastic-darkGray font-bold mb-1">No Recent Activity</h5>
                  <p className="text-xs text-elastic-gray mb-4">Start the agent to begin autonomous monitoring</p>
                  <button
                    onClick={() => navigate('/chat')}
                    className="flex items-center gap-2 px-4 py-2 bg-elastic-blue text-white text-sm font-bold rounded-lg hover:bg-elastic-darkBlue transition-all"
                  >
                    <Bot className="h-4 w-4" />
                    Launch Agent
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Architecture Banner */}
        <div className="mt-8 bg-white rounded-xl border border-elastic-border shadow-sm p-6 animate-fade-in-up delay-600" style={{ opacity: 0 }}>
          <h3 className="text-xs font-bold text-elastic-gray uppercase tracking-widest mb-5 text-center">Multi-Agent Architecture</h3>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            {[
              { label: 'Anomaly Detection', sublabel: 'Observer Engine', icon: Shield, color: 'bg-indigo-50 text-indigo-600 border-indigo-200' },
              { label: '', sublabel: '', icon: ChevronRight, color: 'text-elastic-gray', isArrow: true },
              { label: 'Reasoning', sublabel: 'Gemini AI', icon: Zap, color: 'bg-amber-50 text-amber-600 border-amber-200' },
              { label: '', sublabel: '', icon: ChevronRight, color: 'text-elastic-gray', isArrow: true },
              { label: 'Code Analysis', sublabel: 'Elasticsearch', icon: Activity, color: 'bg-yellow-50 text-yellow-600 border-yellow-200' },
              { label: '', sublabel: '', icon: ChevronRight, color: 'text-elastic-gray', isArrow: true },
              { label: 'Remediation', sublabel: 'GitHub + Slack + Jira', icon: GitPullRequest, color: 'bg-emerald-50 text-emerald-600 border-emerald-200' },
            ].map((step, i) => (
              step.isArrow ? (
                <ChevronRight key={i} className="h-5 w-5 text-elastic-border hidden sm:block" />
              ) : (
                <div key={i} className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${step.color}`}>
                  <step.icon className="h-5 w-5" />
                  <div>
                    <div className="text-xs font-bold">{step.label}</div>
                    <div className="text-[10px] opacity-70">{step.sublabel}</div>
                  </div>
                </div>
              )
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
