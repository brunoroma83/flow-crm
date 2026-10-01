const config = {
  dashboard: { label: 'Dashboard', title: 'Visão geral das operações', description: 'Acompanhamento em tempo real de clientes, faturamento, entregas e compromissos.' },
  clients: { label: 'Clientes', title: 'Diretório de clientes', description: 'Contas, dados fiscais, saúde e valor mensal sob gestão.', fields: [['name', 'Nome da Empresa *'], ['cnpj', 'CNPJ'], ['address', 'Endereço Completo de Cobrança', 'textarea'], ['industry', 'Segmento'], ['status', 'Status', 'select', 'prospect,active,inactive'], ['health_score', 'Health score', 'number'], ['monthly_value', 'Valor mensal (R$)', 'number']] },
  projects: { label: 'Projetos', title: 'Projetos', description: 'Entregas organizadas por cliente, contato de cobrança e fase.', fields: [['name', 'Nome do Projeto *'], ['client_id', 'Cliente *', 'select-api', 'clients'], ['invoice_contact_id', 'Contato Designado para Faturas', 'select-api', 'contacts'], ['status', 'Status', 'select', 'planning,active,paused,completed'], ['project_value', 'Valor do projeto (R$)', 'number'], ['contract_type', 'Tipo de contrato', 'select', 'mensal,avulso'], ['description', 'Descrição', 'textarea'], ['start_date', 'Início', 'date'], ['due_date', 'Prazo', 'date']] },
  invoices: { label: 'Faturas', title: 'Faturas & Cobranças', description: 'Controle de faturamento, prazos de vencimento e recebimento por projeto.', fields: [['invoice_number', 'Número da Fatura *'], ['project_id', 'Projeto *', 'select-api', 'projects'], ['contact_id', 'Para quem foi enviada (Contato)', 'select-api', 'contacts'], ['amount', 'Valor (R$) *', 'number'], ['issue_date', 'Data de Emissão', 'date'], ['due_date', 'Data de Vencimento *', 'date'], ['payment_date', 'Data de Pagamento', 'date'], ['status', 'Status', 'select', 'pending,paid,overdue,draft,cancelled'], ['description', 'Descrição / Serviços Faturados *', 'textarea']] },
  tasks: { label: 'Tarefas', title: 'Central de tarefas', description: 'Priorize a execução e acompanhe prazos.', fields: [['title', 'Título *'], ['client_id', 'Cliente (opcional)', 'select-api', 'clients'], ['project_id', 'Projeto (opcional)', 'select-api', 'projects'], ['status', 'Status', 'select', 'todo,in_progress,done'], ['priority', 'Prioridade', 'select', 'low,medium,high'], ['due_date', 'Prazo', 'date'], ['description', 'Descrição', 'textarea']] },
  meetings: { label: 'Reuniões', title: 'Reuniões e agenda', description: 'Registre compromissos e decisões com os clientes.', fields: [['title', 'Título'], ['client_id', 'Cliente', 'select-api', 'clients'], ['starts_at', 'Data e hora', 'datetime-local'], ['duration_minutes', 'Duração (minutos)', 'number'], ['notes', 'Notas', 'textarea']] },
  contacts: { label: 'Contatos', title: 'Diretório de contatos', description: 'As pessoas-chave em cada conta.', fields: [['name', 'Nome'], ['email', 'E-mail', 'email'], ['role', 'Cargo'], ['phone', 'Telefone'], ['client_id', 'Cliente', 'select-api', 'clients']] },
  users: { label: 'Usuários', title: 'Usuários & Permissões', description: 'Controle de acessos e permissões da equipe e agentes de IA.', fields: [['name', 'Nome'], ['email', 'E-mail', 'email'], ['password', 'Senha', 'password'], ['role', 'Perfil', 'select', 'member,admin,agent'], ['is_active', 'Ativo', 'select', 'true,false']] },
  api_keys: { label: 'Agentes & API Keys', title: 'Chaves de API para Agentes de IA', description: 'Credenciais de acesso para agentes de IA autônomos e conexão com o Servidor MCP.', fields: [['name', 'Identificação do Agente (ex: Antigravity Assistant, Claude Desktop, Bot SDR)'], ['user_id', 'Vincular ao Usuário', 'select-api', 'users']] },
  backups: { label: 'Backups', title: 'Backup & Restauração', description: 'Gerenciamento de cópias de segurança do banco de dados e restauração do sistema.' }
};

document.head.insertAdjacentHTML('beforeend', '<link rel="stylesheet" href="/auth.css"><link rel="stylesheet" href="/dashboard.css">');
function getRoute() {
  let raw = location.hash.slice(1) || 'dashboard';
  let [sec, queryStr] = raw.split('?');
  let params = new URLSearchParams(queryStr || '');
  return { section: sec, params };
}

let { section } = getRoute(), records = [], editing = null, currentUser = null, forcedTargetSection = null;

const $ = s => document.querySelector(s),
      cap = s => s.charAt(0).toUpperCase() + s.slice(1),
      status = v => `<span class="pill ${v}">${String(v).replaceAll('_', ' ')}</span>`,
      money = v => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v || 0);

async function api(path, options = {}) {
  let token = localStorage.getItem('flowcrm_token');
  let endpoint = path.replace(/^api_keys/, 'api-keys');
  let isLogin = path === 'auth/login';
  const r = await fetch('/api/' + endpoint, {
    headers: {
      'Content-Type': 'application/json',
      ...((token && !isLogin) ? { Authorization: 'Bearer ' + token } : {})
    },
    ...options
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({ detail: 'Erro na requisição' }))).detail);
  return r.status === 204 ? null : r.json();
}

function nav() {
  const icons = {
    dashboard: '📊 ',
    clients: '🏢 ',
    projects: '🚀 ',
    invoices: '📄 ',
    tasks: '📋 ',
    meetings: '🤝 ',
    contacts: '📇 ',
    users: '👥 ',
    api_keys: '🤖 ',
    backups: '💾 '
  };

  let activeSection = section === 'project_details' ? 'projects' : (section === 'client_details' ? 'clients' : section);

  $('#nav').innerHTML = Object.entries(config)
    .filter(([key]) => (key !== 'users' && key !== 'api_keys' && key !== 'backups') || currentUser?.role === 'admin')
    .map(([key, x]) => {
      let icon = icons[key] || '';
      return `<button class="nav ${key === activeSection ? 'active' : ''}" data-go="${key}">${icon}${x.label}</button>`;
    })
    .join('');
  document.querySelectorAll('[data-go]').forEach(b => b.onclick = () => { location.hash = b.dataset.go; });
}

function title() {
  let c = config[section];
  let btnLabel = section === 'api_keys' ? '+ Gerar Nova Chave' : '+ Novo registro';
  return `<div class="title-row"><div><div class="eyebrow">FLOWCRM / OPERAÇÕES</div><h1>${c.title}</h1><p>${c.description}</p></div>${section !== 'dashboard' ? `<button id="create">${btnLabel}</button>` : ''}</div>`;
}

function projectArea(title, description, projects, kind) {
  return `<div class="project-area ${kind}"><div class="area-head"><div><div class="eyebrow">${kind === 'active' ? 'EM ANDAMENTO' : 'PROSPECÇÃO'}</div><h2>${title}</h2><p>${description}</p></div><span class="area-count">${projects.length}</span></div><div class="project-list">${projects.length ? projects.map(projectCard).join('') : '<div class="empty">Nenhum projeto nesta etapa.</div>'}</div></div>`;
}

