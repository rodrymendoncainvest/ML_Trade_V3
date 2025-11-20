// ui/src/components/NewsPanel.tsx
import { useEffect, useState } from "react";
import "./NewsPanel.css";
import {
  fetchNews,
  fetchSentiment,
  type NewsItem,
  type SentimentSummary,
} from "../api_news";

interface Props {
  symbol: string;
}

export default function NewsPanel({ symbol }: Props) {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [sentiment, setSentiment] = useState<SentimentSummary | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const [n, s] = await Promise.all([
        fetchNews(symbol),
        fetchSentiment(symbol),
      ]);
      setNews(n);
      setSentiment(s);
      setLoading(false);
    }
    load();
  }, [symbol]);

  function sentimentColor(label: string) {
    if (label === "positive") return "#22c55e";
    if (label === "negative") return "#ef4444";
    return "#eab308";
  }

  function fmt(time: string | number | null) {
    if (!time) return "-";
    const d = new Date(time);
    if (isNaN(d.getTime())) return "-";
    return d.toLocaleString();
  }

  return (
    <div className="news-box">
      <div className="news-title">Notícias & Sentimento</div>

      <div className="sentiment-row">
        <span>Sentimento geral:</span>
        <strong
          style={{
            color: sentiment ? sentimentColor(sentiment.label) : "#888",
          }}
        >
          {sentiment ? sentiment.label : "-"}
        </strong>
      </div>

      {loading && <div className="loading">A carregar...</div>}

      <div className="news-list">
        {news.slice(0, 6).map((n, i) => (
          <a
            key={i}
            href={n.link}
            target="_blank"
            rel="noopener noreferrer"
            className="news-item"
          >
            <div className="news-headline">{n.title}</div>

            <div className="news-meta">
              <span>{n.publisher || "—"}</span>
              <span>{fmt(n.time)}</span>
            </div>
          </a>
        ))}

        {news.length === 0 && !loading && (
          <div className="empty">Sem notícias recentes.</div>
        )}
      </div>
    </div>
  );
}
