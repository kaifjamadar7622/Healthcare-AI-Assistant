async function postJson(url, body){
  const res = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
  return res.json()
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
  document.getElementById('answer').textContent = reply.answer || 'No answer.'
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
