import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider, useQueryClient, type UseQueryResult } from '@tanstack/react-query';
import {
  Activity as ActivityIcon, ArrowDownRight, ArrowUpRight, Bookmark, BriefcaseBusiness,
  Check, CheckCircle2, ChevronRight, Clock3, Cloud, ExternalLink, FileText, Filter,
  GraduationCap, Heart, Layers3, LoaderCircle, MapPin, MessageSquareText, Search, Send, Settings2,
  Sparkles, Upload, UserRound, X, Zap,
} from 'lucide-react';
import {
  getGetApplicationQueryKey, getGetCandidateProfileQueryKey, getGetDashboardQueryKey, getGetInternshipQueryKey,
  getGetRuntimeStatusQueryKey, getListApplicationsQueryKey, getListInternshipsQueryKey,
  useAskAssistant, useGenerateApplicationMaterial, useGetApplication, useGetCandidateProfile,
  useGetDashboard, useGetInternship, useGetRuntimeStatus, useHealthCheck, useListApplications,
  useListInternships, useSaveApplication, useSearchInternships, useUpdateApplication,
  useUpdateCandidateProfile, useUploadResume,
} from '@workspace/api-client-react';
import type {
  Application, ApplicationStatus, CandidateProfile, GenerateMaterialInputKind,
  HealthStatus, Internship, ProfileInput, ProfileState, RuntimeStatus, SearchInput,
} from '@workspace/api-client-react';
import { Link, Route, Switch, useLocation, Router as WouterRouter } from 'wouter';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import NotFound from '@/pages/not-found';

const queryClient = new QueryClient();

const navigation = [
  { href: '/', label: 'Overview', icon: Layers3 },
  { href: '/internships', label: 'Explore roles', icon: Search },
  { href: '/resume', label: 'Candidate profile', icon: UserRound },
  { href: '/tracker', label: 'Application tracker', icon: BriefcaseBusiness },
  { href: '/assistant', label: 'Profile assistant', icon: MessageSquareText },
  { href: '/settings', label: 'Settings', icon: Settings2 },
];

const statusChoices: ApplicationStatus[] = ['saved', 'applied', 'assessment', 'interview', 'offer', 'rejected', 'withdrawn'];
const materialKinds: { value: GenerateMaterialInputKind; label: string }[] = [
  { value: 'cover_letter', label: 'Cover letter' },
  { value: 'recruiter_message', label: 'Recruiter message' },
  { value: 'application_email', label: 'Application email' },
  { value: 'preparation_suggestions', label: 'Preparation suggestions' },
];

function initials(value?: string | null) {
  return (value || 'Candidate').split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'C';
}

function formatDate(value?: string | null) {
  if (!value) return 'Not set';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
}

function titleCase(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function RuntimeBadge({ status }: { status?: RuntimeStatus }) {
  if (!status) return <span className="status-pill"><span className="live-dot" />Checking services</span>;
  const ok = status.ai_configured && status.search_configured;
  return <span className="status-pill"><span className="live-dot" style={{ background: ok ? '#8bc3a5' : '#e0ae64' }} />{ok ? 'Services ready' : 'Setup needed'}</span>;
}

function Shell({ children, status, profile }: { children: ReactNode; status?: RuntimeStatus; profile?: CandidateProfile }) {
  const [location] = useLocation();
  const current = navigation.find((item) => item.href === location)?.label ?? 'Workspace';
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link href="/" className="brand" data-testid="link-brand-home">
          <span className="brand-mark">ih</span>
          <span><span className="brand-name">Internship Hunter</span><span className="brand-sub">fieldnotes / student edition</span></span>
        </Link>
        <div className="nav-label">Workspace</div>
        <nav className="side-nav" aria-label="Main navigation">
          {navigation.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} className={`nav-link ${location === href ? 'active' : ''}`} data-testid={`link-nav-${href === '/' ? 'overview' : href.slice(1)}`}>
              <Icon aria-hidden="true" /><span>{label}</span>
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="side-status">
            <div className="side-status-top"><span><span className="live-dot" />Runtime</span><span>{status ? (status.ai_configured ? 'AI on' : 'AI off') : 'checking'}</span></div>
            <p>{status?.message || 'Checking configured search and language providers.'}</p>
          </div>
          <Link href="/resume" className="profile-shortcut" data-testid="link-profile-shortcut">
            <span className="avatar-initial">{initials(profile?.name)}</span>
            <span>{profile?.name || 'Set up your profile'}<span className="brand-sub">candidate profile</span></span>
          </Link>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs"><span>Workspace</span><ChevronRight size={13} /><span className="crumb-current">{current}</span></div>
          <div className="top-meta"><span className="top-text">AI Internship Hunter</span><RuntimeBadge status={status} /></div>
        </header>
        {children}
      </main>
    </div>
  );
}

function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1 className="page-title">{title}</h1><p className="page-description">{description}</p></div>{action}</div>;
}

function LoadingPanel({ rows = 3 }: { rows?: number }) {
  return <div className="panel panel-body" aria-label="Loading content" data-testid="status-loading">
    <div className="skeleton skeleton-line" style={{ width: '36%' }} />
    {Array.from({ length: rows }).map((_, i) => <div key={i} className="skeleton skeleton-line" style={{ width: `${88 - i * 12}%`, height: i === 0 ? 18 : 11 }} />)}
  </div>;
}

function EmptyState({ icon: Icon = Search, title, children, action }: { icon?: typeof Search; title: string; children: ReactNode; action?: ReactNode }) {
  return <div className="empty-state" data-testid="state-empty"><div className="empty-icon"><Icon size={19} /></div><h3>{title}</h3><p>{children}</p>{action}</div>;
}

function ErrorNotice({ message, retry }: { message: string; retry?: () => void }) {
  return <div className="alert alert-error" role="alert" data-testid="status-error">{message}{retry && <button className="btn btn-quiet" style={{ marginLeft: 10, padding: '6px 9px' }} onClick={retry} data-testid="button-retry">Try again</button>}</div>;
}

