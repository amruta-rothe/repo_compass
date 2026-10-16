# Contributing to RepoCompass 🧭

Thank you for your interest in contributing to **RepoCompass**! We are building a welcoming, gamified, and pedagogically sound environment for open-source developers worldwide.

---

## 🛠️ Development Setup

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/<your-username>/repo_compass.git
   cd repo_compass
   ```

2. **Virtual Environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Setup**:
   ```bash
   cp .env.example .env
   ```
   *(SQLite dev mode is enabled by default if Supabase variables are left empty.)*

5. **Start Local AI (Optional for AI features)**:
   ```bash
   ollama serve
   ollama pull qwen3:4b
   ```

---

## 🧪 Testing Guidelines

Before opening a pull request, run the test suite to ensure all assertions pass:

```bash
pytest app/tests/ -v
```

If adding new features, include corresponding unit tests under `app/tests/`.

---

## 🔒 Security Principles

- **Zero Untrusted Execution**: Never execute repository code directly on host servers.
- **Path Sanitization**: Validate all patch paths against traversal attacks (`../`, `/etc/`, `.git/`, `.env`).
- **No Committed Secrets**: Never commit `.env` or personal access tokens.
- **Idempotency**: All XP and progression records must be idempotent and tamper-proof.

---

## 📥 Submitting Changes

1. Create a descriptive feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Commit changes with clear, structured messages.
3. Push to your fork and submit a Pull Request against `main`.
4. Fill out the PR template with summary, rationale, and verification steps.

Happy hacking! 🚀