function projectCard(p) {
  let contacts = p.contacts.length ? p.contacts.map(c => `<span>${c.name}${c.role ? ' · ' + c.role : ''}</span>`).join('') : 'Sem contatos vinculados';
  let tasks = p.tasks.length ? p.tasks.map(t => `<li>${t.title} ${status(t.status)}</li>`).join('') : '<li>Sem tarefas vinculadas</li>';
  return `<article class="project-card">
  <div class="project-top">
    <div>
      <h3 style="cursor:pointer" onclick="location.hash='project_details?id=${p.id}'" title="Ver detalhes do projeto">
        ${p.name} <span style="font-size:12px;color:var(--blue);font-weight:normal">👁️</span>
      </h3>
      <p>
        ${p.client?.name || 'Sem cliente'}
      </p>
    </div>
    ${p.due_date ? `<span class="due">Prazo: ${new Date(p.due_date + 'T12:00').toLocaleDateString('pt-BR')}</span>` : ''}
    </div>
    <div class="project-data">
      <div>
        <b>Valor do projeto</b><span>${money(p.project_value)}</span>
      </div>
      <div>
        <b>Tipo de contrato</b><span>${p.contract_type === 'avulso' ? 'Avulso' : 'Mensal'}</span>
      </div>
      <div>
        <b>Tarefas</b><span>${p.task_summary.done}/${p.task_summary.total} concluídas · ${p.task_summary.in_progress} em andamento</span>
      </div>
      <div>
        <b>Contatos</b><span>${contacts}</span>
      </div>
    </div>
    <ul class="project-tasks">${tasks}</ul></article>`;
}

async function dashboard() {
  let d = await api('dashboard');
  let y = d.year_metrics;
  let m = d.month_metrics;

  let monthName = new Date().toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
  monthName = monthName.charAt(0).toUpperCase() + monthName.slice(1);

  return title() + `
  <div style="display:grid;gap:24px;">
    <!-- 1. Visão Geral (Ano Corrente) -->
    <section>
      <div style="font-weight:700;font-size:16px;color:var(--ink);margin-bottom:12px;display:flex;align-items:center;gap:8px">
        <span>📅</span> Visão Geral — Ano Corrente (${y.year})
      </div>
      <div class="metrics" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;">
        <div class="card">
          <div class="metric-label">👥 Clientes</div>
          <div class="metric">${y.total_clients}</div>
          <p style="font-size:12px;color:var(--muted);margin-top:4px">Total cadastrado no sistema</p>
        </div>

        <div class="card">
          <div class="metric-label">🚀 Projetos</div>
          <div class="metric" style="font-size:22px;margin-top:6px">
            <span style="color:#0284c7" title="Ativos">${y.projects.active} ativos</span>
          </div>
          <p style="font-size:12px;color:var(--muted);margin-top:6px;display:flex;gap:8px">
            <span>✅ ${y.projects.completed} finalizados</span> · <span>📊 ${y.projects.total} total</span>
          </p>
        </div>

        <div class="card">
          <div class="metric-label">💰 Valores (Ano)</div>
          <div class="metric" style="font-size:20px;color:#047857;margin-top:6px" title="Faturas Pagas no Ano">
            ${money(y.values.paid_invoices)}
          </div>
          <p style="font-size:12px;color:var(--muted);margin-top:6px">
            Soma Projetos: <b>${money(y.values.total_projects)}</b>
          </p>
        </div>

        <div class="card">
          <div class="metric-label">📋 Tarefas</div>
          <div class="metric" style="font-size:22px;margin-top:6px">
            <span style="color:#d97706">${y.tasks.pending} pendentes</span>
          </div>
          <p style="font-size:12px;color:var(--muted);margin-top:6px">
            <span>✅ ${y.tasks.completed} concluídas</span> · <span>Total: ${y.tasks.total}</span>
          </p>
        </div>
      </div>
    </section>

    <!-- 2. Visão do Mês Corrente -->
    <section>
      <div style="font-weight:700;font-size:16px;color:var(--ink);margin-bottom:12px;display:flex;align-items:center;gap:8px">
        <span>🗓️</span> Visão do Mês — ${monthName}
      </div>
      <div class="metrics" style="grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px;">
        <div class="card" style="border-left: 4px solid #059669;">
          <div class="metric-label">💳 Faturas Pagas no Mês</div>
          <div class="metric" style="color:#059669;font-size:24px;margin-top:6px">${money(m.values.paid_invoices)}</div>
          <p style="font-size:12px;color:var(--muted);margin-top:4px">Faturamento já recebido neste mês</p>
        </div>

        <div class="card" style="border-left: 4px solid #2563eb;">
          <div class="metric-label">📈 Projetado no Mês</div>
          <div class="metric" style="color:#2563eb;font-size:24px;margin-top:6px">${money(m.values.projected_values)}</div>
          <p style="font-size:12px;color:var(--muted);margin-top:4px">Lançamentos mensais previstos</p>
        </div>

        <div class="card" style="border-left: 4px solid #d97706;">
          <div class="metric-label">📌 Tarefas do Mês</div>
          <div class="metric" style="color:#d97706;font-size:24px;margin-top:6px">${m.tasks_count}</div>
          <p style="font-size:12px;color:var(--muted);margin-top:4px">Tarefas com vencimento este mês</p>
        </div>

        <div class="card" style="border-left: 4px solid #7c3aed;">
          <div class="metric-label">🤝 Reuniões do Mês</div>
          <div class="metric" style="color:#7c3aed;font-size:24px;margin-top:6px">${m.meetings_count}</div>
          <p style="font-size:12px;color:var(--muted);margin-top:4px">Compromissos agendados no mês</p>
        </div>
      </div>
    </section>

    <!-- 3. Prospecção & Projetos em Andamento -->
    <section class="project-areas">
      ${projectArea('Oportunidades em Prospecção', 'Projetos em fase de planejamento e negociação comercial', d.prospecting_projects, 'planning')}
      ${projectArea('Projetos em Andamento', 'Execução e entregas ativas', d.in_progress_projects, 'active')}
    </section>
  </div>`;
}

function canDelete(record) {
  return currentUser?.role === 'admin' || record.created_by_id === currentUser?.id;
}

function columns() {
  return {
    users: [['name', 'Nome'], ['email', 'E-mail'], ['role', 'Perfil'], ['is_active', 'Status']],
    clients: [['name', 'Cliente'], ['cnpj', 'CNPJ'], ['industry', 'Segmento'], ['status', 'Status'], ['health_score', 'Health'], ['monthly_value', 'Valor mensal']],
    projects: [['name', 'Projeto'], ['client_name', 'Cliente'], ['project_value', 'Valor do projeto'], ['contract_type', 'Tipo de contrato'], ['invoice_contact_name', 'Contato Faturamento'], ['status', 'Status'], ['due_date', 'Prazo']],
    invoices: [['invoice_number', 'Fatura'], ['project_name', 'Projeto'], ['client_name', 'Cliente'], ['contact_name', 'Destinatário'], ['amount', 'Valor'], ['issue_date', 'Emissão'], ['due_date', 'Vencimento'], ['status', 'Status']],
    tasks: [['title', 'Tarefa'], ['client_name', 'Cliente'], ['project_name', 'Projeto'], ['status', 'Status'], ['priority', 'Prioridade'], ['due_date', 'Prazo']],
    meetings: [['title', 'Reunião'], ['client_id', 'Cliente'], ['starts_at', 'Data'], ['duration_minutes', 'Duração']],
    contacts: [['name', 'Contato'], ['email', 'E-mail'], ['role', 'Cargo'], ['client_id', 'Cliente']],
    api_keys: [['name', 'Identificação'], ['key_prefix', 'Prefixo'], ['user_name', 'Usuário Vinculado'], ['created_at', 'Criada em'], ['last_used_at', 'Último Uso']]
  }[section];
}