function DashboardPage({ profile, runtime }: { profile?: CandidateProfile; runtime?: RuntimeStatus }) {
  const { data: dashboard, isLoading, isError, refetch } = useGetDashboard();
  const queryClient = useQueryClient();
  const { data: applications = [] } = useListApplications();
  const { data: internships = [] } = useListInternships({ limit: 100 });
  const readyProfile = Boolean(profile?.name?.trim());
  const stats = dashboard ? [
    ['Roles found', dashboard.internships_found, 'Across recent searches'],
    ['Saved', dashboard.saved, 'Worth a closer look'],
    ['Applications', dashboard.applications, 'Tracked by you'],
    ['Interviews', dashboard.interviews, 'Conversations in motion'],
  ] : [];
  const retry = () => { void refetch(); void queryClient.invalidateQueries({ queryKey: getGetDashboardQueryKey() }); };
  return <div className="page-content">
    <PageHeading eyebrow="Your internship fieldnotes" title={readyProfile ? `Good to see you, ${profile?.name?.split(' ')[0]}.` : 'A clearer path to your next role.'} description="Find roles that fit what you can actually show. Prepare thoughtfully, then apply yourself." action={<Link href="/internships" className="btn btn-primary" data-testid="button-find-roles"><Search size={15} /> Explore opportunities</Link>} />
    {(!runtime?.ai_configured || !runtime?.search_configured) && <div className="alert alert-warn" data-testid="status-provider-not-configured">{runtime?.message || 'Provider configuration is still being checked.'} Search and writing availability depends on the providers configured for this workspace.</div>}
    {!readyProfile && <div className="alert alert-info" data-testid="status-no-profile">Add a resume or candidate profile to get evidence-based match signals. Without a profile, fit scores should not be treated as personalized.</div>}
    {isLoading ? <LoadingPanel rows={5} /> : isError ? <ErrorNotice message="Dashboard data could not be loaded." retry={retry} /> : dashboard ? <>
      <section className="stat-grid" aria-label="Application overview">
        {stats.map(([label, value, note]) => <article className="panel stat-card" key={label}><span className="stat-label">{label}</span><strong className="stat-number" data-testid={`stat-${String(label).toLowerCase().replaceAll(' ', '-')}`}>{value}</strong><span className="stat-note">{note}</span></article>)}
      </section>
      <div className="dashboard-grid">
        <section className="panel">
          <header className="panel-head"><div><h2 className="panel-title">Recent agent activity</h2><p className="panel-kicker">High-level actions only</p></div><ActivityIcon size={16} color="#7c907f" /></header>
          {dashboard.recent_activity?.length ? <div className="activity-list">{dashboard.recent_activity.slice(0, 8).map((activity) => <div className="activity-item" key={activity.id} data-testid={`activity-${activity.id}`}><span className="activity-dot"><Zap size={13} /></span><div className="activity-copy">{activity.message}<span className="activity-time">{formatDate(activity.created_at)} · {titleCase(activity.kind || 'activity')}</span></div></div>)}</div> : <div className="panel-body"><EmptyState icon={ActivityIcon} title="No agent actions yet">Search or update your profile to start a useful activity trail.</EmptyState></div>}
        </section>
        <div style={{ display: 'grid', gap: 15, alignContent: 'start' }}>
          <section className="panel">
            <header className="panel-head"><div><h2 className="panel-title">Your pipeline</h2><p className="panel-kicker">Where applications stand</p></div><BriefcaseBusiness size={16} color="#7c907f" /></header>
            <div className="panel-body pipeline-list">
              {[['Saved', dashboard.saved], ['Applied', Math.max(dashboard.applications - dashboard.pending, 0)], ['In conversation', dashboard.interviews]].map(([label, value]) => <div key={label as string}><div className="pipeline-row"><span>{label}</span><strong>{value}</strong></div><div className="pipeline-bar"><div className="pipeline-fill" style={{ width: `${Math.min(100, Number(value) * 12 + 8)}%` }} /></div></div>)}
              <Link href="/tracker" className="btn btn-quiet" style={{ width: '100%', marginTop: 2 }} data-testid="link-open-tracker">Open application tracker <ArrowUpRight size={14} /></Link>
            </div>
          </section>
          <section className="callout"><strong>Make the match explain itself.</strong><p>Each role shows evidence found in your profile and the requirements that still need a closer look.</p></section>
        </div>
      </div>
      <section style={{ marginTop: 18 }}>
        <div className="results-head"><h2 className="results-title">Recently saved</h2><Link href="/tracker" className="btn btn-outline" data-testid="link-all-saved">View tracker <ArrowUpRight size={13} /></Link></div>
        {applications.length ? <div className="job-list">{applications.slice(0, 3).map((app) => <div className="panel job-card" key={app.id}><div><div className="job-company">{app.company}</div><h3 className="job-title" style={{ marginTop: 6 }}>{app.role}</h3><div className="job-location"><Clock3 />{titleCase(app.status)} · added {formatDate(app.created_at)}</div></div><Link href="/tracker" className="btn btn-quiet">Details <ChevronRight size={14} /></Link></div>)}</div> : internships.length ? <div className="panel panel-body"><p style={{ fontSize: 11, color: '#788176', margin: 0 }}>You have roles to explore, but nothing saved yet.</p></div> : null}
      </section>
    </> : <EmptyState icon={ActivityIcon} title="Your workspace is ready">Dashboard activity will appear here once the service is available.</EmptyState>}
  </div>;
}

