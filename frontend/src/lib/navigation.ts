import type { NavigateFunction, To } from "react-router-dom";

export function goBackOr(nav: NavigateFunction, fallback: To) {
  if (window.history.length > 1) {
    nav(-1);
  } else {
    nav(fallback);
  }
}
