import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserProvider } from 'ethers';
import {
  Activity, ArrowUpRight, BadgeCheck, BarChart3, BriefcaseBusiness, Check,
  ChevronRight, CircleDollarSign, ClipboardCheck, Cloud, Copy, FileAudio,
  FileCode2, FileImage, FileText, Fingerprint, Globe2, LayoutDashboard,
  Link2, Loader2, LockKeyhole, Menu, MessageSquare, Network, Plus, RefreshCw,
  Search, ShieldCheck, Sparkles, Target, UserRound, Users, Wallet, X, Zap
} from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import {
  CHAIN_ID, ESCROW_ADDRESS, connectWallet, ensurePolygonAmoy,
  getConnectedAccount, getEscrowContract, getProvider, parseEther, switchWallet, transactionUrl
} from './services/web3';
import './styles.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const EXPLORER = 'https://amoy.polygonscan.com/tx/';
const IPFS_GATEWAY = 'https://ipfs.io/ipfs/';
const ZERO = '0x0000000000000000000000000000000000000000';
const FALLBACK_FREELANCER = '0xaEBe5A9fba82dd863628EdF77d0C49533C797466';

const statusMap = {
  0: { label: 'Open', tone: 'blue', icon: 'OPEN' },
  1: { label: 'Assigned', tone: 'violet', icon: 'ASSIGNED' },
  2: { label: 'AI Verification', tone: 'amber', icon: 'AI' },
  3: { label: 'Released', tone: 'green', icon: 'RELEASED' },
  4: { label: 'Held', tone: 'red', icon: 'HELD' },
  5: { label: 'Refunded', tone: 'slate', icon: 'REFUNDED' },
};

const sampleChart = [
  { day: 'Mon', score: 62 }, { day: 'Tue', score: 70 }, { day: 'Wed', score: 68 },
  { day: 'Thu', score: 82 }, { day: 'Fri', score: 76 }, { day: 'Sat', score: 91 }, { day: 'Sun', score: 86 },
];

function shortAddress(value = '') {
  if (!value) return '—';
  return `${value.slice(0, 6)}…${value.slice(-4)}`;
}
function copyText(text) { navigator.clipboard?.writeText(text); }
function statusInfo(status) { return statusMap[Number(status)] || statusMap[0]; }
function formatPol(value) { const n = Number(value || 0); return Number.isFinite(n) ? n.toFixed(4).replace(/0+$/, '').replace(/\.$/, '') : '0'; }
function fileIcon(type) {
  return type === 'code' ? FileCode2 : type === 'image' ? FileImage : type === 'audio' ? FileAudio : FileText;
}

function normalizeErrorMessage(data, fallback) {
  const detail = data?.detail;
  if (Array.isArray(detail)) {
    return detail
      .map(item => typeof item === 'string' ? item : item?.msg || item?.message || JSON.stringify(item))
      .join('; ');
  }
  if (typeof detail === 'string') return detail;
  if (typeof data?.message === 'string') return data.message;
  return fallback;
}

async function api(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 45000);
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, { ...options, signal: controller.signal });
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('Request timed out. Check that the backend and blockchain RPC are running.');
    throw error;
  } finally {
    clearTimeout(timeout);
  }
  let data = {};
  try { data = await res.json(); } catch { /* empty */ }
  if (!res.ok) throw new Error(normalizeErrorMessage(data, `Request failed (${res.status})`));
  return data;
}