function cell(r, k) {
  let v = r[k];
  if (k === 'name' && section === 'clients') {
    return `<a href="#client_details?id=${r.id}" style="color:var(--blue);font-weight:600;text-decoration:none" title="Ver detalhes do cliente">${v}</a>`;
  }
  if (k === 'client_name') {
    return v ? `<a href="#client_details?id=${r.client_id}" style="color:var(--ink);font-weight:600;text-decoration:none" title="Ver detalhes do cliente">${v}</a>` : '—';
  }
  if (k === 'name' && section === 'projects') {
    return `<a href="#project_details?id=${r.id}" style="color:var(--blue);font-weight:600;text-decoration:none" title="Ver detalhes do projeto">${v}</a>`;
  }
  if (k === 'project_name') {
    return v ? `<a href="#project_details?id=${r.project_id}" style="color:var(--ink);font-weight:600;text-decoration:none" title="Ver detalhes do projeto">${v}</a>` : '—';
  }
  if (k === 'key_prefix') return `<code style="background:#f1f5f9;padding:3px 6px;border-radius:4px;font-family:monospace;font-weight:600">${v}••••••••</code>`;
  if (k === 'invoice_number') return `<code style="font-family:monospace;font-weight:700;color:var(--blue);font-size:13px">${v}</code>`;
  if (k === 'status' || k === 'priority') {
    if (section === 'invoices' && v === 'pending' && r.due_date && new Date(r.due_date + 'T23:59:59') < new Date()) {
      return `<span class="pill overdue" title="Vencida em ${new Date(r.due_date + 'T12:00').toLocaleDateString('pt-BR')}">Vencida</span>`;
    }
    return status(v);
  }
  if (k === 'role') return `<span class="pill ${v}">${v === 'agent' ? 'Agente IA' : (v === 'admin' ? 'Administrador' : 'Membro')}</span>`;
  if (k === 'is_active') return status(v ? 'active' : 'inactive');
  if (k === 'monthly_value' || k === 'amount' || k === 'project_value') return money(v);
  if (k === 'contract_type') return v === 'avulso' ? 'Avulso' : 'Mensal';
  if (k === 'health_score') return `${v}%`;
  if (k === 'starts_at' || k === 'created_at') return v ? new Date(v).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—';
  if (k === 'due_date' || k === 'issue_date' || k === 'payment_date' || k === 'start_date') return v ? new Date(v + 'T12:00').toLocaleDateString('pt-BR') : '—';
  if (k === 'last_used_at') return v ? new Date(v).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '<span style="color:#94a3b8">Nunca utilizada</span>';
  if (k === 'duration_minutes') return `${v} min`;
  if (k === 'contact_name') return v ? `<b>${v}</b>${r.contact_email ? `<br><small style="color:var(--muted)">${r.contact_email}</small>` : ''}` : '—';
  if (k === 'invoice_contact_name') return v ? `<b>${v}</b>${r.invoice_contact_email ? `<br><small style="color:var(--muted)">${r.invoice_contact_email}</small>` : ''}` : '<span style="color:#94a3b8">Não definido</span>';
  if (k.endsWith('_id')) return v ? '#' + v : '—';
  return v || '—';
}

function integrationBanners() {
  if (section === 'api_keys') {
    return `<div class="card" style="margin-bottom:20px;border-left:4px solid var(--blue)">
      <div style="font-weight:700;font-size:15px;margin-bottom:6px">🤖 Servidor MCP (Model Context Protocol) & Conexão de Agentes</div>
      <p style="font-size:13px;line-height:1.5;margin-bottom:12px">Os agentes de IA (como Claude Desktop, Antigravity e Cursor) conectam-se diretamente ao FlowCRM via <b>SSE (Server-Sent Events)</b> utilizando as chaves geradas abaixo.</p>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;font-size:12px">
        <div style="background:#f8fafc;padding:10px 14px;border-radius:8px;border:1px solid #e2e8f0">
          <b style="color:#475569">Endpoint MCP (SSE):</b><br><code style="color:#2563eb;font-weight:600">http://localhost:8000/mcp/sse</code>
        </div>
        <div style="background:#f8fafc;padding:10px 14px;border-radius:8px;border:1px solid #e2e8f0">
          <b style="color:#475569">Autenticação:</b><br>Header <code style="font-weight:600">X-API-Key: fc_live_...</code> ou <code style="font-weight:600">?api_key=fc_live_...</code>
        </div>
      </div>
    </div>`;
  }
  if (section === 'users') {
    return `<div class="card" style="margin-bottom:18px;display:flex;justify-content:space-between;align-items:center;background:#f0fdf4;border-color:#bbf7d0">
      <div>
        <b style="color:#166534;font-size:14px">🤖 Integração com Agentes de IA & MCP</b>
        <p style="color:#15803d;font-size:12px;margin:2px 0 0">Gere e gerencie chaves de API com permissões controladas para assistentes de IA e automações.</p>
      </div>
      <button type="button" onclick="location.hash='api_keys'" style="background:#16a34a;color:#fff;border:0;font-size:12px;padding:8px 14px;white-space:nowrap">🔑 Ver Chaves de API →</button>
    </div>`;
  }
  return '';
}

async function table() {
  records = await api(section);
  let cols = columns();
  let rows = records.map(r => `<tr>
    ${cols.map(([k]) => `<td>${cell(r, k)}</td>`).join('')}
    <td class="actions-cell">
      ${section === 'clients' ? `<button class="link client-details-btn" data-id="${r.id}" style="color:var(--blue);font-weight:600">👁️ Detalhes</button>` : ''}
      ${section === 'projects' ? `<button class="link project-details-btn" data-id="${r.id}" style="color:var(--blue);font-weight:600">👁️ Detalhes</button><button class="link monthly-values-btn" data-id="${r.id}" data-name="${r.name}" style="color:#0284c7;font-weight:600">💰 Valores</button>` : ''}
      ${section === 'users' && currentUser?.role === 'admin' ? `<button class="link generate-key-user" data-user-id="${r.id}" data-user-name="${r.name}" style="color:#16a34a;font-weight:600">🔑 Gerar Chave</button>` : ''}
      ${section !== 'api_keys' ? `<button class="link edit" data-id="${r.id}">Editar</button>` : ''}
      ${canDelete(r) ? `<button class="link danger remove" data-id="${r.id}">${section === 'api_keys' ? 'Revogar' : 'Excluir'}</button>` : ''}
    </td>
  </tr>`).join('');

  return title() + integrationBanners() + `<div class="table-card"><table><thead><tr>${cols.map(c => `<th>${c[1]}</th>`).join('')}<th></th></tr></thead><tbody>${rows || `<tr><td colspan="${cols.length + 1}" class="empty">Nenhum registro encontrado.</td></tr>`}</tbody></table></div>`;
}

