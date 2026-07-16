export default function FrameWindow({ title, url, onClose }) {
  return <div className="modal-backdrop"><div className="frame-window"><div className="frame-header"><div><div className="frame-kicker">ADAR Portal</div><strong>{title}</strong></div><button onClick={onClose}>חזרה לפורטל</button></div><iframe src={url} title={title} className="frame" allowFullScreen /></div></div>;
}
