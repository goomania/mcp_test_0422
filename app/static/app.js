const btn = document.getElementById('askBtn');
const questionEl = document.getElementById('question');
const adviceEl = document.getElementById('advice');
const coursesEl = document.getElementById('courses');

btn.addEventListener('click', async () => {
  const question = questionEl.value.trim();
  if (!question) return;
  adviceEl.textContent = 'Thinking...';
  coursesEl.innerHTML = '';

  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question })
  });
  const data = await res.json();
  adviceEl.textContent = data.advice;

  if (!data.courses.length) {
    coursesEl.innerHTML = '<p>No courses found.</p>';
    return;
  }

  for (const c of data.courses) {
    const div = document.createElement('div');
    div.className = 'course';
    div.textContent = `${c.id} - ${c.title} | ${c.subject} | ${c.days} ${c.time} | Open seats: ${c.open_seats}`;
    coursesEl.appendChild(div);
  }
});
