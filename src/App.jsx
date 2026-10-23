import { useEffect, useState } from "react";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:5000/api";

function App() {
  const [token, setToken] = useState(
    localStorage.getItem("token") || ""
  );
  const [user, setUser] = useState(null);

  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [name, setName] = useState("");

  const [message, setMessage] = useState("");
  const [documents, setDocuments] = useState([]);

  const [title, setTitle] = useState("");
  const [shareEmail, setShareEmail] = useState("");
  const [sharePermission, setSharePermission] = useState("read");
  const [sharingDocumentId, setSharingDocumentId] = useState(null);

  const [category, setCategory] = useState("General");
  const [file, setFile] = useState(null);

  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  // API REQUEST HELPER
  async function apiRequest(path, options = {}) {
    const headers = {
      ...(options.headers || {}),
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${API}${path}`, {
      ...options,
      headers,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.error || "Request failed");
    }

    return data;
  }

  // LOGIN AND REGISTRATION
  async function handleAuth(event) {
    event.preventDefault();
    setMessage("");
    setLoading(true);

    try {
      const endpoint = isRegister
        ? "/auth/register"
        : "/auth/login";

      const body = isRegister
        ? { name, email, password }
        : { email, password };

      const data = await apiRequest(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      if (isRegister) {
        setMessage("Registration successful. Please sign in.");
        setIsRegister(false);
        setPassword("");
      } else {
        localStorage.setItem(
          "token",
          data.access_token
        );

        setToken(data.access_token);
        setUser(data.user);
        setMessage("Login successful!");

        await loadDocuments(data.access_token);
      }
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  // LOAD USER PROFILE
  async function loadUser() {
    try {
      const data = await apiRequest("/auth/me");
      setUser(data);
      await loadDocuments();
    } catch {
      logout();
    }
  }

  // LOAD DOCUMENTS
  async function loadDocuments(accessToken = token) {
    try {
      const response = await fetch(`${API}/documents/search`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not load documents");
      }

      setDocuments(data.documents || []);
    } catch (error) {
      setMessage(error.message);
    }
  }

  // UPLOAD DOCUMENT
  async function uploadDocument(event) {
    event.preventDefault();

    if (!file) {
      setMessage("Please select a file.");
      return;
    }

    if (!title.trim()) {
      setMessage("Please enter a document title.");
      return;
    }

    const formData = new FormData();

    formData.append("file", file);
    formData.append("title", title);
    formData.append("category", category);

    setLoading(true);
    setMessage("");

    try {
      await apiRequest("/documents/upload", {
        method: "POST",
        body: formData,
      });

      setMessage("Document uploaded successfully!");

      setTitle("");
      setCategory("General");
      setFile(null);

      const input = document.getElementById("fileInput");

      if (input) {
        input.value = "";
      }

      await loadDocuments();
    } catch (error) {
      setMessage(`Upload failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  // DOWNLOAD DOCUMENT
  async function downloadDocument(id, filename) {
    try {
      const response = await fetch(
        `${API}/documents/${id}/download`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || "Download failed");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");

      link.href = url;
      link.download = filename;

      document.body.appendChild(link);
      link.click();
      link.remove();

      window.URL.revokeObjectURL(url);

      setMessage("Download successful!");
    } catch (error) {
      setMessage(error.message);
    }
  }

  // DELETE DOCUMENT
  async function deleteDocument(id) {
    if (
      !window.confirm(
        "Are you sure you want to delete this document?"
      )
    ) {
      return;
    }

    try {
      await apiRequest(`/documents/${id}`, {
        method: "DELETE",
      });

      setMessage("Document deleted successfully.");
      await loadDocuments();
    } catch (error) {
      setMessage(error.message);
    }
  }

  // GRANT DOCUMENT ACCESS
  async function grantAccess(documentId) {
    if (!shareEmail.trim()) {
      setMessage("Enter the recipient's email address.");
      return;
    }

    try {
      await apiRequest(`/permissions/${documentId}/grant`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: shareEmail.trim(),
          permission: sharePermission,
        }),
      });

      setMessage(`Access granted to ${shareEmail}!`);
      setShareEmail("");
      setSharePermission("read");
      setSharingDocumentId(null);
      await loadDocuments();
    } catch (error) {
      setMessage(error.message);
    }
  }

  // LOGOUT
  function logout() {
    localStorage.removeItem("token");

    setToken("");
    setUser(null);
    setDocuments([]);

    setMessage("Logged out.");
  }

  // CHECK EXISTING SESSION
  useEffect(() => {
    if (token) {
      loadUser();
    }

    // Initial session check only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // FRONTEND SEARCH
  const filteredDocuments = documents.filter((doc) =>
    `${doc.title} ${doc.filename} ${doc.category}`
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  // LOGIN / REGISTRATION PAGE
  if (!token || !user) {
    return (
      <main className="auth-page">
        <form className="auth-card" onSubmit={handleAuth}>
          <h1>🔐 TrustVault</h1>

          <p className="subtitle">
            Secure document sharing platform
          </p>

          {isRegister && (
            <>
              <label>Full name</label>

              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter your name"
                required
              />
            </>
          )}

          <label>Email address</label>

          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email"
            required
          />

          <label>Password</label>

          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            required
            minLength={12}
          />

          {message && (
            <p className="message">{message}</p>
          )}

          <button type="submit" disabled={loading}>
            {loading
              ? "Please wait..."
              : isRegister
                ? "Create Account"
                : "Sign In"}
          </button>

          <p className="switch-auth">
            {isRegister
              ? "Already registered?"
              : "New to TrustVault?"}

            <button
              type="button"
              className="text-button"
              onClick={() => {
                setIsRegister(!isRegister);
                setMessage("");
              }}
            >
              {isRegister ? "Sign In" : "Register"}
            </button>
          </p>
        </form>
      </main>
    );
  }

  // DOCUMENT DASHBOARD
  return (
    <main className="dashboard">
      <header className="topbar">
        <div>
          <h1>🔐 TrustVault</h1>
          <p>Secure document sharing platform</p>
        </div>

        <div className="user-info">
          <span>
            {user.name} · {user.role}
          </span>

          <button className="logout" onClick={logout}>
            Logout
          </button>
        </div>
      </header>

      <section className="welcome-card">
        <h2>Document Dashboard</h2>
        <p>Manage your secure documents in one place.</p>
      </section>

      <section className="panel">
        <h2>Upload a Document</h2>

        <form onSubmit={uploadDocument}>
          <label>Document title</label>

          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter document title"
            required
          />

          <label>Category</label>

          <input
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="General"
          />

          <label>
            Select file (PDF, PNG, JPG or TXT)
          </label>

          <input
            id="fileInput"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.txt"
            onChange={(e) =>
              setFile(e.target.files?.[0] || null)
            }
            required
          />

          <button type="submit" disabled={loading}>
            {loading ? "Uploading..." : "Upload Securely"}
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Your Documents</h2>

          <button onClick={() => loadDocuments()}>
            Refresh
          </button>
        </div>

        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search documents..."
        />

        {filteredDocuments.length === 0 ? (
          <p className="empty">No documents found.</p>
        ) : (
          <div className="document-list">
            {filteredDocuments.map((doc) => (
              <article
                className="document-item"
                key={doc.id}
              >
                <div>
                  <h3>{doc.title}</h3>
                  <p>{doc.filename}</p>

                  <small>
                    {doc.category} · Uploaded:{" "}
                    {new Date(
                      doc.uploaded_at
                    ).toLocaleString()}
                  </small>
                </div>

                <div className="document-actions">
                  <button
                    onClick={() =>
                      downloadDocument(doc.id, doc.filename)
                    }
                  >
                    Download
                  </button>

                  {String(doc.owner_id) === String(user.id) && (
  <>
    <button
      className="delete"
      onClick={() => deleteDocument(doc.id)}
    >
      Delete
    </button>

    <button
      type="button"
      onClick={() =>
        setSharingDocumentId(
          sharingDocumentId === doc.id ? null : doc.id
        )
      }
    >
      Share
    </button>

    {sharingDocumentId === doc.id && (
      <div className="share-form">
        <input
          type="email"
          value={shareEmail}
          onChange={(e) => setShareEmail(e.target.value)}
          placeholder="Enter recipient email"
        />

        <select
          value={sharePermission}
          onChange={(e) => setSharePermission(e.target.value)}
        >
          <option value="read">Read only</option>
          <option value="edit">Edit access</option>
        </select>

        <button
          type="button"
          onClick={() => grantAccess(doc.id)}
          disabled={!shareEmail.trim()}
        >
          Grant Access
        </button>
      </div>
    )}
  </>
)}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {user.role === "admin" && (
        <section className="panel">
          <h2>Administrator</h2>

          <p>Administrator account detected.</p>

          <p>
            Activity records are available through the
            protected administrator API.
          </p>
        </section>
      )}

      {message && (
        <p className="message dashboard-message">
          {message}
        </p>
      )}
    </main>
  );
}

export default App;