function InternshipCard({ internship, onOpen, onSave }: { internship: Internship; onOpen: () => void; onSave: () => void }) {
  return <article className="panel job-card" data-testid={`card-internship-${internship.id}`}>
    <div>
      <div className="company-line"><span className="company-mark">{initials(internship.company)}</span><span className="job-company">{internship.company}</span></div>
      <h3 className="job-title">{internship.role}</h3>
      <div className="job-location"><MapPin />{internship.location || 'Location not specified'}{internship.remote ? ' · Remote' : ''}{internship.salary ? ` · ${internship.salary}` : ''}</div>
      <p className="job-desc">{internship.match_summary || internship.description}</p>
      <div className="tag-row">{internship.matched_skills?.slice(0, 4).map((skill) => <span className="tag" key={`match-${skill}`}>{skill}</span>)}{internship.source && <span className="tag">{internship.source}</span>}</div>
    </div>
    <div className="job-side"><div className="match-score" aria-label={`${internship.match_score}% match`}>{internship.match_score}<small>FIT</small></div><div className="job-action-row"><button className="icon-button" title="Save to tracker" onClick={onSave} data-testid={`button-save-${internship.id}`}><Bookmark size={15} /></button><button className="btn btn-quiet" onClick={onOpen} data-testid={`button-details-${internship.id}`}>Details <ChevronRight size={13} /></button></div></div>
  </article>;
}

function InternshipDetail({ item, loading, onClose, onSave }: { item?: Internship; loading: boolean; onClose: () => void; onSave: (item: Internship) => void }) {
  if (!item && !loading) return null;
  return <div className="detail-panel" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="detail-drawer" role="dialog" aria-modal="true" aria-label="Internship details">
      <div className="drawer-top"><span className="eyebrow" style={{ margin: 0 }}>Role evidence</span><button className="icon-button" onClick={onClose} aria-label="Close details" data-testid="button-close-details"><X size={16} /></button></div>
      {loading || !item ? <LoadingPanel rows={6} /> : <>
        <div className="company-line"><span className="company-mark">{initials(item.company)}</span><div><div className="job-company">{item.company}</div><span className="job-location">{item.location || 'Location not specified'}{item.remote ? ' · Remote' : ''}</span></div></div>
        <h2 className="page-title" style={{ fontSize: 30, marginTop: 17 }}>{item.role}</h2>
        <div className="detail-summary"><div className="match-score">{item.match_score}<small>FIT</small></div><div><strong style={{ font: '700 13px var(--app-font-serif)', color: '#31513d' }}>Why this might fit</strong><p>{item.match_summary || 'No match summary was provided. Review the evidence below against the full role description.'}</p></div></div>
        <div className="evidence-row">
          <div className="evidence-box"><h4><Check size={12} /> Evidence in your profile</h4><div className="tag-row">{item.matched_skills?.length ? item.matched_skills.map((skill) => <span className="tag" key={skill}>{skill}</span>) : <span className="job-location">No matched skills provided</span>}</div></div>
          <div className="evidence-box"><h4><ArrowDownRight size={12} /> Requirements to check</h4><div className="tag-row">{item.missing_skills?.length ? item.missing_skills.map((skill) => <span className="tag" key={skill}>{skill}</span>) : <span className="job-location">No missing skills provided</span>}</div></div>
        </div>
        <div className="detail-section"><h3>About the role</h3><p className="job-desc">{item.description || 'No description provided.'}</p></div>
        <div className="detail-section"><h3>Requirements</h3>{item.requirements?.length ? <ul className="bullet-list">{item.requirements.map((requirement) => <li key={requirement}>{requirement}</li>)}</ul> : <p className="job-location">No listed requirements supplied.</p>}</div>
        <div className="detail-section"><h3>Role facts</h3><p className="job-location">Source: {item.source || 'Not provided'} · Found {formatDate(item.date_found)}{item.deadline ? ` · Deadline ${formatDate(item.deadline)}` : ''}{item.salary ? ` · ${item.salary}` : ''}</p></div>
        <div className="inline-actions" style={{ justifyContent: 'space-between' }}>
          {item.application_url ? <a className="btn btn-outline" href={item.application_url} target="_blank" rel="noreferrer" data-testid="link-employer-application">Employer application <ExternalLink size={14} /></a> : <span className="job-location">Application link not available</span>}
          <button className="btn btn-primary" onClick={() => onSave(item)} data-testid="button-save-to-tracker"><Bookmark size={14} /> Save to tracker</button>
        </div>
        <p className="job-location" style={{ marginTop: 12 }}>Saving only adds this opportunity to your tracker. It does not submit an application.</p>
      </>}
    </section>
  </div>;
}

