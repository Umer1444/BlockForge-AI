# 🤝 Contributing to BlockForge AI

First off, thank you for considering contributing to **BlockForge AI**! 🎉

We welcome contributions of all kinds, including bug fixes, feature enhancements, documentation improvements, UI/UX updates, performance optimizations, and testing.

Please read this guide before making a contribution to ensure a smooth collaboration process.

---

# 📑 Table of Contents

- Introduction
- Ways to Contribute
- Development Workflow
- Fork & Clone
- Project Setup
- Branch Naming Convention
- Coding Guidelines
- Commit Message Convention
- Pull Request Process
- Reporting Bugs
- Suggesting Features
- Documentation Contributions
- Code of Conduct
- Tips for First-Time Contributors
- FAQs

---

# 🌟 Introduction

BlockForge AI is an open-source AI-powered video watermark removal and enhancement platform built using modern technologies like:

- FastAPI
- Python
- PyTorch
- Next.js
- React
- TypeScript
- Tailwind CSS
- Docker
- Redis

Our goal is to keep the project clean, maintainable, and beginner-friendly.

Every contribution is appreciated.

---

# 💡 Ways to Contribute

You can contribute by:

- 🐞 Fixing bugs
- ✨ Adding new features
- 📖 Improving documentation
- 🎨 Improving UI/UX
- ⚡ Optimizing performance
- 🧪 Writing tests
- 🔧 Refactoring code
- 🌐 Improving accessibility
- 📦 Updating dependencies

---

# 🍴 Fork the Repository

Fork the repository by clicking the **Fork** button on GitHub.

Then clone your fork:

```bash
git clone https://github.com/<your-username>/BlockForge-AI.git
```

Move into the project:

```bash
cd BlockForge-AI
```

Add the original repository:

```bash
git remote add upstream https://github.com/<owner>/BlockForge-AI.git
```

Verify remotes:

```bash
git remote -v
```

---

# ⚙️ Project Setup

## Backend

Navigate to backend:

```bash
cd backend
```

Create virtual environment:

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Frontend

Navigate to frontend:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

or

```bash
yarn install
```

Start development server:

```bash
npm run dev
```

---

# 🌿 Branch Naming Convention

Never work directly on the `main` branch.

Create a new branch:

```bash
git checkout -b feature/add-dark-mode
```

Recommended branch prefixes:

| Prefix | Usage |
|---------|------|
| feature/ | New features |
| fix/ | Bug fixes |
| docs/ | Documentation |
| refactor/ | Code cleanup |
| style/ | UI improvements |
| test/ | Testing |
| chore/ | Maintenance |

Examples:

```text
feature/user-dashboard

fix/login-error

docs/update-readme

style/navbar-animation

refactor/video-processor
```

---

# 💻 Development Workflow

1. Fork the repository.

2. Clone your fork.

3. Create a new branch.

4. Make your changes.

5. Test your code.

6. Commit your changes.

7. Push to your fork.

8. Open a Pull Request.

---

# 📝 Coding Guidelines

## General

- Write clean code.
- Keep functions small.
- Avoid duplicated code.
- Follow existing project structure.
- Use meaningful variable names.
- Remove unused code.
- Comment only where necessary.

---

## Python

- Follow **PEP 8**
- Use type hints whenever possible.
- Keep functions focused.
- Write readable code.

Example:

```python
def process_video(path: str) -> bool:
    return True
```

---

## TypeScript / React

- Use functional components.
- Use hooks appropriately.
- Keep components reusable.
- Avoid unnecessary re-renders.
- Prefer TypeScript types over `any`.

---

## CSS / Tailwind

- Reuse utility classes.
- Keep responsive layouts.
- Maintain design consistency.
- Avoid inline styles unless necessary.

---

# ✅ Commit Message Guidelines

Write meaningful commit messages.

Good examples:

```text
feat: add watermark preview

fix: resolve upload validation issue

docs: update installation guide

style: improve navbar spacing

refactor: simplify processing pipeline

test: add API endpoint tests
```

Avoid messages like:

```text
update

changes

fix

done

final
```

---

# 🔀 Pull Request Guidelines

Before opening a Pull Request:

- Ensure your branch is up to date.
- Resolve merge conflicts.
- Test your changes.
- Update documentation if necessary.
- Keep PRs focused on a single issue.

Your Pull Request should include:

- Clear title
- Detailed description
- Screenshots (if UI changes)
- Linked issue number (if applicable)

Example:

```text
Fixes #42
```

---

# 🐛 Reporting Bugs

Before opening a bug report:

- Check existing issues.
- Verify the bug still exists.

Include:

- Operating System
- Browser (if frontend)
- Steps to reproduce
- Expected behavior
- Actual behavior
- Screenshots (if applicable)

---

# 🚀 Feature Requests

Feature requests should include:

- Problem statement
- Proposed solution
- Expected benefits
- Additional context
- Mockups (optional)

---

# 📖 Documentation Contributions

Documentation improvements are always welcome.

Examples:

- README improvements
- Installation instructions
- API documentation
- Tutorials
- FAQs
- Code comments

---

# 🧪 Testing

Before submitting a Pull Request:

- Verify the project builds successfully.
- Ensure there are no syntax errors.
- Test affected functionality.
- Check for console errors.
- Ensure existing functionality remains unaffected.

---

# 📂 Project Structure

```text
BlockForge-AI
│
├── backend/
├── frontend/
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── ...
```

---

# 📜 Code of Conduct

Please be respectful and professional.

We expect contributors to:

- Be respectful.
- Welcome newcomers.
- Accept constructive feedback.
- Communicate professionally.
- Avoid harassment or discrimination.

---

# 🌱 Tips for First-Time Contributors

- Start with documentation.
- Pick beginner-friendly issues.
- Ask questions if you're stuck.
- Submit small Pull Requests.
- Read existing code before making changes.
- Be patient during code review.

---

# ❓ Frequently Asked Questions

### Can I work on multiple issues?

Yes, but please complete one issue before taking another if possible.

---

### Should I create an issue before making major changes?

Yes. Discuss significant changes with maintainers first.

---

### Can beginners contribute?

Absolutely! Documentation, bug fixes, and UI improvements are excellent starting points.

---

### My Pull Request has conflicts.

Sync your fork:

```bash
git fetch upstream

git checkout main

git merge upstream/main

git push origin main
```

Then rebase your branch if needed.

---

# 🙌 Thank You

Thank you for taking the time to contribute to **BlockForge AI**.

Every contribution—whether it's fixing a typo, improving documentation, reporting bugs, or implementing a new feature—helps make this project better for everyone.

Happy Coding! 🚀