async function projectDetails(projectId) {
  if (!projectId) {
    return `<div class="card"><b>ID do projeto não especificado.</b><p style="margin-top:8px"><a href="#projects">← Voltar para Projetos</a></p></div>`;
  }
  try {
    let p = await api(`projects/${projectId}/details`);
    let client = p.cliente;
    let invContact = p.invoice_contact;
    let contacts = p.contatos || [];
    let monthly = p.valores_mensais || [];
    let invoices = p.faturas || [];
    let tasks = p.tarefas || [];
    let meetings = p.reunioes || [];

    let totalMonthlySum = monthly.reduce((acc, item) => acc + (item.amount || 0), 0);
    let paidInvoicesSum = invoices.filter(i => i.status === 'paid').reduce((acc, item) => acc + (item.amount || 0), 0);

    let monthlyRows = monthly.length ? monthly.map(m => {
      let parts = m.year_month.split('-');
      return `<tr>
        <td style="font-weight:600">${parts[1]}/${parts[0]}</td>
        <td style="color:#047857;font-weight:600">${money(m.amount)}</td>
        <td style="color:var(--muted);font-size:12px">${m.notes || '—'}</td>
      </tr>`;
    }).join('') : `<tr><td colspan="3" class="empty">Nenhum valor mensal registrado.</td></tr>`;

    let invoiceRows = invoices.length ? invoices.map(inv => `<tr>
      <td><code style="font-family:monospace;font-weight:700;color:var(--blue);font-size:13px">${inv.invoice_number}</code></td>
      <td>${inv.description || '—'}</td>
      <td style="font-weight:600">${money(inv.amount)}</td>
      <td>${inv.issue_date ? new Date(inv.issue_date + 'T12:00').toLocaleDateString('pt-BR') : '—'}</td>
      <td>${inv.due_date ? new Date(inv.due_date + 'T12:00').toLocaleDateString('pt-BR') : '—'}</td>
      <td>${status(inv.status)}</td>
    </tr>`).join('') : `<tr><td colspan="6" class="empty">Nenhuma fatura vinculada a este projeto.</td></tr>`;

    let taskRows = tasks.length ? tasks.map(t => `<tr>
      <td><b>${t.title}</b>${t.description ? `<br><small style="color:var(--muted)">${t.description}</small>` : ''}</td>
      <td>${status(t.status)}</td>
      <td><span class="pill ${t.priority}">${t.priority}</span></td>
      <td>${t.due_date ? new Date(t.due_date + 'T12:00').toLocaleDateString('pt-BR') : '—'}</td>
    </tr>`).join('') : `<tr><td colspan="4" class="empty">Nenhuma tarefa vinculada.</td></tr>`;

    let meetingRows = meetings.length ? meetings.map(m => `<tr>
      <td><b>${m.title}</b>${m.notes ? `<br><small style="color:var(--muted)">${m.notes}</small>` : ''}</td>
      <td>${m.starts_at ? new Date(m.starts_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—'}</td>
      <td>${m.duration_minutes} min</td>
    </tr>`).join('') : `<tr><td colspan="3" class="empty">Nenhuma reunião com o cliente.</td></tr>`;

    let contactList = contacts.length ? contacts.map(c => `
      <div style="background:#f8fafc;padding:10px 12px;border-radius:8px;border:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center">
        <div>
          <b style="color:var(--ink);font-size:13px">${c.name}</b>
          <div style="font-size:12px;color:var(--muted)">${c.role || 'Sem cargo'} ${c.email ? '· ' + c.email : ''}</div>
        </div>
        ${c.phone ? `<span style="font-size:12px;background:#e2e8f0;padding:2px 8px;border-radius:4px">📞 ${c.phone}</span>` : ''}
      </div>
    `).join('') : `<div style="color:var(--muted);font-size:13px">Nenhum outro contato cadastrado.</div>`;

    return `
    <div style="display:grid;gap:20px;">
      <!-- Cabeçalho de detalhes do projeto -->
      <div class="card" style="padding:20px;border-left:5px solid var(--blue)">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
          <div>
            <button type="button" class="secondary" onclick="location.hash='projects'" style="padding:4px 10px;font-size:12px;margin-bottom:10px">← Voltar para Projetos</button>
            <div class="eyebrow">PROJETO #${p.id}</div>
            <h1 style="font-size:24px;margin:4px 0 8px">${p.name}</h1>
            <p style="color:var(--muted);font-size:14px;margin:0 0 12px">${p.description || 'Sem descrição detalhada.'}</p>
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            <button type="button" class="monthly-details-btn" data-id="${p.id}" data-name="${p.name}" style="background:#0284c7;color:#fff;border:0;padding:8px 14px;font-size:13px">💰 Gerenciar Valores Mensais</button>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-top:16px;padding-top:16px;border-top:1px solid #e2e8f0">
          <div><b style="font-size:11px;color:var(--muted);text-transform:uppercase">Status</b><div style="margin-top:4px">${status(p.status)}</div></div>
          <div><b style="font-size:11px;color:var(--muted);text-transform:uppercase">Valor do Projeto</b><div style="font-size:16px;font-weight:700;color:#047857">${money(p.project_value)}</div></div>
          <div><b style="font-size:11px;color:var(--muted);text-transform:uppercase">Contrato</b><div style="font-size:14px;font-weight:600">${p.contract_type === 'avulso' ? 'Avulso' : 'Mensal'}</div></div>
          <div><b style="font-size:11px;color:var(--muted);text-transform:uppercase">Início</b><div style="font-size:14px">${p.start_date ? new Date(p.start_date + 'T12:00').toLocaleDateString('pt-BR') : '—'}</div></div>
          <div><b style="font-size:11px;color:var(--muted);text-transform:uppercase">Prazo / Término</b><div style="font-size:14px">${p.due_date ? new Date(p.due_date + 'T12:00').toLocaleDateString('pt-BR') : '—'}</div></div>
        </div>
      </div>

      <!-- Bloco 1: Cliente & Contato de Cobrança -->
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:20px">
        <div class="card">
          <div style="font-weight:700;font-size:15px;margin-bottom:12px;display:flex;align-items:center;gap:8px">
            <span>🏢</span> Cliente & Dados Fiscais
          </div>
          ${client ? `
            <div style="display:grid;gap:8px;font-size:13px">
              <div><b>Empresa:</b> <a href="#client_details?id=${client.id}" style="color:var(--blue);font-weight:600;text-decoration:none" title="Ver detalhes do cliente">${client.nome} 👁️</a></div>
              <div><b>CNPJ:</b> ${client.cnpj || '—'}</div>
              <div><b>Segmento:</b> ${client.industry || '—'}</div>
              <div><b>Health Score:</b> ${client.health_score}%</div>
              <div><b>Endereço de Cobrança:</b> ${client.endereco || '—'}</div>
            </div>
          ` : '<div style="color:var(--muted)">Nenhum cliente vinculado a este projeto.</div>'}
        </div>

        <div class="card">
          <div style="font-weight:700;font-size:15px;margin-bottom:12px;display:flex;align-items:center;gap:8px">
            <span>📇</span> Contatos Relacionados
          </div>
          <div style="margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #e2e8f0;font-size:13px">
            <b style="font-size:11px;color:var(--muted);text-transform:uppercase;display:block;margin-bottom:4px">Contato Designado para Faturas</b>
            ${invContact ? `<b>${invContact.name}</b> ${invContact.email ? `(${invContact.email})` : ''} ${invContact.phone ? `· 📞 ${invContact.phone}` : ''}` : '<span style="color:#94a3b8">Não definido</span>'}
          </div>
          <div style="display:grid;gap:8px">
            <b style="font-size:11px;color:var(--muted);text-transform:uppercase">Outros Contatos do Cliente</b>
            ${contactList}
          </div>
        </div>
      </div>

      <!-- Bloco 2: Valores Mensais & Faturas -->
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:20px">
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <div style="font-weight:700;font-size:15px;display:flex;align-items:center;gap:8px">
              <span>💰</span> Histórico de Valores Mensais
            </div>
            <button type="button" class="monthly-details-btn link" data-id="${p.id}" data-name="${p.name}" style="font-size:12px;color:#0284c7;font-weight:600">+ Gerar / Editar</button>
          </div>
          <div class="table-card" style="box-shadow:none;border:1px solid #e2e8f0">
            <table>
              <thead><tr><th>Mês/Ano</th><th>Valor</th><th>Observações</th></tr></thead>
              <tbody>${monthlyRows}</tbody>
            </table>
          </div>
          <div style="margin-top:10px;text-align:right;font-size:12px;color:var(--muted)">Total lançado: <b style="color:#047857">${money(totalMonthlySum)}</b></div>
        </div>

        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <div style="font-weight:700;font-size:15px;display:flex;align-items:center;gap:8px">
              <span>📄</span> Histórico de Faturas (${invoices.length})
            </div>
            <div style="font-size:12px;color:var(--muted)">Pagas: <b style="color:#047857">${money(paidInvoicesSum)}</b></div>
          </div>
          <div class="table-card" style="box-shadow:none;border:1px solid #e2e8f0">
            <table>
              <thead><tr><th>Fatura</th><th>Descrição</th><th>Valor</th><th>Emissão</th><th>Vencimento</th><th>Status</th></tr></thead>
              <tbody>${invoiceRows}</tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Bloco 3: Tarefas & Reuniões -->
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:20px">
        <div class="card">
          <div style="font-weight:700;font-size:15px;margin-bottom:12px;display:flex;align-items:center;gap:8px">
            <span>📋</span> Tarefas Relacionadas (${tasks.length})
          </div>
          <div class="table-card" style="box-shadow:none;border:1px solid #e2e8f0">
            <table>
              <thead><tr><th>Tarefa</th><th>Status</th><th>Prioridade</th><th>Prazo</th></tr></thead>
              <tbody>${taskRows}</tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div style="font-weight:700;font-size:15px;margin-bottom:12px;display:flex;align-items:center;gap:8px">
            <span>🤝</span> Reuniões do Cliente (${meetings.length})
          </div>
          <div class="table-card" style="box-shadow:none;border:1px solid #e2e8f0">
            <table>
              <thead><tr><th>Reunião</th><th>Data e Hora</th><th>Duração</th></tr></thead>
              <tbody>${meetingRows}</tbody>
            </table>
          </div>
        </div>
      </div>
    </div>`;
  } catch (err) {
    return `<div class="card"><b>Erro ao carregar detalhes do projeto.</b><p style="color:var(--red)">${err.message}</p><button type="button" onclick="location.hash='projects'">← Voltar para Projetos</button></div>`;
  }
}

