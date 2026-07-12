import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getNews, markAllNewsRead, markNewsRead } from "../api/client";
import type { NewsItem } from "../api/types";

// Badging API: mirror the unread count onto the installed app's icon.
// Silently a no-op where unsupported (typed as optional since TS's DOM lib
// may not include it depending on version).
function setAppBadge(count: number) {
  const nav = navigator as Navigator & {
    setAppBadge?: (n: number) => Promise<void>;
    clearAppBadge?: () => Promise<void>;
  };
  if (count > 0) {
    nav.setAppBadge?.(count).catch(() => {});
  } else {
    nav.clearAppBadge?.().catch(() => {});
  }
}

const SUMMARY_LIMIT = 140;

function truncate(text: string, limit: number): string {
  if (text.length <= limit) return text;
  return `${text.slice(0, limit).trimEnd()}…`;
}

export default function NewsPanel() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["news"],
    queryFn: getNews,
    staleTime: 60 * 60 * 1000,
  });

  const markReadMutation = useMutation({
    mutationFn: (id: number) => markNewsRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["news"] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => markAllNewsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["news"] });
    },
  });

  const items = data?.items ?? [];
  const unreadCount = items.filter((i) => !i.read_at).length;

  useEffect(() => {
    setAppBadge(unreadCount);
  }, [unreadCount]);

  function handleItemClick(item: NewsItem) {
    if (item.read_at) return;
    // Fire-and-forget: don't block the outbound navigation on the mutation.
    markReadMutation.mutate(item.id);
  }

  return (
    <aside className="card news-panel">
      <div className="news-panel-header">
        <h2>&gt; ai_news</h2>
        <button
          type="button"
          className="btn-secondary"
          onClick={() => markAllReadMutation.mutate()}
          disabled={markAllReadMutation.isPending || items.length === 0}
        >
          mark all read
        </button>
      </div>
      {isLoading && <p className="inline-status">loading news…</p>}
      {isError && (
        <p className="inline-status error">
          couldn't load news: {(error as Error)?.message ?? "backend unreachable"}
        </p>
      )}
      {!isLoading && !isError && items.length === 0 && (
        <p className="empty-state">no news cached yet.</p>
      )}
      {!isLoading && !isError && items.length > 0 && (
        <ul className="news-log">
          {items.map((item) => (
            <li key={item.id} className="news-item">
              <span className="source-tag">[{item.source}]</span>
              <a
                className={`news-title${item.read_at ? " news-title-read" : ""}`}
                href={item.url}
                target="_blank"
                rel="noreferrer"
                onClick={() => handleItemClick(item)}
              >
                {item.title}
              </a>
              <p className="news-summary muted">{truncate(item.summary, SUMMARY_LIMIT)}</p>
              <span className="news-date muted">{item.published_date}</span>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
