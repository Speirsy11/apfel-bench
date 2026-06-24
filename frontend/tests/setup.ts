import "@testing-library/jest-dom/vitest";

// jsdom provides localStorage in modern versions, but provide a defensive
// stub in case the test environment is misconfigured.
if (typeof globalThis.localStorage === "undefined") {
  const store = new Map<string, string>();
  // @ts-expect-error - minimal localStorage stub for tests
  globalThis.localStorage = {
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    setItem: (k: string, v: string) => { store.set(k, v); },
    removeItem: (k: string) => { store.delete(k); },
    clear: () => { store.clear(); },
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    get length() { return store.size; },
  };
}
