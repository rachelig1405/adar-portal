export default function StatCard({ icon, number, label, color="blue" }) {
  return <div className={`stat-card ${color}`}><div className="stat-icon">{icon}</div><div><div className="stat-number">{number}</div><div className="stat-label">{label}</div></div></div>;
}
