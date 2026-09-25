const config = {
  dashboard: { label: 'Dashboard', title: 'Visão geral das operações', description: 'Acompanhamento em tempo real de clientes, faturamento, entregas e compromissos.' },
  clients: { label: 'Clientes', title: 'Diretório de clientes', description: 'Contas, dados fiscais, saúde e valor mensal sob gestão.', fields: [['name', 'Nome da Empresa *'], ['cnpj', 'CNPJ'], ['address', 'Endereço Completo de Cobrança', 'textarea'], ['industry', 'Segmento'], ['status', 'Status', 'select', 'prospect,active,inactive'], ['health_score', 'Health score', 'number'], ['monthly_value', 'Valor mensal (R$)', 'number']] },
  projects: { label: 'Projetos', title: 'Projetos', description: 'Entregas organizadas por cliente, contato de cobrança e fase.', fields: [['name', 'Nome do Projeto *'], ['client_id', 'Cliente *', 'select-api', 'clients'], ['invoice_contact_id', 'Contato Designado para Faturas', 'select-api', 'contacts'], ['status', 'Status', 'select', 'planning,active,paused,completed'], ['project_value', 'Valor do projeto (R$)', 'number'], ['contract_type', 'Tipo de contrato', 'select', 'mensal,avulso'], ['description', 'Descrição', 'textarea'], ['start_date', 'Início', 'date'], ['due_date', 'Prazo', 'date']] },
  invoices: { label: 'Faturas', title: 'Faturas & Cobranças', description: 'Controle de faturamento, prazos de vencimento e recebimento por projeto.', fields: [['invoice_number', 'Número da Fatura *'], ['project_id', 'Projeto *', 'select-api', 'projects'], ['contact_id', 'Para quem foi enviada (Contato)', 'select-api', 'contacts'], ['amount', 'Valor (R$) *', 'number'], ['issue_date', 'Data de Emissão', 'date'], ['due_date', 'Data de Vencimento *', 'date'], ['payment_date', 'Data de Pagamento', 'date'], ['status', 'Status', 'select', 'pending,paid,overdue,draft,cancelled'], ['description', 'Descrição / Serviços Faturados *', 'textarea']] },
  tasks: { label: 'Tarefas', title: 'Central de tarefas', description: 'Priorize a execução e acompanhe prazos.', fields: [['title', 'Título'], ['project_id', 'Projeto', 'select-api', 'projects'], ['status', 'Status', 'select', 'todo,in_progress,done'], ['priority', 'Prioridade', 'select', 'low,medium,high'], ['due_date', 'Prazo', 'date'], ['description', 'Descrição', 'textarea']] },
  meetings: { label: 'Reuniões', title: 'Reuniões e agenda', description: 'Registre compromissos e decisões com os clientes.', fields: [['title', 'Título'], ['client_id', 'Cliente', 'select-api', 'clients'], ['starts_at', 'Data e hora', 'datetime-local'], ['duration_minutes', 'Duração (minutos)', 'number'], ['notes', 'Notas', 'textarea']] },
  contacts: { label: 'Contatos', title: 'Diretório de contatos', description: 'As pessoas-chave em cada conta.', fields: [['name', 'Nome'], ['email', 'E-mail', 'email'], ['role', 'Cargo'], ['phone', 'Telefone'], ['client_id', 'Cliente', 'select-api', 'clients']] },
  users: { label: 'Usuários', title: 'Usuários & Permissões', description: 'Controle de acessos e permissões da equipe e agentes de IA.', fields: [['name', 'Nome'], ['email', 'E-mail', 'email'], ['password', 'Senha', 'password'], ['role', 'Perfil', 'select', 'member,admin,agent'], ['is_active', 'Ativo', 'select', 'true,false']] },
  api_keys: { label: 'Agentes & API Keys', title: 'Chaves de API para Agentes de IA', description: 'Credenciais de acesso para agentes de IA autônomos e conexão com o Servidor MCP.', fields: [['name', 'Identificação do Agente (ex: Antigravity Assistant, Claude Desktop, Bot SDR)'], ['user_id', 'Vincular ao Usuário', 'select-api', 'users']] }
};

document.head.insertAdjacentHTML('beforeend', '<link rel="stylesheet" href="/auth.css"><link rel="stylesheet" href="/dashboard.css">');
let section = location.hash.slice(1) || 'dashboard', records = [], editing = null, currentUser = null, forcedTargetSection = null;

const $ = s => document.querySelector(s),
      cap = s => s.charAt(0).toUpperCase() + s.slice(1),
      status = v => `<span class="pill ${v}">${String(v).replaceAll('_', ' ')}</span>`,
      money = v => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v || 0);

async function api(path, options = {}) {
  let token = localStorage.getItem('flowcrm_token');
  let endpoint = path.replace(/^api_keys/, 'api-keys');
  const r = await fetch('/api/' + endpoint, {
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
    ...options
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({ detail: 'Erro na requisição' }))).detail);
  return r.status === 204 ? null : r.json();
}