function App() {
  const [page, setPage] = useState('dashboard');
  const [mobileOpen, setMobileOpen] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [backendOnline, setBackendOnline] = useState(false);
  const [clientWallet, setClientWallet] = useState('');
  const [freelancerWallet, setFreelancerWallet] = useState(FALLBACK_FREELANCER);
  const [connectedWallet, setConnectedWallet] = useState('');
  const [role, setRole] = useState('');
  const [toast, setToast] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [reputation, setReputation] = useState(null);
  const [statusJobId, setStatusJobId] = useState('');
  const jobsRequest = useRef(null);
  const toastTimer = useRef(null);

  const notify = (type, message) => {
    setToast({ type, message });
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 4500);
  };

  const loadJobs = async (refresh = false, silent = false) => {
    if (jobsRequest.current) return jobsRequest.current;

    const request = (async () => {
      setLoadingJobs(true);
      try {
        const data = await api(`/api/jobs/${refresh ? '?refresh=true' : ''}`);
        const list = data.jobs || [];
        setJobs(list);
        setBackendOnline(true);
        const assigned = list.find(j => j.freelancer && j.freelancer !== ZERO);
        if (assigned) setFreelancerWallet(assigned.freelancer);
      } catch (e) {
        setBackendOnline(false);
        if (!silent) notify('error', `Backend unavailable: ${e.message}`);
      } finally { setLoadingJobs(false); }
    })();

    jobsRequest.current = request;
    try {
      return await request;
    } finally {
      if (jobsRequest.current === request) jobsRequest.current = null;
    }
  };

  useEffect(() => { loadJobs(); }, []);

  useEffect(() => {
    if (page !== 'verify') return undefined;
    const refreshTimer = setInterval(() => { void loadJobs(false, true); }, 30000);
    return () => clearInterval(refreshTimer);
  }, [page]);

  useEffect(() => {
    if (!selectedJob) return;
    const latest = jobs.find(job => job.id === selectedJob.id);
    setSelectedJob(latest || null);
  }, [jobs]);

  useEffect(() => {
    api('/api/jobs/status/test').then(d => {
      setClientWallet(d.client_wallet || '');
      setBackendOnline(true);
    }).catch(() => setBackendOnline(false));
  }, []);

  useEffect(() => {
    if (!window.ethereum) return undefined;
    const handleAccounts = accounts => setConnectedWallet(accounts[0] || '');
    const handleChain = () => { void getConnectedAccount().then(setConnectedWallet).catch(() => setConnectedWallet('')); };
    window.ethereum.on('accountsChanged', handleAccounts);
    window.ethereum.on('chainChanged', handleChain);
    void getConnectedAccount().then(setConnectedWallet).catch(() => {});
    return () => {
      window.ethereum.removeListener('accountsChanged', handleAccounts);
      window.ethereum.removeListener('chainChanged', handleChain);
    };
  }, []);

  const connectMetaMask = async () => {
    try {
      const account = await connectWallet();
      setConnectedWallet(account);
      notify('success', `MetaMask connected: ${shortAddress(account)}`);
    } catch (e) { notify('error', e.message || 'Wallet connection failed.'); }
  };

  const switchMetaMask = async () => {
    try {
      const account = await switchWallet();
      setConnectedWallet(account);
      notify('success', `Active MetaMask account: ${shortAddress(account)}`);
    } catch (e) { notify('error', e.message || 'Account switch was cancelled.'); }
  };

  const disconnectWallet = () => setConnectedWallet('');

  const openJob = async (id) => {
    setSelectedJob(null);
    try {
      const data = await api(`/api/jobs/${id}`);
      setSelectedJob(data.job);
      setPage('job');
    } catch (e) { notify('error', e.message); }
  };

  const loadReputation = async (address) => {
    if (!address) return;
    setReputation(null);
    try { setReputation(await api(`/api/reputation/${address}`)); }
    catch (e) { notify('error', e.message); }
  };

  const stats = useMemo(() => {
    const completed = jobs.filter(j => Number(j.status) === 3).length;
    const verified = jobs.filter(j => [2, 3, 4].includes(Number(j.status))).length;
    const released = jobs.filter(j => Number(j.status) === 3).length;
    const value = jobs.reduce((sum, j) => sum + Number(j.amount_pol || 0), 0);
    return { total: jobs.length, completed, verified, released, value };
  }, [jobs]);

  const nav = [
    ['dashboard', 'Overview', LayoutDashboard],
    ['jobs', 'Jobs Marketplace', BriefcaseBusiness],
    ['create', 'Create Job', Plus],
    ['assign', 'Assign Freelancer', Users],
    ['submit', 'Submit Work', ClipboardCheck],
    ['verify', 'AI Verification', Sparkles],
    ['reputation', 'Reputation', BadgeCheck],
    ['status', 'Job Explorer', Search],
  ];

  const navigate = (next) => { setPage(next); setMobileOpen(false); };

  if (!role) return <PortalSelection selectRole={setRole} connect={connectMetaMask} />;

  const clientNav = [
    ['dashboard', 'Dashboard', LayoutDashboard], ['create', 'Create Job', Plus],
    ['jobs', 'My Jobs', BriefcaseBusiness], ['assign', 'Assign Freelancer', Users],
    ['status', 'Transactions', Activity],
  ];
  const freelancerNav = [
    ['dashboard', 'Dashboard', LayoutDashboard], ['jobs', 'Available Jobs', BriefcaseBusiness],
    ['submit', 'Submit Work', ClipboardCheck], ['verify', 'AI Verification', Sparkles],
    ['reputation', 'Reputation', BadgeCheck],
  ];
  const activeNav = role === 'client' ? clientNav : freelancerNav;

  return <div className="app-shell">
    <Sidebar page={page} nav={activeNav} navigate={navigate} mobileOpen={mobileOpen} close={() => setMobileOpen(false)} role={role} />
    <main className="main-shell">
      <Topbar page={page} role={role} setRole={nextRole => { setRole(nextRole); setPage('dashboard'); }} connectedWallet={connectedWallet} connectMetaMask={connectMetaMask} switchMetaMask={switchMetaMask} disconnectWallet={disconnectWallet} onMenu={() => setMobileOpen(true)} />
      <div className="page-wrap">
        {page === 'dashboard' && <Dashboard role={role} jobs={jobs} stats={stats} loading={loadingJobs} openJob={openJob} loadJobs={loadJobs} navigate={navigate} clientWallet={clientWallet} freelancerWallet={freelancerWallet} chart={sampleChart} />}
        {page === 'jobs' && <JobsPage jobs={jobs} loading={loadingJobs} openJob={openJob} loadJobs={loadJobs} />}
        {role === 'client' && page === 'create' && <CreateJob notify={notify} onDone={() => { navigate('assign'); void loadJobs(true); }} expectedWallet={connectedWallet} />}
        {role === 'client' && page === 'assign' && <AssignFreelancer jobs={jobs} notify={notify} onDone={() => { void loadJobs(true); }} expectedWallet={connectedWallet} defaultWallet={freelancerWallet} />}
        {role === 'freelancer' && page === 'submit' && <SubmitWork jobs={jobs} notify={notify} onDone={() => { navigate('verify'); void loadJobs(true); }} expectedWallet={connectedWallet} />}
        {role === 'freelancer' && page === 'verify' && <VerificationCenter jobs={jobs} openJob={openJob} />}
        {role === 'freelancer' && page === 'reputation' && <ReputationPage wallet={freelancerWallet} setWallet={setFreelancerWallet} reputation={reputation} loadReputation={loadReputation} connectedWallet={connectedWallet} />}
        {role === 'client' && page === 'status' && <StatusExplorer initialId={statusJobId} setInitialId={setStatusJobId} notify={notify} openJob={openJob} />}
        {page === 'job' && <JobDetail job={selectedJob} notify={notify} back={() => navigate('jobs')} />}
      </div>
      <Footer backendOnline={backendOnline} />
    </main>
    {toast && <Toast {...toast} close={() => setToast(null)} />}
  </div>;
}

function PortalSelection({ selectRole, connect }) {
  return <main className="portal-selection"><div className="portal-mark"><ShieldCheck size={32}/></div><div className="hero-kicker">TRUSTLANCE PROTOCOL</div><h1>Choose your workspace</h1><p>Use a dedicated portal for client escrow or freelancer delivery.</p><div className="portal-grid"><button className="portal-card" onClick={() => selectRole('client')}><CircleDollarSign size={28}/><strong>Client Portal</strong><span>Create, fund, and assign escrow jobs.</span></button><button className="portal-card" onClick={() => selectRole('freelancer')}><BriefcaseBusiness size={28}/><strong>Freelancer Portal</strong><span>View assignments, submit work, and track reputation.</span></button></div><button className="connect-btn" onClick={connect}><Wallet size={17}/> Connect MetaMask</button></main>;
}

