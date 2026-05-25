let questions = [];
let currentQ = 0;
let jobDescription = '';
let qaPairs = [];
let roleTitle = '';

function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

document.getElementById('answer-box').addEventListener('input', () => {
  const words = document.getElementById('answer-box').value.trim().split(/\s+/).filter(Boolean).length;
  document.getElementById('word-count').textContent = `${words} word${words !== 1 ? 's' : ''}`;
});

document.getElementById('start-btn').addEventListener('click', async () => {
  const desc = document.getElementById('job-desc').value.trim();
  if (!desc) {
    document.getElementById('start-error').classList.remove('hidden');
    return;
  }
  document.getElementById('start-error').classList.add('hidden');
  jobDescription = desc;

  const btn = document.getElementById('start-btn');
  document.getElementById('start-text').classList.add('hidden');
  document.getElementById('start-loader').classList.remove('hidden');
  btn.disabled = true;

  try {
    const res = await fetch('/generate-questions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_description: desc })
    });
    const data = await res.json();
    questions = data.questions;
    roleTitle = data.role_title || 'this role';
    currentQ = 0;
    qaPairs = [];
    loadQuestion(0);
    showScreen('screen-interview');
  } catch (e) {
    alert('Something went wrong. Please try again.');
  } finally {
    btn.disabled = false;
    document.getElementById('start-text').classList.remove('hidden');
    document.getElementById('start-loader').classList.add('hidden');
  }
});

function loadQuestion(index) {
  const q = questions[index];
  document.getElementById('q-number').textContent = `Q${q.number}`;
  document.getElementById('q-type').textContent = q.type;
  document.getElementById('q-text').textContent = q.question;
  document.getElementById('answer-box').value = '';
  document.getElementById('word-count').textContent = '0 words';
  document.getElementById('feedback-card').classList.add('hidden');
  document.getElementById('answer-box').disabled = false;
  document.getElementById('submit-answer-btn').disabled = false;
  document.getElementById('submit-answer-btn').textContent = 'Submit Answer →';

  const pct = (index / questions.length) * 100;
  document.getElementById('progress-fill').style.width = pct + '%';
  document.getElementById('progress-label').textContent = `Question ${index + 1} of ${questions.length}`;
}

document.getElementById('submit-answer-btn').addEventListener('click', async () => {
  const answer = document.getElementById('answer-box').value.trim();
  if (!answer || answer.split(/\s+/).length < 5) {
    alert('Please write a more complete answer (at least a few sentences).');
    return;
  }

  const btn = document.getElementById('submit-answer-btn');
  btn.disabled = true;
  btn.textContent = 'Evaluating...';
  document.getElementById('answer-box').disabled = true;

  try {
    const res = await fetch('/evaluate-answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: questions[currentQ].question,
        answer: answer,
        job_description: jobDescription,
        question_number: currentQ + 1
      })
    });
    const feedback = await res.json();

    qaPairs.push({
      question: questions[currentQ].question,
      answer: answer,
      score: feedback.score
    });

    showFeedback(feedback);
  } catch (e) {
    alert('Error evaluating your answer. Please try again.');
    btn.disabled = false;
    btn.textContent = 'Submit Answer →';
    document.getElementById('answer-box').disabled = false;
  }
});

function showFeedback(fb) {
  document.getElementById('score-num').textContent = fb.score;
  document.getElementById('score-label').textContent = fb.score_label;
  document.getElementById('fb-good').textContent = fb.what_was_good;
  document.getElementById('fb-improve').textContent = fb.what_to_improve;
  document.getElementById('fb-tip').textContent = fb.pro_tip;

  const circle = document.getElementById('score-circle');
  const color = fb.score >= 8 ? 'var(--green)' : fb.score >= 5 ? 'var(--yellow)' : 'var(--red)';
  circle.style.borderColor = color;
  document.getElementById('score-num').style.color = color;

  const isLast = currentQ === questions.length - 1;
  const nextBtn = document.getElementById('next-btn');
  nextBtn.textContent = isLast ? 'See Full Report' : 'Next Question →';

  document.getElementById('feedback-card').classList.remove('hidden');
  document.getElementById('feedback-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

document.getElementById('next-btn').addEventListener('click', async () => {
  currentQ++;
  if (currentQ < questions.length) {
    loadQuestion(currentQ);
    document.getElementById('question-card')?.scrollIntoView({ behavior: 'smooth' });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } else {
    showScreen('screen-loading');
    try {
      const res = await fetch('/generate-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_description: jobDescription, qa_pairs: qaPairs })
      });
      const report = await res.json();
      renderReport(report);
      showScreen('screen-report');
    } catch (e) {
      alert('Error generating report. Please try again.');
      showScreen('screen-interview');
    }
  }
});

function renderReport(r) {
  document.getElementById('report-hero').innerHTML = `
    <div class="overall-score">${r.overall_score}<span style="font-size:2rem;color:var(--muted)">/10</span></div>
    <div class="overall-label">${r.overall_label}</div>
    <p class="overall-summary">${r.summary}</p>
    <span class="hire-badge">Hire likelihood: ${r.hire_likelihood}</span>
  `;

  document.getElementById('report-strengths').innerHTML = `
    <h3>💪 Top Strengths</h3>
    <ul class="report-list strengths-list">
      ${r.top_strengths.map(s => `<li><span></span>${s}</li>`).join('')}
    </ul>
  `;

  document.getElementById('report-weaknesses').innerHTML = `
    <h3>⚠️ Areas to Improve</h3>
    <ul class="report-list weaknesses-list">
      ${r.top_weaknesses.map(w => `<li><span></span>${w}</li>`).join('')}
    </ul>
  `;

  document.getElementById('report-actions').innerHTML = `
    <h3>🎯 Action Plan — Before the Real Interview</h3>
    <ul class="report-list action-list">
      ${r.action_plan.map(a => `<li><span></span>${a}</li>`).join('')}
    </ul>
  `;

  const breakdownHTML = qaPairs.map((qa, i) => `
    <div class="breakdown-item">
      <span class="bd-label">Q${i + 1}</span>
      <div class="bd-bar-track">
        <div class="bd-bar-fill" style="width:${qa.score * 10}%;background:${qa.score >= 8 ? 'var(--green)' : qa.score >= 5 ? 'var(--yellow)' : 'var(--red)'}"></div>
      </div>
      <span class="bd-score" style="color:${qa.score >= 8 ? 'var(--green)' : qa.score >= 5 ? 'var(--yellow)' : 'var(--red)'}">${qa.score}/10</span>
    </div>
  `).join('');

  document.getElementById('report-breakdown').innerHTML = `
    <h3>📊 Score Breakdown</h3>
    <div class="breakdown-list">${breakdownHTML}</div>
  `;

  document.getElementById('report-closing').innerHTML = `
    <p>"${r.closing_advice}"</p>
  `;
}

document.getElementById('restart-btn').addEventListener('click', () => {
  document.getElementById('job-desc').value = '';
  showScreen('screen-landing');
});
