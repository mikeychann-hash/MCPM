# 🔐 Security Best Practices for MCPM

## ⚠️ CRITICAL: Never Commit Secrets

**NEVER commit the following to git:**
- API keys (OpenAI, Anthropic, X.AI/Grok, etc.)
- GitHub tokens
- `.env` files
- Password files
- Private keys
- Configuration files with secrets

---

## 🔑 Managing API Keys & Tokens

### **Environment Variables (RECOMMENDED)**

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your actual keys:**
   ```bash
   nano .env  # or use your preferred editor
   ```

3. **Verify `.env` is in `.gitignore`:**
   ```bash
   grep "^\.env$" .gitignore
   ```

   If not found, add it:
   ```bash
   echo ".env" >> .gitignore
   ```

4. **Load environment variables in code:**
   ```python
   from dotenv import load_dotenv
   import os

   load_dotenv()
   api_key = os.getenv("XAI_API_KEY")
   ```

### **What Goes Where:**

| Secret Type | Storage Method | Committed to Git? |
|-------------|---------------|-------------------|
| API Keys | `.env` file | ❌ NO |
| GitHub Token | Git credential helper | ❌ NO |
| Config templates | `.env.example` | ✅ YES (no real values) |
| Code | Git repository | ✅ YES |

---

## 🔧 Git Authentication (GitHub Token)

### **Method 1: Git Credential Helper (RECOMMENDED)**

**DO NOT** store GitHub tokens in files. Use git's built-in credential helper:

```bash
# Option A: Store credentials permanently (encrypted on disk)
git config --global credential.helper store

# Option B: Cache credentials for 1 hour
git config --global credential.helper cache --timeout=3600
```

**When you push, git will prompt:**
```
Username: your_github_username
Password: ghp_your_github_token_here
```

Git will remember this and auto-fill on future operations.

### **Method 2: SSH Keys (BEST for frequent use)**

1. **Generate SSH key:**
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

2. **Add to GitHub:**
   - Copy public key: `cat ~/.ssh/id_ed25519.pub`
   - Go to https://github.com/settings/keys
   - Click "New SSH key" and paste

3. **Use SSH remote URLs:**
   ```bash
   git remote set-url origin git@github.com:username/repo.git
   ```

4. **Push without tokens:**
   ```bash
   git push  # Just works!
   ```

### **Method 3: GitHub CLI (gh)**

```bash
# Install GitHub CLI
# macOS: brew install gh
# Linux: https://github.com/cli/cli#installation

# Authenticate
gh auth login

# Git operations now work automatically
git push
```

---

## 🚨 If You've Exposed a Token

### **Immediate Steps:**

1. **Revoke the token immediately:**
   - GitHub: https://github.com/settings/tokens
   - X.AI: https://console.x.ai/
   - OpenAI: https://platform.openai.com/api-keys
   - Anthropic: https://console.anthropic.com/

2. **Check git history for exposed secrets:**
   ```bash
   git log -p | grep -i "api_key\|token\|secret"
   ```

3. **If found in git history, use BFG Repo Cleaner:**
   ```bash
   # Download BFG from https://rtyley.github.io/bfg-repo-cleaner/
   bfg --replace-text passwords.txt your-repo.git
   ```

4. **Rotate all related credentials**

5. **Monitor for unauthorized usage:**
   - Check API usage dashboards
   - Review recent GitHub activity
   - Set up billing alerts

---

## 📋 Security Checklist

### **Before First Commit:**
- [ ] `.env` file exists and contains real secrets
- [ ] `.env` is listed in `.gitignore`
- [ ] `.env.example` exists with placeholder values
- [ ] No hardcoded API keys in code
- [ ] Git credential helper is configured

### **Before Every Commit:**
- [ ] Run `git diff --cached` to review changes
- [ ] No secrets in staged files
- [ ] No `.env` files in staged files
- [ ] No `*.token` or `*.key` files in staged files

### **Regular Maintenance:**
- [ ] Rotate API keys every 90 days
- [ ] Review GitHub token scopes (use minimal permissions)
- [ ] Monitor API usage for anomalies
- [ ] Keep dependencies updated (`pip list --outdated`)

---

## 🔍 Scanning for Secrets

### **Pre-commit Hook (Automated)**

Install `detect-secrets`:
```bash
pip install detect-secrets
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

Install pre-commit:
```bash
pre-commit install
```

### **Manual Scan:**

```bash
# Scan repository for secrets
detect-secrets scan --all-files

# Scan specific file
detect-secrets scan path/to/file.py
```

---

## 🛡️ Environment-Specific Configurations

### **Development (.env.local)**
```bash
XAI_API_KEY=dev_key_here
API_HOST=127.0.0.1
API_PORT=8456
API_RELOAD=true
CORS_ORIGINS=*
```

### **Production (.env.production)**
```bash
XAI_API_KEY=prod_key_here
API_HOST=0.0.0.0
API_PORT=8456
API_RELOAD=false
CORS_ORIGINS=https://yourdomain.com
```

**Load specific environment:**
```python
from dotenv import load_dotenv
import os

# Load environment-specific file
env_file = ".env.production" if os.getenv("ENV") == "production" else ".env.local"
load_dotenv(env_file)
```

---

## 📞 Reporting Security Issues

If you discover a security vulnerability in MCPM:

1. **DO NOT** open a public GitHub issue
2. Email the maintainer directly (if available)
3. Provide detailed description of the vulnerability
4. Allow time for a fix before public disclosure

---

## 🔗 Additional Resources

- [GitHub Token Best Practices](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [OWASP Secret Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Python dotenv Documentation](https://github.com/theskumar/python-dotenv)
- [Git Credential Storage](https://git-scm.com/book/en/v2/Git-Tools-Credential-Storage)

---

## ✅ Summary

**DO:**
- ✅ Use environment variables (`.env` files)
- ✅ Use git credential helpers for GitHub auth
- ✅ Add `.env` to `.gitignore`
- ✅ Use `.env.example` for documentation
- ✅ Rotate secrets regularly
- ✅ Use minimal permission scopes

**DON'T:**
- ❌ Commit `.env` files to git
- ❌ Hardcode secrets in source code
- ❌ Share tokens in chat/email/screenshots
- ❌ Use overly permissive token scopes
- ❌ Store tokens in plain text files in the repo
- ❌ Commit files with real secrets

---

**Remember:** Security is not a one-time setup, it's an ongoing practice. Stay vigilant! 🛡️
