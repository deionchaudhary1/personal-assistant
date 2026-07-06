import { useQuery } from "@tanstack/react-query";
import { getNews } from "../api/client";

const SUMMARY_LIMIT = 140;

function truncate(text: string, limit: number): string {
  if (text.length <= limit) return text;
  return `${text.slice(0, limit).trimEnd()}…`;
}

export default function NewsPanel() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["news"],
    queryFn: getNews,
    staleTime: 60 * 60 * 1000,
  });

  const items = data?.items ?? [];

  return (
    <aside className="card news-panel">
      <h2>&gt; ai_news</h2>
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
            <li key={item.url} className="news-item">
              <a
                className="news-title"
                href={item.url}
                target="_blank"
                rel="noreferrer"
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
