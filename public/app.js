async function postJson(url, body){
  const res = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
  return res.json()
}

function escapeText(value){
  return String(value ?? '')
}

function clearNode(node){
  while(node.firstChild) node.removeChild(node.firstChild)
}

function renderAnswer(answer){
  const host = document.getElementById('answer')
  clearNode(host)

  if(!answer){
    host.textContent = 'No answer.'
    return
  }

  const lines = String(answer).split(/\r?\n/).map(line => line.trim()).filter(Boolean)
  const structured = lines.some(line => /^Answer:|^Key points:|^Safety note:/.test(line))

  if(!structured){
    host.textContent = answer
    return
  }

  const sections = { answer: '', points: [], safety: '', question: '' }
  let current = null

  for(const line of lines){
    if(line.startsWith('Answer:')){
      sections.answer = line.slice('Answer:'.length).trim()
      current = 'answer'
      continue
    }
    if(line.startsWith('Key points:')){
      current = 'points'
      continue
    }
    if(line.startsWith('Safety note:')){
      sections.safety = line.slice('Safety note:'.length).trim()
      current = 'safety'
      continue
    }
    if(line.startsWith('Question:')){
      sections.question = line.slice('Question:'.length).trim()
      current = 'question'
      continue
    }
    if(line.startsWith('- ') && current === 'points'){
      sections.points.push(line.slice(2).trim())
      continue
    }
    if(current === 'answer' && sections.answer){
      sections.answer += ` ${line}`
    } else if(current === 'safety' && sections.safety){
      sections.safety += ` ${line}`
    } else if(current === 'question' && sections.question){
      sections.question += ` ${line}`
    }
  }

  const summary = document.createElement('div')
  summary.className = 'answer-summary'
  summary.innerHTML = `<div class="answer-label">Answer</div><div class="answer-text"></div>`
  summary.querySelector('.answer-text').textContent = sections.answer || lines[0] || answer
  host.appendChild(summary)

  if(sections.points.length){
    const points = document.createElement('div')
    points.className = 'answer-block'
    const title = document.createElement('div')
    title.className = 'answer-label'
    title.textContent = 'Key points'
    points.appendChild(title)
    const list = document.createElement('ul')
    list.className = 'answer-list'
    for(const point of sections.points){
      const item = document.createElement('li')
      item.textContent = point
      list.appendChild(item)
    }
    points.appendChild(list)
    host.appendChild(points)
  }

  if(sections.safety){
    const safety = document.createElement('div')
    safety.className = 'answer-safety'
    const title = document.createElement('div')
    title.className = 'answer-label'
    title.textContent = 'Safety note'
    const text = document.createElement('div')
    text.className = 'answer-text'
    text.textContent = sections.safety
    safety.appendChild(title)
    safety.appendChild(text)
    host.appendChild(safety)
  }

  if(sections.question){
    const question = document.createElement('div')
    question.className = 'answer-question'
    question.textContent = `Question: ${sections.question}`
    host.appendChild(question)
  }
}

document.getElementById('upload-form').addEventListener('submit', async (e)=>{
  e.preventDefault()
  const input = document.getElementById('file-input')
  if(!input.files.length){ document.getElementById('upload-result').textContent='Please choose file(s)'; return }
  const fd = new FormData()
  for(const f of input.files) fd.append('files', f, f.name)
  document.getElementById('upload-btn').disabled = true
  const res = await fetch('/ingest/upload', {method:'POST', body:fd})
  const data = await res.json()
  document.getElementById('upload-result').textContent = `Ingested ${data.ingested.length} document(s). Total: ${data.total_documents}`
  document.getElementById('upload-btn').disabled = false
})

document.getElementById('ask-form').addEventListener('submit', async (e)=>{
  e.preventDefault()
  const q = document.getElementById('question').value.trim()
  if(!q) return
  document.getElementById('ask-btn').disabled = true
  document.getElementById('meta').innerHTML = ''
  const reply = await postJson('/ask', {question:q})
  document.getElementById('ask-btn').disabled = false
  renderAnswer(reply.answer || '')
  document.getElementById('meta').innerHTML = `
    <span class="chip">Provider: ${reply.provider || 'unknown'}</span>
    <span class="chip">Model: ${reply.model || 'unknown'}</span>
  `
  const src = document.getElementById('sources')
  if(reply.sources && reply.sources.length){
    src.innerHTML = '<strong>Sources</strong>' + reply.sources.map(s=>`<div class="source-item"><div class="source-title">${s.title}</div><div class="source-score">Score: ${s.score} • ${s.source_type || 'document'}</div></div>`).join('')
  } else { src.innerHTML = '<strong>Sources</strong><div>No retrieved sources.</div>' }
})

document.getElementById('clear-btn').addEventListener('click', ()=>{
  document.getElementById('question').value = ''
  document.getElementById('answer').textContent = ''
  document.getElementById('meta').innerHTML = ''
  document.getElementById('sources').innerHTML = ''
})

document.getElementById('toggle-sources').addEventListener('click', ()=>{
  const src = document.getElementById('sources')
  const hidden = src.classList.toggle('hidden')
  document.getElementById('toggle-sources').textContent = hidden ? 'Show sources' : 'Hide sources'
})