function attachProjectDetailsListeners(projectId) {
  document.querySelectorAll('.monthly-details-btn').forEach(btn => {
    btn.onclick = () => {
      openMonthlyValuesModal(Number(btn.dataset.id), btn.dataset.name);
    };
  });
}

async function clientDetails(clientId) {
  if (!clientId) {
    return `<div class="card"><b>ID do cliente não especificado.</b><p style="margin-top:8px"><a href="#clients">← Voltar para Clientes</a></p></div>`;
  }
  try {
    let d = await api(`clients/${clientId}/details`);
    let c = d.cliente || d.client;
    let contacts = d.contatos || d.contacts || [];
    let projects = d.projetos || d.projects || [];
    let invoices = d.faturas || d.invoices || [];
    let meetings = d.reunioes || d.meetings || [];
    let tasks = d.tarefas || d.tasks || [];
    let m = d.metricas || d.metrics || {};

    let healthColor = c.health_score >= 80 ? '#059669' : (c.health_score >= 50 ? '#d97706' : '#dc2626');

    let contactRows = contacts.length ? contacts.map(ct => `
      <div style="background:#f8fafc;padding:12px 14px;border-radius:8px;border:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center">
        <div>
          <b style="color:var(--ink);font-size:14px">${ct.name || ct.nome}</b>
          <div style="font-size:12px;color:var(--muted);margin-top:2px">${ct.role || ct.cargo || 'Sem cargo'} ${ct.email ? '· ✉️ ' + ct.email : ''}</div>
        </div>
        ${(ct.phone || ct.telefone) ? `<span style="font-size:12px;background:#e2e8f0;padding:4px 10px;border-radius:6px;font-weight:500">📞 ${ct.phone || ct.telefone}</span>` : ''}
      </div>
    `).join('') : `<div style="color:var(--muted);font-size:13px">Nenhum contato cadastrado para este cliente.</div>`;

    let projectRows = projects.length ? projects.map(p => `<tr>
      <td><b><a href="#project_details?id=${p.id}" style="color:var(--blue);font-weight:600;text-decoration:none">${p.name || p.nome} 👁️</a></b></td>
      <td>${status(p.status)}</td>
      <td>${p.contract_type === 'avulso' ? 'Avulso' : 'Mensal'}</td>
      <td style="font-weight:600;color:#047857">${money(p.project_value)}</td>
      <td>${p.due_date ? new Date(p.due_date + 'T12:00').toLocaleDateString('pt-BR') : '—'}</td>
      <td style="text-align:right"><button type="button" class="link" onclick="location.hash='project_details?id=${p.id}'" style="color:var(--blue);font-size:12px;font-weight:600">👁️ Detalhes</button></td>
    </tr>`).join('') : `<tr><td colspan="6" class="empty">Nenhum projeto registrado para este cliente.</td></tr>`;

    let invoiceRows = invoices.length ? invoices.map(inv => `<tr>
      <td><code style="font-family:monospace;font-weight:700;color:var(--blue);font-size:13px">${inv.invoice_number || inv.numero_fatura}</code></td>
      <td>${inv.project_name ? `<a href="#project_details?id=${inv.project_id}" style="color:var(--ink);text-decoration:none">${inv.project_name}</a>` : '—'}</td>
      <td style="font-weight:600">${money(inv.amount || inv.valor)}</td>
      <td>${inv.issue_date ? new Date(inv.issue_date + 'T12:00').toLocaleDateString('pt-BR') : '—'}</td>
      <td>${inv.due_date ? new Date(inv.due_date + 'T12:00').toLocaleDateString('pt-BR') : '—'}</td>
      <td>${status(inv.status)}</td>
    </tr>`).join('') : `<tr><td colspan="6" class="empty">Nenhuma fatura lançada para os projetos deste cliente.</td></tr>`;

    let taskRows = tasks.length ? tasks.map(t => `<tr>
      <td><b>${t.title || t.titulo}</b>${t.description ? `<br><small style="color:var(--muted)">${t.description}</small>` : ''}</td>
      <td>${t.project_id ? `<a href="#project_details?id=${t.project_id}" style="color:var(--blue);font-weight:600;text-decoration:none"><small>${t.project_name}</small></a>` : `<small style="color:var(--muted)">Sem projeto</small>`}</td>
      <td>${status(t.status)}</td>
      <td><span class="pill ${t.priority}">${t.priority}</span></td>
      <td>${t.due_date ? new Date(t.due_date + 'T12:00').toLocaleDateString('pt-BR') : '—'}</td>
    </tr>`).join('') : `<tr><td colspan="5" class="empty">Nenhuma tarefa ativa.</td></tr>`;

    let meetingRows = meetings.length ? meetings.map(mt => `<tr>
      <td><b>${mt.title || mt.titulo}</b>${mt.notes ? `<br><small style="color:var(--muted)">${mt.notes}</small>` : ''}</td>
      <td>${mt.starts_at ? new Date(mt.starts_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—'}</td>
      <td>${mt.duration_minutes} min</td>
    </tr>`).join('') : `<tr><td colspan="3" class="empty">Nenhuma reunião registrada com este cliente.</td></tr>`;

    return `
    <div style="display:grid;gap:20px;">
      <!-- Cabeçalho Principal do Cliente -->
      <div class="card" style="padding:20px;border-left:5px solid #2563eb">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
          <div>
            <button type="button" class="secondary" onclick="location.hash='clients'" style="padding:4px 10px;font-size:12px;margin-bottom:10px">← Voltar para Clientes</button>
            <div class="eyebrow">CLIENTE #${c.id}</div>
            <h1 style="font-size:26px;margin:4px 0 8px;display:flex;align-items:center;gap:10px">
              ${c.name || c.nome}
              ${status(c.status)}
            </h1>
            <p style="color:var(--muted);font-size:13px;margin:0 0 12px">
              ${c.industry || c.segmento ? 'Segmento: <b>' + (c.industry || c.segmento) + '</b> · ' : ''}
              CNPJ: <b>${c.cnpj || 'Não informado'}</b>
            </p>
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            <button type="button" class="edit-client-btn" data-id="${c.id}" style="background:var(--blue);color:#fff;border:0;padding:8px 14px;font-size:13px">✏️ Editar Cliente</button>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-top:16px;padding-top:16px;border-top:1px solid #e2e8f0">
          <div>
            <b style="font-size:11px;color:var(--muted);text-transform:uppercase">Health Score</b>
            <div style="font-size:18px;font-weight:700;color:${healthColor};margin-top:2px">
              ${c.health_score}%
              <span style="font-size:12px;font-weight:normal;color:var(--muted)">/ 100</span>
            </div>
          </div>
          <div>
            <b style="font-size:11px;color:var(--muted);text-transform:uppercase">Valor Mensal (MRR)</b>
            <div style="font-size:18px;font-weight:700;color:#047857;margin-top:2px">${money(c.monthly_value)}</div>
          </div>
          <div>
            <b style="font-size:11px;color:var(--muted);text-transform:uppercase">Endereço de Cobrança</b>
            <div style="font-size:13px;color:var(--ink);margin-top:2px">${c.address || c.endereco || '—'}</div>
          </div>
        </div>
      </div>

      <!-- Métricas em Cards -->
      <div class="metrics" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;">
        <div class="card" style="border-left: 4px solid #2563eb;">
          <div class="metric-label">🚀 Projetos</div>
          <div class="metric" style="font-size:24px;color:#2563eb;margin-top:4px">${m.active_projects || 0} ativos</div>
          <p style="font-size:12px;color:var(--muted);margin-top:4px">${m.total_projects || 0} projetos no total</p>
        </div>

        <div class="card" style="border-left: 4px solid #059669;">
          <div class="metric-label">💰 Faturamento Pago (Acumulado)</div>
          <div class="metric" style="font-size:22px;color:#059669;margin-top:4px">${money(m.paid_invoices_sum)}</div>
          <p style="font-size:12px;color:var(--muted);margin-top:4px">Total Faturado: <b>${money(m.total_invoiced)}</b></p>
        </div>

        <div class="card" style="border-left: 4px solid #d97706;">
          <div class="metric-label">📋 Tarefas da Conta</div>
          <div class="metric" style="font-size:24px;color:#d97706;margin-top:4px">${m.pending_tasks_count || 0} pendentes</div>
          <p style="font-size:12px;color:var(--muted);margin-top:4px">${m.total_tasks_count || 0} tarefas associadas</p>
        </div>

        <div class="card" style="border-left: 4px solid #7c3aed;">
          <div class="metric-label">🤝 Reuniões</div>
          <div class="metric" style="font-size:24px;color:#7c3aed;margin-top:4px">${meetings.length}</div>
          <p style="font-size:12px;color:var(--muted);margin-top:4px">Compromissos com a conta</p>
        </div>
      </div>

      <!-- Bloco 1: Projetos & Contatos da Conta -->
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:20px">
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <div style="font-weight:700;font-size:15px;display:flex;align-items:center;gap:8px">
              <span>🚀</span> Projetos da Empresa (${projects.length})
            </div>
            <button type="button" class="link" onclick="openForm({ client_id: ${c.id} }); section='projects';" style="font-size:12px;color:var(--blue);font-weight:600">+ Novo Projeto</button>
          </div>
          <div class="table-card" style="box-shadow:none;border:1px solid #e2e8f0">
            <table>
              <thead><tr><th>Projeto</th><th>Status</th><th>Tipo</th><th>Valor</th><th>Prazo</th><th></th></tr></thead>
              <tbody>${projectRows}</tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <div style="font-weight:700;font-size:15px;display:flex;align-items:center;gap:8px">
              <span>📇</span> Contatos da Conta (${contacts.length})
            </div>
            <button type="button" class="link" onclick="openForm({ client_id: ${c.id} }); section='contacts';" style="font-size:12px;color:var(--blue);font-weight:600">+ Novo Contato</button>
          </div>
          <div style="display:grid;gap:10px">
            ${contactRows}
          </div>
        </div>
      </div>

      <!-- Bloco 2: Faturas & Reuniões -->
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:20px">
        <div class="card">
          <div style="font-weight:700;font-size:15px;margin-bottom:12px;display:flex;align-items:center;gap:8px">
            <span>📄</span> Histórico de Faturas & Cobranças (${invoices.length})
          </div>
          <div class="table-card" style="box-shadow:none;border:1px solid #e2e8f0">
            <table>
              <thead><tr><th>Fatura</th><th>Projeto</th><th>Valor</th><th>Emissão</th><th>Vencimento</th><th>Status</th></tr></thead>
              <tbody>${invoiceRows}</tbody>
            </table>
          </div>
        </div>

        <div class="card">
          <div style="font-weight:700;font-size:15px;margin-bottom:12px;display:flex;align-items:center;gap:8px">
            <span>🤝</span> Reuniões & Compromissos (${meetings.length})
          </div>
          <div class="table-card" style="box-shadow:none;border:1px solid #e2e8f0">
            <table>
              <thead><tr><th>Reunião</th><th>Data/Hora</th><th>Duração</th></tr></thead>
              <tbody>${meetingRows}</tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Bloco 3: Tarefas da Conta -->
      <div class="card">
        <div style="font-weight:700;font-size:15px;margin-bottom:12px;display:flex;align-items:center;gap:8px">
          <span>📋</span> Central de Tarefas Ativas (${tasks.length})
        </div>
        <div class="table-card" style="box-shadow:none;border:1px solid #e2e8f0">
          <table>
            <thead><tr><th>Tarefa</th><th>Projeto</th><th>Status</th><th>Prioridade</th><th>Prazo</th></tr></thead>
            <tbody>${taskRows}</tbody>
          </table>
        </div>
      </div>
    </div>`;
  } catch (err) {
    return `<div class="card"><b>Erro ao carregar detalhes do cliente.</b><p style="color:var(--red)">${err.message}</p><button type="button" onclick="location.hash='clients'">← Voltar para Clientes</button></div>`;
  }
}

