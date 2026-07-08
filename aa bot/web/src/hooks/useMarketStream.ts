import { useCallback, useEffect, useRef, useState } from "react";
import type { ProductPlan, ProductState } from "../types";

export function useMarketStream() {
  const [states, setStates] = useState<Record<string, ProductState>>({});
  const [connected, setConnected] = useState(false);
  const reconnectRef = useRef<number | null>(null);

  const merge = useCallback((state: ProductState) => {
    setStates((current) => ({ ...current, [state.productId]: state }));
  }, []);

  useEffect(() => {
    let disposed = false;
    fetch("/api/products").then((response) => response.json()).then((items: ProductState[]) => {
      if (!disposed) setStates(Object.fromEntries(items.map((item) => [item.productId, item])));
    }).catch(() => undefined);

    const connect = () => {
      const protocol = location.protocol === "https:" ? "wss:" : "ws:";
      const socket = new WebSocket(`${protocol}//${location.host}/stream`);
      socket.onopen = () => setConnected(true);
      socket.onmessage = (message) => {
        const event = JSON.parse(message.data) as { type: string; payload: ProductState | ProductState[] };
        if (event.type === "snapshot" && Array.isArray(event.payload)) {
          setStates(Object.fromEntries(event.payload.map((item) => [item.productId, item])));
        }
        if (event.type === "state" && !Array.isArray(event.payload)) merge(event.payload);
      };
      socket.onclose = () => {
        setConnected(false);
        if (!disposed) reconnectRef.current = window.setTimeout(connect, 1_500);
      };
      socket.onerror = () => socket.close();
      return socket;
    };
    const socket = connect();
    return () => {
      disposed = true;
      socket.close();
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };
  }, [merge]);

  const savePlan = useCallback(async (plan: ProductPlan) => {
    const response = await fetch(`/api/products/${plan.productId}/plan`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(plan)
    });
    const body = await response.json();
    if (!response.ok) throw new Error(typeof body.error === "string" ? body.error : "Plan validation failed");
    merge(body as ProductState);
  }, [merge]);

  return { states, connected, savePlan };
}