function InternshipsPage({ profile, runtime }: { profile?: CandidateProfile; runtime?: RuntimeStatus }) {
  const queryClient = useQueryClient();
  const list = useListInternships({ limit: 100 });
  const search = useSearchInternships();
  const saveApplication = useSaveApplication();
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('');
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [result, setResult] = useState<Awaited<ReturnType<typeof search.mutateAsync>> | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const { data: detail, isLoading: detailLoading } = useGetInternship(selectedId || '', { query: { enabled: Boolean(selectedId), queryKey: getGetInternshipQueryKey(selectedId || '') } });
  useEffect(() => { if (runtime && !runtime.search_configured) setDemoMode(true); }, [runtime]);
  const items = result?.jobs ?? list.data ?? [];
  const isDemo = result?.data_mode === 'demo' || (!result && !runtime?.search_configured && items.length > 0);
  async function runSearch(event: FormEvent) {
    event.preventDefault();
    if (query.trim().length < 2) { setNotice('Enter at least two characters to search.'); return; }
    setNotice('');
    const input: SearchInput = { query: query.trim(), location: location.trim(), remote_only: remoteOnly, demo_mode: demoMode, max_results: 20 };
    try { const response = await search.mutateAsync({ data: input }); setResult(response); }
    catch { setNotice('Search could not be completed. Check provider status in Settings, then try again.'); }
  }
  function save(item: Internship) {
    saveApplication.mutate({ data: { internship_id: item.id, notes: '' } }, {
      onSuccess: () => { void queryClient.invalidateQueries({ queryKey: getListApplicationsQueryKey() }); setNotice(`${item.role} saved to your tracker. No external application was submitted.`); setSelectedId(null); },
      onError: () => setNotice('Could not save this opportunity. Please try again.'),
    });
  }
  return <div className="page-content">
    <PageHeading eyebrow="Opportunity search" title="Find work worth your time." description="Search current listings when a provider is configured, or explore clearly marked sample roles. Fit signals are evidence, not a hiring prediction." />
    {!profile?.name && <div className="alert alert-info" data-testid="status-profile-needed">No candidate profile is loaded. Search still works, but personalized match scores may be unavailable. <Link href="/resume" style={{ color: '#37664a', fontWeight: 700 }}>Build your profile</Link></div>}
    {runtime && !runtime.search_configured && <div className="alert alert-warn" data-testid="status-search-unconfigured">Live search is not configured. Enable demo listings below for examples; examples are not current openings.</div>}
    {notice && <div className="alert alert-info" role="status" data-testid="status-search-message">{notice}<button className="icon-button" style={{ float: 'right', width: 25, height: 25 }} onClick={() => setNotice('')} aria-label="Dismiss message"><X size={13} /></button></div>}
    <form className="panel search-panel" onSubmit={runSearch}>
      <div className="search-form">
        <label className="input-wrap"><Search /><input className="field" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Role, skill, or company" aria-label="Search roles" data-testid="input-search-query" /></label>
        <label className="input-wrap"><MapPin /><input className="field" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Location" aria-label="Location" data-testid="input-search-location" /></label>
        <label className="checkbox-label"><input type="checkbox" checked={remoteOnly} onChange={(e) => setRemoteOnly(e.target.checked)} data-testid="checkbox-remote-only" /> Remote only</label>
        <label className="checkbox-label"><input type="checkbox" checked={demoMode} onChange={(e) => setDemoMode(e.target.checked)} data-testid="checkbox-demo-mode" /> Include demo listings</label>
        <button className="btn btn-primary" type="submit" disabled={search.isPending} data-testid="button-search-internships">{search.isPending ? <LoaderCircle size={15} /> : <Search size={15} />}{search.isPending ? 'Searching' : 'Search roles'}</button>
      </div>
    </form>
    {search.isError && <ErrorNotice message="Search service returned an error. Provider status is available in Settings." retry={() => { if (query.trim().length >= 2) void runSearch(new Event('submit') as unknown as FormEvent); }} />}
    {result?.message && <div className={`alert ${result.data_mode === 'demo' ? 'alert-warn' : 'alert-info'}`} data-testid="status-search-result-message">{result.message}</div>}
    {list.isError && !result && <ErrorNotice message="Saved search results could not be loaded." retry={() => void list.refetch()} />}
    <div className="results-head">
      <div><h2 className="results-title">{result ? `${result.count} results` : 'Recent opportunities'}</h2><span className="panel-kicker">{result ? `Search mode · ${result.ai_used ? 'AI assisted' : 'standard matching'}` : 'Roles available in this session'}</span></div>
      <div className="results-meta">{result ? (result.data_mode === 'demo' ? <span className="demo-label">Demo listings</span> : <span className="live-label">Live results</span>) : <span>{items.length} listed</span>}<Filter size={14} /></div>
    </div>
    {list.isLoading && !result ? <LoadingPanel rows={7} /> : items.length ? <div className="job-list">{items.map((item) => <InternshipCard key={item.id} internship={item} onOpen={() => setSelectedId(item.id)} onSave={() => save(item)} />)}</div> : <EmptyState icon={Search} title={result ? 'No roles matched that search' : 'No opportunities loaded'}>{result ? 'Try broader role terms, remove a location filter, or change the remote preference.' : 'Search for a role or skill to find available opportunities. Demo examples appear only when enabled and are labeled as examples.'}</EmptyState>}
    <InternshipDetail item={detail ?? items.find((item) => item.id === selectedId)} loading={Boolean(selectedId) && detailLoading} onClose={() => setSelectedId(null)} onSave={save} />
  </div>;
}

const emptyProfile: ProfileInput = { name: '', email: null, education: [], skills: [], programming_languages: [], frameworks: [], ai_ml_skills: [], cloud_skills: [], projects: [], experience: [], certifications: [], locations: [], preferred_roles: [] };
type ProfileArrayField = Exclude<keyof ProfileInput, 'name' | 'email'>;
const profileFields: { key: ProfileArrayField; label: string; hint: string; wide?: boolean }[] = [
  { key: 'education', label: 'Education', hint: 'Degree, school, graduation year' },
  { key: 'skills', label: 'Skills', hint: 'General skills' },
  { key: 'programming_languages', label: 'Programming languages', hint: 'Python, JavaScript…' },
  { key: 'frameworks', label: 'Frameworks', hint: 'Tools and frameworks' },
  { key: 'ai_ml_skills', label: 'AI / machine learning', hint: 'Models, evaluation, data work' },
  { key: 'cloud_skills', label: 'Cloud skills', hint: 'Platforms and infrastructure' },
  { key: 'projects', label: 'Projects', hint: 'Project name and a short outcome', wide: true },
  { key: 'experience', label: 'Experience', hint: 'Roles, responsibilities, results', wide: true },
  { key: 'certifications', label: 'Certifications', hint: 'Certification names' },
  { key: 'locations', label: 'Preferred locations', hint: 'City, region, or remote' },
  { key: 'preferred_roles', label: 'Preferred roles', hint: 'Role titles or functions', wide: true },
];