function attachClientDetailsListeners(clientId) {
  document.querySelectorAll('.edit-client-btn').forEach(btn => {
    btn.onclick = () => {
      let clientRec = records.find(r => r.id == btn.dataset.id);
      section = 'clients';
      openForm(clientRec);
    };
  });
}

async function backupsView() {
  try {
    let backups = await api('v1/admin/backups');
    let rows = backups.length ? backups.map(b => {
      let sizeMb = (b.size_bytes / (1024 * 1024)).toFixed(2);
      let dateStr = b.created_at ? new Date(b.created_at).toLocaleString('pt-BR') : '-';
      let labelPill = b.label === 'daily' ? '<span class="pill active">Diário</span>' : (b.label.includes('safety') ? '<span class="pill paused">Safety Snapshot</span>' : '<span class="pill completed">Manual</span>');
      return `<tr>
        <td><b>${b.filename}</b></td>
        <td>${labelPill}</td>
        <td>${sizeMb} MB (${b.size_bytes} B)</td>
        <td>${dateStr}</td>
        <td><code style="font-size:11px;color:var(--muted)" title="${b.checksum_sha256}">${(b.checksum_sha256 || '').slice(0, 12)}...</code></td>
        <td style="text-align:right">
          <a class="secondary" href="/api/v1/admin/backups/${b.filename}/download" download style="display:inline-block;padding:4px 8px;font-size:12px;margin-right:6px;text-decoration:none;border:1px solid #cbd5e1;border-radius:6px;color:#334155;">📥 Baixar</a>
          <button type="button" class="restore-backup-btn" data-file="${b.filename}" style="font-size:12px;padding:4px 8px;margin-right:6px;background:#f59e0b;color:white;border:none;border-radius:6px;cursor:pointer;">🔄 Restaurar</button>
          <button type="button" class="delete-backup-btn" data-file="${b.filename}" style="font-size:12px;padding:4px 8px;background:#ef4444;color:white;border:none;border-radius:6px;cursor:pointer;">🗑️</button>
        </td>
      </tr>`;
    }).join('') : '<tr><td colspan="6" style="text-align:center;padding:20px;color:var(--muted)">Nenhum backup encontrado.</td></tr>';

    return `${title()}
      <div style="margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;background:#f8fafc;padding:14px 18px;border-radius:10px;border:1px solid #e2e8f0">
        <div>
          <b style="font-size:14px;color:var(--ink)">⚙️ Rotina Diária Automática</b>
          <p style="margin:2px 0 0;font-size:12px;color:var(--muted)">Executada todos os dias às 02:00 AM com retenção automática de 30 dias.</p>
        </div>
        <button type="button" id="trigger-backup-now-btn" style="padding:8px 16px;font-size:13px;background:var(--blue);color:white;border:none;border-radius:8px;cursor:pointer;font-weight:600">+ Criar Backup Agora</button>
      </div>
      <div class="table-card">
        <table>
          <thead>
            <tr>
              <th>Arquivo</th>
              <th>Origem / Rótulo</th>
              <th>Tamanho</th>
              <th>Data de Criação</th>
              <th>Checksum (SHA-256)</th>
              <th style="text-align:right">Ações</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  } catch (err) {
    return `<div class="card"><b>Erro ao carregar backups.</b><p style="color:var(--red)">${err.message}</p></div>`;
  }
}

function attachBackupListeners() {
  let triggerBtn = $('#trigger-backup-now-btn');
  if (triggerBtn) {
    triggerBtn.onclick = async () => {
      triggerBtn.disabled = true;
      triggerBtn.textContent = '⏳ Criando backup...';
      try {
        await api('v1/admin/backups', { method: 'POST', body: JSON.stringify({ label: 'manual' }) });
        alert('Backup criado com sucesso!');
        render();
      } catch (err) {
        alert('Erro ao criar backup: ' + err.message);
      } finally {
        triggerBtn.disabled = false;
        triggerBtn.textContent = '+ Criar Backup Agora';
      }
    };
  }

  document.querySelectorAll('.restore-backup-btn').forEach(btn => {
    btn.onclick = async () => {
      let fname = btn.dataset.file;
      if (confirm(`ATENÇÃO: Deseja realmente restaurar o banco de dados a partir do arquivo '${fname}'?\n\nUm Safety Snapshot do estado atual será criado automaticamente antes da restauração.`)) {
        btn.disabled = true;
        btn.textContent = '⏳ Restaurando...';
        try {
          let res = await api(`v1/admin/backups/${fname}/restore`, {
            method: 'POST',
            body: JSON.stringify({ confirm: true, safety_snapshot: true })
          });
          alert(`Restauração concluída com sucesso!\nSafety Snapshot criado: ${res.safety_snapshot || 'Nenhum'}`);
          render();
        } catch (err) {
          alert('Erro na restauração: ' + err.message);
        } finally {
          btn.disabled = false;
          btn.textContent = '🔄 Restaurar';
        }
      }
    };
  });

  document.querySelectorAll('.delete-backup-btn').forEach(btn => {
    btn.onclick = async () => {
      let fname = btn.dataset.file;
      if (confirm(`Excluir permanentemente o backup '${fname}'?`)) {
        try {
          await api(`v1/admin/backups/${fname}`, { method: 'DELETE' });
          render();
        } catch (err) {
          alert('Erro ao excluir backup: ' + err.message);
        }
      }
    };
  });
}

async function render() {
  let route = getRoute();
  section = route.section;
  nav();
  try {
    if (section === 'client_details') {
      let cid = Number(route.params.get('id'));
      $('#view').innerHTML = await clientDetails(cid);
      attachClientDetailsListeners(cid);
    } else if (section === 'project_details') {
      let pid = Number(route.params.get('id'));
      $('#view').innerHTML = await projectDetails(pid);
      attachProjectDetailsListeners(pid);
    } else if (section === 'backups') {
      $('#view').innerHTML = await backupsView();
      attachBackupListeners();
    } else {
      $('#view').innerHTML = section === 'dashboard' ? await dashboard() : await table();
      $('#create')?.addEventListener('click', () => openForm());
      document.querySelectorAll('.edit').forEach(x => x.onclick = () => openForm(records.find(r => r.id == x.dataset.id)));
      document.querySelectorAll('.monthly-values-btn').forEach(btn => {
        btn.onclick = () => {
          openMonthlyValuesModal(Number(btn.dataset.id), btn.dataset.name);
        };
      });
      document.querySelectorAll('.client-details-btn').forEach(btn => {
        btn.onclick = () => {
          location.hash = `client_details?id=${btn.dataset.id}`;
        };
      });
      document.querySelectorAll('.project-details-btn').forEach(btn => {
        btn.onclick = () => {
          location.hash = `project_details?id=${btn.dataset.id}`;
        };
      });
      document.querySelectorAll('.generate-key-user').forEach(btn => {
        btn.onclick = () => {
          openApiKeyModal(Number(btn.dataset.userId), btn.dataset.userName);
        };
      });
      document.querySelectorAll('.remove').forEach(x => x.onclick = async () => {
        let promptMsg = section === 'api_keys' ? 'Revogar esta chave de API imediatamente? O agente perderá acesso.' : 'Excluir este registro?';
        if (confirm(promptMsg)) {
          await api(`${section}/${x.dataset.id}`, { method: 'DELETE' });
          render();
        }
      });
    }
  } catch (e) {
    $('#view').innerHTML = `<div class="card"><b>Não foi possível carregar os dados.</b><p>${e.message}</p></div>`;
  }
}

async function openApiKeyModal(userId, userName) {
  forcedTargetSection = 'api_keys';
  editing = null;
  $('#form-title').textContent = `Gerar Chave de API para ${userName}`;
  $('#fields').innerHTML = `
    <div class="field">
      <label>Identificação da Chave</label>
      <input name="name" type="text" value="Chave para ${userName}" required placeholder="Ex: Antigravity Assistant, Bot SDR">
    </div>
    <input name="user_id" type="hidden" value="${userId}">
  `;
  $('#error').textContent = '';
  $('#modal').showModal();
}

async function openForm(record = null) {
  forcedTargetSection = null;
  editing = record;
  let isApiKey = section === 'api_keys';
  $('#form-title').textContent = isApiKey ? 'Gerar Chave de API' : (record ? 'Editar registro' : 'Novo ' + config[section].label.slice(0, -1));
  let data = record || {};
  let projRowsCache = null;

  $('#fields').innerHTML = (await Promise.all(config[section].fields.map(async ([name, label, type = 'text', opts]) => {
    let val = data[name] ?? defaults(name);
    if (type === 'select-api') {
      let rows = await api(opts);
      if (opts === 'projects') projRowsCache = rows;
      return field(name, label, `<select name="${name}"><option value="">${isApiKey ? 'Agente IA Padrão' : 'Sem vínculo'}</option>${rows.map(r => `<option value="${r.id}" ${r.id == val ? 'selected' : ''}>${r.name}</option>`).join('')}</select>`);
    }
    if (type === 'select') {
      return field(name, label, `<select name="${name}">${opts.split(',').map(o => `<option value="${o}" ${o == val ? 'selected' : ''}>${o === 'agent' ? 'Agente IA' : (o === 'admin' ? 'Administrador' : (o === 'member' ? 'Membro' : cap(o)))}</option>`).join('')}</select>`);
    }
    let actual = type === 'textarea' ? `<textarea name="${name}" ${name === 'address' ? 'placeholder="Logradouro, número, bairro, cidade, UF, CEP"' : ''}>${val || ''}</textarea>` : `<input name="${name}" type="${type}" ${type === 'number' ? 'step="any"' : ''} value="${type === 'datetime-local' && val ? String(val).slice(0, 16) : val ?? ''}">`;
    return field(name, label, actual);
  }))).join('');

  if (section === 'invoices' && projRowsCache) {
    let projSelect = $('#fields select[name="project_id"]');
    let contactSelect = $('#fields select[name="contact_id"]');
    if (projSelect && contactSelect) {
      projSelect.onchange = () => {
        let p = projRowsCache.find(x => x.id == projSelect.value);
        if (p && p.invoice_contact_id) {
          contactSelect.value = p.invoice_contact_id;
        }
      };
    }
  }

  if (section === 'tasks' && projRowsCache) {
    let projSelect = $('#fields select[name="project_id"]');
    let clientSelect = $('#fields select[name="client_id"]');
    if (projSelect && clientSelect) {
      projSelect.onchange = () => {
        let p = projRowsCache.find(x => x.id == projSelect.value);
        if (p && p.client_id) {
          clientSelect.value = p.client_id;
        }
      };
    }
  }

  $('#error').textContent = '';
  $('#modal').showModal();
}

function defaults(name) {
  if (name === 'issue_date') return new Date().toISOString().slice(0, 10);
  if (name === 'due_date' && section === 'invoices') {
    let d = new Date();
    d.setDate(d.getDate() + 15);
    return d.toISOString().slice(0, 10);
  }
  return {
    health_score: 100,
    status: section === 'clients' ? 'prospect' : (section === 'projects' ? 'planning' : (section === 'tasks' ? 'todo' : (section === 'invoices' ? 'pending' : undefined))),
    project_value: 0,
    contract_type: 'mensal',
    priority: 'medium',
    duration_minutes: 30,
    role: 'member'
  }[name] ?? '';
}

function field(n, l, input) {
  return `<div class="field"><label>${l}</label>${input}</div>`;
}

$('#form').addEventListener('submit', async e => {
  e.preventDefault();
  let targetSection = forcedTargetSection || section;
  let data = Object.fromEntries(new FormData(e.target));
  for (let k of Object.keys(data)) if (data[k] === '') data[k] = null;
  ['health_score', 'monthly_value', 'project_value', 'client_id', 'project_id', 'contact_id', 'invoice_contact_id', 'duration_minutes', 'user_id', 'amount'].forEach(k => {
    if (data[k] !== undefined && data[k] !== null) data[k] = Number(data[k]);
  });
  if (data.is_active !== undefined) data.is_active = data.is_active === 'true';

  try {
    let res = await api(editing ? `${targetSection}/${editing.id}` : targetSection, {
      method: editing ? 'PUT' : 'POST',
      body: JSON.stringify(data)
    });
    $('#modal').close();

    if (res?.raw_key) {
      $('#generated-key-input').value = res.raw_key;
      $('#copy-key-btn').textContent = 'Copiar';
      $('#key-modal').showModal();
    }
    render();
  } catch (err) {
    $('#error').textContent = err.message;
  }
});

// Ações do modal de exibição da chave gerada
$('#copy-key-btn')?.addEventListener('click', () => {
  let keyInput = $('#generated-key-input');
  keyInput.select();
  navigator.clipboard.writeText(keyInput.value);
  $('#copy-key-btn').textContent = '✓ Copiado!';
  setTimeout(() => { $('#copy-key-btn').textContent = 'Copiar'; }, 2000);
});

$('#close-key-modal')?.addEventListener('click', () => $('#key-modal').close());
$('#done-key-btn')?.addEventListener('click', () => $('#key-modal').close());

let currentMonthlyProjectId = null;

async function openMonthlyValuesModal(projectId, projectName) {
  currentMonthlyProjectId = projectId;
  $('#monthly-modal-title').textContent = `💰 Valores Mensais — ${projectName}`;
  $('#monthly-year-month').value = new Date().toISOString().slice(0, 7);
  $('#monthly-amount').value = '';
  $('#monthly-notes').value = '';
  let errEl = $('#monthly-error');
  if (errEl) { errEl.style.display = 'none'; errEl.textContent = ''; }
  $('#monthly-modal').showModal();
  await loadMonthlyValues(projectId);
}

async function loadMonthlyValues(projectId) {
  let body = $('#monthly-table-body');
  if (!body) return;
  body.innerHTML = '<tr><td colspan="4" style="padding: 14px; text-align: center; color: var(--muted);">Carregando...</td></tr>';
  try {
    let items = await api(`projects/${projectId}/monthly-values`);
    if (!items || !items.length) {
      body.innerHTML = '<tr><td colspan="4" style="padding: 14px; text-align: center; color: var(--muted);">Nenhum valor mensal lançado para este projeto.</td></tr>';
      return;
    }
    body.innerHTML = items.map(item => {
      let parts = item.year_month.split('-');
      let dateStr = `${parts[1]}/${parts[0]}`;
      return `<tr>
        <td style="padding: 8px 12px; font-weight: 600;">${dateStr}</td>
        <td style="padding: 8px 12px; color: #047857; font-weight: 600;">${money(item.amount)}</td>
        <td style="padding: 8px 12px; color: var(--muted); font-size: 12px;">${item.notes || '—'}</td>
        <td style="padding: 8px 12px; text-align: right;">
          <button type="button" class="link danger remove-monthly-item" data-id="${item.id}" style="font-size: 12px; padding: 2px 6px;">Excluir</button>
        </td>
      </tr>`;
    }).join('');

    document.querySelectorAll('.remove-monthly-item').forEach(btn => {
      btn.onclick = async (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        if (confirm('Excluir este lançamento mensal?')) {
          await api(`project-monthly-values/${btn.dataset.id}`, { method: 'DELETE' });
          await loadMonthlyValues(projectId);
          if (section === 'projects') render();
        }
      };
    });
  } catch (err) {
    body.innerHTML = `<tr><td colspan="4" style="padding: 14px; text-align: center; color: var(--red);">${err.message}</td></tr>`;
  }
}

$('#monthly-form')?.addEventListener('submit', async e => {
  e.preventDefault();
  if (!currentMonthlyProjectId) return;
  let yearMonth = $('#monthly-year-month').value;
  let amount = Number($('#monthly-amount').value);
  let notes = $('#monthly-notes').value;
  let errEl = $('#monthly-error');

  try {
    if (errEl) errEl.style.display = 'none';
    await api(`projects/${currentMonthlyProjectId}/monthly-values`, {
      method: 'POST',
      body: JSON.stringify({ year_month: yearMonth, amount: amount, notes: notes || null })
    });
    $('#monthly-amount').value = '';
    $('#monthly-notes').value = '';
    await loadMonthlyValues(currentMonthlyProjectId);
    if (section === 'projects') render();
  } catch (err) {
    if (errEl) {
      errEl.textContent = err.message;
      errEl.style.display = 'block';
    }
  }
});

$('#close-monthly-modal')?.addEventListener('click', () => {
  $('#monthly-modal').close();
  if (section === 'projects') render();
});
$('#done-monthly-btn')?.addEventListener('click', () => {
  $('#monthly-modal').close();
  if (section === 'projects') render();
});



$('#new').onclick = () => {
  if (section === 'dashboard') {
    location.hash = 'clients';
  } else if (section === 'project_details') {
    location.hash = 'projects';
  } else if (section === 'client_details') {
    location.hash = 'clients';
  } else {
    openForm();
  }
};
$('#close').onclick = $('#cancel').onclick = () => $('#modal').close();
$('#search').oninput = e => {
  let q = e.target.value.toLowerCase();
  document.querySelectorAll('tbody tr').forEach(r => r.hidden = !r.textContent.toLowerCase().includes(q));
};
window.onhashchange = () => {
  render();
};

function showLogin() {
  localStorage.removeItem('flowcrm_token');
  document.body.innerHTML = `<div class="login"><form id="login-form"><div class="login-logo">F</div><h1>FlowCRM</h1><p>Acesse sua central de operações.</p><label>E-mail<input name="email" type="email" required></label><label>Senha<input name="password" type="password" required></label><p id="login-error"></p><button>Entrar</button></form></div>`;
  $('#login-form').onsubmit = async e => {
    e.preventDefault();
    let data = Object.fromEntries(new FormData(e.target));
    if (data.email) data.email = String(data.email).trim();
    try {
      let r = await api('auth/login', { method: 'POST', body: JSON.stringify(data) });
      localStorage.setItem('flowcrm_token', r.access_token);
      location.reload();
    } catch (err) {
      $('#login-error').textContent = err.message || 'Erro ao efetuar login. Verifique o e-mail e a senha.';
    }
  };
}

$('#logout').onclick = () => {
  localStorage.removeItem('flowcrm_token');
  location.reload();
};

async function init() {
  try {
    currentUser = await api('auth/me');
    $('#current-user').firstChild.nodeValue = currentUser.name;
    $('#current-role').textContent = currentUser.role === 'admin' ? 'Administrador' : (currentUser.role === 'agent' ? 'Agente IA' : 'Membro');
    $('#user-initials').textContent = currentUser.name.split(' ').map(x => x[0]).slice(0, 2).join('').toUpperCase();
    render();
  } catch (_) {
    showLogin();
  }
}

init();