function TransactionStatus({ operation, status, hash }) {
  const label = status === 'waiting' ? 'Waiting for MetaMask confirmation...' : status === 'confirming' ? 'Transaction submitted. Confirming...' : 'Transaction confirmed';
  return <section className={`transaction-status ${status}`}><div className="panel-title">{operation}</div><span>{label}</span>{hash&&<a href={transactionUrl(hash)} target="_blank" rel="noreferrer">View on PolygonScan <ArrowUpRight size={14}/></a>}</section>;
}

function Sidebar({ page, nav, navigate, mobileOpen, close }) {
  return <>
    {mobileOpen && <div className="mobile-overlay" onClick={close} />}
    <aside className={`sidebar ${mobileOpen ? 'mobile-show' : ''}`}>
      <div className="brand-row"><div className="brand-mark"><ShieldCheck size={22}/></div><div><div className="brand">Trustlance</div><div className="brand-sub">AI • ESCROW • REPUTATION</div></div><button className="icon-btn mobile-close" onClick={close}><X size={19}/></button></div>
      <div className="network-chip"><span className="pulse-dot"/> Polygon Amoy <span className="chain-id">80002</span></div>
      <div className="nav-label">WORKSPACE</div>
      <nav>{nav.map(([key, label, Icon]) => <button key={key} className={`nav-item ${page === key ? 'active' : ''}`} onClick={() => navigate(key)}><Icon size={18}/><span>{label}</span>{page === key && <ChevronRight className="nav-arrow" size={16}/>}</button>)}</nav>
      <div className="sidebar-bottom">
        <div className="security-mini"><LockKeyhole size={17}/><div><strong>AI-gated escrow</strong><span>Funds release from oracle score</span></div></div>
        <div className="sidebar-version">Trustlance v2 • Polygon testnet</div>
      </div>
    </aside>
  </>;
}

function Topbar({ page, role, setRole, connectedWallet, connectMetaMask, switchMetaMask, disconnectWallet, onMenu }) {
  const title = { dashboard: 'Command Center', jobs: 'Jobs Marketplace', create: 'Create a Job', assign: 'Assign Freelancer', submit: 'Submit Work', verify: 'AI Verification', reputation: 'Portable Reputation', status: 'Job Explorer', job: 'Job Details' }[page] || 'Trustlance';
  return <header className="topbar"><button className="icon-btn menu-btn" onClick={onMenu}><Menu size={21}/></button><div><div className="eyebrow">TRUSTLANCE / {page.toUpperCase()}</div><h1>{title}</h1></div><div className="top-actions"><div className="role-switch"><button className={role === 'client' ? 'selected' : ''} onClick={() => setRole('client')}><UserRound size={15}/> Client</button><button className={role === 'freelancer' ? 'selected' : ''} onClick={() => setRole('freelancer')}><BriefcaseBusiness size={15}/> Freelancer</button></div>{connectedWallet ? <><button className="wallet-connected" onClick={switchMetaMask} title="Choose another active MetaMask account"><span className="wallet-dot"/>{shortAddress(connectedWallet)} · Switch</button><button className="soft-btn" onClick={disconnectWallet}>Disconnect</button></> : <button className="connect-btn" onClick={connectMetaMask}><Wallet size={17}/> Connect MetaMask</button>}</div></header>;
}