function ResumePage({ profileState }: { profileState?: ProfileState }) {
  const queryClient = useQueryClient();
  const saveProfile = useUpdateCandidateProfile();
  const uploadResume = useUploadResume();
  const [form, setForm] = useState<ProfileInput>(emptyProfile);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  useEffect(() => { if (profileState?.profile) setForm({ ...profileState.profile }); }, [profileState]);
  const setScalar = (key: 'name' | 'email', value: string) => setForm((current) => ({ ...current, [key]: value }));
  const setArray = (key: ProfileArrayField, value: string) => setForm((current) => ({ ...current, [key]: value.split('\n').map((v) => v.trim()).filter(Boolean) }));
  function save(event: FormEvent) {
    event.preventDefault();
    setMessage(''); setError('');
    saveProfile.mutate({ data: { ...form, email: form.email || null } }, {
      onSuccess: () => { setMessage('Candidate profile saved. Match evidence will use these details.'); void queryClient.invalidateQueries({ queryKey: getGetCandidateProfileQueryKey() }); },
      onError: () => setError('The profile could not be saved. Your edits remain here; please retry.'),
    });
  }
  function uploadFile(file?: File) {
    if (!file) return;
    setMessage(''); setError('');
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) { setError('Choose a PDF file to extract profile details.'); return; }
    uploadResume.mutate({ data: { file } }, {
      onSuccess: (result) => {
        setForm({ ...result.profile });
        setMessage(`${result.message} Review extracted details and save any edits. ${result.ai_configured ? '' : 'AI provider is not configured; extraction may be limited.'}`);
        void queryClient.invalidateQueries({ queryKey: getGetCandidateProfileQueryKey() });
      },
      onError: () => setError('Resume extraction failed. You can still complete the profile manually.'),
    });
  }
  const hasProfile = Boolean(form.name || profileState?.resume_loaded);
  return <div className="page-content">
    <PageHeading eyebrow="Resume & candidate profile" title="Put your experience to work." description="Upload a PDF for extraction, then review every detail. The profile is the evidence base for match summaries and tailored materials." />
    {profileState === undefined && <LoadingPanel rows={5} />}
    {profileState && <div className="profile-layout">
      <div style={{ display: 'grid', gap: 15 }}>
        <section className="panel">
          <header className="panel-head"><div><h2 className="panel-title">Resume source</h2><p className="panel-kicker">{profileState.resume_loaded ? `Resume loaded · ${profileState.extraction_method || 'extraction method not specified'}` : 'No PDF resume loaded'}</p></div><FileText size={16} color="#77907c" /></header>
          <div className="panel-body">
            {error && <ErrorNotice message={error} />}
            {message && <div className="alert alert-info" role="status" data-testid="status-profile-message">{message}</div>}
            <label className="upload-zone" style={{ display: 'block', cursor: uploadResume.isPending ? 'wait' : 'pointer' }}>
              {uploadResume.isPending ? <LoaderCircle size={21} /> : <Upload size={21} />}
              <p>{uploadResume.isPending ? 'Reading your PDF…' : 'Choose a PDF resume to extract profile details'}</p>
              <input type="file" accept="application/pdf,.pdf" disabled={uploadResume.isPending} onChange={(e) => uploadFile(e.currentTarget.files?.[0])} data-testid="input-resume-upload" />
            </label>
            <p className="panel-kicker" style={{ marginTop: 10 }}>The upload is used to populate this candidate profile. Review extracted information before saving.</p>
          </div>
        </section>
        <form className="panel" onSubmit={save}>
          <header className="panel-head"><div><h2 className="panel-title">Candidate details</h2><p className="panel-kicker">Edit the source-of-truth profile used for fit evidence</p></div><UserRound size={16} color="#77907c" /></header>
          <div className="panel-body">
            {!hasProfile && <div className="alert alert-warn" data-testid="status-no-profile">No profile is available yet. Fill in at least your name and a few skills to begin.</div>}
            <div className="profile-grid">
              <div className="form-field"><label htmlFor="candidate-name">Name</label><input id="candidate-name" className="field" value={form.name} onChange={(e) => setScalar('name', e.target.value)} placeholder="Your name" data-testid="input-profile-name" /></div>
              <div className="form-field"><label htmlFor="candidate-email">Email</label><input id="candidate-email" type="email" className="field" value={form.email || ''} onChange={(e) => setScalar('email', e.target.value)} placeholder="you@example.com" data-testid="input-profile-email" /></div>
              {profileFields.map(({ key, label, hint, wide }) => <div className={`form-field ${wide ? 'wide' : ''}`} key={key}><label htmlFor={`profile-${key}`}>{label}</label><textarea id={`profile-${key}`} className="textarea" rows={key === 'projects' || key === 'experience' ? 3 : 2} value={(form[key] as string[]).join('\n')} onChange={(e) => setArray(key, e.target.value)} placeholder={`${hint}\nOne item per line`} data-testid={`input-profile-${key}`} /></div>)}
            </div>
            <div className="inline-actions"><button className="btn btn-primary" type="submit" disabled={saveProfile.isPending} data-testid="button-save-profile">{saveProfile.isPending ? 'Saving profile…' : <><Check size={14} /> Save profile</>}</button></div>
          </div>
        </form>
      </div>
      <aside className="panel profile-side-note">
        <span className="eyebrow">Profile completeness</span>
        <h3>{hasProfile ? 'A living document' : 'Start with the evidence'}</h3>
        <p>{hasProfile ? 'Keep skills, projects, and experience current. Strong specific details make match explanations more useful.' : 'Your profile will be compared with role requirements. Missing items are surfaced rather than guessed.'}</p>
        <div className="provider-row"><div className="provider-name"><div className="provider-icon"><GraduationCap size={15} /></div><div><strong>Education</strong><span>{form.education.length} detail{form.education.length === 1 ? '' : 's'}</span></div></div></div>
        <div className="provider-row"><div className="provider-name"><div className="provider-icon"><Sparkles size={15} /></div><div><strong>Skills & tools</strong><span>{[...form.skills, ...form.programming_languages, ...form.frameworks, ...form.ai_ml_skills, ...form.cloud_skills].length} profile entries</span></div></div></div>
        <div className="provider-row"><div className="provider-name"><div className="provider-icon"><Layers3 size={15} /></div><div><strong>Experience & projects</strong><span>{form.experience.length + form.projects.length} details</span></div></div></div>
        <Link href="/assistant" className="btn btn-quiet" style={{ width: '100%', marginTop: 16 }} data-testid="link-profile-assistant">Ask about your profile <MessageSquareText size={14} /></Link>
      </aside>
    </div>}
  </div>;
}

