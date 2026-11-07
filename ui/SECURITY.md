# Security Policy for RAGamuffin

- **No external network access** – RAGamuffin does not connect to the internet. It makes no outbound HTTP requests, no telemetry, and no analytics.
- **Local communication only** – The app communicates exclusively with your local Ollama instance (default: `http://localhost:11434`) to generate embeddings and chat responses.
- **No data collection** – All preferences and chat histories are stored locally on your machine (`config.json` and `chat_history.json`). No information ever leaves your computer.
- **No third-party scripts** – The application only runs local Python and Slint code. No external code is downloaded or executed at runtime.
- **No cloud APIs** – RAGamuffin does not store or process any cloud API keys, passwords, or personal information.

# Reporting a Vulnerability
If you discover a possible security issue, please do not create a public issue. Instead, report it privately using GitHub’s built‑in vulnerability reporting.

Go to the **Security** tab of this repository, and click **"Report a vulnerability"**. All reports will be acknowledged within a week, and I’ll work with you to validate and resolve the issue before any public disclosure. Security reports are best done privately to avoid exposing vulnerabilities before a fix is ready.

# Privacy
RAGamuffin respects your privacy – there are no hidden trackers, no usage logging, and no external dependencies that phone home. Your novel and your chats stay on your hard drive.