interface ButtonBarProps {
  status: {
    project: string;
    status: string;
  };
}

export function ButtonBar({ status }: ButtonBarProps) {
  return (
    <div className="button-bar">
      <button type="button">Assemble</button>
      <button type="button">Run</button>
      <button type="button" className="secondary">
        Pause
      </button>
      <div>
        <strong>{status.project}</strong>
        <div>{status.status}</div>
      </div>
    </div>
  );
}