function nav() {
  $('#nav').innerHTML = Object.entries(config)
    .filter(([key]) => (key !== 'users' && key !== 'api_keys') || currentUser?.role === 'admin')
    .map(([key, x]) => {
      let icon = key === 'api_keys' ? '🤖 ' : (key === 'users' ? '👥 ' : (key === 'invoices' ? '📄 ' : ''));
      return `<button class="nav ${key === section ? 'active' : ''}" data-go="${key}">${icon}${x.label}</button>`;
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
  return `<article class="project-card"><div class="project-top"><div><h3>${p.name}</h3><p>${p.client?.name || 'Sem cliente'}</p></div>${p.due_date ? `<span class="due">Prazo: ${new Date(p.due_date + 'T12:00').toLocaleDateString('pt-BR')}</span>` : ''}</div><div class="project-data"><div><b>Valor do projeto</b><span>${money(p.project_value)}</span></div><div><b>Tipo de contrato</b><span>${p.contract_type === 'avulso' ? 'Avulso' : 'Mensal'}</span></div><div><b>Tarefas</b><span>${p.task_summary.done}/${p.task_summary.total} concluídas · ${p.task_summary.in_progress} em andamento</span></div><div><b>Contatos</b><span>${contacts}</span></div></div><ul class="project-tasks">${tasks}</ul></article>`;
}

async function dashboard() {
  let d = await api('dashboard');
  return title() + `<section class="metrics"><div class="card"><div class="metric-label">Clientes ativos</div><div class="metric">${d.active_clients}</div></div><div class="card"><div class="metric-label">Projetos em andamento</div><div class="metric">${d.active_projects}</div></div><div class="card"><div class="metric-label">Faturas a receber</div><div class="metric">${money(d.invoices_pending_value)}</div><p style="font-size:12px;margin-top:4px">${d.invoices_pending_count} faturas pendentes · ${d.invoices_overdue_count} vencidas</p></div><div class="card"><div class="metric-label">Tarefas para hoje</div><div class="metric">${d.tasks_today}</div></div></section><div class="card revenue"><div class="metric-label">Receita mensal sob gestão</div><div class="metric">${money(d.monthly_value)}</div><p>Dados calculados a partir das contas ativas.</p></div><section class="project-areas">${projectArea('Projetos em andamento', 'Execução e entregas ativas', d.in_progress_projects, 'active')}${projectArea('Projetos em prospecção', 'Oportunidades em planejamento', d.prospecting_projects, 'planning')}</section>`;
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
    tasks: [['title', 'Tarefa'], ['project_id', 'Projeto'], ['status', 'Status'], ['priority', 'Prioridade'], ['due_date', 'Prazo']],
    meetings: [['title', 'Reunião'], ['client_id', 'Cliente'], ['starts_at', 'Data'], ['duration_minutes', 'Duração']],
    contacts: [['name', 'Contato'], ['email', 'E-mail'], ['role', 'Cargo'], ['client_id', 'Cliente']],
    api_keys: [['name', 'Identificação'], ['key_prefix', 'Prefixo'], ['user_name', 'Usuário Vinculado'], ['created_at', 'Criada em'], ['last_used_at', 'Último Uso']]
  }[section];
}

function cell(r, k) {
  let v = r[k];
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
      ${section === 'users' && currentUser?.role === 'admin' ? `<button class="link generate-key-user" data-user-id="${r.id}" data-user-name="${r.name}" style="color:#16a34a;font-weight:600">🔑 Gerar Chave</button>` : ''}
      ${section !== 'api_keys' ? `<button class="link edit" data-id="${r.id}">Editar</button>` : ''}
      ${canDelete(r) ? `<button class="link danger remove" data-id="${r.id}">${section === 'api_keys' ? 'Revogar' : 'Excluir'}</button>` : ''}
    </td>
  </tr>`).join('');

  return title() + integrationBanners() + `<div class="table-card"><table><thead><tr>${cols.map(c => `<th>${c[1]}</th>`).join('')}<th></th></tr></thead><tbody>${rows || `<tr><td colspan="${cols.length + 1}" class="empty">Nenhum registro encontrado.</td></tr>`}</tbody></table></div>`;
}

async function render() {
  nav();
  try {
    $('#view').innerHTML = section === 'dashboard' ? await dashboard() : await table();
    $('#create')?.addEventListener('click', () => openForm());
    document.querySelectorAll('.edit').forEach(x => x.onclick = () => openForm(records.find(r => r.id == x.dataset.id)));
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

$('#new').onclick = () => {
  if (section === 'dashboard') {
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
  section = location.hash.slice(1) || 'dashboard';
  render();
};

function showLogin() {
  document.body.innerHTML = `<div class="login"><form id="login-form"><div class="login-logo">F</div><h1>FlowCRM</h1><p>Acesse sua central de operações.</p><label>E-mail<input name="email" type="email" required></label><label>Senha<input name="password" type="password" required></label><p id="login-error"></p><button>Entrar</button></form></div>`;
  $('#login-form').onsubmit = async e => {
    e.preventDefault();
    try {
      let r = await api('auth/login', { method: 'POST', body: JSON.stringify(Object.fromEntries(new FormData(e.target))) });
      localStorage.setItem('flowcrm_token', r.access_token);
      location.reload();
    } catch (err) {
      $('#login-error').textContent = err.message;
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
