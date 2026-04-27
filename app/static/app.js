const btn = document.getElementById('askBtn');
const questionEl = document.getElementById('question');
const adviceEl = document.getElementById('advice');
const coursesEl = document.getElementById('courses');
const matchBtn = document.getElementById('matchBtn');
const matchesEl = document.getElementById('matches');

function getSelectedSubjects() {
  return Array.from(document.querySelectorAll('input[name="subject"]:checked')).map((el) => el.value);
}

function renderMatches(results) {
  if (!matchesEl) return;
  matchesEl.innerHTML = '';
  if (!results.length) {
    matchesEl.innerHTML = '<p>No matches found.</p>';
    return;
  }
  for (const r of results) {
    const c = r.course;
    const div = document.createElement('div');
    div.className = 'course';
    const reasons = (r.reasons || []).slice(0, 4).join(' ');
    div.innerHTML = `<strong>${c.id} - ${c.title}</strong><br/>${c.subject} | ${c.days} ${c.time} | Open seats: ${c.open_seats}<br/><em>${reasons}</em>`;
    matchesEl.appendChild(div);
  }
}

if (btn && questionEl && adviceEl && coursesEl) btn.addEventListener('click', async () => {
  const question = questionEl.value.trim();
  if (!question) return;
  adviceEl.textContent = 'Thinking...';
  coursesEl.innerHTML = '';

  try {
    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });
    if (!res.ok) {
      const t = await res.text();
      adviceEl.textContent = `Request failed (${res.status}). ${t}`;
      return;
    }
    const data = await res.json();
    adviceEl.textContent = data.advice ?? '(No advice returned.)';

    if (!data.courses?.length) {
      coursesEl.innerHTML = '<p>No courses found.</p>';
      return;
    }

    for (const c of data.courses) {
      const div = document.createElement('div');
      div.className = 'course';
      div.textContent = `${c.id} - ${c.title} | ${c.subject} | ${c.days} ${c.time} | Open seats: ${c.open_seats}`;
      coursesEl.appendChild(div);
    }
  } catch (e) {
    adviceEl.textContent = `Request error: ${e?.message || e}`;
  }
});

if (matchBtn && matchesEl) matchBtn.addEventListener('click', async () => {
  const subjects = getSelectedSubjects();
  const days = document.getElementById('matchDays').value;
  const earliestStart = document.getElementById('earliestStart').value.trim();
  const latestEnd = document.getElementById('latestEnd').value.trim();
  const onlyOpen = document.getElementById('onlyOpen').checked;
  const interests = document.getElementById('interests').value.trim();
  const topN = Number(document.getElementById('topN').value || 5);
  const maxPerSubject = Number(document.getElementById('maxPerSubject').value || 3);

  matchesEl.innerHTML = '<p>Matching...</p>';

  const body = {
    student: {
      subjects,
      days,
      earliest_start: earliestStart || null,
      latest_end: latestEnd || null,
      only_open: onlyOpen,
      interests,
      avoid_instructors: [],
      prefer_instructors: []
    },
    top_n: topN,
    max_per_subject: maxPerSubject
  };

  const res = await fetch('/api/match', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    const t = await res.text();
    matchesEl.innerHTML = `<p>Match request failed (${res.status}).</p><pre>${t}</pre>`;
    return;
  }
  const data = await res.json();
  renderMatches(data.results || []);
});
