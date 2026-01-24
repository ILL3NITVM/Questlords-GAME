import { ReactNode } from "react";

interface SplitPaneProps {
  left: ReactNode;
  right: ReactNode;
  bottom: ReactNode;
}

export function SplitPane({ left, right, bottom }: SplitPaneProps) {
  return (
    <div className="split-pane">
      <div>{left}</div>
      <div>{right}</div>
      <div className="bottom">{bottom}</div>
    </div>
  );
}