function TrackerPage({ profile }: { profile?: CandidateProfile }) {
  const queryClient = useQueryClient();
  const list = useListApplications();
  const update = useUpdateApplication();
  const generate = useGenerateApplicationMaterial();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notes, setNotes] = useState('');
  const [draft, setDraft] = useState('');
  const [materialKind, setMaterialKind] = useState<GenerateMaterialInputKind>('cover_letter');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const { data: selected, isLoading: selectedLoading } = useGetApplication(selectedId || '', { query: { enabled: Boolean(selectedId), queryKey: getGetApplicationQueryKey(selectedId || '') } });
  const current = selected ?? list.data?.find((item) => item.id === selectedId);
  useEffect(() => { if (current) { setNotes(current.notes || ''); setDraft(''); setMessage(''); setError(''); } }, [current]);
  function changeStatus(app: Application, status: ApplicationStatus) {
    update.mutate({ applicationId: app.id, data: { status } }, { onSuccess: () => { void queryClient.invalidateQueries({ queryKey: getListApplicationsQueryKey() }); setMessage(`Status updated to ${titleCase(status)}. This only updates your tracker.`); }, onError: () => setError('Could not update status.') });
  }
  function saveNotes() {
    if (!current) return;
    update.mutate({ applicationId: current.id, data: { notes } }, { onSuccess: () => { void queryClient.invalidateQueries({ queryKey: getListApplicationsQueryKey() }); setMessage('Notes saved.'); }, onError: () => setError('Could not save notes.') });
  }
  function generateMaterial() {
    if (!current) return;
    setError(''); setMessage('');
    generate.mutate({ applicationId: current.id, data: { kind: materialKind } }, { onSuccess: (material) => { setDraft(material.content); setMessage(`${titleCase(material.kind)} generated${material.ai_used ? ` with ${material.model}` : ' without configured AI'}. Edit it before saving.`); }, onError: () => setError('Material generation is unavailable. Check AI provider status in Settings.') });
  }
  function saveMaterial() {
    if (!current) return;
    const generated_material = { ...(current.generated_material || {}), [materialKind]: draft };
    update.mutate({ applicationId: current.id, data: { generated_material } }, { onSuccess: () => { void queryClient.invalidateQueries({ queryKey: getListApplicationsQueryKey() }); setMessage('Edited material saved to this application.'); }, onError: () => setError('Could not save edited material.') });
  }
  return <div className="page-content">
    <PageHeading eyebrow="Your application log" title="Keep every next step visible." description="Track your own application journey. Status changes are notes for you—they never submit anything to an employer." action={<Link href="/internships" className="btn btn-primary" data-testid="button-tracker-search"><Search size={15} /> Find another role</Link>} />
    {list.isLoading ? <LoadingPanel rows={6} /> : list.isError ? <ErrorNotice message="Applications could not be loaded." retry={() => void list.refetch()} /> : list.data?.length ? <div className="tracker-detail-grid">
      <section className="panel">
        <header className="panel-head"><div><h2 className="panel-title">Applications & saved roles</h2><p className="panel-kicker">{list.data.length} opportunities in your tracker</p></div><span className="tag">{list.data.filter((app) => app.status === 'saved').length} saved</span></header>
        <div className="tracker-table-wrap"><table className="tracker-table"><thead><tr><th>Role</th><th>Status</th><th>Added</th><th>Next step</th></tr></thead><tbody>{list.data.map((app) => <tr key={app.id} data-testid={`row-application-${app.id}`}><td><button onClick={() => setSelectedId(app.id)} style={{ border: 0, padding: 0, textAlign: 'left', background: 'transparent', color: '#39493e' }} data-testid={`button-open-application-${app.id}`}><strong style={{ display: 'block', fontSize: 11 }}>{app.role}</strong><span className="panel-kicker">{app.company}</span></button></td><td><select className="status-select" value={app.status} onChange={(e) => changeStatus(app, e.target.value as ApplicationStatus)} aria-label={`Status for ${app.role}`} data-testid={`select-status-${app.id}`}>{statusChoices.map((status) => <option key={status} value={status}>{titleCase(status)}</option>)}</select></td><td>{formatDate(app.created_at)}</td><td><button className="btn btn-quiet" style={{ padding: '7px 9px' }} onClick={() => setSelectedId(app.id)} data-testid={`button-manage-${app.id}`}>Manage <ChevronRight size={13} /></button></td></tr>)}</tbody></table></div>
      </section>
      <aside className="panel">
        {!selectedId ? <div className="panel-body"><EmptyState icon={BriefcaseBusiness} title="Choose an opportunity">Open a row to edit notes, review tailored material, or record a status update.</EmptyState></div> : selectedLoading && !current ? <LoadingPanel rows={4} /> : current ? <div className="panel-body">
          <div className="drawer-top"><div><p className="eyebrow">Tracker entry</p><h2 className="panel-title">{current.role}</h2><p className="panel-kicker">{current.company}</p></div><button className="icon-button" onClick={() => setSelectedId(null)} aria-label="Close application details" data-testid="button-close-application"><X size={15} /></button></div>
          {error && <ErrorNotice message={error} />}{message && <div className="alert alert-info" data-testid="status-tracker-message">{message}</div>}
          <div className="form-field"><label>Status · a personal record</label><select className="select" value={current.status} onChange={(e) => changeStatus(current, e.target.value as ApplicationStatus)} data-testid="select-current-status">{statusChoices.map((s) => <option value={s} key={s}>{titleCase(s)}</option>)}</select></div>
          <div className="form-field" style={{ marginTop: 14 }}><label htmlFor="application-notes">Notes</label><textarea id="application-notes" className="textarea" rows={4} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Interview date, contact, follow-up reminder…" data-testid="input-application-notes" /><button className="btn btn-quiet" style={{ marginTop: 8 }} onClick={saveNotes} disabled={update.isPending} data-testid="button-save-notes">Save notes</button></div>
          <div className="detail-section" style={{ borderTop: '1px solid #e9e7dd', paddingTop: 17 }}>
            <h3>Tailored material</h3>
            {!profile?.name && <div className="alert alert-warn">No candidate profile is loaded. Add profile details for more relevant writing suggestions.</div>}
            <label className="form-field"><span style={{ display: 'block', marginBottom: 7, fontSize: 10, color: '#687267' }}>Material type</span><select className="select" value={materialKind} onChange={(e) => { setMaterialKind(e.target.value as GenerateMaterialInputKind); setDraft(''); }} data-testid="select-material-kind">{materialKinds.map((kind) => <option value={kind.value} key={kind.value}>{kind.label}</option>)}</select></label>
            <button className="btn btn-outline" style={{ width: '100%', marginTop: 9 }} onClick={generateMaterial} disabled={generate.isPending} data-testid="button-generate-material">{generate.isPending ? 'Preparing draft…' : <><Sparkles size={14} /> Generate a draft</>}</button>
            {(draft || Object.keys(current.generated_material || {}).length > 0) && <>
              <textarea className="textarea" style={{ marginTop: 10, minHeight: 165 }} value={draft || current.generated_material?.[materialKind] || ''} onChange={(e) => setDraft(e.target.value)} placeholder="Generated material appears here. Edit it before saving." data-testid="textarea-generated-material" />
              <button className="btn btn-primary" style={{ width: '100%', marginTop: 9 }} onClick={saveMaterial} disabled={update.isPending || !draft.trim()} data-testid="button-save-material"><Check size={14} /> Save edited material</button>
            </>}
            <p className="panel-kicker" style={{ marginTop: 10 }}>Review and edit every draft. Nothing is sent to an employer.</p>
          </div>
          {current.application_url && <a href={current.application_url} target="_blank" rel="noreferrer" className="btn btn-outline" style={{ width: '100%' }} data-testid="link-open-employer">Open employer application <ExternalLink size={13} /></a>}
          <p className="panel-kicker" style={{ marginTop: 8 }}>Opening the employer page does not submit an application.</p>
        </div> : <ErrorNotice message="This application detail could not be loaded." />}
      </aside>
    </div> : <EmptyState icon={BriefcaseBusiness} title="Your tracker starts with one role">Save an opportunity from search. Then record your own application status, keep notes, and prepare material to review.</EmptyState>}
  </div>;
}

