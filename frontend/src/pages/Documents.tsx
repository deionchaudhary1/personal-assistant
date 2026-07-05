import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createDocument,
  deleteDocument,
  getDocuments,
  queryDocuments,
} from "../api/client";
import type { DocumentQueryResult } from "../api/types";

export default function Documents() {
  const queryClient = useQueryClient();
  const { data: documents, isLoading, isError, error } = useQuery({
    queryKey: ["documents"],
    queryFn: getDocuments,
  });

  const [name, setName] = useState("");
  const [text, setText] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<DocumentQueryResult | null>(null);

  const uploadMutation = useMutation({
    mutationFn: () => createDocument(name, text),
    onSuccess: () => {
      setName("");
      setText("");
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteDocument(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  const queryMutation = useMutation({
    mutationFn: (q: string) => queryDocuments(q),
    onSuccess: (res) => setAnswer(res),
  });

  function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !text.trim()) return;
    uploadMutation.mutate();
  }

  function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setAnswer(null);
    queryMutation.mutate(question);
  }

  const is503 = (queryMutation.error as (Error & { status?: number }) | null)?.status === 503;

  return (
    <div className="page documents-page">
      <div className="page-header">
        <h1>Documents</h1>
      </div>

      <section className="card">
        <h2>Upload document</h2>
        <p className="hint">v1 is paste-only — paste the document's text below.</p>
        <form onSubmit={handleUpload}>
          <div className="form-row">
            <label>
              Name
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Document name"
                required
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              Text
              <textarea
                rows={8}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste document text here…"
                required
              />
            </label>
          </div>
          <div className="form-actions">
            <button
              type="submit"
              className="btn-primary"
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending ? "Uploading…" : "Upload"}
            </button>
          </div>
        </form>
        {uploadMutation.isError && (
          <p className="inline-status error">
            {(uploadMutation.error as Error)?.message ?? "Failed to upload document"}
          </p>
        )}
      </section>

      <section className="card">
        <h2>Existing documents</h2>
        {isLoading && <p className="inline-status">Loading documents…</p>}
        {isError && (
          <p className="inline-status error">
            Couldn't load documents: {(error as Error)?.message ?? "backend unreachable"}
          </p>
        )}
        {documents && documents.length === 0 && (
          <p className="empty-state">No documents yet — upload one above.</p>
        )}
        {documents && documents.length > 0 && (
          <ul className="documents-list">
            {documents.map((d) => (
              <li key={d.id}>
                <span className="doc-name">{d.name}</span>
                <span className="muted">{d.num_chunks} chunks</span>
                <button
                  className="btn-x"
                  aria-label="Delete document"
                  onClick={() => deleteMutation.mutate(d.id)}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2>Ask your documents</h2>
        <form onSubmit={handleAsk} className="inline-form">
          <input
            type="text"
            placeholder="Ask a question about your documents…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button
            type="submit"
            className="btn-primary"
            disabled={queryMutation.isPending || !question.trim()}
          >
            {queryMutation.isPending ? "Asking…" : "Ask"}
          </button>
        </form>
        {queryMutation.isError && is503 && (
          <p className="inline-status error">
            Local AI (Ollama) is not reachable.
          </p>
        )}
        {queryMutation.isError && !is503 && (
          <p className="inline-status error">
            {(queryMutation.error as Error)?.message ?? "Failed to query documents"}
          </p>
        )}
        {answer && (
          <div className="answer-panel">
            <p className="answer-text">{answer.answer}</p>
            {answer.sources.length > 0 && (
              <div className="sources">
                <h3>Sources</h3>
                {answer.sources.map((s, i) => (
                  <blockquote key={i}>
                    <p>{s.snippet}</p>
                    <cite>{s.document_name}</cite>
                  </blockquote>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
