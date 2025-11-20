// ui/src/components/RightPane.tsx
import "./RightPane.css";

export default function RightPane({
  width,
  snapshot,
  onSnapshot,
  onTrain,
  symbol,
  tf,
}: any) {
  return (
    <div className="right-pane" style={{ width }}>
      <h2 className="panel-title">Model Snapshot</h2>

      <div className="snapshot-row">
        <span>Prob. Up:</span>
        <strong>
          {snapshot?.prob_up != null
            ? (snapshot.prob_up * 100).toFixed(1) + "%"
            : "-"}
        </strong>
      </div>

      <div className="snapshot-row">
        <span>Sinal:</span>
        <strong>{snapshot?.signal ?? "-"}</strong>
      </div>

      <div className="snapshot-row">
        <span>Last Close:</span>
        <strong>{snapshot?.last_close ?? "-"}</strong>
      </div>

      <button onClick={onSnapshot}>Atualizar Snapshot</button>
      <button onClick={onTrain}>Reentreinar</button>
    </div>
  );
}