type ChatMessage = { role: 'user' | 'agent'; content: string; model?: string; aiUsed?: boolean };
function AssistantPage({ profile, runtime }: { profile?: CandidateProfile; runtime?: RuntimeStatus }) {
  const ask = useAskAssistant();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  const questions = ['Which projects best support an ML internship?', 'What skills should I highlight for a data role?', 'What evidence is missing from my profile?'];
  async function submit(event: FormEvent) {
    event.preventDefault();
    const prompt = text.trim();
    if (!prompt || ask.isPending) return;
    setError(''); setText('');
    setMessages((items) => [...items, { role: 'user', content: prompt }]);
    try {
      const reply = await ask.mutateAsync({ data: { message: prompt } });
      setMessages((items) => [...items, { role: 'agent', content: reply.reply, model: reply.model, aiUsed: reply.ai_used }]);
    } catch {
      setError('The assistant could not answer. Check whether an AI provider is configured, then try again.');
    }
  }
  function askSuggestion(question: string) {
    setText(question);
    window.setTimeout(() => document.getElementById('assistant-prompt')?.focus(), 0);
  }
  return <div className="page-content">
    <PageHeading eyebrow="Profile-aware assistant" title="Ask better questions of your profile." description="Use the assistant to understand your experience and explore role fit. Answers are guidance to review, not an application or a guarantee." />
    {!profile?.name && <div className="alert alert-warn" data-testid="status-assistant-no-profile">No candidate profile is loaded. Add your resume first for profile-aware answers. <Link href="/resume" style={{ color: '#37664a', fontWeight: 700 }}>Set up profile</Link></div>}
    {runtime && !runtime.ai_configured && <div className="alert alert-warn" data-testid="status-ai-unconfigured">AI provider is not configured. Assistant replies may be unavailable; no provider is implied by this interface.</div>}
    <div className="assistant-layout">
      <div className="assistant-intro"><div className="assistant-mark"><Sparkles size={18} /></div><div><h2>Ask about evidence, not magic.</h2><p>Answers use the candidate profile and tracked opportunities available in this session.</p></div></div>
      <section className="panel">
        <div className="chat-window" aria-live="polite" data-testid="assistant-conversation">
          {!messages.length && <div className="chat-bubble agent">I can help you reflect on the experience and skills in your profile. Try a suggested question, or ask about a role you have saved.<div className="chat-note">Profile-aware support · review every answer</div></div>}
          {messages.map((message, index) => <div key={`${message.role}-${index}`} className={`chat-bubble ${message.role}`} data-testid={`chat-message-${index}`}>{message.content}{message.role === 'agent' && <div className="chat-note">{message.aiUsed ? `AI-assisted · ${message.model || 'provider model'}` : 'Standard response · no configured AI used'}</div>}</div>)}
          {ask.isPending && <div className="chat-bubble agent" data-testid="status-assistant-loading"><span className="skeleton" style={{ display: 'block', width: 170, height: 10 }} /><span className="skeleton" style={{ display: 'block', width: 110, height: 10, marginTop: 8 }} /></div>}
          {error && <div className="alert alert-error" role="alert">{error}<button className="btn btn-quiet" style={{ marginLeft: 8, padding: '5px 8px' }} onClick={() => setError('')}>Dismiss</button></div>}
        </div>
        {!messages.length && <div className="suggestions" style={{ padding: '0 18px' }}>{questions.map((question) => <button className="suggestion" key={question} onClick={() => askSuggestion(question)} data-testid={`button-question-${questions.indexOf(question)}`}>{question}</button>)}</div>}
        <form className="chat-form" onSubmit={submit}><input id="assistant-prompt" className="field" value={text} onChange={(e) => setText(e.target.value)} maxLength={4000} placeholder="Ask about your experience or a role…" aria-label="Ask a question" data-testid="input-assistant-question" /><button className="btn btn-primary" disabled={!text.trim() || ask.isPending} type="submit" data-testid="button-send-question"><Send size={14} /> Send</button></form>
      </section>
      <p className="panel-kicker" style={{ textAlign: 'center', marginTop: 12 }}>Suggestions can be incomplete. Verify details against the role and your own experience.</p>
    </div>
  </div>;
}

