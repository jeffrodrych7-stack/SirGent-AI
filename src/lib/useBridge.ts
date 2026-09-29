import { useSyncExternalStore } from "react";
import { bridge } from "./bridge";

export function useBridge() {
  return useSyncExternalStore(bridge.subscribe, () => bridge.snap);
}
