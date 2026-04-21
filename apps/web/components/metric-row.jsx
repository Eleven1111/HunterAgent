export function MetricRow({ items }) {
  return (
    <div className="metric-row">
      {items.map((item) => (
        <div className="metric" key={item.label}>
          <div className="metric-label">{item.label}</div>
          <div className="metric-value">{item.value}</div>
          <div className="metric-foot">{item.foot}</div>
        </div>
      ))}
    </div>
  );
}