function SettingsPage({ runtime, health }: { runtime?: RuntimeStatus; health: UseQueryResult<HealthStatus, Error> }) {
  return <div className="page-content">
    <PageHeading eyebrow="Workspace configuration" title="Know what is connected." description="Provider readiness affects whether live search and tailored writing can run. Demo roles are examples, not current job openings." />
    {health.isError && <ErrorNotice message="The API health check failed. Some workspace features may be unavailable." retry={() => void health.refetch()} />}
    {!runtime && (health.isLoading ? <LoadingPanel rows={4} /> : <EmptyState icon={Cloud} title="Provider status unavailable">The runtime status could not be loaded. Check the API server and retry.</EmptyState>)}
    {runtime && <div className="settings-grid">
      <section className="panel">
        <header className="panel-head"><div><h2 className="panel-title">Provider readiness</h2><p className="panel-kicker">Reported by this workspace runtime</p></div><Cloud size={16} color="#77907c" /></header>
        <div className="panel-body">
          <div className="alert alert-info" data-testid="status-runtime-message">{runtime.message}</div>
          <div className="provider-row"><div className="provider-name"><div className="provider-icon"><Sparkles size={15} /></div><div><strong>AI writing provider</strong><span>{runtime.ai_provider || 'No provider configured'}{runtime.model ? ` · ${runtime.model}` : ''}</span></div></div><span className={runtime.ai_configured ? 'live-label' : 'demo-label'}>{runtime.ai_configured ? 'Configured' : 'Missing'}</span></div>
          <div className="provider-row"><div className="provider-name"><div className="provider-icon"><Search size={15} /></div><div><strong>Internship search</strong><span>{runtime.search_provider || 'No provider configured'}</span></div></div><span className={runtime.search_configured ? 'live-label' : 'demo-label'}>{runtime.search_configured ? 'Configured' : 'Missing'}</span></div>
          <div className="provider-row"><div className="provider-name"><div className="provider-icon"><CheckCircle2 size={15} /></div><div><strong>API health</strong><span>{health.data?.status || (health.isLoading ? 'Checking' : 'Not confirmed')}</span></div></div><span className={health.data?.status === 'ok' ? 'live-label' : 'demo-label'}>{health.data?.status === 'ok' ? 'Online' : 'Unconfirmed'}</span></div>
        </div>
      </section>
      <div style={{ display: 'grid', gap: 15, alignContent: 'start' }}>
        <section className="panel"><header className="panel-head"><div><h2 className="panel-title">Data mode, clearly labeled</h2><p className="panel-kicker">Search results identify their source mode</p></div><Filter size={16} color="#77907c" /></header><div className="panel-body"><div className="callout" style={{ background: runtime.search_configured ? '#e5eee6' : '#fbf0dc', color: runtime.search_configured ? '#355643' : '#805e31' }}><strong>{runtime.search_configured ? 'Live search provider reported as configured' : 'Demo mode may be needed'}</strong><p>{runtime.search_configured ? 'Search results are labeled live or demo according to the API response.' : 'If demo listings are available, enable the explicit demo option in Explore roles. Those examples are not current openings.'}</p></div></div></section>
        <section className="panel"><header className="panel-head"><div><h2 className="panel-title">What this agent does</h2><p className="panel-kicker">A deliberate human-in-the-loop workflow</p></div><Heart size={16} color="#77907c" /></header><div className="panel-body"><ol className="bullet-list"><li>Search for internships and review the source.</li><li>Compare your profile with role requirements.</li><li>Generate and edit material for your own review.</li><li>Open the employer page and apply manually.</li></ol><div className="alert alert-warn" style={{ margin: '15px 0 0' }}>This product does not submit external applications.</div></div></section>
      </div>
    </div>}
  </div>;
}

function RoutedErrorBoundary({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>;
}

function AppRouter() {
  const runtime = useGetRuntimeStatus();
  const candidate = useGetCandidateProfile();
  const health = useHealthCheck();
  const { data: runtimeData } = runtime;
  const profile = candidate.data?.profile;
  return <Shell status={runtimeData} profile={profile}>
    <RoutedErrorBoundary>
      <Switch>
        <Route path="/"><DashboardPage profile={profile} runtime={runtimeData} /></Route>
        <Route path="/internships"><InternshipsPage profile={profile} runtime={runtimeData} /></Route>
        <Route path="/resume"><ResumePage profileState={candidate.data} /></Route>
        <Route path="/tracker"><TrackerPage profile={profile} /></Route>
        <Route path="/assistant"><AssistantPage profile={profile} runtime={runtimeData} /></Route>
        <Route path="/settings"><SettingsPage runtime={runtimeData} health={health} /></Route>
        <Route component={NotFound} />
      </Switch>
    </RoutedErrorBoundary>
  </Shell>;
}

function App() {
  return <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
        <AppRouter />
      </WouterRouter>
      <Toaster />
    </TooltipProvider>
  </QueryClientProvider>;
}

export default App;
