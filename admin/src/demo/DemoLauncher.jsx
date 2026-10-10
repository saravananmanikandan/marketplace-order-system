import { useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { fetchSimulatorConfig } from "./demoApi.js";
import SimulatorDrawer from "./SimulatorDrawer.jsx";
import "./demo.css";

const SIMULATOR_CONFIG_QUERY_KEY = ["demo-simulator-config"];

export default function DemoLauncher() {
  const launcherRef = useRef(null);
  const [isOpen, setIsOpen] = useState(false);
  const [lastOrderIds, setLastOrderIds] = useState(null);
  const config = useQuery({
    queryKey: SIMULATOR_CONFIG_QUERY_KEY,
    queryFn: fetchSimulatorConfig,
    retry: false,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });

  // A 404, a network error or a disabled demo all mean: show nothing.
  if (!config.data?.enabled) return null;

  function close() {
    setIsOpen(false);
    launcherRef.current?.focus();
  }

  return (
    <>
      <button
        ref={launcherRef}
        type="button"
        className="button button-quiet demo-launcher"
        aria-haspopup="dialog"
        onClick={() => setIsOpen(true)}
      >
        Webhook simulator <span className="demo-tag">Demo</span>
      </button>
      {isOpen && (
        <SimulatorDrawer
          config={config.data}
          lastOrderIds={lastOrderIds ?? config.data.last_order_ids}
          onSent={setLastOrderIds}
          onClose={close}
        />
      )}
    </>
  );
}
