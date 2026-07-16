export default function ActionCard({ item, onClick }) {
  return <button className={`action-card ${item.color}`} onClick={onClick}><div className="action-icon">{item.icon}</div><div className="action-title">{item.title}</div>{item.subtitle && <div className="action-subtitle">{item.subtitle}</div>}</button>;
}
