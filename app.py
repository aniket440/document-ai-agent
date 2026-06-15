import io
import os
from pathlib import Path

import streamlit as st
from PyPDF2 import PdfReader
from docx import Document

try:
    from openai import OpenAI
    openai_module = None
    has_openai_class = True
except ImportError:
    import openai as openai_module
    OpenAI = None
    has_openai_class = False

openai_client = None

SUPPORTED_TYPES = {
    ".pdf": "PDF",
    ".txt": "Text",
    ".md": "Markdown",
    ".docx": "Word",
}


def read_pdf(file_data: io.BytesIO) -> str:
    reader = PdfReader(file_data)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages).strip()


def read_docx(file_data: io.BytesIO) -> str:
    file_data.seek(0)
    document = Document(file_data)
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    return "\n\n".join(paragraphs).strip()


def read_text(file_data: io.BytesIO) -> str:
    file_data.seek(0)
    raw = file_data.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="ignore")
    return text.strip()


def split_text(text: str, max_chars: int = 3000) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks = []
    current = []
    current_len = 0

    for paragraph in paragraphs:
        if current_len + len(paragraph) + 1 > max_chars and current:
            chunks.append("\n".join(current).strip())
            current = [paragraph]
            current_len = len(paragraph)
        else:
            current.append(paragraph)
            current_len += len(paragraph) + 1

    if current:
        chunks.append("\n".join(current).strip())

    return chunks


def create_openai_client() -> object:
    global openai_client

    if openai_client is not None:
        return openai_client

    api_key = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not api_key:
        raise RuntimeError(
            "GitHub token is not configured. Set GITHUB_TOKEN or GH_TOKEN environment variable."
        )

    if has_openai_class and OpenAI is not None:
        openai_client = OpenAI(
            api_key=api_key,
            base_url="https://models.inference.ai.azure.com",
        )
    else:
        openai_module.api_key = api_key
        openai_client = openai_module

    return openai_client


def create_chat_completion(model: str, messages: list[dict], temperature: float = 0.2) -> str:
    client = create_openai_client()

    if hasattr(client, "chat"):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content

    if hasattr(client, "ChatCompletion"):
        response = client.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0]["message"]["content"]

    raise RuntimeError("OpenAI client is not configured correctly.")


def summarize_chunk(text: str, model: str) -> str:
    prompt = (
        "You are a helpful assistant that summarizes documents clearly and concisely. "
        "For the text below, provide a short summary that highlights the main points, important findings, and any key recommendations. "
        "Use plain language and keep the output easy to scan.\n\n"
        f"Text:\n{text.strip()}"
    )
    messages = [
        {"role": "system", "content": "You summarize documents for business and technical users."},
        {"role": "user", "content": prompt},
    ]
    return create_chat_completion(model=model, messages=messages)


def summarize_document(text: str, model: str) -> str:
    chunks = split_text(text, max_chars=3000)
    if not chunks:
        return "No readable text was found in the uploaded file."

    if len(chunks) == 1:
        return summarize_chunk(chunks[0], model)

    summaries = []
    for idx, chunk in enumerate(chunks, start=1):
        summaries.append(summarize_chunk(chunk, model))

    combined = "\n\n".join(summaries)
    final_prompt = (
        "You are a helpful assistant that synthesizes summaries. "
        "Combine the following chunk summaries into a single cohesive document summary. "
        "Keep the output concise, preserve key points, and remove duplication.\n\n"
        f"Chunk summaries:\n{combined}"
    )
    final_messages = [
        {"role": "system", "content": "You synthesize multiple summaries into one clean final summary."},
        {"role": "user", "content": final_prompt},
    ]
    return create_chat_completion(model=model, messages=final_messages)


def load_document(file) -> tuple[str, str]:
    suffix = Path(file.name).suffix.lower()
    if suffix == ".pdf":
        return read_pdf(io.BytesIO(file.read())), "PDF"
    if suffix == ".docx":
        return read_docx(io.BytesIO(file.read())), "Word"
    if suffix in {".txt", ".md"}:
        return read_text(io.BytesIO(file.read())), SUPPORTED_TYPES.get(suffix, "Text")

    raise ValueError(f"Unsupported file type: {suffix}")


def is_api_key_configured() -> bool:
    return bool(os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN"))


def main() -> None:
    st.set_page_config(page_title="Gen AI Document Reader", page_icon="📄")
    st.title("Gen AI Document Reader & Summarizer")
    st.write(
        "Upload a document and get a concise, AI-generated summary. "
        "Supports PDF, DOCX, TXT, and Markdown files."
    )

    if not is_api_key_configured():
        st.error(
            "GitHub token is required. Set the environment variable `GITHUB_TOKEN` or `GH_TOKEN` before running this app. "
            "Get a token from https://github.com/settings/tokens"
        )
        st.stop()

    uploaded_file = st.file_uploader(
        "Choose a document file to summarize",
        type=[ext.lstrip(".") for ext in SUPPORTED_TYPES],
    )

    model = st.selectbox(
        "GitHub Models",
        ["gpt-4o-mini", "gpt-3.5-turbo", "mistral-small", "mistral-large", "phi-4"],
        index=0,
        help="Choose a model. All models are free via GitHub.",
    )

    if uploaded_file is not None:
        try:
            with st.spinner("Reading document..."):
                text, file_type = load_document(uploaded_file)

            if not text:
                st.warning("The document contained no visible text to summarize.")
                return

            st.success(f"Loaded {file_type} document successfully.")
            st.markdown(f"**Extracted text length:** {len(text)} characters")
            st.button("Show extracted text")
            if st.expander("Preview extracted text").button("Toggle preview"):
                st.text_area("Document text preview", text[:10000], height=300)

            if st.button("Summarize document"):
                with st.spinner("Generating summary..."):
                    summary = summarize_document(text, model=model)
                st.subheader("Summary")
                st.write(summary)

        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"An error occurred while processing the document: {exc}")


if __name__ == "__main__":
    main()
