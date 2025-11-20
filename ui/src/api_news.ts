// ui/src/api_news.ts
import { API_BASE } from "./api";

export interface NewsItem {
  title: string;
  publisher: string;
  link: string;
  time: number | null;
  type: string;
}

export interface SentimentSummary {
  label: "positive" | "neutral" | "negative";
  count: number;
}

// ---------------------------------------
// FETCH NEWS
// ---------------------------------------
export async function fetchNews(symbol: string): Promise<NewsItem[]> {
  try {
    const res = await fetch(`${API_BASE}/news/items?symbol=${symbol}`);
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.error("Erro news:", err);
    return [];
  }
}

// ---------------------------------------
// FETCH SENTIMENT
// ---------------------------------------
export async function fetchSentiment(symbol: string): Promise<SentimentSummary | null> {
  try {
    const res = await fetch(`${API_BASE}/news/sentiment?symbol=${symbol}`);
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("Erro sentiment:", err);
    return null;
  }
}
