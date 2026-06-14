const views = {
  loading: document.getElementById('loadingView'),
  login: document.getElementById('loginView'),
  error: document.getElementById('errorView'),
  usage: document.getElementById('usageView')
};

let resetTimers = { five_hour: null, seven_day: null };

function showView(name) {
  for (const key of Object.keys(views)) {
    views[key].classList.toggle('hidden', key !== name);
  }
}

function barClass(pct) {
  if (pct >= 90) return 'danger';
  if (pct >= 70) return 'warn';
  return '';
}

function formatCountdown(resetIso) {
  if (!resetIso) return '';
  const ms = new Date(resetIso).getTime() - Date.now();
  if (ms <= 0) return 'resets now';
  const totalMin = Math.floor(ms / 60000);
  const hours = Math.floor(totalMin / 60);
  const mins = totalMin % 60;
  if (hours > 0) return `resets in ${hours}h ${mins}m`;
  return `resets in ${mins}m`;
}

function setBar(prefix, windowData) {
  const pctEl = document.getElementById(`${prefix}Pct`);
  const barEl = document.getElementById(`${prefix}Bar`);
  const resetEl = document.getElementById(`${prefix}Reset`);

  if (!windowData) {
    pctEl.textContent = '--%';
    barEl.style.width = '0%';
    barEl.className = 'bar-fill';
    resetEl.textContent = '';
    return;
  }

  const pct = Math.round(windowData.utilization);
  pctEl.textContent = `${pct}%`;
  barEl.style.width = `${Math.min(100, pct)}%`;
  barEl.className = `bar-fill ${barClass(pct)}`;
  resetEl.textContent = formatCountdown(windowData.resets_at);
}

function render(result) {
  if (!result) {
    showView('loading');
    return;
  }

  if (result.status === 'login-required' || result.status === 'no-orgs') {
    showView('login');
  } else if (result.status === 'error') {
    document.getElementById('errorText').textContent = result.message || 'Something went wrong.';
    showView('error');
  } else if (result.status === 'ok') {
    showView('usage');
    setBar('fiveHour', result.usage.five_hour);
    setBar('sevenDay', result.usage.seven_day);
    document.getElementById('orgName').textContent = result.orgName || '';

    resetTimers.five_hour = result.usage.five_hour?.resets_at || null;
    resetTimers.seven_day = result.usage.seven_day?.resets_at || null;
  } else {
    showView('loading');
  }

  if (result.fetchedAt) {
    const d = new Date(result.fetchedAt);
    document.getElementById('lastUpdated').textContent =
      'Updated ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
}

document.getElementById('refreshBtn').addEventListener('click', () => window.claudeUsage.refresh());
document.getElementById('loginBtn').addEventListener('click', () => window.claudeUsage.login());
document.getElementById('retryBtn').addEventListener('click', () => window.claudeUsage.refresh());

window.claudeUsage.onUpdate(render);
window.claudeUsage.getLastResult().then(render);

// Live-update the reset countdowns every 30s without waiting for a full refetch
setInterval(() => {
  if (resetTimers.five_hour) {
    document.getElementById('fiveHourReset').textContent = formatCountdown(resetTimers.five_hour);
  }
  if (resetTimers.seven_day) {
    document.getElementById('sevenDayReset').textContent = formatCountdown(resetTimers.seven_day);
  }
}, 30000);