function Dashboard({ role, jobs, stats, loading, openJob, loadJobs, navigate, clientWallet, freelancerWallet, chart }) {
  const recent = jobs.slice(0, 5);
  return <div className="content-stack">
    <section className="hero-panel"><div className="hero-copy"><div className="hero-kicker"><Sparkles size={14}/> {role === 'client' ? 'CLIENT PORTAL' : 'FREELANCER PORTAL'}</div><h2>Freelance work, verified before the money moves.</h2><p>AI compliance scoring + IPFS evidence + blockchain escrow + on-chain reputation — presented in one transparent workflow.</p><div className="hero-buttons">{role === 'client' ? <button className="primary-btn" onClick={() => navigate('create')}><Plus size={17}/> Create & Fund Job</button> : <button className="primary-btn" onClick={() => navigate('jobs')}><BriefcaseBusiness size={17}/> Assigned Jobs</button>}<button className="ghost-btn" onClick={() => navigate('jobs')}>Explore Jobs <ArrowUpRight size={16}/></button></div></div><div className="hero-orbit"><div className="orbit-ring r1"/><div className="orbit-ring r2"/><div className="orbit-core"><ShieldCheck size={42}/><span>AI<br/>GATED</span></div><div className="orbit-node n1"><Fingerprint size={16}/></div><div className="orbit-node n2"><Cloud size={16}/></div><div className="orbit-node n3"><Network size={16}/></div></div></section>
    <WalletPanel clientWallet={clientWallet} freelancerWallet={freelancerWallet} />
    <section className="metric-grid">{[
      ['Jobs Created', stats.total, BriefcaseBusiness, 'All indexed jobs'], ['AI Verified', stats.verified, Sparkles, 'Submitted / scored'], ['Payments Released', stats.released, CircleDollarSign, 'Successful escrow releases'], ['Escrow Volume', `${formatPol(stats.value)} POL`, LockKeyhole, 'Indexed job value']
    ].map(([label, value, Icon, sub]) => <div className="metric-card" key={label}><div className="metric-icon"><Icon size={19}/></div><div><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-sub">{sub}</div></div></div>)}</section>
    <section className="two-col"><div className="panel chart-panel"><div className="panel-head"><div><div className="panel-title">AI score activity</div><div className="panel-sub">Illustrative trend view • live job scores below</div></div><div className="mini-stat"><Target size={15}/> 100 max</div></div><div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chart}><defs><linearGradient id="scoreFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#7c3aed" stopOpacity={0.28}/><stop offset="100%" stopColor="#7c3aed" stopOpacity={0}/></linearGradient></defs><XAxis dataKey="day" axisLine={false} tickLine={false}/><YAxis domain={[0,100]} axisLine={false} tickLine={false}/><Tooltip contentStyle={{borderRadius:12,border:'1px solid #e6eaf0'}}/><Area type="monotone" dataKey="score" stroke="#7c3aed" fill="url(#scoreFill)" strokeWidth={2.5}/></AreaChart></ResponsiveContainer></div></div>
      <div className="panel timeline-panel"><div className="panel-head"><div><div className="panel-title">Protocol lifecycle</div><div className="panel-sub">The path a successful job follows</div></div><Zap size={18}/></div><Timeline active={5}/></div></section>
    <section className="panel"><div className="panel-head"><div><div className="panel-title">Latest jobs</div><div className="panel-sub">Read directly from the existing FastAPI + blockchain flow</div></div><button className="soft-btn" onClick={loadJobs}><RefreshCw size={15}/> Refresh</button></div>{loading ? <LoadingRows/> : recent.length ? <JobTable jobs={recent} openJob={openJob}/> : <EmptyState text="No indexed jobs yet." action="Create your first job" onClick={() => navigate('create')}/>}</section>
  </div>;
}

function WalletPanel({ clientWallet, freelancerWallet }) {
  return <section className="wallet-grid"><WalletCard label="CLIENT WALLET" address={clientWallet} tone="client"/><WalletCard label="FREELANCER WALLET" address={freelancerWallet} tone="freelancer"/></section>;
}
function WalletCard({ label, address, tone }) {
  return <div className={`wallet-card ${tone}`}><div className="wallet-card-top"><div className="wallet-role"><Wallet size={16}/>{label}</div><span className="wallet-live">SERVER CONFIG</span></div><div className="wallet-address">{address || 'Connect backend / load status'}</div><div className="wallet-card-bottom"><span>Used by existing backend operation</span>{address && <button onClick={() => copyText(address)}><Copy size={14}/> Copy</button>}</div></div>;
}

function JobsPage({ jobs, loading, openJob, loadJobs }) {
  const [filter, setFilter] = useState('all');
  const [q, setQ] = useState('');
  const filtered = jobs.filter(j => (filter === 'all' || Number(j.status) === Number(filter)) && `${j.id} ${j.job_brief} ${j.submission_type}`.toLowerCase().includes(q.toLowerCase()));
  return <div className="content-stack"><section className="page-intro"><div><div className="hero-kicker"><BriefcaseBusiness size={14}/> MARKETPLACE INDEX</div><h2>Every job. Every state. One source of truth.</h2><p>Browse the same jobs exposed by <code>/api/jobs/</code>. No backend workflow was changed.</p></div><button className="soft-btn" onClick={loadJobs}><RefreshCw size={15}/> Refresh chain data</button></section><div className="filter-row"><div className="search-box"><Search size={17}/><input value={q} onChange={e => setQ(e.target.value)} placeholder="Search job, description, submission type…"/></div><div className="filter-pills">{[['all','All'],['0','Open'],['1','Assigned'],['2','AI'],['3','Released'],['4','Held']].map(([v,l]) => <button key={v} className={filter === v ? 'on' : ''} onClick={() => setFilter(v)}>{l}</button>)}</div></div><section className="panel">{loading ? <LoadingRows/> : filtered.length ? <JobTable jobs={filtered} openJob={openJob}/> : <EmptyState text="No jobs match your filters." action="Clear filters" onClick={() => {setFilter('all');setQ('')}}/>}</section></div>;
}

function JobTable({ jobs, openJob }) {
  return <div className="table-wrap"><table><thead><tr><th>JOB</th><th>STATUS</th><th>PAYMENT</th><th>AI</th><th>TYPE</th><th>FREELANCER</th><th/></tr></thead><tbody>{jobs.map(job => { const s=statusInfo(job.status); const Icon=fileIcon(job.submission_type); return <tr key={job.id}><td><div className="job-cell"><span className="job-id">#{job.id}</span><div><strong>{job.job_brief}</strong><span>Client {shortAddress(job.client)}</span></div></div></td><td><span className={`status-pill ${s.tone}`}><span/> {s.label}</span></td><td><strong>{formatPol(job.amount_pol)} POL</strong></td><td><div className="score-chip"><span>{job.ai_score || 0}</span><small>/100</small></div><div className="threshold">≥ {job.threshold}</div></td><td><span className="type-pill"><Icon size={14}/>{job.submission_type || 'pending'}</span></td><td>{job.freelancer && job.freelancer !== ZERO ? shortAddress(job.freelancer) : <span className="muted">Unassigned</span>}</td><td><button className="row-open" onClick={() => openJob(job.id)}>Open <ArrowUpRight size={14}/></button></td></tr>})}</tbody></table></div>;
}

function CreateJob({ notify, onDone, expectedWallet }) {
  const [form, setForm] = useState({ job_id: '', job_title: '', ai_threshold: 60, payment_pol: 0.01 });
  const [tx, setTx] = useState(null);
  const [busy, setBusy] = useState(false);
  const update = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const submit = async e => {
    e.preventDefault();
    const jobId = Number(form.job_id);
    const paymentPol = Number(form.payment_pol);
    const jobTitle = String(form.job_title ?? '').trim();

    if (!jobTitle || jobTitle.length < 5) {
      notify('error', 'Job title must be at least 5 characters long.');
      return;
    }
    if (!Number.isFinite(jobId) || jobId < 1) {
      notify('error', 'Enter a valid Job ID greater than 0.');
      return;
    }
    if (!Number.isFinite(paymentPol) || paymentPol <= 0) {
      notify('error', 'Payment must be greater than 0 POL.');
      return;
    }

    setBusy(true);
    try {
      if (!expectedWallet) throw new Error('Please connect MetaMask to continue.');
      await ensurePolygonAmoy();
      const contract = await getEscrowContract(expectedWallet);
      setTx({ operation: 'Create & Fund Job', status: 'waiting' });
      const transaction = await contract.createJob(jobId, jobTitle, Number(form.ai_threshold), { value: parseEther(String(paymentPol)) });
      setTx({ operation: 'Create & Fund Job', status: 'confirming', hash: transaction.hash });
      await transaction.wait();
      setTx({ operation: 'Create & Fund Job', status: 'confirmed', hash: transaction.hash });
      notify('success', `Job #${jobId} created and escrow funded.`);
      await onDone();
    } catch (e) {
      notify('error', e.message || 'Create job failed.');
    } finally {
      setBusy(false);
    }
  };
  return <div className="content-stack"><section className="page-intro"><div><div className="hero-kicker"><CircleDollarSign size={14}/> CLIENT FLOW</div><h2>Create a funded escrow job</h2><p>This form calls the existing <code>POST /api/jobs/create</code> endpoint. The backend continues to sign and submit the blockchain transaction.</p></div><div className="security-badge"><LockKeyhole size={16}/> Escrow protected</div></section><form className="form-layout" onSubmit={submit}><div className="panel form-panel"><div className="panel-title">Job configuration</div><div className="form-grid"><Field label="Job ID" hint="Unique on-chain ID"><input required type="number" min="1" value={form.job_id} onChange={e=>update('job_id',e.target.value)} placeholder="e.g. 63"/></Field><Field label="Job title / brief" hint="Minimum 5 characters"><input required value={form.job_title} onChange={e=>update('job_title',e.target.value)} placeholder="Create a landing page for a SaaS product"/></Field><Field label="Payment" hint="Escrow amount"><div className="input-suffix"><input required type="number" min="0.000001" step="0.000001" value={form.payment_pol} onChange={e=>update('payment_pol',e.target.value)}/><span>POL</span></div></Field><Field label="Submission type" hint="AI checker used after submission"><div className="type-select-grid">{['text','code','image','audio'].map(t=>{const I=fileIcon(t);return <button type="button" key={t} className="type-choice"><I size={17}/><span>{t}</span><Check size={15}/></button>})}</div></Field></div><div className="threshold-box"><div><div className="field-label">AI release threshold <strong>{form.ai_threshold}/100</strong></div><div className="field-hint">The existing smart contract releases automatically when oracle score ≥ threshold.</div></div><input className="range" type="range" min="0" max="100" value={form.ai_threshold} onChange={e=>update('ai_threshold',Number(e.target.value))}/><div className="range-labels"><span>0 • permissive</span><span>100 • strict</span></div></div><div className="wallet-note"><Wallet size={18}/><div><strong>Client signer</strong><span>The current backend wallet remains the blockchain signer. MetaMask connection is available for wallet identity/network visibility without changing backend operations.</span></div></div><button className="primary-btn wide" disabled={busy}>{busy ? <><Loader2 className="spin" size={17}/> Creating & funding…</> : <><LockKeyhole size={17}/> Create & Fund Escrow</>}</button></div><aside className="side-guide"><div className="side-guide-icon"><ShieldCheck size={24}/></div><h3>What happens next?</h3><Step n="01" title="Escrow funded" text="The backend creates the job and locks POL on-chain."/><Step n="02" title="Assign freelancer" text="Client assigns a wallet through the existing endpoint."/><Step n="03" title="Work submitted" text="Freelancer submission is uploaded to IPFS."/><Step n="04" title="AI oracle" text="The automatic oracle calculates the score and records it."/></aside></form></div>;
}

function Field({label,hint,children}){return <label className="field"><span className="field-label">{label}</span><span className="field-hint">{hint}</span>{children}</label>}
function Step({n,title,text}){return <div className="guide-step"><span>{n}</span><div><strong>{title}</strong><p>{text}</p></div></div>}

function AssignFreelancer({ jobs, notify, onDone, defaultWallet, expectedWallet }) {
  const open = jobs.filter(j => Number(j.status) === 0);
  const [jobId,setJobId]=useState(open[0]?.id||'');
  const [wallet,setWallet]=useState(defaultWallet||'');
  const [busy,setBusy]=useState(false);
  const [tx,setTx]=useState(null);
  useEffect(()=>{if(!open.some(job=>String(job.id)===String(jobId)))setJobId(open[0]?.id||'')},[jobs]);
  useEffect(()=>{if(!wallet&&defaultWallet)setWallet(defaultWallet)},[defaultWallet]);
  const submit=async e=>{e.preventDefault();if(!jobId||!wallet)return notify('error','Select a job and enter the freelancer wallet.');setBusy(true);try{if(!expectedWallet)throw new Error('Please connect MetaMask to continue.');await ensurePolygonAmoy();const contract=await getEscrowContract(expectedWallet);setTx({operation:'Assign Freelancer',status:'waiting'});const transaction=await contract.assignFreelancer(Number(jobId),wallet.trim());setTx({operation:'Assign Freelancer',status:'confirming',hash:transaction.hash});await transaction.wait();setTx({operation:'Assign Freelancer',status:'confirmed',hash:transaction.hash});notify('success',`Freelancer assigned to Job #${jobId}.`);await onDone()}catch(e){notify('error',e.message||'Assignment failed.')}finally{setBusy(false)}};
  return <div className="content-stack"><section className="page-intro"><div><div className="hero-kicker"><Users size={14}/> CLIENT FLOW</div><h2>Assign the freelancer wallet</h2><p>Uses the existing <code>POST /api/jobs/assign-freelancer</code> operation. The backend remains the blockchain signer.</p></div><div className="security-badge"><Wallet size={16}/> Wallet mapped</div></section><form className="form-layout" onSubmit={submit}><div className="panel form-panel"><div className="panel-title">Assignment details</div><div className="form-grid"><Field label="Open job" hint="Only Open jobs can be assigned"><select required value={jobId} onChange={e=>setJobId(e.target.value)}><option value="">Choose a job…</option>{open.map(j=><option key={j.id} value={j.id}>#{j.id} — {j.job_brief}</option>)}</select></Field><Field label="Freelancer wallet" hint="Must be a valid 0x wallet address"><input required value={wallet} onChange={e=>setWallet(e.target.value)} placeholder="0x…"/></Field></div><div className="wallet-preview"><div className="avatar freelancer-avatar"><BriefcaseBusiness size={18}/></div><div><span>FREELANCER WALLET</span><code>{wallet||'Enter wallet address'}</code></div>{wallet&&<button type="button" onClick={()=>copyText(wallet)}><Copy size={14}/></button>}</div><div className="wallet-note"><ShieldCheck size={18}/><div><strong>Assignment security</strong><span>The smart contract checks that only the job client can assign a freelancer. This frontend does not bypass or replace that rule.</span></div></div><button className="primary-btn wide" disabled={busy}>{busy?<><Loader2 className="spin" size={17}/> Assigning…</>:<><Users size={17}/> Assign Freelancer</>}</button></div><aside className="side-guide"><div className="side-guide-icon"><Users size={24}/></div><h3>Role hand-off</h3><Step n="01" title="Client selects job" text="Pick an Open job from the live blockchain index."/><Step n="02" title="Enter freelancer wallet" text="Use the exact public address that will receive the assignment."/><Step n="03" title="Backend submits" text="The existing FastAPI route signs assignFreelancer()."/><Step n="04" title="Freelancer submits" text="The assigned wallet can then submit work through the existing flow."/></aside></form></div>;
}

function SubmitWork({ jobs, notify, onDone, expectedWallet }) {
  const assigned = jobs.filter(j => Number(j.status) === 1); const [jobId,setJobId]=useState(assigned[0]?.id||''); const [type,setType]=useState('text'); const [file,setFile]=useState(null); const [busy,setBusy]=useState(false); const I=fileIcon(type);
  useEffect(()=>{if(!assigned.some(job=>String(job.id)===String(jobId)))setJobId(assigned[0]?.id||'')},[jobs]);
  const [cid,setCid]=useState('');
  const submit=async e=>{e.preventDefault();if(!jobId||!file)return notify('error','Select a job and choose a file.');setBusy(true);try{if(!expectedWallet)throw new Error('Please connect the freelancer wallet to continue.');const selected=assigned.find(job=>String(job.id)===String(jobId));if(!selected)throw new Error('This job is no longer assigned. Refresh the jobs list.');if(selected.freelancer.toLowerCase()!==expectedWallet.toLowerCase())throw new Error(`Switch MetaMask to the assigned freelancer wallet: ${selected.freelancer}`);const formData=new FormData();formData.append('file',file);const upload=await api('/api/submissions/upload',{method:'POST',body:formData});const submissionCid=upload.ipfs_cid;if(!submissionCid)throw new Error('IPFS upload did not return a CID.');setCid(submissionCid);await ensurePolygonAmoy();const contract=await getEscrowContract(expectedWallet);const transaction=await contract.submitWork(Number(jobId),submissionCid,type);await transaction.wait();notify('success',`Work submitted. IPFS CID: ${submissionCid}`);await onDone()}catch(e){notify('error',e.message||'Submission failed.')}finally{setBusy(false)}};
  return <div className="content-stack"><section className="page-intro"><div><div className="hero-kicker"><ClipboardCheck size={14}/> FREELANCER FLOW</div><h2>Submit work for AI verification</h2><p>Upload a single submission file. The existing backend handles IPFS upload and blockchain submission.</p></div><div className="security-badge"><Cloud size={16}/> IPFS evidence</div></section><form className="form-layout" onSubmit={submit}><div className="panel form-panel"><div className="panel-title">Submission package</div><Field label="Assigned job" hint="Only jobs currently in Assigned state can accept work"><select required value={jobId} onChange={e=>setJobId(e.target.value)}><option value="">Choose a job…</option>{assigned.map(j=><option key={j.id} value={j.id}>#{j.id} — {j.job_brief}</option>)}</select></Field><div className="field"><span className="field-label">Submission type</span><span className="field-hint">Must match the AI checker expected by the existing backend.</span><div className="type-select-grid">{['text','code','image','audio'].map(t=>{const X=fileIcon(t);return <button type="button" key={t} onClick={()=>setType(t)} className={`type-choice ${type===t?'selected':''}`}><X size={17}/><span>{t}</span>{type===t&&<Check size={15}/>}</button>})}</div></div><label className="dropzone"><input type="file" required onChange={e=>setFile(e.target.files?.[0]||null)} accept={type==='image'?'image/*':type==='audio'?'audio/*':type==='code'?'.py,.js,.java,.txt,.cpp,.c':'.txt,.md,.pdf,.doc,.docx'}/><div className="drop-icon"><I size={24}/></div><strong>{file ? file.name : 'Drop your work here'}</strong><span>{file ? `${(file.size/1024).toFixed(1)} KB ready` : 'or click to browse • type-aware file picker'}</span></label><div className="wallet-note"><Wallet size={18}/><div><strong>Freelancer wallet</strong><span>The configured backend freelancer signer must be the wallet assigned to the selected job.</span></div></div><button className="primary-btn wide" disabled={busy}>{busy?<><Loader2 className="spin" size={17}/> Uploading & submitting…</>:<><Cloud size={17}/> Submit to IPFS + Blockchain</>}</button></div><aside className="side-guide"><div className="side-guide-icon"><Fingerprint size={24}/></div><h3>Submission pipeline</h3><Step n="01" title="File validation" text="The selected type is sent exactly as the existing API expects."/><Step n="02" title="IPFS upload" text="The backend uploads the file and receives its CID."/><Step n="03" title="On-chain submit" text="The existing freelancer signer calls submitWork(job, CID, type)."/><Step n="04" title="Oracle trigger" text="WorkSubmitted is picked up by the automatic AI oracle service."/></aside></form></div>;
}

function VerificationCenter({jobs,openJob}){const active=jobs.filter(j=>Number(j.status)===2);const completed=jobs.filter(j=>[3,4].includes(Number(j.status)));return <div className="content-stack"><section className="page-intro"><div><div className="hero-kicker"><Sparkles size={14}/> AUTOMATIC ORACLE</div><h2>AI verification command center</h2><p>Monitor jobs as they move from IPFS evidence to AI score to automatic escrow decision.</p></div><div className="oracle-live"><span className="pulse-dot"/> ORACLE SERVICE READY</div></section><div className="verification-grid"><div className="panel oracle-flow"><div className="panel-title">Verification pipeline</div><div className="flow-cards">{[['01','IPFS','Submission received',Cloud],['02','AI','Checker selected',Sparkles],['03','SCORE','Relevance + duplication',Target],['04','CHAIN','recordScore()',Network],['05','ESCROW','Release / Hold',LockKeyhole]].map(([n,t,s,I],i)=><React.Fragment key={n}><div className="flow-card"><span>{n}</span><I size={21}/><strong>{t}</strong><small>{s}</small></div>{i<4&&<ChevronRight className="flow-chevron" size={17}/>}</React.Fragment>)}</div></div><div className="panel score-card"><div className="panel-title">Live decision logic</div><div className="score-visual"><div className="score-ring"><div><strong>AI</strong><span>ORACLE</span></div></div><div><div className="score-rule">score <b>≥</b> threshold</div><p>Automatic release + reputation NFT</p><div className="score-rule muted-rule">score <b>&lt;</b> threshold</div><p>Funds held for client review</p></div></div></div></div><section className="panel"><div className="panel-head"><div><div className="panel-title">Jobs awaiting verification</div><div className="panel-sub">Status 2 • Submitted • waiting for oracle</div></div></div>{active.length?<JobTable jobs={active} openJob={openJob}/>:<EmptyState text="No jobs are currently waiting for AI verification." action="Review completed jobs" onClick={()=>{}}/>}</section><section className="panel"><div className="panel-head"><div><div className="panel-title">Recent decisions</div><div className="panel-sub">Released and Held outcomes</div></div></div>{completed.length?<JobTable jobs={completed.slice(0,8)} openJob={openJob}/>:<EmptyState text="No AI decisions indexed yet."/>}</section></div>}

function ReputationPage({wallet,setWallet,reputation,loadReputation,connectedWallet}){const [input,setInput]=useState(wallet);return <div className="content-stack"><section className="page-intro"><div><div className="hero-kicker"><BadgeCheck size={14}/> REPUTATION LAYER</div><h2>Portable proof of reliable work</h2><p>Read the existing reputation endpoint and surface completed jobs, average AI score and NFT count in a presentation-ready identity card.</p></div><div className="security-badge"><LockKeyhole size={16}/> Non-transferable</div></section><section className="panel reputation-search"><div className="search-box"><Wallet size={17}/><input value={input} onChange={e=>setInput(e.target.value)} placeholder="Freelancer wallet address"/></div><button className="primary-btn" onClick={()=>{setWallet(input);loadReputation(input)}}>Load Reputation <ArrowUpRight size={16}/></button>{connectedWallet&&<button className="soft-btn" onClick={()=>{setInput(connectedWallet);setWallet(connectedWallet);loadReputation(connectedWallet)}}>Use MetaMask</button>}</section>{reputation?<><div className="reputation-hero"><div className="nft-art"><BadgeCheck size={44}/><span>TRUSTLANCE</span><small>REPUTATION</small></div><div className="rep-copy"><div className="hero-kicker">VERIFIED FREELANCER</div><h3>{shortAddress(reputation.freelancer)}</h3><div className="rep-level">{reputation.average_ai_score>=80?'Elite':'Verified Contributor'}</div><p>Reputation is earned through successful AI-verified completion and recorded on-chain by the existing smart-contract flow.</p><div className="address-line"><code>{reputation.freelancer}</code><button onClick={()=>copyText(reputation.freelancer)}><Copy size={14}/></button></div></div></div><div className="metric-grid">{[['Completed Jobs',reputation.completed_jobs,Check],['Average AI Score',`${reputation.average_ai_score}/100`,Target],['Total AI Score',reputation.total_ai_score,Sparkles],['Reputation NFTs',reputation.nft_count,BadgeCheck]].map(([l,v,I])=><div className="metric-card" key={l}><div className="metric-icon"><I size={19}/></div><div><div className="metric-label">{l}</div><div className="metric-value">{v}</div></div></div>)}</div><section className="two-col"><div className="panel"><div className="panel-title">Credential rules</div><div className="rule-list"><div><Check/><span>AI-verified completion</span></div><div><Check/><span>On-chain reputation update</span></div><div><LockKeyhole/><span>Transferable: {String(reputation.transferable ?? false)}</span></div><div><Fingerprint/><span>{reputation.nft_type || 'Reputation NFT'}</span></div></div></div><div className="panel"><div className="panel-title">Reputation interpretation</div><div className="rep-bars"><Bar label="AI quality" value={Number(reputation.average_ai_score)}/><Bar label="Completion history" value={Math.min(100,Number(reputation.completed_jobs)*10)}/><Bar label="Credential strength" value={reputation.nft_count?100:0}/></div></div></section></>:<EmptyState text="Enter a freelancer wallet to load reputation." action="Use the configured freelancer wallet" onClick={()=>{setInput(wallet);loadReputation(wallet)}}/>}</div>}
function Bar({label,value}){return <div className="bar-row"><div><span>{label}</span><b>{value}%</b></div><div className="bar"><span style={{width:`${Math.max(0,Math.min(100,value))}%`}}/></div></div>}

function StatusExplorer({initialId,setInitialId,notify,openJob}){const [job,setJob]=useState(null);const [busy,setBusy]=useState(false);const load=async()=>{if(!initialId)return notify('error','Enter a Job ID.');setBusy(true);try{const d=await api(`/api/jobs/${initialId}`);setJob(d.job)}catch(e){setJob(null);notify('error',e.message)}finally{setBusy(false)}};return <div className="content-stack"><section className="page-intro"><div><div className="hero-kicker"><Search size={14}/> ON-CHAIN JOB EXPLORER</div><h2>Inspect a job from end to end</h2><p>Search the existing backend by Job ID and inspect participants, IPFS evidence, AI score and final escrow state.</p></div></section><div className="explorer-search"><div className="search-box"><Search size={17}/><input type="number" min="1" value={initialId} onChange={e=>setInitialId(e.target.value)} placeholder="Job ID e.g. 61"/></div><button className="primary-btn" onClick={load} disabled={busy}>{busy?<Loader2 className="spin" size={17}/>:<Search size={17}/>} Check Job</button></div>{job&&<JobDetail job={job} notify={notify} back={()=>{}} compact/>}</div>}

function JobDetail({job,notify,back,compact=false}){if(!job)return <EmptyState text="No job selected." action="Go to marketplace" onClick={back}/>;const s=statusInfo(job.status);const score=Number(job.ai_score||0);const threshold=Number(job.threshold||0);return <div className="content-stack"><section className="page-intro"><div><div className="hero-kicker"><span className={`status-dot ${s.tone}`}/> JOB #{job.id} / {s.label.toUpperCase()}</div><h2>{job.job_brief}</h2><p>Transparent evidence trail across escrow, IPFS, AI oracle and reputation.</p></div>{!compact&&<button className="soft-btn" onClick={back}>← Back to jobs</button>}</section><section className="detail-top"><div className="panel decision-panel"><div className={`decision ${s.tone}`}><span>{s.label}</span><strong>{score}/100</strong></div><div className="decision-copy"><div className="panel-title">AI decision</div><p>{Number(job.status)===3?'Threshold passed — escrow release completed automatically.':Number(job.status)===4?'Threshold not met — funds remain held for client review.':Number(job.status)===2?'Submission is waiting for automatic oracle verification.':'AI score will appear after work is submitted and verified.'}</p></div><div className="score-meter"><span style={{width:`${Math.min(100,score)}%`}}/><i style={{left:`${Math.min(100,threshold)}%`}}/></div><div className="meter-labels"><span>0</span><b>Score {score}</b><span>Threshold {threshold}</span><span>100</span></div></div><div className="panel value-panel"><div className="panel-title">Escrow</div><div className="big-value">{formatPol(job.amount_pol)} <small>POL</small></div><div className="value-lines"><span><LockKeyhole size={14}/> Funds locked at creation</span><span><Network size={14}/> Polygon Amoy</span></div></div></section><section className="two-col"><div className="panel"><div className="panel-head"><div><div className="panel-title">Job lifecycle</div><div className="panel-sub">Current blockchain state: {s.label}</div></div></div><Timeline status={Number(job.status)}/></div><div className="panel"><div className="panel-title">Participants</div><div className="participant"><div className="avatar client-avatar"><UserRound size={18}/></div><div><span>CLIENT</span><code>{job.client}</code></div><button onClick={()=>copyText(job.client)}><Copy size={14}/></button></div><div className="participant"><div className="avatar freelancer-avatar"><BriefcaseBusiness size={18}/></div><div><span>FREELANCER</span><code>{job.freelancer===ZERO?'Not assigned':job.freelancer}</code></div>{job.freelancer!==ZERO&&<button onClick={()=>copyText(job.freelancer)}><Copy size={14}/></button>}</div></div></section><section className="two-col"><div className="panel"><div className="panel-title">Submission evidence</div>{job.ipfs_cid?<><div className="evidence-row"><div className="evidence-icon"><Cloud size={19}/></div><div><span>IPFS CID</span><code>{job.ipfs_cid}</code></div><button onClick={()=>copyText(job.ipfs_cid)}><Copy size={14}/></button></div><div className="evidence-actions"><span className="type-pill"><FileText size={14}/>{job.submission_type||'unknown'}</span><a className="soft-btn" href={`${IPFS_GATEWAY}${job.ipfs_cid}`} target="_blank" rel="noreferrer">View IPFS <ArrowUpRight size={14}/></a></div></>:<EmptyState text="No work submitted yet."/>}</div><div className="panel"><div className="panel-title">Blockchain evidence</div><Evidence label="Contract" value="FreelanceEscrow"/><Evidence label="Network" value="Polygon Amoy • 80002"/><Evidence label="AI threshold" value={`${threshold}/100`}/><Evidence label="Final score" value={`${score}/100`}/></div></section></div>}
function Evidence({label,value}){return <div className="evidence-line"><span>{label}</span><strong>{value}</strong></div>}

function Timeline({status,active}){const n=active ?? (status===0?1:status===1?2:status===2?4:5);const steps=[['Created',FileText],['Assigned',Users],['Submitted',Cloud],['AI Verified',Sparkles],['Released / Held',LockKeyhole]];return <div className="timeline">{steps.map(([label,I],i)=><div className={`timeline-step ${i+1<=n?'done':''}`} key={label}><div className="timeline-icon"><I size={15}/>{i+1<n&&<span className="timeline-check"><Check size={9}/></span>}</div><span>{label}</span>{i<steps.length-1&&<div className={`timeline-line ${i+1<n?'done':''}`}/>}</div>)}</div>}
function LoadingRows(){return <div className="loading-list">{[1,2,3,4].map(i=><div className="skeleton-row" key={i}><span/><div><i/><i/></div><b/></div>)}</div>}
function EmptyState({text,action,onClick}){return <div className="empty-state"><div className="empty-icon"><Search size={21}/></div><strong>{text}</strong>{action&&<button className="soft-btn" onClick={onClick}>{action}</button>}</div>}
function Toast({type,message,close}){return <div className={`toast ${type}`}><div className="toast-icon">{type==='success'?<Check size={17}/>:<X size={17}/>}</div><span>{message}</span><button onClick={close}><X size={15}/></button></div>}
function Footer({backendOnline}){return <footer><span>Trustlance • AI-Verified Decentralized Freelance Marketplace</span><span className="footer-status"><span className={`pulse-dot ${backendOnline?'':'offline'}`}/>{backendOnline?'Backend connected':'Backend offline'} • Polygon Amoy</span></footer>}

createRoot(document.getElementById('root')).render(<App />);
