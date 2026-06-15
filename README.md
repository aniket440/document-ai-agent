# Document AI Agent

A Streamlit app for document summarization using **GitHub Models** (free LLM).

## Features
- Upload PDF, DOCX, TXT, and Markdown files
- AI-powered document summarization
- **Free** - Uses GitHub Models API
- Support for large documents (automatic chunking)

## Setup

### 1. Get a GitHub Token
1. Go to [GitHub Personal Access Tokens](https://github.com/settings/tokens)
2. Click "Generate new token" → "Generate new token (classic)"
3. Select scope: `read:user` (minimal permissions needed)
4. Copy the token

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the App
```bash
export GITHUB_TOKEN="your_github_token_here"
streamlit run app.py
```

Or on Windows:
```bash
set GITHUB_TOKEN=your_github_token_here
streamlit run app.py
```

## Available Models
- `gpt-4o-mini` - GPT-4 optimized mini version
- `gpt-3.5-turbo` - GPT-3.5 Turbo
- `mistral-small` - Mistral Small
- `mistral-large` - Mistral Large
- `phi-4` - Microsoft Phi-4

All models are free to use via GitHub Models API.