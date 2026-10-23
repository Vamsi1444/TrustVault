import { useEffect, useState } from 'react'
import './App.css'

const API = 'http://127.0.0.1:5000'

function App() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [token, setToken] = useState(localStorage.getItem('token') || '')
  const [documents, setDocuments] = useState([])
  const [title, setTitle] = useState('')
  const [category, setCategory] = useState('General')
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (token) loadDocuments(token)
  }, [])

  async function login(e) {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Login failed')
      }

      localStorage.setItem('token', data.access_token)
      setToken(data.access_token)
      await loadDocuments(data.access_token)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function loadDocuments(accessToken = token) {
    try {
      const response = await fetch(`${API}/api/documents/`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Could not load documents')
      }

      setDocuments(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message)
    }
  }

  async function uploadDocument(e) {
    e.preventDefault()

    if (!file) {
      setError('Please select a document.')
      return
    }

    setLoading(true)
    setError('')
    setSuccess('')

    const formData = new FormData()
    formData.append('file', file)
    formData.append('title', title)
    formData.append('category', category)

    try {
      const response = await fetch(`${API}/api/documents/upload`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Upload failed')
      }

      setSuccess('Document uploaded successfully!')
      setTitle('')
      setCategory('General')
      setFile(null)

      document.getElementById('document-file').value = ''

      await loadDocuments()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function downloadDocument(id, filename) {
    setError('')
    setSuccess('')

    try {
      const response = await fetch(
        `${API}/api/documents/${id}/download`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      )

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Download failed')
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')

      link.href = url
      link.download = filename
      link.click()

      window.URL.revokeObjectURL(url)
    } catch (err) {
      setError(err.message)
    }
  }

  function logout() {
    localStorage.removeItem('token')
    setToken('')
    setDocuments([])
    setEmail('')
    setPassword('')
    setError('')
    setSuccess('')
  }

  if (!token) {
    return (
      <main className="login-page">
        <div className="login-card">
          <h1>🔐 TrustVault</h1>
          <p>Secure document sharing platform</p>

          <form onSubmit={login}>
            <label>Email address</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="Enter your email"
              required
            />

            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
            />

            {error && <p className="error">{error}</p>}

            <button type="submit" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>
      </main>
    )
  }

  return (
    <main className="dashboard">
      <header>
        <h1>🔐 TrustVault</h1>
        <button className="logout" onClick={logout}>Logout</button>
      </header>

      <section className="welcome">
        <h2>Document Dashboard</h2>
        <p>Manage your secure documents in one place.</p>
      </section>

      <section className="documents">
        <h2>Upload a Document</h2>

        <form onSubmit={uploadDocument}>
          <label>Document title</label>
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Enter document title"
            required
          />

          <label>Category</label>
          <input
            type="text"
            value={category}
            onChange={e => setCategory(e.target.value)}
            placeholder="General"
          />

          <label>Select file (PDF, PNG, JPG or TXT)</label>
          <input
            id="document-file"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.txt"
            onChange={e => setFile(e.target.files[0] || null)}
            required
          />

          {error && <p className="error">{error}</p>}
          {success && <p className="success">{success}</p>}

          <button type="submit" disabled={loading}>
            {loading ? 'Please wait...' : 'Upload Securely'}
          </button>
        </form>
      </section>

      <section className="documents">
        <div className="section-heading">
          <h2>Your Documents ({documents.length})</h2>
          <button onClick={() => loadDocuments()}>Refresh</button>
        </div>

        {documents.length === 0 ? (
          <p>No documents found. Upload your first document!</p>
        ) : (
          documents.map(doc => (
            <div className="document-card" key={doc.id}>
              <h3>📄 {doc.title}</h3>
              <p>Filename: {doc.filename}</p>
              <p>Category: {doc.category}</p>
              <p>Uploaded: {new Date(doc.uploaded_at).toLocaleString()}</p>

              <button
                onClick={() => downloadDocument(doc.id, doc.filename)}
              >
                Download
              </button>
            </div>
          ))
        )}
      </section>
    </main>
  )
}

export default App

