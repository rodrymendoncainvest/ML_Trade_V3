// ui/src/components/WatchlistPanel.tsx
import { useState } from "react";
import "./WatchlistPanel.css";

import {
  loadWatchlists,
  createList,
  renameList,
  deleteList,
  addTicker,
  removeTicker,
  type Watchlists,
} from "../watchlists";

interface Props {
  current: string;
  onSelect: (ticker: string) => void;
}

export default function WatchlistPanel({ current, onSelect }: Props) {
  const [lists, setLists] = useState<Watchlists>(loadWatchlists());
  const [newListName, setNewListName] = useState("");

  function handleCreate() {
    if (!newListName.trim()) return;
    const updated = createList(newListName.trim());
    setLists(updated);
    setNewListName("");
  }

  function handleDelete(name: string) {
    const updated = deleteList(name);
    setLists(updated);
  }

  function handleRename(name: string) {
    const newName = prompt("Novo nome da lista:", name);
    if (!newName) return;
    const updated = renameList(name, newName.trim());
    setLists(updated);
  }

  function handleAdd(name: string) {
    const updated = addTicker(name, current);
    setLists(updated);
  }

  function handleRemove(name: string, ticker: string) {
    const updated = removeTicker(name, ticker);
    setLists(updated);
  }

  return (
    <div className="wl-wrapper">

      {/* Header */}
      <div className="wl-header">
        <h2>Watchlists</h2>
      </div>

      {/* Criar nova lista */}
      <div className="wl-newlist">
        <input
          className="wl-input"
          placeholder="Nova lista…"
          value={newListName}
          onChange={(e) => setNewListName(e.target.value)}
        />
        <button className="wl-btn" onClick={handleCreate}>
          Criar
        </button>
      </div>

      {/* Listas */}
      <div className="wl-lists">
        {Object.entries(lists).map(([name, tickers]) => (
          <div key={name} className="wl-block">

            <div className="wl-block-header">
              <span className="wl-block-title">{name}</span>

              <div className="wl-block-actions">
                <button
                  className="wl-icon-btn"
                  onClick={() => handleRename(name)}
                  title="Renomear lista"
                >
                  ✎
                </button>

                <button
                  className="wl-icon-btn"
                  onClick={() => handleDelete(name)}
                  title="Apagar lista"
                >
                  🗑
                </button>

                <button
                  className="wl-add-btn"
                  onClick={() => handleAdd(name)}
                >
                  + {current}
                </button>
              </div>
            </div>

            <ul className="wl-tickers">
              {tickers.map((ticker) => (
                <li
                  key={ticker}
                  className={`wl-ticker ${ticker === current ? "active" : ""}`}
                >
                  <span className="wl-ticker-name" onClick={() => onSelect(ticker)}>
                    {ticker}
                  </span>

                  <button
                    className="wl-remove-ticker"
                    onClick={() => handleRemove(name, ticker)}
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>

          </div>
        ))}
      </div>
    </div>
  );
}
