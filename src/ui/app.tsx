import { useMemo } from "react";
import { ButtonBar } from "./components/ButtonBar";
import { EditorPanel } from "./panels/EditorPanel";
import { DebugPanel } from "./panels/DebugPanel";
import { MemoryPanel } from "./panels/MemoryPanel";
import { DisasmPanel } from "./panels/DisasmPanel";
import { TracePanel } from "./panels/TracePanel";
import { BusPanel } from "./panels/BusPanel";
import { ProjectPanel } from "./panels/ProjectPanel";
import { SettingsPanel } from "./panels/SettingsPanel";
import { SplitPane } from "./components/SplitPane";

export function App() {
  const status = useMemo(
    () => ({
      project: "Milestone 1: Core CPU + Memory",
      status: "Idle"
    }),
    []
  );

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>6502 Emulator IDE</h1>
          <p>Core CPU scaffolding with a production-ready architecture.</p>
        </div>
        <ButtonBar status={status} />
      </header>
      <main className="app-body">
        <SplitPane
          left={
            <section className="panel-stack">
              <ProjectPanel />
              <EditorPanel />
            </section>
          }
          right={
            <section className="panel-stack">
              <DebugPanel />
              <DisasmPanel />
              <MemoryPanel />
            </section>
          }
          bottom={
            <section className="panel-stack bottom-panels">
              <TracePanel />
              <BusPanel />
              <SettingsPanel />
            </section>
          }
        />
      </main>
    </div>
  );
}
