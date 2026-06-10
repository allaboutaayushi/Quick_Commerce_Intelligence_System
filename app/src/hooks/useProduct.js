import { useEffect, useState } from "react";

export function useProduct(id) {
  const [state, setState] = useState({ status: "loading", data: null, error: null });

  useEffect(() => {
    if (!id) {
      setState({ status: "empty", data: null, error: null });
      return;
    }
    setState({ status: "loading", data: null, error: null });

    let cancelled = false;
    fetch(`/api/products/${id}`)
      .then((r) => {
        if (r.status === 404) throw new Error("Product not found");
        if (!r.ok) throw new Error(`Server error (${r.status})`);
        return r.json();
      })
      .then((data) => {
        if (!cancelled) setState({ status: "success", data, error: null });
      })
      .catch((e) => {
        if (!cancelled) setState({ status: "error", data: null, error: e.message });
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  return state;
}
