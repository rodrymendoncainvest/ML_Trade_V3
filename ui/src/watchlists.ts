// ui/src/watchlists.ts
//--------------------------------------------------------------
// Watchlists Manager (localStorage)
//--------------------------------------------------------------

export interface Watchlists {
  [name: string]: string[]; // "Lista": ["AAPL", "TSLA"]
}

const STORAGE_KEY = "mltrade_watchlists";

// --------------------------------------------------------------
// Load watchlists
// --------------------------------------------------------------
export function loadWatchlists(): Watchlists {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      const initial: Watchlists = { Pesquisas: [] };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(initial));
      return initial;
    }
    return JSON.parse(raw);
  } catch {
    const fallback: Watchlists = { Pesquisas: [] };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(fallback));
    return fallback;
  }
}

// --------------------------------------------------------------
// Save watchlists
// --------------------------------------------------------------
function save(list: Watchlists) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
}

// --------------------------------------------------------------
// Create list
// --------------------------------------------------------------
export function createList(name: string): Watchlists {
  const lists = loadWatchlists();
  if (!lists[name]) lists[name] = [];
  save(lists);
  return lists;
}

// --------------------------------------------------------------
// Rename list
// --------------------------------------------------------------
export function renameList(oldName: string, newName: string): Watchlists {
  const lists = loadWatchlists();
  if (!lists[oldName]) return lists;
  if (lists[newName]) return lists;

  lists[newName] = lists[oldName];
  delete lists[oldName];

  save(lists);
  return lists;
}

// --------------------------------------------------------------
// Delete list
// --------------------------------------------------------------
export function deleteList(name: string): Watchlists {
  const lists = loadWatchlists();
  if (!lists[name]) return lists;

  delete lists[name];
  save(lists);
  return lists;
}

// --------------------------------------------------------------
// Add ticker to list
// --------------------------------------------------------------
export function addTicker(listName: string, ticker: string): Watchlists {
  const lists = loadWatchlists();
  if (!lists[listName]) lists[listName] = [];
  if (!lists[listName].includes(ticker)) lists[listName].push(ticker);

  save(lists);
  return lists;
}

// --------------------------------------------------------------
// Remove ticker
// --------------------------------------------------------------
export function removeTicker(listName: string, ticker: string): Watchlists {
  const lists = loadWatchlists();
  if (!lists[listName]) return lists;

  lists[listName] = lists[listName].filter((t) => t !== ticker);

  save(lists);
  return lists;
}
